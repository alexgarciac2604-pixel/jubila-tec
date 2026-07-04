"""Régimen de mercado: mezcla gaussiana de 2 estados (EM, numpy puro) + tendencia.

Estado de volatilidad (calma/turbulencia) vía GMM sobre retornos del benchmark;
estado de tendencia vía precio vs SMA200. El régimen ajusta los pesos del score:
en turbulencia, el momentum pierde fiabilidad y la calidad/forense pesan más
(evidencia de momentum crashes: Daniel & Moskowitz 2016).
"""
from __future__ import annotations

import numpy as np

from src.data.market_data import get_history
from src.utils.cache import ttl_cache


def fit_gmm2(x: np.ndarray, iters: int = 60) -> dict:
    """EM para mezcla de 2 gaussianas (media compartida ~0, varianzas distintas)."""
    x = np.asarray(x, float)
    mu = float(x.mean())
    s = float(x.std())
    s1, s2, pi = 0.5 * s, 2.0 * s, 0.5
    for _ in range(iters):
        p1 = pi * np.exp(-0.5 * ((x - mu) / s1) ** 2) / (s1 + 1e-12)
        p2 = (1 - pi) * np.exp(-0.5 * ((x - mu) / s2) ** 2) / (s2 + 1e-12)
        g = p1 / (p1 + p2 + 1e-300)                    # resp. estado calmado
        pi = float(g.mean())
        s1 = float(np.sqrt(np.sum(g * (x - mu) ** 2) / (g.sum() + 1e-12))) or s
        s2 = float(np.sqrt(np.sum((1 - g) * (x - mu) ** 2) / ((1 - g).sum() + 1e-12))) or s
        if s1 > s2:                                    # estado 1 = baja vol siempre
            s1, s2, pi, g = s2, s1, 1 - pi, 1 - g
    return {"sigma_calm": s1, "sigma_turb": s2, "pi_calm": pi, "gamma_calm": g}


_REGIMES = {
    ("calma", "alcista"): ("🟢", "Calma alcista",
                           "Tendencia sana con volatilidad baja: el entorno más benigno."),
    ("calma", "bajista"): ("🟡", "Calma bajista",
                           "Deriva bajista sin pánico: paciencia; vigilar soportes."),
    ("turbulencia", "alcista"): ("🟠", "Turbulencia alcista",
                                 "Sube con volatilidad alta: rallies frágiles, tomar con cautela."),
    ("turbulencia", "bajista"): ("🔴", "Turbulencia bajista",
                                 "Régimen de estrés: la correlación sube y el momentum falla."),
}


@ttl_cache(ttl=3600)
def market_regime(bench: str = "SPY") -> dict:
    h = get_history(bench)
    r = h.Close.pct_change().dropna().values
    g = fit_gmm2(r)
    p_turb_recent = float(1 - g["gamma_calm"][-10:].mean())   # prob. turb. últimos 10d
    vol_state = "turbulencia" if p_turb_recent > 0.5 else "calma"
    sma200 = float(h.Close.rolling(200).mean().iloc[-1])
    trend = "alcista" if float(h.Close.iloc[-1]) > sma200 else "bajista"
    emoji, name, desc = _REGIMES[(vol_state, trend)]
    return {
        "vol_state": vol_state, "trend": trend,
        "p_turbulent": p_turb_recent,
        "sigma_calm_ann": g["sigma_calm"] * np.sqrt(252),
        "sigma_turb_ann": g["sigma_turb"] * np.sqrt(252),
        "emoji": emoji, "name": name, "description": desc,
        "bench": bench,
    }


def regime_weights(base: dict, regime: dict) -> dict:
    """En turbulencia: menos técnico/momentum, más calidad y forense."""
    if regime["vol_state"] != "turbulencia":
        return dict(base)
    w = {"fundamental": 0.30, "valuation": 0.20, "technical": 0.10,
         "forensic": 0.25, "sentiment": 0.15}
    assert abs(sum(w.values()) - 1) < 1e-9
    return w
