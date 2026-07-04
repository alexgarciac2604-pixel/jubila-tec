"""Stress testing: shocks macro → P&L estimado del portafolio por sector.

Sensibilidades direccionales aproximadas (% de caída/subida por sector ante
cada escenario), calibradas con episodios históricos análogos. Es un mapa de
exposición, no un pronóstico.
"""
from __future__ import annotations

import pandas as pd

from src.config import SECTOR_OF

# % de impacto estimado por sector
SCENARIOS: dict[str, dict[str, float]] = {
    "Tasas +100bp": {
        "Tecnología": -8, "Comunicación": -6, "Consumo Disc.": -5, "Financiero": 2,
        "Salud": -2, "Energía": -1, "Consumo Básico": -2, "Industrial": -3, "Otro": -3,
    },
    "Equity -20% (corrección)": {
        "Tecnología": -26, "Comunicación": -22, "Consumo Disc.": -24, "Financiero": -22,
        "Salud": -14, "Energía": -18, "Consumo Básico": -10, "Industrial": -20, "Otro": -20,
    },
    "Petróleo +30%": {
        "Energía": 18, "Industrial": -4, "Consumo Disc.": -5, "Tecnología": -2,
        "Consumo Básico": -2, "Financiero": -1, "Salud": 0, "Comunicación": -1, "Otro": -1,
    },
    "USD fuerte (+10% DXY)": {
        "Tecnología": -5, "Industrial": -4, "Energía": -4, "Consumo Básico": -2,
        "Salud": -2, "Financiero": 0, "Consumo Disc.": -3, "Comunicación": -3, "Otro": -2,
    },
    "Crisis crédito (tipo 2008)": {
        "Financiero": -45, "Consumo Disc.": -35, "Industrial": -35, "Tecnología": -38,
        "Energía": -30, "Comunicación": -30, "Salud": -20, "Consumo Básico": -15, "Otro": -30,
    },
}


def portfolio_stress(tickers: list[str], weights) -> pd.DataFrame:
    """P&L % estimado del portafolio en cada escenario."""
    rows = []
    for name, impacts in SCENARIOS.items():
        pnl = sum(
            float(w) * impacts.get(SECTOR_OF.get(t.upper(), "Otro"), impacts["Otro"])
            for t, w in zip(tickers, weights)
        )
        worst = min(
            ((t, impacts.get(SECTOR_OF.get(t.upper(), "Otro"), 0)) for t in tickers),
            key=lambda x: x[1],
        )
        rows.append({"Escenario": name, "P&L estimado %": round(pnl, 1),
                     "Más expuesto": f"{worst[0]} ({worst[1]:+.0f}%)"})
    return pd.DataFrame(rows)
