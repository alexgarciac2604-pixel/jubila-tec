"""Proveedor Stooq (gratis, sin clave) — segundo eslabón del failover."""
from __future__ import annotations

import io

import pandas as pd


def get_history(ticker: str, days: int = 500) -> pd.DataFrame | None:
    """OHLCV diario desde stooq.com. None si falla (el failover sigue)."""
    try:
        import requests
        sym = ticker.lower()
        if "." not in sym and not sym.startswith("^"):
            sym += ".us"
        r = requests.get(f"https://stooq.com/q/d/l/?s={sym}&i=d", timeout=8)
        if r.status_code != 200 or "Date" not in r.text[:100]:
            return None
        df = pd.read_csv(io.StringIO(r.text), parse_dates=["Date"], index_col="Date")
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna().tail(days)
        return df if len(df) > 30 else None
    except Exception:
        return None
