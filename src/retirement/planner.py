"""Motor de jubilación: acumulación, glide path y reglas de retiro.

Todo en TÉRMINOS REALES (dinero de hoy): la inflación se simula estocástica
y se deflacta cada trayectoria. Retornos de equity con colas gordas (t-Student
df=5); el supuesto gaussiano subestima gravemente la probabilidad de ruina.
"""
from __future__ import annotations

import numpy as np

DF_T = 5  # grados de libertad t-Student


def glide_path_equity(age: float, floor: float = 0.30, cap: float = 0.95) -> float:
    """Regla 120−edad acotada: % en acciones según edad."""
    return float(np.clip((120.0 - age) / 100.0, floor, cap))


def simulate_accumulation(age: int, retire_age: int, capital: float, monthly: float,
                          goal: float | None = None,
                          eq_mu: float = 0.07, eq_vol: float = 0.16,
                          bd_mu: float = 0.035, bd_vol: float = 0.05,
                          infl_mu: float = 0.035, infl_vol: float = 0.012,
                          n: int = 2000, seed: int = 99) -> dict:
    """Proyecta el patrimonio real hasta el retiro con aportes mensuales.

    El aporte crece con la inflación de cada trayectoria (mantiene poder
    de compra). Devuelve bandas P10/P50/P90 mensuales y prob. de meta.
    """
    months = max((retire_age - age) * 12, 1)
    rng = np.random.default_rng(seed)
    t_scale = np.sqrt((DF_T - 2) / DF_T)

    wealth = np.full(n, float(capital))
    infl_cum = np.ones(n)
    real_paths = np.empty((n, months))

    eq_m, eq_s = eq_mu / 12, eq_vol / np.sqrt(12)
    bd_m, bd_s = bd_mu / 12, bd_vol / np.sqrt(12)
    pi_m, pi_s = infl_mu / 12, infl_vol / np.sqrt(12)

    for m in range(months):
        w_eq = glide_path_equity(age + m / 12.0)
        eq_r = eq_m + eq_s * rng.standard_t(DF_T, n) * t_scale
        bd_r = bd_m + bd_s * rng.standard_normal(n)
        infl = pi_m + pi_s * rng.standard_normal(n)
        infl_cum *= 1.0 + infl
        wealth = wealth * (1.0 + w_eq * eq_r + (1.0 - w_eq) * bd_r) + monthly * infl_cum
        real_paths[:, m] = wealth / infl_cum

    final_real = real_paths[:, -1]
    bands = np.percentile(real_paths, [10, 50, 90], axis=0)
    out = {
        "months": months,
        "p10": float(np.percentile(final_real, 10)),
        "p50": float(np.percentile(final_real, 50)),
        "p90": float(np.percentile(final_real, 90)),
        "bands": bands,                       # 3 × months (P10/P50/P90 reales)
        "sample_paths": real_paths[:80],      # para el fan chart
        "equity_now": glide_path_equity(age),
        "equity_at_retire": glide_path_equity(retire_age),
        "seed": seed,
    }
    if goal:
        out["prob_goal"] = float((final_real >= goal).mean())
    return out


def required_monthly(goal: float, age: int, retire_age: int, capital: float,
                     target_prob: float = 0.80, cap: float = 500_000.0,
                     **kw) -> float | None:
    """Aporte mensual necesario para alcanzar la meta con prob. objetivo (bisección)."""
    kw.setdefault("n", 800)

    def prob(m: float) -> float:
        r = simulate_accumulation(age, retire_age, capital, m, goal=goal, **kw)
        return r["prob_goal"]

    lo, hi = 0.0, cap
    if prob(hi) < target_prob:
        return None  # inalcanzable incluso con el tope
    if prob(lo) >= target_prob:
        return 0.0
    for _ in range(22):
        mid = (lo + hi) / 2
        if prob(mid) >= target_prob:
            hi = mid
        else:
            lo = mid
    return round(hi, -1)


def simulate_withdrawal(capital: float, years: int = 30, rule: str = "fixed_real",
                        initial_rate: float = 0.04,
                        eq_mu: float = 0.07, eq_vol: float = 0.16,
                        bd_mu: float = 0.035, bd_vol: float = 0.05,
                        infl_mu: float = 0.035, equity_w: float = 0.50,
                        n: int = 3000, seed: int = 123) -> dict:
    """Simula el retiro en términos reales. Reglas:

    - fixed_real: 4% inicial ajustado por inflación (el clásico Bengen).
    - percent: % fijo del saldo actual (nunca quiebra, ingreso variable).
    - guyton: fixed_real + guardrails (recorta 10% si la tasa sube >20%,
      sube 10% si baja >20%) — Guyton-Klinger simplificado.
    """
    rng = np.random.default_rng(seed)
    t_scale = np.sqrt((DF_T - 2) / DF_T)
    mu_real = equity_w * eq_mu + (1 - equity_w) * bd_mu - infl_mu
    vol = np.sqrt((equity_w * eq_vol) ** 2 + ((1 - equity_w) * bd_vol) ** 2)

    wealth = np.full(n, float(capital))
    ruined = np.zeros(n, dtype=bool)
    w0 = capital * initial_rate
    wd = np.full(n, w0)
    incomes = np.empty((n, years))

    for y in range(years):
        if rule == "percent":
            wd = wealth * initial_rate
        take = np.minimum(wd, wealth)
        incomes[:, y] = take
        wealth = wealth - take
        r = mu_real + vol * rng.standard_t(DF_T, n) * t_scale
        wealth = np.maximum(wealth * (1.0 + r), 0.0)
        newly = (wealth <= 1e-9) & (~ruined)
        ruined |= newly
        if rule == "guyton":
            with np.errstate(divide="ignore", invalid="ignore"):
                rate_now = np.where(wealth > 0, wd / wealth, np.inf)
            wd = np.where(rate_now > initial_rate * 1.2, wd * 0.9, wd)
            wd = np.where(rate_now < initial_rate * 0.8, wd * 1.1, wd)
        wd = np.where(ruined, 0.0, wd)

    return {
        "rule": rule,
        "ruin_prob": float(ruined.mean()),
        "median_final": float(np.median(wealth)),
        "median_income": float(np.median(incomes)),
        "p10_income": float(np.percentile(incomes, 10)),
        "seed": seed,
    }


def compare_withdrawal_rules(capital: float, years: int = 30, **kw) -> list[dict]:
    return [simulate_withdrawal(capital, years, rule=r, **kw)
            for r in ("fixed_real", "percent", "guyton")]
