"""Vista: estado de fuentes de datos y cómo activar cada una."""
from __future__ import annotations

import streamlit as st

from src.config import get_settings
from src.data.dbx import backend, ping
from src.data.market_data import using_sample, yf_status


def render() -> None:
    st.title("🛰️ Fuentes de datos")
    s = get_settings()

    rows = [
        ("Mercado (precios/fundamentales)", "yfinance + Stooq",
         ("🧪 sintético (JT_FORCE_SAMPLE)" if using_sample()
          else ("🟢 activo" if yf_status()[0]
                else "🟡 yfinance roto — Stooq al rescate")),
         ("Sin clave; automático con internet."
          if yf_status()[0] else f"Error de yfinance: {yf_status()[1][:80]}")),
        ("Noticias", "NewsAPI / yfinance",
         "🟢 activo" if s.has_news() else "🟡 fallback", "Agrega NEWSAPI_KEY en `.env`."),
        ("Macro", "FRED",
         "🟢 activo" if s.has_fred() else "🟡 fallback", "Agrega FRED_API_KEY en `.env` (gratis)."),
        ("Fundamentales 10-K + insiders", "SEC EDGAR", "🟢 activo (fallback 🧪)", "Sin clave; requiere internet."),
        ("Contratos gob.", "USAspending.gov", "🧩 planificado", "Fase 3 del Plan Maestro."),
        ("Base de datos (clientes, listas)", "Turso / SQLite",
         ("🟢 Turso — conectada" if ping()[0] else "🔴 Turso — ERROR (ver abajo)")
         if backend() == "turso" else "🟡 SQLite local",
         "Agrega TURSO_DATABASE_URL y TURSO_AUTH_TOKEN en Secrets de AMBAS apps."),
    ]
    for name, provider, status, how in rows:
        c1, c2, c3, c4 = st.columns([2, 1.4, 1, 2.6])
        c1.markdown(f"**{name}**")
        c2.markdown(provider)
        c3.markdown(status)
        c4.caption(how)

    if backend() == "turso":
        ok, msg = ping()
        if not ok:
            st.error(f"Detalle del error Turso: {msg}")

    st.divider()
    st.markdown(
        "**Degradación elegante:** si una fuente falla o falta la clave, la app usa "
        "el siguiente proveedor o el generador sintético determinista (misma serie "
        "siempre para cada ticker), marcado con 🧪. Nada se rompe."
    )
    st.markdown(
        "**Agregar un proveedor nuevo:** crea `src/data/<proveedor>.py` con las mismas "
        "firmas de `market_data.py` y enlázalo ahí. El resto de la app no cambia."
    )
