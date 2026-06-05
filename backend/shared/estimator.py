"""
Cargo-tonnage estimator.

Formula:
    load_ratio = clamp(current_draught / design_draught, 0, 1)
    estimated_tonnes = dwt * load_ratio

Confidence heuristic:
    - 'high'   when all three inputs present and load_ratio in [0.85, 1.0] (clearly laden)
                or in [0.30, 0.55] (clearly ballast)
    - 'medium' when all three inputs present, ratio in between
    - 'low'    when load_ratio falls outside [0, 1] before clamp
    - 'none'   when any input is missing
"""

from __future__ import annotations

from decimal import Decimal


def _as_float(x: float | int | Decimal | None) -> float | None:
    if x is None:
        return None
    return float(x)


def estimate_cargo(
    dwt: int | None,
    design_draught_m: float | Decimal | None,
    current_draught_m: float | Decimal | None,
) -> tuple[int | None, str]:
    """Return (estimated_tonnes, confidence)."""
    design = _as_float(design_draught_m)
    current = _as_float(current_draught_m)

    if dwt is None or design is None or current is None or design <= 0:
        return None, "none"

    raw_ratio = current / design
    confidence = "low" if (raw_ratio < 0 or raw_ratio > 1.0) else "medium"
    ratio = max(0.0, min(1.0, raw_ratio))

    if confidence == "medium" and (0.85 <= ratio <= 1.0 or 0.30 <= ratio <= 0.55):
        confidence = "high"

    tonnes = int(round(dwt * ratio))
    return tonnes, confidence
