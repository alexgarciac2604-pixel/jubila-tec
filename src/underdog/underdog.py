"""Underdog Score: empresas castigadas por precio pero sólidas por fundamentos.

Componentes (0-100): valor (earnings yield), calidad (ROE + conversión de caja),
castigo (distancia del máx. 52s — más caída = más potencial SI hay calidad),
giro de momentum (3m recuperando tras 12m débil).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.market_data import get_fundamentals, get_history
from src.fundamental.metrics import analyze


def _clip100(x: float) -> float:
    return float(max(0.0, min(100.0, x)))


def underdog_score(ticker: str) -> dict:
    f = get_fundamentals(ticker)
    m = analyze(f)
    h = get_history(ticker)
    close = h.Close

    ey = m.get("earnings_yield") or 0.0
    value = _clip100(np.tanh(ey * 12) * 100)                     # 8%+ e.y. ≈ tope

    roe = m.get("roe") or 0.0
    conv = m.get("fcf_conversion") or 0.0
    quality = _clip100(50 * np.tanh(roe * 5) + 50 * np.tanh(conv))

    hi52 = float(close.tail(252).max())
    drawdown = 1 - float(close.iloc[-1]) / hi52                   # 0..1
    beaten = _clip100(drawdown * 250)                             # -40% ≈ tope

    mom3 = float(close.iloc[-1] / close.iloc[-63] - 1) if len(close) > 63 else 0.0
    mom12 = float(close.iloc[-1] / close.iloc[-252] - 1) if len(close) > 252 else 0.0
    turn = _clip100(50 + 200 * mom3 - 100 * max(mom12, 0))        # premia giro reciente

    # el castigo solo suma si hay calidad (underdog ≠ value trap)
    beaten_adj = beaten * (quality / 100)
    score = round(0.30 * value + 0.30 * quality + 0.25 * beaten_adj + 0.15 * turn)

    return {
        "ticker": ticker.upper(), "name": f.get("name"), "sector": f.get("sector"),
        "score": score, "value": round(value), "quality": round(quality),
        "beaten": round(beaten), "turnaround": round(turn),
        "drawdown_52w_pct": round(-drawdown * 100, 1),
        "pe": m.get("pe"), "roe": roe,
    }


def scan(universe: list[str]) -> pd.DataFrame:
    rows = []
    for t in universe:
        try:
            rows.append(underdog_score(t))
        except Exception:
            continue
    df = pd.DataFrame(rows)
    return df.sort_values("score", ascending=False).reset_index(drop=True) if len(df) else df
