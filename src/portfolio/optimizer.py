"""Optimización de portafolio (numpy puro; scipy/sklearn opcionales).

Métodos: tangencia (max Sharpe, forma cerrada + proyección long-only),
mínima varianza, risk parity iterativo, HRP (López de Prado), pesos iguales.
Covarianza con shrinkage tipo Ledoit-Wolf hacia la identidad escalada.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.models.risk import TRADING_DAYS, cvar_hist, var_hist

try:
    from sklearn.covariance import LedoitWolf
    _HAS_LW = True
except Exception:
    _HAS_LW = False


def returns_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.pct_change().dropna()


def shrunk_cov(rets: pd.DataFrame, delta: float = 0.15) -> np.ndarray:
    """Covarianza anualizada con shrinkage (estabiliza la optimización)."""
    if _HAS_LW and len(rets) > rets.shape[1] + 2:
        return LedoitWolf().fit(rets.values).covariance_ * TRADING_DAYS
    S = rets.cov().values * TRADING_DAYS
    target = np.eye(len(S)) * np.trace(S) / len(S)
    return (1 - delta) * S + delta * target


def _project_long_only(w: np.ndarray) -> np.ndarray:
    w = np.clip(w, 0, None)
    s = w.sum()
    return w / s if s > 0 else np.full_like(w, 1 / len(w))


def max_sharpe(rets: pd.DataFrame, rf: float = 0.042) -> np.ndarray:
    mu = rets.mean().values * TRADING_DAYS
    cov = shrunk_cov(rets)
    try:
        w = np.linalg.pinv(cov) @ (mu - rf)
    except np.linalg.LinAlgError:
        w = np.ones(len(mu))
    return _project_long_only(w)


def min_variance(rets: pd.DataFrame) -> np.ndarray:
    cov = shrunk_cov(rets)
    ones = np.ones(cov.shape[0])
    try:
        w = np.linalg.pinv(cov) @ ones
    except np.linalg.LinAlgError:
        w = ones
    return _project_long_only(w)


def risk_parity(rets: pd.DataFrame, iters: int = 200) -> np.ndarray:
    """Iguala contribuciones al riesgo (iteración de punto fijo)."""
    cov = shrunk_cov(rets)
    w = 1 / np.sqrt(np.diag(cov))
    w = w / w.sum()
    for _ in range(iters):
        mrc = cov @ w                      # riesgo marginal
        rc = w * mrc                       # contribución
        w = w * (rc.mean() / np.where(rc > 0, rc, rc.mean())) ** 0.5
        w = _project_long_only(w)
    return w


def _single_linkage_order(dist: np.ndarray) -> list[int]:
    """Orden de cuasi-diagonalización vía clustering jerárquico (numpy puro)."""
    n = dist.shape[0]
    members = {i: [i] for i in range(n)}
    d = {(i, j): float(dist[i, j]) for i in range(n) for j in range(i + 1, n)}
    active = set(range(n))
    next_id = n
    while len(active) > 1:
        i, j = min(
            ((a, b) for a in active for b in active if a < b),
            key=lambda p: d.get(p, np.inf),
        )
        members[next_id] = members[i] + members[j]
        for k in active:
            if k not in (i, j):
                d[(min(k, next_id), max(k, next_id))] = min(
                    d[(min(i, k), max(i, k))], d[(min(j, k), max(j, k))]
                )
        active -= {i, j}
        active.add(next_id)
        next_id += 1
    return members[next_id - 1]


def _cluster_var(cov: np.ndarray, idx: list[int]) -> float:
    sub = cov[np.ix_(idx, idx)]
    ivp = 1.0 / np.diag(sub)
    w = ivp / ivp.sum()
    return float(w @ sub @ w)


def hrp(rets: pd.DataFrame) -> np.ndarray:
    """Hierarchical Risk Parity (López de Prado, 2016) sin dependencias extra.

    1) Clusteriza por distancia de correlación, 2) cuasi-diagonaliza,
    3) bisección recursiva asignando inverso de la varianza del clúster.
    Más robusto que media-varianza: no invierte la matriz de covarianza.
    """
    corr = rets.corr().values
    cov = shrunk_cov(rets)
    dist = np.sqrt(np.clip(0.5 * (1 - corr), 0, 1))
    order = _single_linkage_order(dist)

    w = np.ones(len(order))
    pos = {asset: k for k, asset in enumerate(order)}
    stack = [order]
    while stack:
        cl = stack.pop()
        if len(cl) < 2:
            continue
        half = len(cl) // 2
        c1, c2 = cl[:half], cl[half:]
        v1, v2 = _cluster_var(cov, c1), _cluster_var(cov, c2)
        alpha = 1 - v1 / (v1 + v2)
        for a in c1:
            w[pos[a]] *= alpha
        for a in c2:
            w[pos[a]] *= 1 - alpha
        stack += [c1, c2]

    final = np.zeros(len(order))
    for asset, k in pos.items():
        final[asset] = w[k]
    return _project_long_only(final)


def equal_weight(rets: pd.DataFrame) -> np.ndarray:
    n = rets.shape[1]
    return np.full(n, 1 / n)


def portfolio_stats(w: np.ndarray, rets: pd.DataFrame, rf: float = 0.042) -> dict:
    port_r = pd.Series(rets.values @ w, index=rets.index)
    mu = float(port_r.mean()) * TRADING_DAYS
    vol = float(port_r.std()) * np.sqrt(TRADING_DAYS)
    cum = (1 + port_r).cumprod()
    dd = float((cum / cum.cummax() - 1).min())
    cov = shrunk_cov(rets)
    mrc = cov @ w
    rc = w * mrc
    rc_pct = rc / rc.sum() if rc.sum() else rc
    return {
        "ann_return": mu, "ann_vol": vol,
        "sharpe": (mu - rf) / vol if vol else None,
        "max_drawdown": dd,
        "var95_d": var_hist(port_r), "cvar95_d": cvar_hist(port_r),
        "risk_contrib_pct": rc_pct,                # contribución al riesgo por activo
        "daily_returns": port_r,
    }


def random_frontier(rets: pd.DataFrame, n: int = 2500, rf: float = 0.042,
                    seed: int = 11) -> pd.DataFrame:
    """Nube (vol, retorno, sharpe) de portafolios aleatorios para graficar."""
    rng = np.random.default_rng(seed)
    mu = rets.mean().values * TRADING_DAYS
    cov = shrunk_cov(rets)
    ws = rng.dirichlet(np.ones(rets.shape[1]), n)
    port_mu = ws @ mu
    port_vol = np.sqrt(np.einsum("ij,jk,ik->i", ws, cov, ws))
    return pd.DataFrame({
        "vol": port_vol, "ret": port_mu,
        "sharpe": np.where(port_vol > 0, (port_mu - rf) / port_vol, 0),
    })
