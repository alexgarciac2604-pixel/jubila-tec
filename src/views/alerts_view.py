"""Vista: alertas — condiciones sobre precio/RSI/score con Telegram opcional."""
from __future__ import annotations

import streamlit as st

from src.alerts.engine import (KINDS, add_alert, check_and_notify, delete_alert,
                               list_alerts, telegram_configured)
from src.config import DEFAULT_UNIVERSE


def render() -> None:
    st.title("🔔 Alertas")
    st.caption(
        "Define condiciones y verifícalas cuando quieras. Con TELEGRAM_BOT_TOKEN y "
        "TELEGRAM_CHAT_ID en `.env`, las alertas disparadas también llegan a tu Telegram."
    )
    st.markdown(("🟢 Telegram configurado" if telegram_configured()
                 else "🟡 Telegram no configurado (las alertas solo se muestran aquí)"))

    with st.form("nueva_alerta"):
        c1, c2, c3 = st.columns(3)
        ticker = c1.selectbox("Ticker", DEFAULT_UNIVERSE)
        kind = c2.selectbox("Condición", list(KINDS), format_func=KINDS.get)
        level = c3.number_input("Nivel", 0.0, 1e6, 100.0)
        if st.form_submit_button("➕ Crear alerta", type="primary"):
            add_alert(ticker, kind, level)
            st.success(f"Alerta creada: {ticker} · {KINDS[kind]} {level:g}")

    alerts = list_alerts()
    if not alerts:
        st.info("Sin alertas activas. Crea la primera arriba.")
        return

    st.subheader(f"Activas ({len(alerts)})")
    for a in alerts:
        c1, c2 = st.columns([5, 1])
        c1.markdown(f"**{a['ticker']}** · {KINDS[a['kind']]} **{a['level']:g}** "
                    f"<span style='color:#64748b'>(desde {a['created']})</span>",
                    unsafe_allow_html=True)
        if c2.button("🗑️", key=f"del_{a['id']}"):
            delete_alert(a["id"])
            st.rerun()

    if st.button("▶️ Verificar todas ahora", type="primary"):
        with st.status("Evaluando condiciones…"):
            res = check_and_notify()
        if not res["triggered"]:
            st.success("Ninguna alerta disparada: todo dentro de tus niveles.")
        else:
            for t in res["triggered"]:
                st.warning(t["message"])
            if res["telegram"]:
                st.caption(f"📨 {res['sent']} notificaciones enviadas a Telegram.")
