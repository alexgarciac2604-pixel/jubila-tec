"""
AL-X Studio — institutional-grade equity & market analysis.

Run:  streamlit run app.py

The analytical core lives in `src/` (pure Python). This file is only the
Streamlit shell: theme, ticker tape, navigation and routing.
"""
from __future__ import annotations

import streamlit as st

# ---- page config MUST be the first Streamlit call -------------------------
st.set_page_config(
    page_title="AL-X Studio",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src import __version__
from src.config import DISCLAIMER, get_settings
from src.utils.styles import inject_css
from src.views import (advisor_view, about, alerts_view, backtest_view, clients_view, copilot_view, dashboard, macro_view,
                       markets_view, news_view, portfolio_view,
                       retirement_view, sources_view, stock, underdog_view)
from src.views.components import render_ticker_tape

inject_css()

# --- session defaults ------------------------------------------------------
st.session_state.setdefault("ticker", "AAPL")
st.session_state.setdefault("page", "🌐 Dashboard")

# --- top ticker tape -------------------------------------------------------
render_ticker_tape()

PAGES = [
    "🌐 Dashboard",
    "🤖 Copiloto",
    "🧠 Mesa del Asesor",
    "🔍 Análisis de Acción",
    "🗺️ Mercados",
    "🐤 Underdog",
    "💼 Portafolio",
    "👥 Clientes",
    "🎯 Jubilación",
    "🧪 Backtesting",
    "🌍 Macro & Geopolítica",
    "🔔 Alertas",
    "📰 Noticias",
    "🛰️ Fuentes",
    "📚 Modelos & Compliance",
]

# --- sidebar ---------------------------------------------------------------
with st.sidebar:
    from src.utils.branding import logo_html
    st.markdown(
        logo_html(120, centrado=False) +
        f"<div style='color:#64748B;font-size:.74rem;margin:-2px 0 1.2rem'>"
        f"Studio · v{__version__}</div>",
        unsafe_allow_html=True,
    )

    st.markdown("**🔎 Buscar acción**")
    typed = st.text_input("Ticker", value=st.session_state["ticker"],
                          label_visibility="collapsed",
                          placeholder="Ej. AAPL, NVDA, MSFT").upper().strip()
    if st.button("Analizar acción", use_container_width=True, type="primary"):
        from src.data.market_data import resolve_symbol
        st.session_state["ticker"] = resolve_symbol(typed) or typed or "AAPL"
        st.session_state["page"] = "🔍 Análisis de Acción"
        st.rerun()

    if st.button("🔄 Actualizar datos", use_container_width=True):
        from jobs.daily_update import clear_caches
        from datetime import datetime as _dt
        clear_caches()
        st.session_state["last_refresh"] = _dt.now().strftime("%H:%M")
        st.rerun()
    st.caption("Última actualización: "
               + st.session_state.get("last_refresh", "al abrir la app")
               + " · datos con caché de 2-30 min")

    st.session_state["pro_mode"] = st.toggle(
        "Modo Pro", value=st.session_state.get("pro_mode", True),
        help="Apágalo para ver solo lo esencial en lenguaje sencillo.")

    st.divider()
    choice = st.radio(
        "Navegación", PAGES,
        index=PAGES.index(st.session_state["page"]) if st.session_state["page"] in PAGES else 0,
        label_visibility="collapsed",
    )
    st.session_state["page"] = choice

    st.divider()
    s = get_settings()
    st.markdown("**Estado de fuentes**")
    st.caption(("🟢" if not s.force_sample else "🧪") + " yfinance/Stooq · mercado")
    st.caption(("🟢" if s.has_news() else "🟡") + " NewsAPI · noticias")
    st.caption(("🟢" if s.has_fred() else "🟡") + " FRED · macro")
    st.caption("🟡 = requiere clave (usa fallback). Configúralas en `.env`.")

# --- routing ---------------------------------------------------------------
page = st.session_state["page"]
_routes = {
    "🌐 Dashboard": dashboard.render,
    "🤖 Copiloto": copilot_view.render,
    "🧠 Mesa del Asesor": advisor_view.render,
    "🗺️ Mercados": markets_view.render,
    "🐤 Underdog": underdog_view.render,
    "💼 Portafolio": portfolio_view.render,
    "👥 Clientes": clients_view.render,
    "🎯 Jubilación": retirement_view.render,
    "🧪 Backtesting": backtest_view.render,
    "🌍 Macro & Geopolítica": macro_view.render,
    "📰 Noticias": news_view.render,
    "🔔 Alertas": alerts_view.render,
    "🛰️ Fuentes": sources_view.render,
    "📚 Modelos & Compliance": about.render,
}
if page == "🔍 Análisis de Acción":
    stock.render(st.session_state["ticker"])
else:
    _routes.get(page, dashboard.render)()

# --- global disclaimer footer ---------------------------------------------
st.divider()
st.caption(DISCLAIMER)
