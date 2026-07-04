"""Motor fundamental: márgenes, retornos, DuPont, calidad."""
from __future__ import annotations

TAX_RATE = 0.21


def _safe_div(a, b):
    try:
        return a / b if b else None
    except TypeError:
        return None


def analyze(f: dict) -> dict:
    rev, ni, ebit = f.get("revenue"), f.get("net_income"), f.get("ebit")
    ta, eq = f.get("total_assets"), f.get("equity")
    debt, cash = f.get("total_debt", 0), f.get("cash", 0)

    gross_m = _safe_div(f.get("gross_profit"), rev)
    op_m = _safe_div(ebit, rev)
    net_m = _safe_div(ni, rev)
    roe = _safe_div(ni, eq)
    roa = _safe_div(ni, ta)
    invested = (debt or 0) + (eq or 0) - (cash or 0)
    roic = _safe_div((ebit or 0) * (1 - TAX_RATE), invested) if invested else None
    fcf_margin = _safe_div(f.get("fcf"), rev)
    fcf_conv = _safe_div(f.get("fcf"), ni)  # conversión de caja
    debt_equity = _safe_div(debt, eq)
    current_ratio = _safe_div(f.get("current_assets"), f.get("current_liabilities"))

    dupont = {
        "margen_neto": net_m,
        "rotacion_activos": _safe_div(rev, ta),
        "apalancamiento": _safe_div(ta, eq),
        "roe": roe,
    }

    # score de calidad 0-100 (umbrales estándar de literatura de quality investing)
    checks = [
        (roic is not None and roic > 0.12, 2),      # ROIC > 12%
        (gross_m is not None and gross_m > 0.40, 1),
        (net_m is not None and net_m > 0.10, 1),
        (fcf_conv is not None and fcf_conv > 0.8, 2),  # utilidades respaldadas por caja
        (debt_equity is not None and debt_equity < 1.0, 1),
        (current_ratio is not None and current_ratio > 1.2, 1),
        (roe is not None and roe > 0.15, 1),
        (f.get("revenue_prev") and rev and rev > f["revenue_prev"], 1),  # crece
    ]
    earned = sum(w for ok, w in checks if ok)
    total = sum(w for _, w in checks)
    quality_score = round(100 * earned / total)

    return {
        "gross_margin": gross_m, "operating_margin": op_m, "net_margin": net_m,
        "roe": roe, "roa": roa, "roic": roic,
        "fcf_margin": fcf_margin, "fcf_conversion": fcf_conv,
        "debt_equity": debt_equity, "current_ratio": current_ratio,
        "dupont": dupont, "quality_score": quality_score,
        "pe": _safe_div(f.get("market_cap"), ni),
        "pb": _safe_div(f.get("market_cap"), eq),
        "ev_ebit": _safe_div((f.get("market_cap") or 0) + (debt or 0) - (cash or 0), ebit),
        "earnings_yield": _safe_div(ni, f.get("market_cap")),
    }


def peer_comparison(ticker: str, max_peers: int = 5):
    """Tabla ticker vs. pares del sector: P/E, ROIC, margen, calidad, momentum 6m."""
    import pandas as pd
    from src.config import SECTOR_OF
    from src.data.market_data import get_fundamentals, get_history

    t0 = ticker.upper()
    sector = SECTOR_OF.get(t0)
    peers = [t for t, s in SECTOR_OF.items() if s == sector and t != t0][:max_peers]
    rows = []
    for t in [t0] + peers:
        try:
            fm = analyze(get_fundamentals(t))
            close = get_history(t).Close
            mom6 = (float(close.iloc[-1] / close.iloc[-126]) - 1) * 100 if len(close) > 126 else 0.0
            rows.append({
                "Ticker": ("⭐ " if t == t0 else "") + t,
                "P/E": fm["pe"],
                "ROIC %": (fm["roic"] or 0) * 100,
                "Margen neto %": (fm["net_margin"] or 0) * 100,
                "Calidad": fm["quality_score"],
                "Momentum 6m %": mom6,
            })
        except Exception:
            continue
    return pd.DataFrame(rows)
