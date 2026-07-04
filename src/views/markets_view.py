"""Vista: panorama de mercados — universo completo y desempeño sectorial."""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from src.config import DEFAULT_UNIVERSE
from src.data.market_data import get_quotes
from src.views.components import dark_fig, download_df, source_caption


def render() -> None:
    st.title("🗺️ Mercados")
    source_caption()

    df = get_quotes(DEFAULT_UNIVERSE)

    st.subheader("Desempeño por sector (hoy)")
    sec = df.groupby("sector")["change_pct"].mean().sort_values()
    fig = px.bar(sec, orientation="h",
                 color=sec.values, color_continuous_scale=["#f87171", "#94a3b8", "#34d399"],
                 labels={"value": "% cambio", "sector": ""})
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(dark_fig(fig), use_container_width=True)

    st.subheader("Universo")
    show = df[["ticker", "name", "sector", "price", "change_pct", "from_52w_high_pct"]]
    show = show.rename(columns={
        "ticker": "Ticker", "name": "Nombre", "sector": "Sector",
        "price": "Precio", "change_pct": "% Día", "from_52w_high_pct": "% desde máx 52s",
    })
    st.dataframe(
        show.style.format({"Precio": "${:.2f}", "% Día": "{:+.2f}%", "% desde máx 52s": "{:+.1f}%"}),
        hide_index=True, use_container_width=True, height=520,
    )
    download_df(show, "jubilatec_mercados.csv")
