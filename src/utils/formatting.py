"""Helpers de formato numérico."""
from __future__ import annotations

import math


def fmt_num(x, decimals: int = 2) -> str:
    """Abrevia números grandes: 1.23T, 45.6B, 789M."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    ax = abs(x)
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if ax >= div:
            return f"{x / div:.{decimals}f}{suf}"
    return f"{x:.{decimals}f}"


def fmt_money(x, decimals: int = 2) -> str:
    return "—" if x is None else f"${fmt_num(x, decimals)}"


def fmt_pct(x, decimals: int = 1, signed: bool = True) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    sign = "+" if signed and x > 0 else ""
    return f"{sign}{x:.{decimals}f}%"


def arrow(x) -> str:
    if x is None:
        return "•"
    return "▲" if x > 0 else ("▼" if x < 0 else "•")
