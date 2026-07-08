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

    from src.screener.engine import load_screener
    scr = load_screener()
    if scr and scr.get("rows"):
        if st.toggle(f"🌙 Universo ampliado — screener nocturno "
                     f"({scr['n']} empresas · {scr['date']})", value=True):
            import pandas as pd
            sdf = pd.DataFrame(scr["rows"])
            secs = ["Todos"] + sorted(sdf["sector"].dropna().unique().tolist())
            sec = st.selectbox("Sector", secs, key="scr_sector")
            if sec != "Todos":
                sdf = sdf[sdf["sector"] == sec]
            top = sdf.head(10)
            fig = px.bar(top, x="score", y="ticker", orientation="h", color="score",
                         color_continuous_scale=["#94A3B8", "#2563EB", "#059669"],
                         hover_data=["name", "desde_max_pct"])
            fig.update_layout(yaxis=dict(autorange="reversed"))
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(dark_fig(fig), use_container_width=True)
            show = sdf.rename(columns={
                "ticker": "Ticker", "name": "Nombre", "sector": "Sector",
                "price": "Precio", "score": "Score", "calidad": "Calidad",
                "tecnico": "Técnico", "valoracion": "Valoración",
                "upside_pct": "Upside %", "mom_6m": "Mom 6m %",
                "desde_max_pct": "% desde máx",
            })
            st.dataframe(show, hide_index=True, use_container_width=True, height=480)
            download_df(show, "jubilatec_screener.csv")
            st.caption(
                f"Score de screening (calidad 35 · técnico 35 · valoración 30), "
                f"pre-calculado de madrugada — fuente {scr['source']}. Para el "
                "score completo (con noticias, forense y régimen), analiza el "
                "ticker en la barra lateral."
            )
            return
        st.divider()

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
                 color_continuous_scale=["#94A3B8", "#2563EB", "#059669"],
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
