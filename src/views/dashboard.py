"""Vista: Dashboard global — índices, heatmap sectorial, movers, macro."""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from src.config import DEFAULT_UNIVERSE
from src.data.market_data import get_quote, get_quotes
from src.macro.macro import curve_signal, get_macro_series, yield_curve
from src.views.components import dark_fig, source_caption


def render() -> None:
    st.title("🌐 Dashboard global")
    if not st.session_state.get("onboarded"):
        with st.container(border=True):
            st.markdown("### 👋 Bienvenido a Jubila-Tec — 3 pasos para empezar")
            c1, c2, c3 = st.columns(3)
            c1.markdown("**1️⃣ Analiza una acción**\n\nEscribe un ticker en la "
                        "barra lateral (ej. AAPL) o pregúntale al 🤖 Copiloto "
                        "\"¿qué te parece apple?\".")
            c2.markdown("**2️⃣ Arma tu plan**\n\nEn 🎯 Jubilación pon tu edad, "
                        "aporte y meta: verás 2,000 futuros posibles en dinero de hoy.")
            c3.markdown("**3️⃣ Hazlo tuyo**\n\nCrea 🔔 Alertas, apaga el Modo Pro "
                        "si prefieres lo sencillo, y programa la actualización diaria.")
            if st.button("Entendido, no volver a mostrar"):
                st.session_state["onboarded"] = True
                st.rerun()

    source_caption()

    cols = st.columns(4)
    for col, t in zip(cols, ["SPY", "QQQ", "DIA", "GLD"]):
        q = get_quote(t)
        col.metric(q["name"], f"${q['price']:.2f}", f"{q['change_pct']:+.2f}%")

    with st.expander("🌅 Briefing de hoy (en sencillo)", expanded=False):
        from src.report.briefing import daily_briefing
        from src.alerts.engine import send_telegram, telegram_configured
        brief = daily_briefing()
        st.markdown(brief)
        if telegram_configured() and st.button("📨 Enviármelo a Telegram"):
            ok = send_telegram(brief.replace("**", "").replace("*", ""))
            st.success("Enviado." if ok else "No se pudo enviar; revisa el token.")

    from src.models.regime import market_regime
    reg = market_regime()
    st.markdown(f"### {reg['emoji']} Régimen de mercado: **{reg['name']}**")
    st.caption(f"{reg['description']} Prob. de turbulencia (10d): {reg['p_turbulent']:.0%} · "
               f"vol. calma {reg['sigma_calm_ann']:.0%} vs. turbulencia {reg['sigma_turb_ann']:.0%} "
               f"(GMM 2 estados sobre {reg['bench']}). En turbulencia, el score reduce el peso "
               "del momentum y sube calidad/forense.")

    st.subheader("🗺️ Heatmap sectorial")
    df = get_quotes(DEFAULT_UNIVERSE)
    fig = px.treemap(
        df, path=["sector", "ticker"], values=df["price"].abs(),
        color="change_pct", color_continuous_scale=["#f87171", "#1e293b", "#34d399"],
        range_color=[-3, 3], hover_data={"change_pct": ":.2f"},
    )
    st.plotly_chart(dark_fig(fig, 420), use_container_width=True)

    c1, c2 = st.columns(2)
    movers = df.sort_values("change_pct")
    with c1:
        st.subheader("📈 Ganadores del día")
        st.dataframe(
            movers.tail(5)[["ticker", "name", "price", "change_pct"]].iloc[::-1],
            hide_index=True, use_container_width=True,
        )
    with c2:
        st.subheader("📉 Perdedores del día")
        st.dataframe(
            movers.head(5)[["ticker", "name", "price", "change_pct"]],
            hide_index=True, use_container_width=True,
        )

    st.subheader("🌍 Pulso macro")
    series = get_macro_series()
    mcols = st.columns(4)
    for col, name in zip(mcols, [k for k in series if k != "source"]):
        s = series[name]
        col.metric(name, f"{s.iloc[-1]:.2f}", f"{s.iloc[-1] - s.iloc[-2]:+.2f}")
    st.caption(curve_signal(yield_curve()) + f" · Fuente macro: {series['source']}")
