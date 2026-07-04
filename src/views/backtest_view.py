"""Vista: laboratorio de backtesting — señales y portafolios, con honestidad estadística."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.config import DEFAULT_UNIVERSE
from src.backtest.engine import backtest_momentum, backtest_portfolio
from src.portfolio import optimizer as opt
from src.utils.formatting import fmt_num, fmt_pct
from src.views.components import dark_fig, source_caption

_METHODS = {
    "HRP": opt.hrp,
    "Máx. Sharpe": opt.max_sharpe,
    "Mínima varianza": opt.min_variance,
    "Risk parity": opt.risk_parity,
}


def render() -> None:
    st.title("🧪 Laboratorio de backtesting")
    st.warning(
        "**Honestidad estadística:** universo actual (posible sesgo de supervivencia); "
        "solo señales de precio son point-in-time por ahora. Un backtest sin estas "
        "advertencias es marketing, no ciencia."
    )
    source_caption()

    st.subheader("1️⃣ ¿Funciona el momentum 12-1 en este universo?")
    st.caption("Señal clásica de Jegadeesh-Titman: retorno de 12 meses saltando el último. "
               "Se forman 3 grupos por ranking y se mide el retorno de los 3 meses siguientes.")
    if st.button("▶️ Backtest de momentum", type="primary"):
        with st.status("Corriendo walk-forward…"):
            r = backtest_momentum(DEFAULT_UNIVERSE)
        if not r["ok"]:
            st.error("Historial insuficiente para el backtest.")
        else:
            q = r["quantile_returns_ann"]
            fig = go.Figure(go.Bar(
                x=["Perdedores (Q1)", "Medio (Q2)", "Ganadores (Q3)"],
                y=[v * 100 for v in q],
                marker_color=["#f87171", "#94a3b8", "#34d399"],
            ))
            fig.update_layout(title="Retorno anualizado por grupo de momentum",
                              yaxis_title="% anual")
            st.plotly_chart(dark_fig(fig, 320), use_container_width=True)
            lo, hi = r["spread_ci_ann"]
            c1, c2, c3 = st.columns(3)
            c1.metric("Spread ganadores−perdedores", fmt_pct(r["spread_ann"] * 100))
            c2.metric("IC 95% (bootstrap bloques)",
                      f"[{lo * 100:+.1f}%, {hi * 100:+.1f}%]")
            c3.metric("Hit rate", f"{r['hit_rate']:.0%} de {r['n_obs']} fechas")
            if r["significant"]:
                st.success("El IC 95% no cruza cero: la señal es estadísticamente "
                           "distinguible de ruido **en esta muestra**.")
            else:
                st.info("El IC 95% cruza cero: con estos datos NO se puede afirmar que "
                        "la señal funcione. Así se ve la honestidad estadística.")

    st.subheader("2️⃣ ¿El optimizador le gana a pesos iguales, después de costos?")
    c1, c2, c3 = st.columns(3)
    tickers = c1.multiselect("Activos", DEFAULT_UNIVERSE,
                             default=["AAPL", "MSFT", "JNJ", "XOM", "JPM", "WMT"])
    method = c2.selectbox("Método", list(_METHODS))
    cost = c3.slider("Costo por rebalanceo (bps)", 0, 50, 10)
    if len(tickers) >= 3 and st.button("▶️ Backtest walk-forward de portafolio"):
        with st.status("Estimando con pasado, aplicando al futuro, cobrando costos…"):
            r = backtest_portfolio(tickers, _METHODS[method], cost_bps=float(cost))
        fig = go.Figure()
        fig.add_scatter(x=r["dates"], y=r["curve_method"], name=method,
                        line=dict(color="#34d399", width=2))
        fig.add_scatter(x=r["dates"], y=r["curve_equal"], name="Pesos iguales",
                        line=dict(color="#94a3b8", width=2, dash="dot"))
        fig.update_layout(title=f"Curva out-of-sample (neta de {cost} bps, "
                                f"{r['n_rebalances']} rebalanceos)")
        st.plotly_chart(dark_fig(fig, 360), use_container_width=True)
        sm, se = r["stats_method"], r["stats_equal"]
        rows = st.columns(4)
        rows[0].metric("Retorno anual", fmt_pct(sm["ann_return"] * 100),
                       f"vs {se['ann_return'] * 100:+.1f}% equal")
        rows[1].metric("Sharpe", fmt_num(sm["sharpe"]),
                       f"vs {se['sharpe']:.2f} equal" if se["sharpe"] else "")
        rows[2].metric("Máx. drawdown", fmt_pct(sm["max_drawdown"] * 100),
                       f"vs {se['max_drawdown'] * 100:.1f}% equal")
        rows[3].metric("Valor final (base 1)", fmt_num(sm["final"]),
                       f"vs {se['final']:.2f} equal")
        st.caption("Si el método no supera a pesos iguales tras costos, esa también es "
                   "una conclusión valiosa: la simplicidad es difícil de vencer (DeMiguel 2009).")
