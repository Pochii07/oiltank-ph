"""
Daily AIS ingestion job.

Reads env:
    AISSTREAM_API_KEY        AISStream.io API key
    PH_BBOX                  "min_lat,min_lon,max_lat,max_lon"
    CAPTURE_MINUTES          int, default 45
    DB_*                     Cloud SQL / DATABASE_URL — handled by shared.db

For each capture window:
    1. Open WebSocket to AISStream filtered to PH bbox.
    2. Track latest ShipStaticData per MMSI (ship type, imo, draught).
    3. For each PositionReport, attach static-cache fields, enrich via vessel_master,
       and buffer.
    4. Flush every 1000 positions or every 5 minutes (whichever first), and once
       more at the end.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from dateutil.parser import isoparse

from ingestor.aisstream import stream_messages
from ingestor.enrich import Enricher
from ingestor.store import PositionInsert, VesselUpsert, write_batch
from shared.db import apply_schema, get_engine


logging.basicConfig(level=logging.INFO, format="%(message)s")
structlog.configure(processors=[structlog.processors.KeyValueRenderer()])
log = structlog.get_logger(__name__)

BATCH_POSITIONS = 1000
FLUSH_INTERVAL_S = 300
TANKER_TYPES = set(range(80, 90))


@dataclass
class StaticInfo:
    imo: int | None = None
    name: str | None = None
    ship_type: int | None = None
    length_m: Decimal | None = None
    width_m: Decimal | None = None
    current_draught_m: Decimal | None = None
    flag: str | None = None


@dataclass
class Buffer:
    vessels_pending: dict[int, VesselUpsert] = field(default_factory=dict)
    positions: list[PositionInsert] = field(default_factory=list)

    def size(self) -> int:
        return len(self.positions)


def parse_bbox(s: str) -> tuple[float, float, float, float]:
    parts = [float(x) for x in s.split(",")]
    if len(parts) != 4:
        raise ValueError(f"PH_BBOX must be 4 floats, got {s!r}")
    return tuple(parts)  # type: ignore[return-value]


def mmsi_to_flag(mmsi: int) -> str | None:
    """Crude MID → ISO country lookup. Returns None for unknown prefixes."""
    if mmsi < 100_000_000:
        return None
    mid = mmsi // 1_000_000
    # Minimal subset relevant to PH oil traffic; expand from a full MID table later.
    table = {
        548: "PH", 538: "MH", 563: "SG", 477: "HK",
        351: "PA", 352: "PA", 353: "PA", 354: "PA",
        412: "CN", 413: "CN", 414: "CN",
        636: "LR", 248: "MT", 215: "CY", 256: "MT",
        232: "GB", 235: "GB", 244: "NL", 245: "NL",
    }
    return table.get(mid)


def update_static(static: dict[int, StaticInfo], msg: dict[str, Any]) -> None:
    body = msg.get("Message", {}).get("ShipStaticData") or {}
    meta = msg.get("MetaData") or {}
    mmsi = meta.get("MMSI") or body.get("UserID")
    if not isinstance(mmsi, int):
        return

    info = static.setdefault(mmsi, StaticInfo())
    if "Type" in body:
        info.ship_type = body["Type"]
    if "ImoNumber" in body:
        imo = body["ImoNumber"]
        info.imo = imo if imo and imo > 0 else None
    if "Name" in body:
        info.name = (body["Name"] or "").strip() or None
    if "MaximumStaticDraught" in body and body["MaximumStaticDraught"]:
        info.current_draught_m = Decimal(str(body["MaximumStaticDraught"]))
    dim = body.get("Dimension") or {}
    if dim:
        a, b, c, d = dim.get("A", 0), dim.get("B", 0), dim.get("C", 0), dim.get("D", 0)
        length = (a or 0) + (b or 0)
        width = (c or 0) + (d or 0)
        if length:
            info.length_m = Decimal(length)
        if width:
            info.width_m = Decimal(width)
    if info.flag is None:
        info.flag = mmsi_to_flag(mmsi)


def reported_at(meta: dict[str, Any]) -> datetime:
    t = meta.get("time_utc")
    if t:
        try:
            return isoparse(t).astimezone(timezone.utc)
        except Exception:
            pass
    return datetime.now(tz=timezone.utc)


def build_position_and_vessel(
    msg: dict[str, Any],
    static: dict[int, StaticInfo],
    enricher: Enricher,
) -> tuple[VesselUpsert, PositionInsert] | None:
    meta = msg.get("MetaData") or {}
    body = msg.get("Message", {}).get("PositionReport") or {}
    mmsi = meta.get("MMSI") or body.get("UserID")
    if not isinstance(mmsi, int):
        return None

    info = static.get(mmsi)
    if info is None or info.ship_type not in TANKER_TYPES:
        return None  # filter out non-tankers / waiting for static data

    master = enricher.lookup(info.imo)
    subtype = master.subtype if master else "unknown"
    enriched_at = datetime.now(tz=timezone.utc) if info.imo else None

    lat = body.get("Latitude")
    lon = body.get("Longitude")
    if lat is None or lon is None:
        return None

    vessel: VesselUpsert = {
        "mmsi": mmsi,
        "imo": info.imo,
        "name": info.name or (meta.get("ShipName") or "").strip() or None,
        "ship_type": info.ship_type,
        "subtype": subtype,
        "flag": info.flag,
        "length_m": info.length_m,
        "width_m": info.width_m,
        "current_draught_m": info.current_draught_m,
        "last_seen": datetime.now(tz=timezone.utc),
        "enriched_at": enriched_at,
    }

    pos: PositionInsert = {
        "mmsi": mmsi,
        "latitude": float(lat),
        "longitude": float(lon),
        "sog": body.get("Sog"),
        "cog": body.get("Cog"),
        "heading": body.get("TrueHeading"),
        "nav_status": body.get("NavigationalStatus"),
        "draught_m": info.current_draught_m,
        "reported_at": reported_at(meta),
    }
    return vessel, pos


async def run() -> int:
    api_key = os.environ["AISSTREAM_API_KEY"]
    bbox = parse_bbox(os.environ.get("PH_BBOX", "4.5,116.5,21.5,127.0"))
    duration = int(os.environ.get("CAPTURE_MINUTES", "45")) * 60

    apply_schema()
    engine = get_engine()
    enricher = Enricher(engine)

    static: dict[int, StaticInfo] = {}
    buf = Buffer()
    last_flush = time.monotonic()

    total_msgs = total_vessels = total_positions = 0

    log.info("ingest.start", bbox=bbox, duration_s=duration)

    async for msg in stream_messages(api_key, bbox, duration):
        total_msgs += 1
        mtype = msg.get("MessageType")
        if mtype == "ShipStaticData":
            update_static(static, msg)
        elif mtype == "PositionReport":
            result = build_position_and_vessel(msg, static, enricher)
            if result is not None:
                vessel, pos = result
                buf.vessels_pending[vessel["mmsi"]] = vessel
                buf.positions.append(pos)

        if buf.size() >= BATCH_POSITIONS or (time.monotonic() - last_flush) >= FLUSH_INTERVAL_S:
            v, p = write_batch(engine, list(buf.vessels_pending.values()), buf.positions)
            total_vessels += v
            total_positions += p
            log.info("ingest.flush", vessels=v, positions=p, total_msgs=total_msgs)
            buf.vessels_pending.clear()
            buf.positions.clear()
            last_flush = time.monotonic()

    v, p = write_batch(engine, list(buf.vessels_pending.values()), buf.positions)
    total_vessels += v
    total_positions += p

    hits, misses = enricher.stats
    log.info(
        "ingest.done",
        messages=total_msgs,
        vessels=total_vessels,
        positions=total_positions,
        enrich_hits=hits,
        enrich_misses=misses,
        tanker_mmsis=sum(1 for v in static.values() if v.ship_type in TANKER_TYPES),
    )
    return 0


def main() -> None:
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
