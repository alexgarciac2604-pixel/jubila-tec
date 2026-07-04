"""Backtesting honesto: walk-forward, costos, bootstrap por bloques.

Limitaciones declaradas (se muestran en la UI):
- Universo actual (posible sesgo de supervivencia hasta integrar constituyentes
  históricos vía SEC EDGAR, Fase 3).
- Solo señales de PRECIO son point-in-time hoy; los fundamentales sintéticos /
  de yfinance no tienen fecha de publicación (look-ahead si se usaran).
Por eso la v1 backtesta momentum 12-1 (Jegadeesh-Titman) — 100% point-in-time.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.market_data import get_history
from src.models.risk import TRADING_DAYS


def _prices(universe: list[str]) -> pd.DataFrame:
    return pd.DataFrame({t: get_history(t).Close for t in universe}).dropna()


def block_bootstrap_ci(x: np.ndarray, n_boot: int = 1000, block: int = 4,
                       seed: int = 5) -> tuple[float, float]:
    """IC 95% de la media por bootstrap de bloques (respeta autocorrelación)."""
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    nb = max(len(x) // block, 1)
    means = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, max(len(x) - block, 1), nb)
        sample = np.concatenate([x[s:s + block] for s in starts])
        means[b] = sample.mean()
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def backtest_momentum(universe: list[str], fwd: int = 63, step: int = 21,
                      n_q: int = 3) -> dict:
    """Momentum 12-1: señal = retorno de t-252 a t-21 (se salta el último mes).

    En cada fecha se forman n_q grupos por ranking; se mide el retorno forward
    de cada grupo y el spread top−bottom con IC bootstrap.
    """
    px = _prices(universe)
    dates = range(252, len(px) - fwd, step)
    spreads, q_rets = [], []
    for t in dates:
        sig = px.iloc[t - 21] / px.iloc[t - 252] - 1.0
        fwd_ret = px.iloc[t + fwd] / px.iloc[t] - 1.0
        ranks = sig.rank(pct=True)
        groups = np.minimum((ranks * n_q).astype(int), n_q - 1)
        by_q = [float(fwd_ret[groups == q].mean()) for q in range(n_q)]
        if not any(np.isnan(by_q)):
            q_rets.append(by_q)
            spreads.append(by_q[-1] - by_q[0])
    if not spreads:
        return {"ok": False}
    spreads = np.array(spreads)
    q_mean = np.array(q_rets).mean(axis=0)
    lo, hi = block_bootstrap_ci(spreads)
    factor = TRADING_DAYS / fwd
    return {
        "ok": True,
        "n_obs": len(spreads),
        "quantile_returns_ann": (q_mean * factor).tolist(),   # por grupo, anualizado
        "spread_ann": float(spreads.mean() * factor),
        "spread_ci_ann": (lo * factor, hi * factor),
        "significant": lo > 0 or hi < 0,
        "hit_rate": float((spreads > 0).mean()),
    }


def backtest_portfolio(tickers: list[str], weight_fn, lookback: int = 252,
                       rebal: int = 63, cost_bps: float = 10.0) -> dict:
    """Walk-forward: estima pesos con datos PASADOS, aplica al periodo siguiente,
    descuenta costos de rotación. Compara contra pesos iguales."""
    px = _prices(tickers)
    rets = px.pct_change().dropna()
    n = px.shape[1]
    eq_w = np.full(n, 1 / n)
    curve_m, curve_e = [1.0], [1.0]
    prev_w = None
    dates_used = [rets.index[lookback]]

    for t in range(lookback, len(rets) - 1, rebal):
        train = rets.iloc[t - lookback:t]
        test = rets.iloc[t:t + rebal]
        try:
            w = weight_fn(train)
        except Exception:
            w = eq_w
        cost = 0.0 if prev_w is None else float(np.abs(w - prev_w).sum()) * cost_bps / 1e4
        prev_w = w
        gross_m = float((1 + test.values @ w).prod())
        gross_e = float((1 + test.values @ eq_w).prod())
        curve_m.append(curve_m[-1] * gross_m * (1 - cost))
        curve_e.append(curve_e[-1] * gross_e)
        dates_used.append(test.index[-1])

    def _stats(curve: list[float]) -> dict:
        c = np.array(curve)
        total_years = max((len(c) - 1) * rebal / TRADING_DAYS, 1e-9)
        ann = c[-1] ** (1 / total_years) - 1
        r = np.diff(c) / c[:-1]
        vol = float(np.std(r)) * np.sqrt(TRADING_DAYS / rebal)
        mdd = float((c / np.maximum.accumulate(c) - 1).min())
        return {"ann_return": float(ann), "ann_vol": vol,
                "sharpe": (float(ann) - 0.042) / vol if vol else None,
                "max_drawdown": mdd, "final": float(c[-1])}

    return {
        "dates": dates_used,
        "curve_method": curve_m,
        "curve_equal": curve_e,
        "stats_method": _stats(curve_m),
        "stats_equal": _stats(curve_e),
        "cost_bps": cost_bps,
        "n_rebalances": len(curve_m) - 1,
    }
