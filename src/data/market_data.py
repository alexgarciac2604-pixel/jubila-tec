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
    _HAS_YF = True
except Exception:
    _HAS_YF = False

_SOURCES: dict[str, str] = {}  # ticker → proveedor que realmente respondió


def using_sample() -> bool:
    return get_settings().force_sample or not _HAS_YF


def source_of(ticker: str) -> str:
    return _SOURCES.get(ticker.upper(), "sample")


@ttl_cache(ttl=600)
def get_history(ticker: str, period: str = "2y") -> pd.DataFrame:
    """OHLCV diario con failover en cadena. Nunca lanza: degrada a sintético."""
    if not get_settings().force_sample:
        if _HAS_YF:
            try:
                df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
                if df is not None and len(df) > 30:
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
    if not using_sample():
        try:
            info = yf.Ticker(ticker).info or {}
            for src_key, dst_key in _YF_MAP.items():
                v = info.get(src_key)
                if v is not None:
                    base[dst_key] = v
            base["source"] = "yfinance"
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
    if not using_sample():
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
    if using_sample():
        return False
    try:
        h = yf.Ticker(symbol.upper()).history(period="5d")
        return h is not None and len(h) > 0
    except Exception:
        return False
