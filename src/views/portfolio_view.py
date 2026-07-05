"""Vista: constructor de portafolio — optimización, riesgo, stress y Monte Carlo."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.config import DEFAULT_UNIVERSE, RISK_FREE
from src.data.market_data import get_history
from src.models.risk import monte_carlo_paths
from src.models.stress import portfolio_stress
from src.portfolio import optimizer as opt
from src.utils.formatting import fmt_num, fmt_pct
from src.views.components import dark_fig, source_caption

_METHODS = {
    "Máx. Sharpe (tangencia)": opt.max_sharpe,
    "HRP (Hierarchical Risk Parity)": opt.hrp,
    "Mínima varianza": opt.min_variance,
    "Risk parity": opt.risk_parity,
    "Pesos iguales": opt.equal_weight,
}


def render() -> None:
    st.title("💼 Constructor de portafolio")
    source_caption()

    tickers = st.multiselect("Activos (3-12)", DEFAULT_UNIVERSE,
                             default=["AAPL", "MSFT", "JNJ", "XOM", "JPM"])
    c1, c2 = st.columns(2)
    method = c1.selectbox("Método", list(_METHODS))
    rf = c2.slider("Tasa libre de riesgo", 0.0, 0.08, RISK_FREE, 0.005, format="%.3f")

    if len(tickers) < 3:
        st.info("Elige al menos 3 activos.")
        return

    with st.status("Optimizando…"):
        prices = pd.DataFrame({t: get_history(t).Close for t in tickers}).dropna()
        rets = opt.returns_matrix(prices)
        if method == "Máx. Sharpe (tangencia)":
            w = opt.max_sharpe(rets, rf)
        else:
            w = _METHODS[method](rets)
        stats = opt.portfolio_stats(w, rets, rf)

    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("Pesos")
        wdf = pd.DataFrame({"Activo": tickers, "Peso": w}).sort_values("Peso", ascending=False)
        fig = px.pie(wdf, names="Activo", values="Peso", hole=0.45)
        st.plotly_chart(dark_fig(fig), use_container_width=True)
    with c2:
        st.subheader("Contribución al riesgo")
        rc = pd.DataFrame({"Activo": tickers, "Contribución": stats["risk_contrib_pct"]})
        fig = px.bar(rc.sort_values("Contribución"), x="Contribución", y="Activo",
                     orientation="h", color_discrete_sequence=["#2563EB"])
        fig.update_layout(xaxis_tickformat=".0%")
        st.plotly_chart(dark_fig(fig), use_container_width=True)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Retorno anual", fmt_pct(stats["ann_return"] * 100))
    m2.metric("Volatilidad", fmt_pct(stats["ann_vol"] * 100, signed=False))
    m3.metric("Sharpe", fmt_num(stats["sharpe"]))
    m4.metric("Máx. drawdown", fmt_pct(stats["max_drawdown"] * 100))
    m5.metric("CVaR 95% (día)", fmt_pct(stats["cvar95_d"] * 100, signed=False))

    st.subheader("🧨 Stress testing — ¿qué pasa si…?")
    sdf = portfolio_stress(tickers, w)
    st.dataframe(
        sdf.style.map(
            lambda v: "color:#DC2626" if isinstance(v, float) and v < 0 else "color:#059669",
            subset=["P&L estimado %"],
        ),
        hide_index=True, use_container_width=True,
    )
    st.caption("Shocks direccionales por sector calibrados con episodios históricos "
               "análogos. Mapa de exposición, no pronóstico.")

    st.subheader("Frontera (nube de portafolios aleatorios)")
    cloud = opt.random_frontier(rets, rf=rf)
    fig = px.scatter(cloud, x="vol", y="ret", color="sharpe",
                     color_continuous_scale="Tealgrn",
                     labels={"vol": "Volatilidad", "ret": "Retorno esperado"})
    fig.add_scatter(x=[stats["ann_vol"]], y=[stats["ann_return"]], mode="markers",
                    marker=dict(size=14, color="#DC2626", symbol="star"), name="Tu portafolio")
    st.plotly_chart(dark_fig(fig, 380), use_container_width=True)

    st.subheader("Proyección Monte Carlo (colas gordas, 5 años, base 100)")
    mc = monte_carlo_paths(stats["ann_return"], stats["ann_vol"], years=5, n_paths=800)
    paths = mc["paths"]
    fig = go.Figure()
    for i in range(0, 60):
        fig.add_scatter(y=paths[i], mode="lines",
                        line=dict(width=0.6, color="rgba(37,99,235,.20)"),
                        showlegend=False)
    st.plotly_chart(dark_fig(fig, 340), use_container_width=True)
    st.caption(
        f"**En sencillo:** de 100 invertidos, en 5 años el escenario mediano termina en "
        f"{mc['p50']:.0f}; el pesimista (P10) en {mc['p10']:.0f} y el optimista (P90) en "
        f"{mc['p90']:.0f}. Probabilidad de acabar con pérdida: {mc['prob_loss']:.0%}. "
        f"Simulación t-Student (colas realistas), seed={mc['seed']}."
    )

    with st.expander("🇲🇽 Ver este portafolio en pesos mexicanos (riesgo cambiario)"):
        from src.data.market_data import get_fx_history
        from src.models.fx import currency_decomposition
        dec = currency_decomposition(stats["daily_returns"], get_fx_history("MXN=X"))
        if not dec.get("ok"):
            st.info("Historial FX insuficiente para descomponer.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Retorno anual en USD", fmt_pct(dec["ann_usd"] * 100))
            c2.metric("Efecto cambiario USD/MXN", fmt_pct(dec["ann_fx"] * 100))
            c3.metric("Retorno anual en MXN", fmt_pct(dec["ann_mxn"] * 100))
            c1, c2, c3 = st.columns(3)
            c1.metric("Volatilidad en USD", fmt_pct(dec["vol_usd"] * 100, signed=False))
            c2.metric("Volatilidad del peso", fmt_pct(dec["vol_fx"] * 100, signed=False))
            c3.metric("Volatilidad en MXN", fmt_pct(dec["vol_mxn"] * 100, signed=False))
            corr = dec["corr"]
            nota = ("amortigua" if corr < -0.1 else ("amplifica" if corr > 0.1 else "casi no altera"))
            st.caption(
                f"**En sencillo:** si vives y gastas en pesos, tu retorno real incluye al "
                f"tipo de cambio. La correlación portafolio-peso es {corr:+.2f}, así que el "
                f"peso {nota} tu riesgo total ({dec['n_days']} días de historia)."
            )
