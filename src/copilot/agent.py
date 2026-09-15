"""Copiloto agéntico (A1): Claude orquesta las herramientas (los motores).

Bucle de tool-use sobre la API de Anthropic (sin SDK, con `requests`, igual que
el resto del proyecto). El modelo pide herramientas, nosotros ejecutamos el
motor y le devolvemos SOLO hechos; el modelo redacta la respuesta final en
español simple. Regla de oro: **orquesta, nunca calcula.**

Sin `ANTHROPIC_API_KEY` esta capa no está disponible (`agent_answer` → None) y
el copiloto usa su camino clásico (plantillas deterministas).
"""
from __future__ import annotations

import json
import os

from src.config import get_secret
from src.copilot.tools import TOOL_SPECS, dispatch

_SYSTEM = (
    "Eres el copiloto de AL-X, una terminal financiera educativa. Respondes en "
    "español claro y cálido, en 2-4 párrafos cortos. REGLAS DURAS:\n"
    "1) Para CUALQUIER número usa las herramientas; JAMÁS inventes ni calcules "
    "cifras de memoria. Si comparas dos empresas, usa la herramienta adecuada.\n"
    "2) Si las herramientas no dan lo necesario, dilo y sugiere qué vista de la "
    "app usar; no rellenes con cifras inventadas.\n"
    "3) Lenguaje no imperativo: 'el modelo indica', nunca 'compra' o 'vende'.\n"
    "4) Cierra recordando brevemente que es análisis educativo, no asesoría "
    "personalizada."
)

_ENDPOINT = "https://api.anthropic.com/v1/messages"


def agent_answer(question: str, max_turns: int = 4) -> dict | None:
    """Devuelve {text, mode:'agente', tools_used, hechos} o None si no disponible."""
    key = get_secret("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import requests
    except Exception:
        return None

    model = os.getenv("JT_COPILOT_MODEL", "claude-sonnet-4-5")
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01",
               "content-type": "application/json"}
    messages: list[dict] = [{"role": "user", "content": question}]
    tools_used: list[str] = []
    hechos: list[dict] = []

    for _ in range(max_turns):
        try:
            r = requests.post(_ENDPOINT, headers=headers, timeout=45, json={
                "model": model, "max_tokens": 900, "system": _SYSTEM,
                "tools": TOOL_SPECS, "messages": messages})
        except Exception:
            return None
        if r.status_code != 200:
            return None
        data = r.json()
        blocks = data.get("content", [])

        if data.get("stop_reason") == "tool_use":
            messages.append({"role": "assistant", "content": blocks})
            resultados = []
            for b in blocks:
                if b.get("type") == "tool_use":
                    out = dispatch(b.get("name", ""), b.get("input", {}))
                    tools_used.append(b.get("name", ""))
                    hechos.append(out)
                    resultados.append({
                        "type": "tool_result", "tool_use_id": b.get("id"),
                        "content": json.dumps(out, ensure_ascii=False, default=str)})
            messages.append({"role": "user", "content": resultados})
            continue

        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        if not text.strip():
            return None
        return {"text": text, "mode": "agente",
                "tools_used": tools_used, "hechos": hechos}

    return None  # demasiadas vueltas sin cerrar
