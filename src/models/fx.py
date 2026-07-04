"""Riesgo cambiario: descomposición del retorno en moneda local (MXN).

R_mxn = (1 + R_usd)(1 + R_fx) − 1. La varianza en MXN incluye la del activo,
la del tipo de cambio y 2× su covarianza — a veces el peso amortigua
(correlación negativa en risk-off) y a veces amplifica.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.models.risk import TRADING_DAYS


def currency_decomposition(port_rets: pd.Series, fx_hist: pd.DataFrame) -> dict:
    fx_r = fx_hist.Close.pct_change().dropna()
    joined = pd.concat([port_rets, fx_r], axis=1, join="inner").dropna()
    joined.columns = ["p", "fx"]
    if len(joined) < 60:
        return {"ok": False}
    mxn = (1 + joined.p) * (1 + joined.fx) - 1

    def ann(s: pd.Series) -> float:
        return float((1 + s.mean()) ** TRADING_DAYS - 1)

    def vol(s: pd.Series) -> float:
        return float(s.std() * np.sqrt(TRADING_DAYS))

    return {
        "ok": True,
        "ann_usd": ann(joined.p), "ann_fx": ann(joined.fx), "ann_mxn": ann(mxn),
        "vol_usd": vol(joined.p), "vol_fx": vol(joined.fx), "vol_mxn": vol(mxn),
        "corr": float(joined.p.corr(joined.fx)),
        "n_days": len(joined),
    }
