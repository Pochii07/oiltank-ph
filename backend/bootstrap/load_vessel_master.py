"""
One-off bootstrap: load tanker master data into the `vessel_master` table.

Expected input: a CSV at backend/bootstrap/data/tankers_master.csv with these columns
(case-insensitive headers):

    imo, name, subtype, dwt, design_draught_m, length_m, width_m, flag, year_built

`subtype` must be one of:
    crude_oil | product | chemical | lng | lpg | other

The IMO GISIS export from https://gisis.imo.org/ (Ship & Company particulars module)
provides IMO, name, type, deadweight, length, breadth, flag. A small mapping table
below converts GISIS "Ship type" strings to our `subtype` enum. If your source uses
different labels, edit `SUBTYPE_MAP` or pre-process the CSV.

Usage (local):

    DATABASE_URL="postgresql+pg8000://user:pass@localhost:5432/tankers" \
        python -m bootstrap.load_vessel_master backend/bootstrap/data/tankers_master.csv
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from shared.db import apply_schema, get_engine


SUBTYPE_MAP = {
    # Common labels from IMO/MarineTraffic/Equasis exports → our enum
    "crude oil tanker": "crude_oil",
    "crude/oil products tanker": "crude_oil",
    "oil products tanker": "product",
    "products tanker": "product",
    "oil/chemical tanker": "product",
    "chemical tanker": "chemical",
    "chemical/oil products tanker": "chemical",
    "lng tanker": "lng",
    "lng carrier": "lng",
    "liquefied natural gas tanker": "lng",
    "lpg tanker": "lpg",
    "lpg carrier": "lpg",
    "liquefied petroleum gas tanker": "lpg",
    "bitumen tanker": "other",
    "asphalt tanker": "other",
}


def normalize_subtype(raw: str) -> str:
    key = raw.strip().lower()
    if key in {"crude_oil", "product", "chemical", "lng", "lpg", "other"}:
        return key
    return SUBTYPE_MAP.get(key, "other")


def parse_row(row: dict[str, str]) -> dict | None:
    lower = {k.lower().strip(): v for k, v in row.items()}
    try:
        imo = int(lower["imo"])
    except (KeyError, ValueError):
        return None

    def num(key: str) -> float | None:
        v = lower.get(key, "").strip()
        if not v:
            return None
        try:
            return float(v)
        except ValueError:
            return None

    def integer(key: str) -> int | None:
        v = num(key)
        return int(v) if v is not None else None

    return {
        "imo": imo,
        "name": lower.get("name") or None,
        "subtype": normalize_subtype(lower.get("subtype") or lower.get("type") or ""),
        "dwt": integer("dwt"),
        "design_draught_m": num("design_draught_m") or num("draught"),
        "length_m": num("length_m") or num("length"),
        "width_m": num("width_m") or num("breadth") or num("width"),
        "flag": lower.get("flag") or None,
        "year_built": integer("year_built"),
        "source": "imo_gisis",
        "loaded_at": datetime.now(tz=timezone.utc),
    }


def load_csv(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            parsed = parse_row(raw)
            if parsed:
                rows.append(parsed)
    return rows


UPSERT_SQL = text(
    """
    INSERT INTO vessel_master (
        imo, name, subtype, dwt, design_draught_m, length_m, width_m, flag, year_built, source, loaded_at
    ) VALUES (
        :imo, :name, :subtype, :dwt, :design_draught_m, :length_m, :width_m, :flag, :year_built, :source, :loaded_at
    )
    ON CONFLICT (imo) DO UPDATE SET
        name              = EXCLUDED.name,
        subtype           = EXCLUDED.subtype,
        dwt               = EXCLUDED.dwt,
        design_draught_m  = EXCLUDED.design_draught_m,
        length_m          = EXCLUDED.length_m,
        width_m           = EXCLUDED.width_m,
        flag              = EXCLUDED.flag,
        year_built        = EXCLUDED.year_built,
        source            = EXCLUDED.source,
        loaded_at         = EXCLUDED.loaded_at;
    """
)


def main(csv_path: str) -> None:
    path = Path(csv_path)
    if not path.exists():
        sys.exit(f"CSV not found: {path}")

    apply_schema()
    rows = load_csv(path)
    if not rows:
        sys.exit("No valid rows parsed from CSV.")

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(UPSERT_SQL, rows)

    from collections import Counter
    distribution = Counter(r["subtype"] for r in rows)
    print(f"Loaded {len(rows)} vessel_master rows.")
    for subtype, count in sorted(distribution.items()):
        print(f"  {subtype:12} {count}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m bootstrap.load_vessel_master <path-to-csv>")
    main(sys.argv[1])
