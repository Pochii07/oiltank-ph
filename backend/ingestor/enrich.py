"""
Enrichment: look up an IMO in vessel_master and resolve the subtype.

Caches lookups in memory for the lifetime of a single job run so we hit Postgres
once per IMO, not once per position.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class MasterRecord:
    subtype: str
    dwt: int | None
    design_draught_m: Decimal | None


class Enricher:
    def __init__(self, engine: Engine):
        self._engine = engine
        self._cache: dict[int, MasterRecord | None] = {}

    def lookup(self, imo: int | None) -> MasterRecord | None:
        if imo is None:
            return None
        if imo in self._cache:
            return self._cache[imo]

        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT subtype, dwt, design_draught_m "
                    "FROM vessel_master WHERE imo = :imo"
                ),
                {"imo": imo},
            ).first()

        result = (
            MasterRecord(subtype=row[0], dwt=row[1], design_draught_m=row[2])
            if row is not None
            else None
        )
        self._cache[imo] = result
        return result

    @property
    def stats(self) -> tuple[int, int]:
        """(hits, misses) where hits = imos resolved, misses = imos not in master."""
        hits = sum(1 for v in self._cache.values() if v is not None)
        misses = sum(1 for v in self._cache.values() if v is None)
        return hits, misses
