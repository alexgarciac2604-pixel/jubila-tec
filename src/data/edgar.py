"""SEC EDGAR (público, sin API key): fundamentales oficiales point-in-time
y actividad de insiders (Form 4).

Requiere header User-Agent (política de la SEC). Timeouts cortos y fallback
sintético: la app nunca se bloquea esperando a la SEC.
"""
from __future__ import annotations

import numpy as np

from src.data import sample_data as sd
from src.utils.cache import ttl_cache

_UA = {"User-Agent": "AL-X research (contacto: alexgarciac2604@gmail.com)"}

# CIKs de los principales tickers del universo (best-effort; si uno falla,
# el failover sintético cubre). Fuente: EDGAR company_tickers.json.
_CIK = {
    "AAPL": 320193, "MSFT": 789019, "NVDA": 1045810, "GOOGL": 1652044,
    "AMZN": 1018724, "META": 1326801, "TSLA": 1318605, "AVGO": 1730168,
    "JPM": 19617, "BAC": 70858, "V": 1403161, "MA": 1141391,
    "JNJ": 200406, "PFE": 78003, "UNH": 731766, "LLY": 59478,
    "XOM": 34088, "CVX": 93410, "WMT": 104169, "PG": 80424,
    "KO": 21344, "PEP": 77476, "HD": 354950, "MCD": 63908,
    "DIS": 1744489, "NFLX": 1065280, "CAT": 18230, "BA": 12927,
    "GE": 40545, "LMT": 936468, "T": 732717, "VZ": 732712,
}

# tag XBRL (us-gaap) → clave estándar de AL-X
_TAGS = {
    "Revenues": "revenue",
    "RevenueFromContractWithCustomerExcludingAssessedTax": "revenue",
    "GrossProfit": "gross_profit",
    "OperatingIncomeLoss": "ebit",
    "NetIncomeLoss": "net_income",
    "Assets": "total_assets",
    "Liabilities": "total_liabilities",
    "StockholdersEquity": "equity",
    "CashAndCashEquivalentsAtCarryingValue": "cash",
    "NetCashProvidedByUsedInOperatingActivities": "cfo",
    "PaymentsToAcquirePropertyPlantAndEquipment": "capex",
}


def _get_json(url: str) -> dict | None:
    try:
        import requests
        r = requests.get(url, headers=_UA, timeout=8)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def _last_two_annual(facts: dict, tag: str) -> tuple[float | None, float | None]:
    try:
        arr = facts["facts"]["us-gaap"][tag]["units"]["USD"]
        annual = {}
        for x in arr:
            if x.get("form") == "10-K" and x.get("fp") == "FY" and x.get("fy"):
                annual[x["fy"]] = x["val"]        # el último filing por año fiscal gana
        years = sorted(annual)
        if not years:
            return None, None
        cur = float(annual[years[-1]])
        prev = float(annual[years[-2]]) if len(years) > 1 else None
        return cur, prev
    except Exception:
        return None, None


@ttl_cache(ttl=86400)
def fundamentals_overlay(ticker: str) -> dict:
    """Fundamentales anuales oficiales (10-K). {} si EDGAR no responde."""
    cik = _CIK.get(ticker.upper())
    if not cik:
        return {}
    facts = _get_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")
    if not facts:
        return {}
    out: dict = {}
    for tag, key in _TAGS.items():
        if key in out:                      # el primer tag que responda gana
            continue
        cur, prev = _last_two_annual(facts, tag)
        if cur is not None:
            out[key] = cur
            if prev is not None and key in ("revenue", "net_income", "total_assets",
                                            "gross_profit", "cfo"):
                out[key + "_prev"] = prev
    if "cfo" in out and "capex" in out:
        out["fcf"] = out["cfo"] - abs(out["capex"])
    if out:
        out["source"] = "SEC EDGAR (10-K)"
    return out


@ttl_cache(ttl=21600)
def insider_activity(ticker: str) -> dict:
    """Actividad de insiders: nº de Form 4 en 90 días (EDGAR) o sintético."""
    cik = _CIK.get(ticker.upper())
    if cik:
        subs = _get_json(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
        if subs:
            try:
                import pandas as pd
                recent = subs["filings"]["recent"]
                df = pd.DataFrame({"form": recent["form"], "date": recent["filingDate"]})
                cutoff = str((pd.Timestamp.today() - pd.Timedelta(days=90)).date())
                n = int(((df.form == "4") & (df.date >= cutoff)).sum())
                level = "alta" if n >= 10 else ("moderada" if n >= 3 else "baja")
                return {
                    "source": "SEC EDGAR", "form4_90d": n, "signal": "n/d",
                    "badge": "🟢" if n < 10 else "🟡",
                    "summary": f"{n} filings Form 4 en 90 días (actividad {level}).",
                    "note": ("Dirección compra/venta requiere parsear cada filing "
                             "(pendiente); el conteo ya indica intensidad."),
                }
            except Exception:
                pass
    # fallback sintético determinista
    rng = sd._rng(ticker, "insiders")
    n = int(rng.integers(0, 14))
    buys = int(rng.integers(0, n + 1))
    net = buys - (n - buys)
    signal = "compra neta" if net > 1 else ("venta neta" if net < -1 else "neutral")
    badge = {"compra neta": "🟢", "neutral": "🟡", "venta neta": "🔴"}[signal]
    return {
        "source": "sample", "form4_90d": n, "signal": signal, "badge": badge,
        "summary": f"{n} operaciones de insiders en 90 días — {signal} "
                   f"({buys} compras / {n - buys} ventas).",
        "note": "🧪 Datos sintéticos (sin conexión a EDGAR en este momento).",
    }
