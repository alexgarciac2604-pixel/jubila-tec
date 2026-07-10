"""Acceso a datos de mercado con failover: yfinance → Stooq → sintético.

Contrato estable: cualquier proveedor nuevo (`src/data/<proveedor>.py`) debe
exponer estas mismas firmas y enlazarse aquí. El resto de la app no cambia.
"""
from __future__ import annotations

import pandas as pd

from src.config import SECTOR_OF, TICKER_NAMES, get_settings
from src.data import sample_data as sd
from src.data import stooq
from src.utils.cache import ttl_cache

try:
    import yfinance as yf
    _HAS_YF, _YF_ERR = True, ""
except Exception as _e:                     # nunca tragar el motivo en silencio
    _HAS_YF, _YF_ERR = False, f"{type(_e).__name__}: {_e}"

_SOURCES: dict[str, str] = {}  # ticker → proveedor que realmente respondió


def using_sample() -> bool:
    """True SOLO si el usuario pidió modo sintético (JT_FORCE_SAMPLE=1).

    v0.23.1: que falte yfinance ya NO autoriza datos sintéticos — Stooq
    sigue entregando datos reales. Sin este cambio, un import roto en el
    runner publicaba screeners sintéticos con la conciencia tranquila.
    """
    return get_settings().force_sample


def yf_status() -> tuple[bool, str]:
    """¿yfinance importó? (ok, error) — para logs y la página de Fuentes."""
    return _HAS_YF, _YF_ERR


def source_of(ticker: str) -> str:
    return _SOURCES.get(ticker.upper(), "sample")


@ttl_cache(ttl=600)
def get_history(ticker: str, period: str = "2y") -> pd.DataFrame:
    """OHLCV diario con failover en cadena. Nunca lanza: degrada a sintético."""
    if not get_settings().force_sample:
        if _HAS_YF:
            try:
                df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
                # ≥5 días basta: una IPO reciente merece sus datos REALES,
                # no 500 días sintéticos (bug detectado con SPCX, jun-2026)
                if df is not None and len(df) >= 5:
                    _SOURCES[ticker.upper()] = "yfinance"
                    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
            except Exception:
                pass
        df = stooq.get_history(ticker)
        if df is not None:
            _SOURCES[ticker.upper()] = "stooq"
            return df
    _SOURCES[ticker.upper()] = "sample"
    return sd.sample_history(ticker)


# sectores en inglés de yfinance → nuestra taxonomía (peers y stress tests)
SECTOR_EN_ES = {
    "Technology": "Tecnología", "Communication Services": "Comunicación",
    "Consumer Cyclical": "Consumo Disc.", "Financial Services": "Financiero",
    "Healthcare": "Salud", "Energy": "Energía",
    "Consumer Defensive": "Consumo Básico", "Industrials": "Industrial",
    "Basic Materials": "Industrial", "Utilities": "Energía",
    "Real Estate": "Financiero",
}

_YF_MAP = {  # info de yfinance → claves estándar
    "longName": "name", "sector": "sector", "marketCap": "market_cap",
    "sharesOutstanding": "shares", "beta": "beta", "totalRevenue": "revenue",
    "grossProfits": "gross_profit", "netIncomeToCommon": "net_income",
    "totalCash": "cash", "totalDebt": "total_debt", "freeCashflow": "fcf",
    "operatingCashflow": "cfo", "dividendYield": "dividend_yield",
    "currentPrice": "price",
}


@ttl_cache(ttl=1800)
def get_fundamentals(ticker: str) -> dict:
    """Dict estandarizado. Base sintética coherente + overlay real si hay red."""
    base = sd.sample_fundamentals(ticker)
    if not get_settings().force_sample:
        from src.data import edgar
        overlay = edgar.fundamentals_overlay(ticker)
        if overlay:
            base.update(overlay)
    if not using_sample() and _HAS_YF:
        try:
            info = yf.Ticker(ticker).info or {}
            for src_key, dst_key in _YF_MAP.items():
                v = info.get(src_key)
                if v is not None:
                    base[dst_key] = v
            base["source"] = "yfinance"
            sec = base.get("sector", "")
            base["sector"] = SECTOR_EN_ES.get(sec, sec if sec in
                set(SECTOR_OF.values()) else "Otro")
        except Exception:
            pass
    return base


@ttl_cache(ttl=120)
def get_quote(ticker: str) -> dict:
    h = get_history(ticker)
    last = float(h.Close.iloc[-1])
    prev = float(h.Close.iloc[-2])
    hi52 = float(h.Close.tail(252).max())
    return {
        "ticker": ticker.upper(),
        "name": TICKER_NAMES.get(ticker.upper(), ticker.upper()),
        "sector": SECTOR_OF.get(ticker.upper(), "Otro"),
        "price": last,
        "change_pct": (last / prev - 1.0) * 100.0,
        "from_52w_high_pct": (last / hi52 - 1.0) * 100.0,
    }


def get_quotes(tickers: list[str]) -> pd.DataFrame:
    return pd.DataFrame([get_quote(t) for t in tickers])


@ttl_cache(ttl=3600)
def get_fx_history(pair: str = "MXN=X") -> pd.DataFrame:
    """Tipo de cambio (p. ej. USD/MXN). Failover a serie sintética."""
    if not using_sample() and _HAS_YF:
        try:
            df = yf.Ticker(pair).history(period="2y")
            if df is not None and len(df) > 30:
                return df[["Close"]].dropna()
        except Exception:
            pass
    return sd.sample_fx(pair)


def lookup_ticker(symbol: str) -> bool:
    """Valida contra el proveedor EN VIVO si un símbolo desconocido cotiza.

    Evita afirmaciones desactualizadas (caso SpaceX): antes de decir que algo
    no existe, se le pregunta al mercado. False si no hay red o no cotiza.
    """
    if using_sample() or not _HAS_YF:
        return False
    try:
        h = yf.Ticker(symbol.upper()).history(period="5d")
        return h is not None and len(h) > 0
    except Exception:
        return False


def resolve_symbol(query: str) -> str | None:
    """Resuelve lo que el usuario escribió a un ticker real.

    Acepta el ticker (TSLA), el nombre (tesla, TESLA, coca cola) o un typo
    cercano. Último recurso: pregunta al proveedor en vivo. None si no hay
    forma honesta de resolverlo — mejor negarse que inventar (bug TESLA).
    """
    import difflib
    import unicodedata
    from src.config import NAME_TO_TICKER

    q = (query or "").strip()
    if not q:
        return None
    qu = q.upper()
    if qu in TICKER_NAMES:
        return qu
    ql = unicodedata.normalize("NFD", q.lower()).encode("ascii", "ignore").decode()
    if ql in NAME_TO_TICKER:
        return NAME_TO_TICKER[ql]
    close = difflib.get_close_matches(
        ql, list(NAME_TO_TICKER) + [t.lower() for t in TICKER_NAMES], n=1, cutoff=0.8)
    if close:
        c = close[0]
        return NAME_TO_TICKER.get(c, c.upper())
    if lookup_ticker(qu):                # cotiza aunque no esté en el universo
        return qu
    return None
