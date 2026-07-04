"""Motor macro: FRED si hay clave, series sintéticas realistas si no."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import get_settings
from src.utils.cache import ttl_cache

_FRED_SERIES = {
    "PIB (crecimiento % anual)": "A191RL1Q225SBEA",
    "Inflación CPI (% anual)": "CPIAUCSL",
    "Desempleo (%)": "UNRATE",
    "Tasa Fed Funds (%)": "FEDFUNDS",
}


def _synthetic_series(name: str, base: float, vol: float, periods: int = 48) -> pd.Series:
    rng = np.random.default_rng(abs(hash(name)) % 2**31)
    idx = pd.date_range(end=pd.Timestamp.today().normalize(), periods=periods, freq="MS")
    vals = base + np.cumsum(rng.normal(0, vol, periods))
    return pd.Series(np.round(vals, 2), index=idx, name=name)


def _fetch_fred(series_id: str, api_key: str) -> pd.Series | None:
    try:
        import requests
        r = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={"series_id": series_id, "api_key": api_key,
                    "file_type": "json", "observation_start": "2020-01-01"},
            timeout=10,
        )
        obs = r.json().get("observations", [])
        s = pd.Series(
            {pd.Timestamp(o["date"]): float(o["value"]) for o in obs if o["value"] != "."}
        )
        return s if len(s) else None
    except Exception:
        return None


@ttl_cache(ttl=3600)
def get_macro_series() -> dict:
    """dict nombre → pd.Series. Marca 'source' en el resultado."""
    s = get_settings()
    out: dict = {"source": "sample"}
    if s.has_fred() and not s.force_sample:
        fetched = {name: _fetch_fred(sid, s.fred_api_key) for name, sid in _FRED_SERIES.items()}
        if all(v is not None for v in fetched.values()):
            out.update(fetched)
            out["source"] = "FRED"
            return out
    out["PIB (crecimiento % anual)"] = _synthetic_series("gdp", 2.4, 0.15)
    out["Inflación CPI (% anual)"] = _synthetic_series("cpi", 3.1, 0.12)
    out["Desempleo (%)"] = _synthetic_series("unemp", 4.0, 0.08)
    out["Tasa Fed Funds (%)"] = _synthetic_series("ff", 4.5, 0.05)
    return out


@ttl_cache(ttl=3600)
def yield_curve() -> pd.Series:
    """Curva de rendimientos del Tesoro (sintética suave si no hay FRED)."""
    tenors = ["1M", "3M", "6M", "1A", "2A", "5A", "10A", "30A"]
    rng = np.random.default_rng(20260703)
    short = 4.4 + rng.normal(0, 0.05)
    # curva levemente invertida en el tramo corto, normal al largo
    rates = [short, short + 0.02, short - 0.05, short - 0.25, short - 0.45,
             short - 0.35, short - 0.15, short + 0.25]
    return pd.Series(np.round(rates, 2), index=tenors, name="Rendimiento %")


def curve_signal(curve: pd.Series) -> str:
    spread = curve.get("10A", 0) - curve.get("2A", 0)
    if spread < 0:
        return f"⚠️ Curva invertida (10A−2A = {spread:.2f}pp) — históricamente precede recesiones."
    return f"🟢 Curva normal (10A−2A = {spread:+.2f}pp)."
