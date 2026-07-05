"""Vista: planificador de jubilación — metas, glide path y reglas de retiro."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.retirement.planner import (compare_withdrawal_rules, required_monthly,
                                    simulate_accumulation)
from src.utils.formatting import fmt_money
from src.views.components import dark_fig


def render() -> None:
    st.title("🎯 Planificador de jubilación")
    st.caption(
        "Todo se calcula en **dinero de hoy** (la inflación se simula y se descuenta) "
        "y con **colas gordas** (t-Student): los mercados tienen crisis, el plan debe saberlo."
    )

    c1, c2, c3, c4 = st.columns(4)
    age = c1.number_input("Edad actual", 18, 80, 35)
    retire_age = c2.number_input("Edad de retiro", int(age) + 1, 90, max(65, int(age) + 1))
    capital = c3.number_input("Capital actual ($)", 0.0, 1e9, 50_000.0, step=5_000.0)
    monthly = c4.number_input("Aporte mensual ($)", 0.0, 1e6, 500.0, step=100.0)
    goal = st.number_input("Meta al retiro (en dinero de hoy, $)", 0.0, 1e10,
                           1_000_000.0, step=50_000.0)

    with st.status("Simulando 2,000 futuros posibles…"):
        sim = simulate_accumulation(int(age), int(retire_age), capital, monthly,
                                    goal=goal or None)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Escenario pesimista (P10)", fmt_money(sim["p10"]))
    m2.metric("Escenario mediano (P50)", fmt_money(sim["p50"]))
    m3.metric("Escenario optimista (P90)", fmt_money(sim["p90"]))
    if "prob_goal" in sim:
        p = sim["prob_goal"]
        m4.metric("Prob. de alcanzar tu meta", f"{p:.0%}",
                  "🟢 sólida" if p >= 0.8 else ("🟡 justa" if p >= 0.6 else "🔴 baja"),
                  delta_color="off")

    # fan chart
    months = list(range(sim["months"]))
    years_axis = [int(age) + m / 12 for m in months]
    fig = go.Figure()
    for path in sim["sample_paths"][:60]:
        fig.add_scatter(x=years_axis, y=path, mode="lines",
                        line=dict(width=0.5, color="rgba(96,165,250,.15)"),
                        showlegend=False)
    for i, (name, color) in enumerate([("P10", "#DC2626"), ("P50", "#0F172A"), ("P90", "#059669")]):
        fig.add_scatter(x=years_axis, y=sim["bands"][i], name=name,
                        line=dict(width=2.2, color=color))
    if goal:
        fig.add_hline(y=goal, line_dash="dot", line_color="#D97706",
                      annotation_text="tu meta")
    fig.update_layout(title="Patrimonio real proyectado (dinero de hoy)",
                      xaxis_title="Edad", yaxis_title="$ reales")
    st.plotly_chart(dark_fig(fig, 420), use_container_width=True)

    st.caption(
        f"Glide path automático (regla 120−edad): hoy {sim['equity_now']:.0%} en acciones, "
        f"al retiro {sim['equity_at_retire']:.0%}. Seed={sim['seed']} (reproducible)."
    )

    if goal and sim.get("prob_goal", 1) < 0.8:
        with st.status("Calculando el aporte necesario para 80% de probabilidad…"):
            req = required_monthly(goal, int(age), int(retire_age), capital)
        if req is None:
            st.error("La meta no es alcanzable ni con aportes muy altos: "
                     "considera retrasar el retiro o ajustar la meta.")
        else:
            st.info(f"💡 Para llegar a {fmt_money(goal)} con **80% de probabilidad** "
                    f"necesitarías aportar ≈ **{fmt_money(req)}/mes** "
                    f"(hoy aportas {fmt_money(monthly)}).")

    st.subheader("🏖️ Y al llegar al retiro, ¿cómo retirar sin quebrar?")
    cap_ret = st.number_input("Capital al retiro para simular ($, dinero de hoy)",
                              10_000.0, 1e10, float(max(sim["p50"], 10_000)), step=50_000.0)
    horizon = st.slider("Años de retiro a simular", 15, 45, 30)
    rows = compare_withdrawal_rules(cap_ret, years=horizon)
    labels = {"fixed_real": "4% fijo real (Bengen)", "percent": "% del saldo",
              "guyton": "Guyton-Klinger (guardrails)"}
    df = pd.DataFrame([{
        "Regla": labels[r["rule"]],
        "Prob. de quedarte sin dinero": f"{r['ruin_prob']:.0%}",
        "Ingreso anual mediano": fmt_money(r["median_income"]),
        "Ingreso anual P10 (año malo)": fmt_money(r["p10_income"]),
        "Capital final mediano": fmt_money(r["median_final"]),
    } for r in rows])
    st.dataframe(df, hide_index=True, use_container_width=True)
    st.caption(
        "**En sencillo:** la regla del 4% fijo es simple pero rígida; retirar un % del "
        "saldo nunca te deja en cero pero tu ingreso varía; Guyton-Klinger ajusta con "
        "guardrails y suele equilibrar mejor ingreso y seguridad. Portafolio 50/50 en el retiro."
    )
    st.info("🇲🇽/🇺🇸 Contexto fiscal (Afore/CETES vs. 401k/IRA) llega en una próxima fase; "
            "estas cifras son antes de impuestos.")
