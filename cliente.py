"""
◆ AL-X — Portal de Clientes (app standalone).

Segunda app del mismo repo: SOLO login + panel del cliente. Sin terminal,
sin administración. Desplegar en Streamlit Cloud con Main file = cliente.py.

Diseño v0.14 — "private banking": fondo marfil, texto carbón, bordes de oro
metálico sutil, acento verde bosque y CTAs de cristal líquido (liquid glass).

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
from src.views.clients_view import _client_panel

# --- tema marfil / carbón / oro (exclusivo del Portal) -----------------------
_LUX_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

/* lienzo marfil, texto carbón */
.stApp { background: #FAF7F0; }
html, body, [class*="css"] { font-family:'Inter',sans-serif; color:#1C1917; }
h1 { font-family:'Playfair Display',serif !important; font-weight:700 !important;
     letter-spacing:-0.02em; color:#1C1917 !important; }
h2, h3 { font-weight:700 !important; letter-spacing:-0.01em; color:#1C1917 !important; }
.block-container { padding-top:2rem; padding-bottom:3.5rem; max-width:1180px; }
section[data-testid="stSidebar"], div[data-testid="collapsedControl"] { display:none; }

/* tarjetas: marfil claro + borde dorado fino */
div[data-testid="stMetric"] {
  background:#FFFEFA;
  border:1px solid rgba(198,167,94,.45);
  border-radius:18px; padding:20px 24px;
  box-shadow:0 1px 2px rgba(28,25,23,.04);
  transition:box-shadow .25s ease, transform .25s ease;
}
div[data-testid="stMetric"]:hover {
  box-shadow:0 10px 28px rgba(28,25,23,.08); transform:translateY(-1px);
}
div[data-testid="stMetric"] label { color:#78716C; font-weight:500; }

/* CTA liquid glass: vidrio orgánico sobre verde bosque, borde de oro 1px */
button[kind="primary"], div[data-testid="stFormSubmitButton"] > button {
  position:relative; overflow:hidden;
  background:
    linear-gradient(180deg, rgba(255,255,255,.32) 0%, rgba(255,255,255,.07) 46%,
                    rgba(0,0,0,.12) 100%), #1B4D3E !important;
  color:#FFFFFF !important;
  border:1px solid rgba(214,183,110,.9) !important;
  border-radius:14px !important;
  backdrop-filter:blur(7px); -webkit-backdrop-filter:blur(7px);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.38),
             inset 0 -1px 0 rgba(0,0,0,.18),
             0 6px 20px rgba(27,77,62,.20);
  transition:all .22s ease;
}
button[kind="primary"]:hover, div[data-testid="stFormSubmitButton"] > button:hover {
  transform:translateY(-1px);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.5), 0 10px 26px rgba(27,77,62,.30);
  border-color:#D6B76E !important;
}
/* reflejo superior del cristal */
button[kind="primary"]::before, div[data-testid="stFormSubmitButton"] > button::before {
  content:""; position:absolute; top:0; left:6%; right:6%; height:46%;
  background:linear-gradient(180deg, rgba(255,255,255,.35), rgba(255,255,255,0));
  border-radius:12px 12px 40% 40%; pointer-events:none;
}

/* botones secundarios: cristal marfil con borde dorado, texto carbón */
button[kind="secondary"] {
  background:linear-gradient(180deg, rgba(255,255,255,.75), rgba(250,247,240,.4)) !important;
  color:#1C1917 !important;
  border:1px solid rgba(198,167,94,.55) !important; border-radius:12px !important;
  backdrop-filter:blur(5px);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.6);
}

/* pestañas: acento verde bosque con subrayado dorado */
button[data-baseweb="tab"] { font-weight:600; color:#78716C; }
button[data-baseweb="tab"][aria-selected="true"] { color:#1B4D3E; }
div[data-baseweb="tab-highlight"] { background-color:#C6A75E !important; }

/* contenedores, expanders, inputs */
div[data-testid="stExpander"] {
  border:1px solid rgba(198,167,94,.4); border-radius:16px; background:#FFFEFA;
}
div[data-baseweb="input"], div[data-baseweb="textarea"] {
  border-radius:12px;
}

/* badges dorados */
.jt-badge {
  display:inline-block; padding:4px 14px; border-radius:999px;
  font-size:.78rem; font-weight:500; background:#FFFEFA; color:#57534E;
  border:1px solid rgba(198,167,94,.55); margin-right:4px;
}

/* ticker tape sobre marfil */
.jt-tape {
  overflow:hidden; white-space:nowrap; background:#FFFEFA;
  border-top:1px solid rgba(198,167,94,.35);
  border-bottom:1px solid rgba(198,167,94,.35);
  padding:8px 0; margin-bottom:12px;
}
.jt-tape-inner {
  display:inline-block; animation:jt-scroll 45s linear infinite;
  font-family:'Inter',monospace; font-size:.85rem; font-weight:500;
}
.jt-tape-inner span { margin:0 20px; color:#44403C; }
.jt-up { color:#0E6B45 !important; font-weight:600; }
.jt-down { color:#B42318 !important; font-weight:600; }
@keyframes jt-scroll { 0% {transform:translateX(0);} 100% {transform:translateX(-50%);} }

hr { border-color:rgba(198,167,94,.35); }
</style>
"""
st.markdown(_LUX_CSS, unsafe_allow_html=True)

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

# --- pantalla de acceso -------------------------------------------------------
_, centro, _ = st.columns([1, 1.3, 1])
with centro:
    st.markdown(
        "<div style='text-align:center;margin-top:7vh'>"
        "<div style='font-family:Playfair Display,serif;font-weight:700;"
        "font-size:3.2rem;letter-spacing:-0.02em;color:#1C1917'>AL·X</div>"
        "<div style='width:64px;height:1px;background:#C6A75E;margin:14px auto'></div>"
        "<div style='color:#78716C;margin-bottom:2rem;letter-spacing:.06em;"
        "text-transform:uppercase;font-size:.8rem'>Portal privado de clientes</div>"
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
