"""
◆ AL-X — Portal de Clientes (app standalone).

Segunda app del mismo repo: SOLO login + panel del cliente. Sin terminal,
sin administración. Desplegar en Streamlit Cloud con Main file = cliente.py.

Run local:  streamlit run cliente.py
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="AL-X · Portal de Clientes",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from src.clients.manager import verify_client
from src.config import get_secret
from src.utils.styles import inject_css
from src.views.clients_view import _client_panel

inject_css()
st.markdown(  # sin sidebar: esta app es solo para clientes
    "<style>section[data-testid='stSidebar'], "
    "div[data-testid='collapsedControl'] {display:none;}</style>",
    unsafe_allow_html=True,
)

MAX_INTENTOS = 5
_contacto = get_secret("ALX_CONTACTO") or "tu asesor AL-X"


def _footer() -> None:
    st.markdown("---")
    st.caption(f"◆ AL-X · Portal privado de clientes · ¿Dudas? Contacta a {_contacto}. "
               "Información educativa con datos públicos; no constituye asesoría "
               "de inversión ni garantiza rendimientos.")


if "client_auth" in st.session_state:
    _client_panel(st.session_state["client_auth"])
    _footer()
    st.stop()

# --- pantalla de acceso -----------------------------------------------------
_, centro, _ = st.columns([1, 1.3, 1])
with centro:
    st.markdown(
        "<div style='text-align:center;margin-top:8vh'>"
        "<div style='font-family:Playfair Display,serif;font-weight:700;"
        "font-size:3rem;letter-spacing:-0.02em'>AL·X</div>"
        "<div style='color:#64748B;margin-bottom:2rem'>Portal privado de clientes</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    from src.data.dbx import backend, ping
    if backend() != "turso":
        st.warning("⚠️ Este portal usa una base LOCAL: faltan TURSO_DATABASE_URL "
                   "y TURSO_AUTH_TOKEN en los Secrets de ESTA app, así que no ve "
                   "los clientes creados en el Studio.")
    else:
        _ok, _msg = ping()
        if not _ok:
            st.error(f"⚠️ Sin conexión a la base compartida: {_msg}")

    intentos = st.session_state.get("login_intentos", 0)
    if intentos >= MAX_INTENTOS:
        st.error("Demasiados intentos fallidos. Cierra esta pestaña, espera unos "
                 f"minutos e inténtalo de nuevo, o contacta a {_contacto}.")
    else:
        with st.form("acceso"):
            who = st.text_input("Número de cliente o nombre",
                                placeholder="C-001 o Juan Pérez")
            pin = st.text_input("PIN", type="password")
            if st.form_submit_button("Entrar", type="primary",
                                     use_container_width=True):
                cli = verify_client(who, pin)
                if cli:
                    st.session_state["client_auth"] = cli
                    st.session_state["login_intentos"] = 0
                    st.rerun()
                st.session_state["login_intentos"] = intentos + 1
                restantes = MAX_INTENTOS - st.session_state["login_intentos"]
                st.error(f"Cliente o PIN incorrectos. Intentos restantes: {restantes}.")

_footer()
