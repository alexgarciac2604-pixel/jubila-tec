"""Vista: noticias agregadas del universo con sentimiento y filtros."""
from __future__ import annotations

import streamlit as st

from src.config import TAPE_TICKERS
from src.geopolitics.events import classify_text
from src.news.news_feed import get_news
from src.views.components import source_caption


def render() -> None:
    st.title("📰 Noticias & Sentimiento")
    source_caption()

    from src.data.store import watchlist as _my_list
    from src.config import DEFAULT_UNIVERSE
    wl = _my_list()
    options = list(dict.fromkeys(DEFAULT_UNIVERSE + TAPE_TICKERS + wl))
    default = [t for t in (wl or ["AAPL", "MSFT", "NVDA", "TSLA"]) if t in options][:8]
    tickers = st.multiselect("Tickers a seguir", options, default=default)
    tone = st.radio("Filtro", ["Todas", "🟢 positivas", "🔴 negativas"], horizontal=True)

    items = []
    for t in tickers:
        for it in get_news(t, n=5):
            it["ticker"] = t
            items.append(it)
    items.sort(key=lambda x: x.get("date", ""), reverse=True)

    if tone == "🟢 positivas":
        items = [i for i in items if i["sentiment"] > 0.15]
    elif tone == "🔴 negativas":
        items = [i for i in items if i["sentiment"] < -0.15]

    if not items:
        st.info("No hay noticias con este filtro. Prueba con otros tickers o filtro.")
        return

    for it in items:
        geo = classify_text(it["title"])
        geo_tag = f" · ♟️ {geo['event']}" if geo else ""
        ev = it.get("event")
        if ev:
            geo_tag += f" · {ev['label']} (impacto típico: {ev['impact']})"
        st.markdown(
            f"{it['label']} **[{it['ticker']}]** {it['title']}  \n"
            f"<span style='color:#64748b'>{it['publisher']} · {it['date']}{geo_tag}</span>",
            unsafe_allow_html=True,
        )
