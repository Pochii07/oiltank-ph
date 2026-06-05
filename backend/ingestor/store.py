"""Batch upsert helpers for the ingestion job."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import text
from sqlalchemy.engine import Engine


class VesselUpsert(TypedDict, total=False):
    mmsi: int
    imo: int | None
    name: str | None
    ship_type: int
    subtype: str
    flag: str | None
    length_m: Decimal | None
    width_m: Decimal | None
    current_draught_m: Decimal | None
    last_seen: datetime
    enriched_at: datetime | None


class PositionInsert(TypedDict, total=False):
    mmsi: int
    latitude: float
    longitude: float
    sog: float | None
    cog: float | None
    heading: float | None
    nav_status: int | None
    draught_m: Decimal | None
    reported_at: datetime


VESSEL_UPSERT_SQL = text(
    """
    INSERT INTO vessels (
        mmsi, imo, name, ship_type, subtype, flag, length_m, width_m,
        current_draught_m, first_seen, last_seen, enriched_at
    ) VALUES (
        :mmsi, :imo, :name, :ship_type, :subtype, :flag, :length_m, :width_m,
        :current_draught_m, :last_seen, :last_seen, :enriched_at
    )
    ON CONFLICT (mmsi) DO UPDATE SET
        imo               = COALESCE(EXCLUDED.imo, vessels.imo),
        name              = COALESCE(EXCLUDED.name, vessels.name),
        ship_type         = EXCLUDED.ship_type,
        subtype           = CASE WHEN EXCLUDED.subtype <> 'unknown'
                                 THEN EXCLUDED.subtype ELSE vessels.subtype END,
        flag              = COALESCE(EXCLUDED.flag, vessels.flag),
        length_m          = COALESCE(EXCLUDED.length_m, vessels.length_m),
        width_m           = COALESCE(EXCLUDED.width_m, vessels.width_m),
        current_draught_m = COALESCE(EXCLUDED.current_draught_m, vessels.current_draught_m),
        last_seen         = GREATEST(vessels.last_seen, EXCLUDED.last_seen),
        enriched_at       = COALESCE(EXCLUDED.enriched_at, vessels.enriched_at);
    """
)


POSITION_INSERT_SQL = text(
    """
    INSERT INTO positions (
        mmsi, latitude, longitude, sog, cog, heading, nav_status, draught_m, reported_at, ingested_at
    ) VALUES (
        :mmsi, :latitude, :longitude, :sog, :cog, :heading, :nav_status, :draught_m, :reported_at, :ingested_at
    )
    ON CONFLICT (mmsi, reported_at) DO NOTHING;
    """
)


def write_batch(
    engine: Engine,
    vessels: list[VesselUpsert],
    positions: list[PositionInsert],
) -> tuple[int, int]:
    """Upsert vessels then insert positions in a single transaction."""
    if not vessels and not positions:
        return 0, 0

    now = datetime.now(tz=timezone.utc)
    for p in positions:
        p.setdefault("ingested_at", now)

    with engine.begin() as conn:
        if vessels:
            conn.execute(VESSEL_UPSERT_SQL, vessels)
        if positions:
            conn.execute(POSITION_INSERT_SQL, positions)

    return len(vessels), len(positions)
