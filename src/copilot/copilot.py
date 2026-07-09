"""Copiloto conversacional — la regla de oro: TRADUCE, NUNCA CALCULA.

Todos los números salen de los motores (auditables, testeados). Con
ANTHROPIC_API_KEY en `.env`, Claude redacta la respuesta sobre ese contexto;
sin clave, un respondedor determinista genera la respuesta con plantillas.
Entiende nombres de empresa ("apple"), tickers (AAPL), empresas privadas
(SpaceX) y tickers desconocidos (sugiere el más parecido).
"""
from __future__ import annotations

import difflib
import os
import re
import unicodedata

from src.config import TICKER_NAMES, get_secret

_SYSTEM = (
    "Eres el copiloto de AL-X, una terminal financiera educativa. "
    "Respondes en español claro y cálido, en 2-4 párrafos cortos. REGLAS DURAS: "
    "1) Usa EXCLUSIVAMENTE los números del CONTEXTO; jamás inventes ni recalcules cifras. "
    "2) Si el contexto no contiene lo necesario, dilo y sugiere qué vista de la app usar. "
    "3) Lenguaje no imperativo: 'el modelo indica', nunca 'compra' o 'vende'. "
    "4) Cierra recordando brevemente que es análisis educativo, no asesoría personalizada."
)

# nombre común (minúsculas, sin acentos) → ticker
from src.config import NAME_TO_TICKER as _NAME_TO_TICKER

# empresas famosas que NO cotizan en bolsa (o no en NYSE/Nasdaq)
_PRIVATE = {
    "openai": "OpenAI presentó su registro para salir a bolsa pero pospuso la IPO (previsiblemente a 2027); por ahora no cotiza. La exposición pública más cercana es Microsoft (MSFT), su principal socio.",
    "stripe": "Stripe sigue siendo privada; no hay acciones públicas disponibles.",
    "bytedance": "ByteDance (TikTok) es privada; no cotiza en ninguna bolsa occidental.",
    "tiktok": "TikTok pertenece a ByteDance, que es privada; no cotiza en bolsa.",
    "ikea": "IKEA es propiedad de una fundación privada; no cotiza en bolsa.",
}

# tickers que son palabras comunes en español: solo cuentan si van EN MAYÚSCULAS
_AMBIGUOUS = {"META", "T", "V", "MA", "GE", "KO", "HD", "BA", "DIS", "PG", "CAT"}

_STOPWORDS = {"COMO", "VES", "HOY", "QUE", "LA", "EL", "LOS", "LAS", "UN", "UNA",
              "DE", "DEL", "MI", "TU", "ES", "Y", "O", "POR", "PARA", "CON", "SIN",
              "ME", "TE", "SE", "AL", "EN", "NO", "SI"}


def _norm(text: str) -> str:
    return unicodedata.normalize("NFD", text.lower()).encode("ascii", "ignore").decode()


def detect_intent(question: str) -> dict:
    ql = _norm(question)

    # 1) empresas privadas famosas
    for name, msg in _PRIVATE.items():
        if name in ql:
            return {"kind": "private", "name": name.capitalize(), "msg": msg}

    # 2) nombre de empresa → ticker (apple, tesla, coca cola…)
    for name, tk in _NAME_TO_TICKER.items():
        if re.search(rf"\b{re.escape(name)}\b", ql):
            return {"kind": "ticker", "ticker": tk}

    # 3) ticker directo (los ambiguos solo si van en mayúsculas en el original)
    qu = question.upper()
    for t in TICKER_NAMES:
        if re.search(rf"\b{t}\b", qu):
            if t in _AMBIGUOUS and not re.search(rf"\b{t}\b", question):
                continue
            return {"kind": "ticker", "ticker": t}

    # 4) temas
    if any(w in ql for w in ("jubil", "retiro", "pension", "meta")):
        return {"kind": "retirement"}
    if any(w in ql for w in ("portafolio", "cartera", "diversif")):
        return {"kind": "portfolio"}
    if any(w in ql for w in ("mercado", "regimen", "panorama", "macro", "bolsa")):
        return {"kind": "market"}
    if any(w in ql for w in ("hola", "buenos dias", "buenas", "gracias", "que tal", "hey")):
        return {"kind": "greeting"}

    # 5) ¿intentó escribir un ticker que no conozco? (SPCX, XYZ…)
    tokens = [w for w in re.findall(r"\b[A-Z]{2,5}\b", question) if w not in _STOPWORDS]
    if tokens:
        universe = list(TICKER_NAMES) + [n.upper() for n in _NAME_TO_TICKER]
        close = difflib.get_close_matches(tokens[0], universe, n=2, cutoff=0.5)
        sugg = [_NAME_TO_TICKER.get(c.lower(), c) for c in close]
        return {"kind": "unknown_ticker", "token": tokens[0],
                "suggestions": list(dict.fromkeys(sugg))}

    return {"kind": "unknown"}


