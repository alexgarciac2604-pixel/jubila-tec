"""Vista: copiloto conversacional — pregunta en lenguaje natural."""
from __future__ import annotations

import streamlit as st

from src.copilot.copilot import answer, llm_available


def render() -> None:
    st.title("🤖 Copiloto")
    st.caption(
        "Pregunta en tus palabras: *\"¿cómo ves NVDA?\"*, *\"¿cómo está el mercado?\"*, "
        "*\"¿me alcanza para jubilarme?\"*. Los números salen SIEMPRE de los motores "
        "auditados de la terminal — el copiloto traduce, nunca calcula."
    )
    st.markdown("🟢 Modo conversacional (Claude API)" if llm_available()
                else "🟡 Modo plantillas — agrega ANTHROPIC_API_KEY en `.env` para "
                     "conversación natural completa.")

    st.session_state.setdefault("chat", [])
    for msg in st.session_state["chat"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if q := st.chat_input("Escribe tu pregunta…"):
        st.session_state["chat"].append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            with st.spinner("Consultando los motores…"):
                res = answer(q)
            st.markdown(res["text"])
        st.session_state["chat"].append({"role": "assistant", "content": res["text"]})
