"""Vista: macro (series + curva de rendimientos) y geopolítica (evento→sector)."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.geopolitics.events import EVENTS
from src.macro.macro import curve_signal, get_macro_series, yield_curve
from src.views.components import dark_fig, source_caption


def render() -> None:
    st.title("🌍 Macro & Geopolítica")
    source_caption()

    series = get_macro_series()
    st.caption(f"Fuente macro: {series['source']}"
               + (" — agrega FRED_API_KEY en `.env` para datos reales." if series["source"] == "sample" else ""))
    names = [k for k in series if k != "source"]
    c1, c2 = st.columns(2)
    for i, name in enumerate(names):
        fig = px.line(series[name], labels={"value": "", "index": ""}, title=name)
        fig.update_traces(line_color="#60a5fa")
        (c1 if i % 2 == 0 else c2).plotly_chart(dark_fig(fig, 260), use_container_width=True)

    st.subheader("📉 Curva de rendimientos (Tesoro EE.UU.)")
    curve = yield_curve()
    fig = px.line(curve, markers=True, labels={"value": "%", "index": "Plazo"})
    fig.update_traces(line_color="#fbbf24")
    st.plotly_chart(dark_fig(fig, 300), use_container_width=True)
    st.info(curve_signal(curve))

    st.subheader("♟️ Radar geopolítico: evento → impacto sectorial")
    ev_names = [e["event"] for e in EVENTS]
    chosen = st.selectbox("Escenario", ev_names)
    ev = EVENTS[ev_names.index(chosen)]
    st.markdown(f"**Región:** {ev['region']} — {ev['note']}")
    imp = pd.Series(ev["impacts"]).sort_values()
    fig = px.bar(imp, orientation="h", color=imp.values,
                 color_continuous_scale=["#f87171", "#94a3b8", "#34d399"],
                 range_color=[-2, 2], labels={"value": "impacto (-2 a +2)", "index": ""})
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(dark_fig(fig, 300), use_container_width=True)
    st.caption("Dirección esperada, no magnitud. Úsalo como mapa de exposición, no como pronóstico.")
