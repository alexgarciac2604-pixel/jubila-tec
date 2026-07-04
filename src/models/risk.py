"""Modelos de riesgo: VaR/CVaR (histórico y Cornish-Fisher), ratios, Monte Carlo."""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252
Z_95 = -1.6449  # cuantil normal 5%


def daily_returns(close: pd.Series) -> pd.Series:
    return close.pct_change().dropna()


def max_drawdown(close: pd.Series) -> float:
    dd = close / close.cummax() - 1.0
    return float(dd.min())


def var_hist(rets: pd.Series, level: float = 0.95) -> float:
    return float(-np.percentile(rets, (1 - level) * 100))


def cvar_hist(rets: pd.Series, level: float = 0.95) -> float:
    cut = np.percentile(rets, (1 - level) * 100)
    tail = rets[rets <= cut]
    return float(-tail.mean()) if len(tail) else var_hist(rets, level)


def var_cornish_fisher(rets: pd.Series) -> float:
    """VaR 95% ajustado por asimetría y curtosis (retornos no gaussianos)."""
    s = float(rets.skew())
    k = float(rets.kurtosis())  # exceso
    z = Z_95
    zcf = (z + (z**2 - 1) * s / 6 + (z**3 - 3 * z) * k / 24
           - (2 * z**3 - 5 * z) * s**2 / 36)
    return float(-(rets.mean() + zcf * rets.std()))


def beta_vs(rets: pd.Series, bench_rets: pd.Series) -> float | None:
    joined = pd.concat([rets, bench_rets], axis=1).dropna()
    if len(joined) < 60:
        return None
    cov = np.cov(joined.iloc[:, 0], joined.iloc[:, 1])
    return float(cov[0, 1] / cov[1, 1]) if cov[1, 1] else None


def omega_ratio(rets: pd.Series, threshold_ann: float = 0.0) -> float | None:
    """Ganancias sobre pérdidas respecto a un umbral (captura toda la distribución)."""
    th = threshold_ann / TRADING_DAYS
    gains = float((rets - th).clip(lower=0).sum())
    losses = float((th - rets).clip(lower=0).sum())
    return gains / losses if losses > 0 else None


def ulcer_index(close: pd.Series) -> float:
    """Raíz del promedio de drawdowns² — castiga profundidad Y duración."""
    dd = (close / close.cummax() - 1.0) * 100
    return float(np.sqrt((dd**2).mean()))


def risk_summary(close: pd.Series, rf: float = 0.042) -> dict:
    r = daily_returns(close)
    mu_d, sd_d = float(r.mean()), float(r.std())
    ann_ret = (1 + mu_d) ** TRADING_DAYS - 1
    ann_vol = sd_d * np.sqrt(TRADING_DAYS)
    downside = float(r[r < 0].std()) * np.sqrt(TRADING_DAYS)
    mdd = max_drawdown(close)
    return {
        "ann_return": ann_ret,
        "ann_vol": ann_vol,
        "sharpe": (ann_ret - rf) / ann_vol if ann_vol else None,
        "sortino": (ann_ret - rf) / downside if downside else None,
        "max_drawdown": mdd,
        "var95_d": var_hist(r),
        "cvar95_d": cvar_hist(r),
        "var95_cf_d": var_cornish_fisher(r),
        "skew": float(r.skew()),
        "kurtosis": float(r.kurtosis()),
        "omega": omega_ratio(r, rf),
        "ulcer": ulcer_index(close),
        "calmar": ann_ret / abs(mdd) if mdd else None,
    }


def monte_carlo_paths(mu_ann: float, vol_ann: float, years: float = 1.0,
                      n_paths: int = 2000, start: float = 100.0,
                      fat_tails: bool = True, seed: int = 7) -> dict:
    """Simulación de riqueza. fat_tails usa t-Student (df=5) — colas realistas."""
    rng = np.random.default_rng(seed)
    steps = max(int(years * TRADING_DAYS), 1)
    mu_d = mu_ann / TRADING_DAYS
    sd_d = vol_ann / np.sqrt(TRADING_DAYS)
    if fat_tails:
        df = 5
        shocks = rng.standard_t(df, (n_paths, steps)) * np.sqrt((df - 2) / df)
    else:
        shocks = rng.standard_normal((n_paths, steps))
    paths = start * np.exp(np.cumsum(mu_d - 0.5 * sd_d**2 + sd_d * shocks, axis=1))
    final = paths[:, -1]
    return {
        "paths": paths,
        "p10": float(np.percentile(final, 10)),
        "p50": float(np.percentile(final, 50)),
        "p90": float(np.percentile(final, 90)),
        "prob_loss": float((final < start).mean()),
        "seed": seed,
    }
