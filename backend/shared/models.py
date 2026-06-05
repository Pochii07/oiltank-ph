from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Integer, Numeric, SmallInteger, Text, TIMESTAMP, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class VesselMaster(Base):
    __tablename__ = "vessel_master"

    imo: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text)
    subtype: Mapped[str] = mapped_column(Text, nullable=False)
    dwt: Mapped[int | None] = mapped_column(Integer)
    design_draught_m: Mapped[Decimal | None] = mapped_column(Numeric)
    length_m: Mapped[Decimal | None] = mapped_column(Numeric)
    width_m: Mapped[Decimal | None] = mapped_column(Numeric)
    flag: Mapped[str | None] = mapped_column(Text)
    year_built: Mapped[int | None] = mapped_column(SmallInteger)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))


class Vessel(Base):
    __tablename__ = "vessels"

    mmsi: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    imo: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("vessel_master.imo"))
    name: Mapped[str | None] = mapped_column(Text)
    ship_type: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    subtype: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    flag: Mapped[str | None] = mapped_column(Text)
    length_m: Mapped[Decimal | None] = mapped_column(Numeric)
    width_m: Mapped[Decimal | None] = mapped_column(Numeric)
    current_draught_m: Mapped[Decimal | None] = mapped_column(Numeric)
    first_seen: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    last_seen: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    enriched_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    master: Mapped[VesselMaster | None] = relationship(VesselMaster, lazy="joined")


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    mmsi: Mapped[int] = mapped_column(BigInteger, ForeignKey("vessels.mmsi"), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    sog: Mapped[float | None] = mapped_column(Float)
    cog: Mapped[float | None] = mapped_column(Float)
    heading: Mapped[float | None] = mapped_column(Float)
    nav_status: Mapped[int | None] = mapped_column(SmallInteger)
    draught_m: Mapped[Decimal | None] = mapped_column(Numeric)
    reported_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
