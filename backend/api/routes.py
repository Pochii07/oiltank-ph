"""Public API endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from shared.db import get_engine
from shared.estimator import estimate_cargo


router = APIRouter()


DEFAULT_OIL_SUBTYPES = ("crude_oil", "product")
ALL_SUBTYPES = ("crude_oil", "product", "chemical", "lng", "lpg", "other", "unknown")


class Position(BaseModel):
    latitude: float
    longitude: float
    sog: float | None = None
    cog: float | None = None
    heading: float | None = None
    nav_status: int | None = None
    reported_at: datetime


class VesselSummary(BaseModel):
    mmsi: int
    imo: int | None = None
    name: str | None = None
    subtype: str
    ship_type: int
    flag: str | None = None
    length_m: float | None = None
    width_m: float | None = None
    dwt: int | None = None
    design_draught_m: float | None = None
    current_draught_m: float | None = None
    estimated_cargo_tonnes: int | None = None
    estimate_confidence: str = "none"
    last_seen: datetime
    last_position: Position | None = None


def _parse_subtypes(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return DEFAULT_OIL_SUBTYPES
    parts = tuple(s.strip() for s in raw.split(",") if s.strip())
    invalid = [s for s in parts if s not in ALL_SUBTYPES]
    if invalid:
        raise HTTPException(status_code=400, detail=f"unknown subtypes: {invalid}")
    return parts


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


VESSEL_BASE_SQL = """
    SELECT
        v.mmsi, v.imo, v.name, v.subtype, v.ship_type, v.flag,
        v.length_m, v.width_m, v.current_draught_m, v.last_seen,
        m.dwt, m.design_draught_m,
        p.latitude, p.longitude, p.sog, p.cog, p.heading, p.nav_status, p.reported_at
    FROM vessels v
    LEFT JOIN vessel_master m ON m.imo = v.imo
    LEFT JOIN LATERAL (
        SELECT latitude, longitude, sog, cog, heading, nav_status, reported_at
        FROM positions
        WHERE mmsi = v.mmsi
        ORDER BY reported_at DESC
        LIMIT 1
    ) p ON TRUE
"""


def _row_to_vessel(row) -> VesselSummary:
    cargo, confidence = estimate_cargo(row.dwt, row.design_draught_m, row.current_draught_m)
    last_position = None
    if row.latitude is not None and row.longitude is not None:
        last_position = Position(
            latitude=row.latitude,
            longitude=row.longitude,
            sog=row.sog,
            cog=row.cog,
            heading=row.heading,
            nav_status=row.nav_status,
            reported_at=row.reported_at,
        )
    return VesselSummary(
        mmsi=row.mmsi,
        imo=row.imo,
        name=row.name,
        subtype=row.subtype,
        ship_type=row.ship_type,
        flag=row.flag,
        length_m=float(row.length_m) if row.length_m is not None else None,
        width_m=float(row.width_m) if row.width_m is not None else None,
        dwt=row.dwt,
        design_draught_m=float(row.design_draught_m) if row.design_draught_m is not None else None,
        current_draught_m=float(row.current_draught_m) if row.current_draught_m is not None else None,
        estimated_cargo_tonnes=cargo,
        estimate_confidence=confidence,
        last_seen=row.last_seen,
        last_position=last_position,
    )


@router.get("/vessels", response_model=list[VesselSummary])
def list_vessels(
    subtype: Annotated[str | None, Query(description="comma-separated subtypes")] = None,
    seen_within_hours: Annotated[int, Query(ge=1, le=24 * 14)] = 48,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> list[VesselSummary]:
    subtypes = _parse_subtypes(subtype)
    since = datetime.now(tz=timezone.utc) - timedelta(hours=seen_within_hours)
    sql = text(
        VESSEL_BASE_SQL
        + " WHERE v.subtype = ANY(:subtypes) AND v.last_seen >= :since"
        " ORDER BY v.last_seen DESC LIMIT :limit"
    )
    with get_engine().connect() as conn:
        rows = conn.execute(
            sql, {"subtypes": list(subtypes), "since": since, "limit": limit}
        ).all()
    return [_row_to_vessel(r) for r in rows]


@router.get("/vessels/{mmsi}", response_model=VesselSummary)
def get_vessel(mmsi: int) -> VesselSummary:
    sql = text(VESSEL_BASE_SQL + " WHERE v.mmsi = :mmsi")
    with get_engine().connect() as conn:
        row = conn.execute(sql, {"mmsi": mmsi}).first()
    if row is None:
        raise HTTPException(status_code=404, detail="vessel not found")
    return _row_to_vessel(row)


@router.get("/vessels/{mmsi}/track", response_model=list[Position])
def get_vessel_track(
    mmsi: int,
    hours: Annotated[int, Query(ge=1, le=24 * 14)] = 24,
) -> list[Position]:
    since = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
    sql = text(
        "SELECT latitude, longitude, sog, cog, heading, nav_status, reported_at "
        "FROM positions WHERE mmsi = :mmsi AND reported_at >= :since "
        "ORDER BY reported_at ASC"
    )
    with get_engine().connect() as conn:
        rows = conn.execute(sql, {"mmsi": mmsi, "since": since}).all()
    return [
        Position(
            latitude=r.latitude,
            longitude=r.longitude,
            sog=r.sog,
            cog=r.cog,
            heading=r.heading,
            nav_status=r.nav_status,
            reported_at=r.reported_at,
        )
        for r in rows
    ]


@router.get("/positions/latest", response_model=list[VesselSummary])
def latest_positions(
    subtype: Annotated[str | None, Query(description="comma-separated subtypes")] = None,
    seen_within_hours: Annotated[int, Query(ge=1, le=24 * 14)] = 48,
    limit: Annotated[int, Query(ge=1, le=2000)] = 1000,
) -> list[VesselSummary]:
    # Same shape as /vessels but ordered by latest position for map rendering.
    subtypes = _parse_subtypes(subtype)
    since = datetime.now(tz=timezone.utc) - timedelta(hours=seen_within_hours)
    sql = text(
        VESSEL_BASE_SQL
        + " WHERE v.subtype = ANY(:subtypes) AND v.last_seen >= :since"
        " ORDER BY p.reported_at DESC NULLS LAST LIMIT :limit"
    )
    with get_engine().connect() as conn:
        rows = conn.execute(
            sql, {"subtypes": list(subtypes), "since": since, "limit": limit}
        ).all()
    return [_row_to_vessel(r) for r in rows]
