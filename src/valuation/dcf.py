"""Motor de valoración: DCF, reverse DCF, sensibilidad y Monte Carlo."""
from __future__ import annotations

import numpy as np
import pandas as pd


def dcf_value(fcf0: float, growth: float, wacc: float, terminal_growth: float = 0.025,
              years: int = 5, net_debt: float = 0.0, shares: float = 1.0) -> dict:
    """DCF de dos etapas. Devuelve EV, valor de equity y valor por acción."""
    wacc = max(wacc, terminal_growth + 0.005)  # evita divergencia
    t = np.arange(1, years + 1)
    flows = fcf0 * (1 + growth) ** t / (1 + wacc) ** t
    fcf_n = fcf0 * (1 + growth) ** years
    tv = fcf_n * (1 + terminal_growth) / (wacc - terminal_growth)
    ev = float(flows.sum() + tv / (1 + wacc) ** years)
    eq = ev - net_debt
    return {"ev": ev, "equity_value": eq, "per_share": eq / max(shares, 1.0),
            "terminal_pct": float(tv / (1 + wacc) ** years / ev) if ev else None}


def reverse_dcf(market_cap: float, fcf0: float, wacc: float, terminal_growth: float = 0.025,
                years: int = 5, net_debt: float = 0.0) -> float | None:
    """Crecimiento implícito en el precio actual (bisección). None si no converge."""
    lo, hi = -0.5, 0.8
    f = lambda g: dcf_value(fcf0, g, wacc, terminal_growth, years, net_debt)["equity_value"] - market_cap
    if f(lo) * f(hi) > 0:
        return None
    for _ in range(80):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def sensitivity_table(fcf0: float, wacc: float, growth: float, terminal_growth: float = 0.025,
                      years: int = 5, net_debt: float = 0.0, shares: float = 1.0) -> pd.DataFrame:
    """Valor por acción en grilla WACC × crecimiento (±2pp alrededor del caso base)."""
    waccs = [wacc + d for d in (-0.02, -0.01, 0.0, 0.01, 0.02)]
    growths = [growth + d for d in (-0.04, -0.02, 0.0, 0.02, 0.04)]
    data = {
        f"g={g:.1%}": [
            dcf_value(fcf0, g, w, terminal_growth, years, net_debt, shares)["per_share"]
            for w in waccs
        ]
        for g in growths
    }
    return pd.DataFrame(data, index=[f"WACC={w:.1%}" for w in waccs])


def monte_carlo_dcf(fcf0: float, growth: float, wacc: float, terminal_growth: float = 0.025,
                    years: int = 5, net_debt: float = 0.0, shares: float = 1.0,
                    n: int = 4000, seed: int = 42) -> dict:
    """Distribución del valor por acción con incertidumbre en g y WACC."""
    rng = np.random.default_rng(seed)
    gs = rng.normal(growth, 0.03, n)
    ws = np.clip(rng.normal(wacc, 0.01, n), terminal_growth + 0.01, 0.30)
    vals = np.array([
        dcf_value(fcf0, g, w, terminal_growth, years, net_debt, shares)["per_share"]
        for g, w in zip(gs, ws)
    ])
    return {
        "values": vals,
        "p10": float(np.percentile(vals, 10)),
        "p50": float(np.percentile(vals, 50)),
        "p90": float(np.percentile(vals, 90)),
        "mean": float(vals.mean()),
        "seed": seed,
    }


def scenarios(fcf0: float, growth: float, wacc: float, **kw) -> dict:
    """Bear / Base / Bull con supuestos desplazados de forma conservadora."""
    return {
        "bear": dcf_value(fcf0, growth - 0.05, wacc + 0.01, **kw),
        "base": dcf_value(fcf0, growth, wacc, **kw),
        "bull": dcf_value(fcf0, growth + 0.04, wacc - 0.005, **kw),
    }
