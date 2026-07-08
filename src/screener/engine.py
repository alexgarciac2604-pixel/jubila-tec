"""Screener nocturno: pre-calcula scores de un universo amplio (~100 empresas).

Corre en GitHub Actions de madrugada y publica `data/screener.json` en el repo;
la app lo lee al instante sin golpear a yfinance en vivo.

El score de screening es LIGERO a propósito: calidad + técnico + valoración.
Omite noticias/sentimiento (caros por ticker) y forense (los datos del año
previo solo son oficiales para empresas con CIK en EDGAR). El score completo
sigue siendo el del análisis individual.
"""
from __future__ import annotations

import json
import os
from datetime import date


def _path() -> str:
    env = os.getenv("JT_SCREENER_PATH")
    if env:
        return env
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "data", "screener.json")


def screen_ticker(ticker: str) -> dict | None:
    """Fila del screener para un ticker. None si online no hay datos reales."""
    from src.config import RISK_FREE
    from src.data.market_data import (get_fundamentals, get_history, source_of,
                                      using_sample)
    from src.fundamental.metrics import analyze
    from src.technical.signals import technical_summary
    from src.valuation.dcf import dcf_value

    h = get_history(ticker)
    if source_of(ticker) == "sample" and not using_sample():
        return None                       # candado anti-sintético también aquí
    f = get_fundamentals(ticker)
    m = analyze(f)
    tech = technical_summary(h)
    price = float(h.Close.iloc[-1])

    fcf = f.get("fcf") or 0.0
    upside = None
    if fcf > 0 and price > 0:
        shares = f.get("shares") or 1.0
        nd = (f.get("total_debt") or 0) - (f.get("cash") or 0)
        wacc = max(RISK_FREE + (f.get("beta") or 1.0) * 0.05, 0.06)
        ps = dcf_value(fcf, 0.08, wacc, net_debt=nd, shares=shares)["per_share"]
        upside = ps / price - 1.0
    val_score = (round(max(0.0, min(100.0, 50 + upside * 125)))
                 if upside is not None else 50)

    score = round(0.35 * m["quality_score"] + 0.35 * tech["score"] + 0.30 * val_score)
    hi52 = float(h.Close.tail(252).max())
    return {
        "ticker": ticker.upper(),
        "name": f.get("name", ticker),
        "sector": f.get("sector", "Otro"),
        "price": round(price, 2),
        "score": score,
        "calidad": m["quality_score"],
        "tecnico": tech["score"],
        "valoracion": val_score,
        "upside_pct": round(upside * 100, 1) if upside is not None else None,
        "mom_6m": round(tech["mom_6m"], 1),
        "desde_max_pct": round((price / hi52 - 1) * 100, 1) if hi52 else None,
    }


def run_screener(universe: list[str] | None = None) -> dict:
    from src.config import SCREENER_UNIVERSE
    from src.data.market_data import using_sample
    rows = []
    for t in (universe or SCREENER_UNIVERSE):
        try:
            r = screen_ticker(t)
            if r:
                rows.append(r)
        except Exception:
            continue
    rows.sort(key=lambda r: r["score"], reverse=True)
    return {"date": str(date.today()),
            "source": "sample" if using_sample() else "yfinance",
            "n": len(rows), "rows": rows}


def save_screener(data: dict | None = None) -> str:
    data = data or run_screener()
    path = _path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    return path


def load_screener() -> dict | None:
    try:
        with open(_path(), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None
