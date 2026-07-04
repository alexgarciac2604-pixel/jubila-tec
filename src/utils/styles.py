"""Tema visual oscuro premium + CSS del ticker tape."""
from __future__ import annotations

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important; }

.block-container { padding-top: 1.2rem; }

/* tarjetas de métricas */
div[data-testid="stMetric"] {
  background: linear-gradient(145deg, #111827, #0b1120);
  border: 1px solid #1f2937; border-radius: 12px; padding: 12px 16px;
}
div[data-testid="stMetric"] label { color: #94a3b8; }

/* ticker tape */
.jt-tape {
  overflow: hidden; white-space: nowrap; background: #0b1120;
  border-top: 1px solid #1f2937; border-bottom: 1px solid #1f2937;
  padding: 6px 0; margin-bottom: 6px;
}
.jt-tape-inner {
  display: inline-block; animation: jt-scroll 45s linear infinite;
  font-family: 'Space Grotesk', monospace; font-size: 0.85rem;
}
.jt-tape-inner span { margin: 0 18px; color: #e2e8f0; }
.jt-up { color: #34d399 !important; }
.jt-down { color: #f87171 !important; }
@keyframes jt-scroll { 0% {transform: translateX(0);} 100% {transform: translateX(-50%);} }

.jt-badge {
  display: inline-block; padding: 2px 10px; border-radius: 999px;
  font-size: 0.75rem; background: #1e293b; color: #94a3b8;
  border: 1px solid #334155;
}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