def build_context(intent: dict) -> str:
    """Empaqueta la salida de los motores como texto plano para el LLM."""
    if intent["kind"] == "ticker":
        from src.scoring.composite import composite_score
        a = composite_score(intent["ticker"])
        v, r, t = a["valuation"], a["risk"], a["technical"]
        pil = " · ".join(f"{k} {s}/100 (peso {a['weights'][k]:.0%})"
                         for k, s in a["pillars"].items())
        return (
            f"{a['name']} ({a['ticker']}), sector {a['sector']}. "
            f"Score {a['total']}/100 {a['semaforo']}, postura {a['thesis']['stance']}. "
            f"Pilares: {pil}. Precio ${a['quote']['price']:.2f} "
            f"({a['quote']['change_pct']:+.2f}% hoy, {a['quote']['from_52w_high_pct']:+.1f}% desde máx 52s). "
            f"Valor justo DCF ${v['fair_value']:.2f} (upside {v['upside']:+.0%}, WACC {v['wacc']:.1%}, "
            f"crecimiento asumido {v['growth']:.0%}). "
            f"Riesgo: vol anual {r['ann_vol']:.0%}, VaR95 diario {r['var95_d']:.1%}, "
            f"máx drawdown {r['max_drawdown']:.0%}, Sharpe {r['sharpe']:.2f}. "
            f"Técnico: RSI {t['rsi']:.0f}, momentum 6m {t['mom_6m']:+.1f}%. "
            f"Forense: Altman {a['forensic']['altman']['z']} (zona {a['forensic']['altman']['zone']}), "
            f"Piotroski {a['forensic']['piotroski']['score']}/9. "
            f"Sentimiento noticias: {a['sentiment']['label']} ({a['sentiment']['avg']:+.2f}). "
            f"Régimen de mercado: {a['regime']['name']}. "
            f"Tesis alcista: {a['thesis']['bull']} Tesis bajista: {a['thesis']['bear']} "
            f"Fuente de datos: {a['data_source']}, calidad {a['data_quality']['score']}/100."
        )
    if intent["kind"] == "market":
        from src.models.regime import market_regime
        from src.macro.macro import curve_signal, yield_curve
        reg = market_regime()
        return (f"Régimen: {reg['name']} — {reg['description']} "
                f"Prob. turbulencia (10d): {reg['p_turbulent']:.0%}. "
                f"Curva: {curve_signal(yield_curve())}")
    if intent["kind"] == "retirement":
        return ("El usuario pregunta por jubilación. La vista 🎯 Jubilación simula su plan "
                "en dinero de hoy con colas gordas: metas, aporte requerido para 80% de "
                "probabilidad, y compara reglas de retiro (4% Bengen, % del saldo, "
                "Guyton-Klinger) con probabilidad de ruina.")
    if intent["kind"] == "portfolio":
        return ("El usuario pregunta por portafolios. La vista 💼 Portafolio optimiza con "
                "Máx. Sharpe, HRP, mínima varianza o risk parity; muestra contribución al "
                "riesgo, stress tests (tasas +100bp, crisis 2008…), frontera, Monte Carlo "
                "de colas gordas y descomposición en pesos mexicanos.")
    return ""


def _ask_llm(question: str, context: str, key: str) -> str | None:
    try:
        import requests
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": os.getenv("JT_COPILOT_MODEL", "claude-sonnet-4-5"),
                  "max_tokens": 700, "system": _SYSTEM,
                  "messages": [{"role": "user",
                                "content": f"CONTEXTO (única fuente de números):\n{context}\n\nPREGUNTA: {question}"}]},
            timeout=30,
        )
        if r.status_code == 200:
            return r.json()["content"][0]["text"]
    except Exception:
        pass
    return None


