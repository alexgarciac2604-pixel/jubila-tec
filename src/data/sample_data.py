"""Generador de datos sintéticos deterministas (fallback sin internet).

Cada ticker produce siempre la misma serie (seed = CRC32 del símbolo),
con estados financieros coherentes entre sí (ingresos > EBIT > utilidad, etc.).
"""
from __future__ import annotations

import zlib

import numpy as np
import pandas as pd

from src.config import SECTOR_OF, TICKER_NAMES


def _rng(ticker: str, salt: str = "") -> np.random.Generator:
    seed = zlib.crc32((ticker.upper() + salt).encode()) & 0xFFFFFFFF
    return np.random.default_rng(seed)


def sample_history(ticker: str, days: int = 500) -> pd.DataFrame:
    """OHLCV diario vía GBM con drift/vol propios del ticker."""
    rng = _rng(ticker, "px")
    mu = rng.uniform(-0.05, 0.20) / 252
    vol = rng.uniform(0.15, 0.45) / np.sqrt(252)
    p0 = rng.uniform(15, 480)
    rets = rng.normal(mu, vol, days)
    close = p0 * np.exp(np.cumsum(rets))
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
    spread_h = rng.uniform(0.001, 0.02, days)
    spread_l = rng.uniform(0.001, 0.02, days)
    high = close * (1 + spread_h)
    low = close * (1 - spread_l)
    open_ = low + (high - low) * rng.uniform(0.2, 0.8, days)
    volume = rng.integers(1_000_000, 60_000_000, days).astype(float)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=idx,
    )


def sample_fundamentals(ticker: str) -> dict:
    """Estado financiero sintético coherente + año previo (para forense)."""
    rng = _rng(ticker, "fund")
    g = rng.uniform(-0.05, 0.25)                     # crecimiento YoY
    revenue = rng.uniform(2e9, 4e11)
    gross_margin = rng.uniform(0.25, 0.65)
    gross = revenue * gross_margin
    ebit = gross * rng.uniform(0.35, 0.70)
    net_income = ebit * rng.uniform(0.55, 0.85)
    total_assets = revenue * rng.uniform(0.8, 2.2)
    equity = total_assets * rng.uniform(0.30, 0.60)
    total_liab = total_assets - equity
    total_debt = total_liab * rng.uniform(0.30, 0.60)
    lt_debt = total_debt * rng.uniform(0.6, 0.9)
    cash = total_assets * rng.uniform(0.05, 0.20)
    current_assets = total_assets * rng.uniform(0.25, 0.45)
    current_liab = current_assets * rng.uniform(0.50, 1.10)
    retained = equity * rng.uniform(0.30, 0.80)
    cfo = net_income * rng.uniform(0.90, 1.40)
    capex = revenue * rng.uniform(0.03, 0.08)
    receivables = revenue * rng.uniform(0.08, 0.18)
    depreciation = total_assets * rng.uniform(0.02, 0.05)
    sga = revenue * rng.uniform(0.10, 0.25)
    shares = rng.uniform(3e8, 1.6e10)
    price = float(sample_history(ticker).Close.iloc[-1])

    prev = 1.0 / (1.0 + g)
    return {
        "ticker": ticker.upper(),
        "name": TICKER_NAMES.get(ticker.upper(), ticker.upper()),
        "sector": SECTOR_OF.get(ticker.upper(), "Otro"),
        "source": "sample",
        "price": price,
        "shares": shares,
        "market_cap": price * shares,
        "beta": float(rng.uniform(0.6, 1.8)),
        "dividend_yield": float(rng.uniform(0.0, 0.04)),
        # estado de resultados
        "revenue": revenue, "gross_profit": gross, "ebit": ebit,
        "net_income": net_income, "sga": sga, "depreciation": depreciation,
        # balance
        "total_assets": total_assets, "equity": equity, "total_liabilities": total_liab,
        "total_debt": total_debt, "lt_debt": lt_debt, "cash": cash,
        "current_assets": current_assets, "current_liabilities": current_liab,
        "retained_earnings": retained, "receivables": receivables,
        # flujo
        "cfo": cfo, "capex": capex, "fcf": cfo - capex,
        # año previo (para Piotroski / Beneish / Sloan)
        "revenue_prev": revenue * prev,
        "net_income_prev": net_income * prev * rng.uniform(0.85, 1.15),
        "total_assets_prev": total_assets * prev,
        "gross_profit_prev": gross * prev * rng.uniform(0.9, 1.1),
        "lt_debt_prev": lt_debt * rng.uniform(0.85, 1.2),
        "current_assets_prev": current_assets * prev,
        "current_liabilities_prev": current_liab * prev * rng.uniform(0.9, 1.15),
        "receivables_prev": receivables * prev * rng.uniform(0.85, 1.15),
        "depreciation_prev": depreciation * prev,
        "sga_prev": sga * prev,
        "shares_prev": shares * rng.uniform(0.98, 1.03),
        "cfo_prev": cfo * prev * rng.uniform(0.85, 1.15),
    }


_HEADLINE_TEMPLATES = [
    ("{n} supera expectativas de ingresos en el trimestre", 0.6),
    ("{n} anuncia recompra de acciones por miles de millones", 0.7),
    ("Analistas elevan precio objetivo de {n}", 0.5),
    ("{n} enfrenta investigación regulatoria en la UE", -0.6),
    ("{n} recorta su guía anual por debilidad de demanda", -0.8),
    ("{n} presenta nuevo producto insignia con buena recepción", 0.5),
    ("Insiders de {n} venden acciones tras el rally", -0.3),
    ("{n} expande operaciones a nuevos mercados", 0.4),
    ("Demanda colectiva contra {n} avanza en tribunales", -0.5),
    ("{n} firma contrato gubernamental multianual", 0.6),
]


def sample_news(ticker: str, n: int = 8) -> list[dict]:
    rng = _rng(ticker, "news")
    name = TICKER_NAMES.get(ticker.upper(), ticker.upper())
    idx = rng.choice(len(_HEADLINE_TEMPLATES), size=min(n, len(_HEADLINE_TEMPLATES)), replace=False)
    today = pd.Timestamp.today().normalize()
    out = []
    for k, i in enumerate(idx):
        tpl, tone = _HEADLINE_TEMPLATES[i]
        out.append({
            "title": tpl.format(n=name),
            "publisher": rng.choice(["MarketWatch", "Reuters", "Bloomberg", "El Financiero", "WSJ"]),
            "link": "",
            "date": str((today - pd.Timedelta(days=int(k))).date()),
            "tone_hint": tone,
        })
    return out


_FX_BASE = {"MXN=X": 18.4, "EURUSD=X": 1.08, "JPY=X": 155.0}


def sample_fx(pair: str, days: int = 500) -> pd.DataFrame:
    """Serie FX sintética determinista (vol diaria realista ~0.6%)."""
    rng = _rng(pair, "fxpair")
    base = _FX_BASE.get(pair, 1.0)
    rets = rng.normal(0.00005, 0.006, days)
    close = base * np.exp(np.cumsum(rets))
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
    return pd.DataFrame({"Close": close}, index=idx)
