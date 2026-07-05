"""Sistema de diseño Jubila-Tec — tema claro premium.

Lenguaje visual: fondo blanco, aire generoso, esmeralda como acento,
Inter para todo y Playfair Display solo para énfasis de títulos.
Inspiración: Apple, Stripe, Linear — institucional, no template.
"""
from __future__ import annotations

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #0F172A; }
h1 { font-family: 'Playfair Display', serif !important; font-weight: 700 !important;
     letter-spacing: -0.02em; color: #0F172A !important; }
h2, h3 { font-family: 'Inter', sans-serif !important; font-weight: 700 !important;
         letter-spacing: -0.01em; color: #0F172A !important; }

/* aire generoso */
.block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1200px; }
h2 { margin-top: 2.2rem !important; }
h3 { margin-top: 1.6rem !important; }

/* tarjetas de métricas: blancas, borde suave, sombra mínima */
div[data-testid="stMetric"] {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 16px;
  padding: 18px 22px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: box-shadow .25s ease, transform .25s ease;
}
div[data-testid="stMetric"]:hover {
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.07);
  transform: translateY(-1px);
}
div[data-testid="stMetric"] label { color: #64748B; font-weight: 500; }

/* sidebar limpia */
section[data-testid="stSidebar"] {
  background: #FAFBFC;
  border-right: 1px solid #EEF2F6;
}

/* tabs elegantes */
button[data-baseweb="tab"] { font-weight: 600; color: #64748B; }
button[data-baseweb="tab"][aria-selected="true"] { color: #059669; }

/* expanders y contenedores con borde */
div[data-testid="stExpander"] {
  border: 1px solid #E2E8F0; border-radius: 14px;
}

/* ticker tape claro */
.jt-tape {
  overflow: hidden; white-space: nowrap; background: #F8FAFC;
  border-top: 1px solid #EEF2F6; border-bottom: 1px solid #EEF2F6;
  padding: 8px 0; margin-bottom: 10px;
}
.jt-tape-inner {
  display: inline-block; animation: jt-scroll 45s linear infinite;
  font-family: 'Inter', monospace; font-size: 0.85rem; font-weight: 500;
}
.jt-tape-inner span { margin: 0 20px; color: #334155; }
.jt-up { color: #059669 !important; font-weight: 600; }
.jt-down { color: #DC2626 !important; font-weight: 600; }
@keyframes jt-scroll { 0% {transform: translateX(0);} 100% {transform: translateX(-50%);} }

/* badges tipo pill */
.jt-badge {
  display: inline-block; padding: 4px 14px; border-radius: 999px;
  font-size: 0.78rem; font-weight: 500; background: #F1F5F9; color: #475569;
  border: 1px solid #E2E8F0; margin-right: 4px;
}

/* botones con transición suave */
button[kind="primary"] { border-radius: 10px !important; transition: all .2s ease; }
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
