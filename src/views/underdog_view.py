"""Vista: Underdog Score — castigadas por precio, sólidas por fundamentos."""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from src.config import DEFAULT_UNIVERSE, SECTOR_OF
from src.underdog.underdog import scan
from src.views.components import dark_fig, download_df, source_caption


def render() -> None:
    st.title("🐤 Underdog Scanner")
    st.caption(
        "Busca empresas **castigadas por el mercado pero sólidas por dentro**: "
        "valor (earnings yield) + calidad (ROE, caja) + castigo (caída desde máx. 52s, "
        "solo cuenta si hay calidad — evita value traps) + giro de momentum."
    )
    source_caption()

    sectors = ["Todos"] + sorted(set(SECTOR_OF.values()))
    sector = st.selectbox("Sector", sectors)
    universe = DEFAULT_UNIVERSE if sector == "Todos" else [
        t for t, s in SECTOR_OF.items() if s == sector
    ]

    if st.button("🔎 Escanear universo", type="primary"):
        with st.status(f"Analizando {len(universe)} empresas…"):
            df = scan(universe)
        if df.empty:
            st.info("Sin resultados para este universo.")
            return
        st.session_state["underdog_df"] = df

    df = st.session_state.get("underdog_df")
    if df is None:
        st.info("Elige un sector y pulsa **Escanear universo**.")
        return

    top = df.head(10)
    fig = px.bar(top, x="score", y="ticker", orientation="h", color="score",
                 color_continuous_scale=["#475569", "#60a5fa", "#34d399"],
                 hover_data=["name", "drawdown_52w_pct"])
    fig.update_layout(yaxis=dict(autorange="reversed"))
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(dark_fig(fig), use_container_width=True)

    show = df.rename(columns={
        "ticker": "Ticker", "name": "Nombre", "sector": "Sector", "score": "Underdog",
        "value": "Valor", "quality": "Calidad", "beaten": "Castigo",
        "turnaround": "Giro", "drawdown_52w_pct": "% desde máx",
    })[["Ticker", "Nombre", "Sector", "Underdog", "Valor", "Calidad", "Castigo", "Giro", "% desde máx"]]
    st.dataframe(show, hide_index=True, use_container_width=True)
    download_df(show, "jubilatec_underdog.csv")
    st.caption("Haz clic en un ticker y análizalo a fondo con el buscador de la barra lateral.")