def _rule_based(intent: dict, context: str) -> str:
    kind = intent["kind"]

    if kind == "ticker":
        from src.scoring.composite import composite_score
        a = composite_score(intent["ticker"])
        v = a["valuation"]
        best = max(a["pillars"], key=a["pillars"].get)
        worst = min(a["pillars"], key=a["pillars"].get)
        up = v["upside"]
        return (
            f"{a['semaforo']} **{a['name']}** obtiene **{a['total']}/100** — postura "
            f"{a['thesis']['stance']}.\n\n"
            f"Cotiza a ${a['quote']['price']:.2f} y el DCF base la valúa en "
            f"${v['fair_value']:.2f} ({up:+.0%}). Su punto más fuerte es "
            f"**{best}** ({a['pillars'][best]}/100) y el más débil **{worst}** "
            f"({a['pillars'][worst]}/100).\n\n"
            f"**En sencillo:** en un día malo de 1 entre 20 pierde "
            f"≈{a['risk']['var95_d']:.1%} o más, y su peor racha reciente fue "
            f"{a['risk']['max_drawdown']:.0%}. El régimen actual es "
            f"{a['regime']['name']}, y el score ya lo tiene en cuenta.\n\n"
            f"*Análisis educativo con {a['data_source']}, no asesoría personalizada. "
            f"Detalle completo: busca {a['ticker']} en la barra lateral.*"
        )

    if kind == "private":
        return (f"Buena pregunta 🙂 — pero {intent['msg']}\n\n"
                "Solo puedo analizar empresas que cotizan públicamente, porque mis motores "
                "trabajan con precios y estados financieros públicos. Si te interesa el "
                "sector, dime y te sugiero empresas comparables que sí cotizan.")

    if kind == "unknown_ticker":
        sugg = intent.get("suggestions") or []
        if sugg:
            hint = " · ".join(f"**{s}**" for s in sugg)
            return (f"No encuentro el ticker **{intent['token']}** en mi universo 🤔 "
                    f"¿Quizá quisiste decir {hint}?\n\n"
                    "Si es otra empresa, prueba con su nombre (\"¿cómo ves apple?\") "
                    "o revisa el ticker exacto en 🗺️ Mercados, donde está todo mi universo.")
        return (f"No encuentro **{intent['token']}** en mi universo actual. "
                "En 🗺️ Mercados puedes ver las ~32 empresas que cubro hoy; "
                "el universo crecerá en próximas versiones.")

    if kind == "greeting":
        return ("¡Hola! 👋 Soy el copiloto de AL-X. Pregúntame por una empresa "
                "(\"¿qué te parece apple?\"), por el mercado (\"¿cómo está el panorama?\"), "
                "por tu portafolio o por tu plan de jubilación — y te lo explico en "
                "sencillo, con los números reales de los motores.")

    if kind == "market":
        return (f"{context}\n\n*Para el detalle visual: 🌐 Dashboard y "
                f"🌍 Macro & Geopolítica.*")

    if kind in ("retirement", "portfolio"):
        return context + "\n\n*Abre esa vista desde la barra lateral y juega con los controles.*"

    return (
        "No estoy seguro de qué necesitas, pero seguro te puedo ayudar 🙂 Prueba con:\n\n"
        "- *\"¿Qué te parece apple?\"* o cualquier empresa/ticker\n"
        "- *\"¿Cómo está el mercado hoy?\"*\n"
        "- *\"¿Cómo armo un buen portafolio?\"*\n"
        "- *\"¿Me alcanza para jubilarme a los 65?\"*"
    )


def llm_available() -> bool:
    return bool(get_secret("ANTHROPIC_API_KEY"))


def answer(question: str) -> dict:
    intent = detect_intent(question)
    if intent["kind"] == "unknown_ticker":
        from src.data.market_data import lookup_ticker
        if lookup_ticker(intent["token"]):      # cotiza aunque no esté en mi lista
            intent = {"kind": "ticker", "ticker": intent["token"]}
    context = build_context(intent)
    key = get_secret("ANTHROPIC_API_KEY")
    if key and context:
        text = _ask_llm(question, context, key)
        if text:
            return {"text": text, "mode": "llm", "intent": intent["kind"]}
    return {"text": _rule_based(intent, context), "mode": "plantilla", "intent": intent["kind"]}
