"""Extracción de eventos tipados desde titulares (ES/EN).

Cada tipo de evento tiene dirección e impacto típico aproximado (event studies:
MacKinlay 1997 y literatura posterior). Un evento tipado pesa más que el
sentimiento léxico: "recorte de guía" es accionable, "tono negativo" es vago.
"""
from __future__ import annotations

# orden = prioridad de matching (el primero que aplique gana)
EVENT_TYPES: list[dict] = [
    {"type": "guidance_cut", "label": "📉 Recorte de guía", "dir": -0.9,
     "impact": "-6 a -12% típico el día del anuncio",
     "keys": ["recorta su guía", "recorta guía", "cuts guidance", "lowers outlook",
              "reduce su pronóstico"]},
    {"type": "earnings_beat", "label": "📈 Supera expectativas", "dir": 0.7,
     "impact": "+2 a +6% típico",
     "keys": ["supera expectativas", "beats estimates", "beats expectations",
              "mejor a lo esperado"]},
    {"type": "buyback", "label": "💵 Recompra", "dir": 0.6,
     "impact": "+1 a +3% típico",
     "keys": ["recompra", "buyback", "repurchase"]},
    {"type": "regulatory", "label": "⚖️ Riesgo regulatorio", "dir": -0.6,
     "impact": "-2 a -8% según severidad",
     "keys": ["investigación regulatoria", "antimonopolio", "antitrust", "probe",
              "multa", "sanción", "regulator"]},
    {"type": "lawsuit", "label": "🧑‍⚖️ Litigio", "dir": -0.5,
     "impact": "-1 a -5% según exposición",
     "keys": ["demanda colectiva", "demanda contra", "lawsuit", "tribunales"]},
    {"type": "ma", "label": "🤝 M&A", "dir": 0.4,
     "impact": "objetivo +15-30%; comprador -1 a -3%",
     "keys": ["adquiere", "adquisición", "fusión", "merger", "acquisition"]},
    {"type": "contract", "label": "📜 Contrato relevante", "dir": 0.6,
     "impact": "+1 a +5% según tamaño",
     "keys": ["firma contrato", "contrato gubernamental", "contrato multianual",
              "wins contract"]},
    {"type": "product", "label": "🚀 Lanzamiento", "dir": 0.5,
     "impact": "+1 a +4% con buena recepción",
     "keys": ["lanza", "presenta nuevo", "producto insignia", "launches", "unveils"]},
    {"type": "layoffs", "label": "✂️ Despidos", "dir": -0.3,
     "impact": "ambiguo: -2% (demanda débil) a +2% (disciplina de costos)",
     "keys": ["despidos", "layoffs", "recorte de personal"]},
    {"type": "insider_sell", "label": "👤 Venta de insiders", "dir": -0.3,
     "impact": "-0.5 a -2%; señal débil aislada",
     "keys": ["insiders", "venden acciones"]},
    {"type": "analyst", "label": "🎯 Revisión de analistas", "dir": 0.3,
     "impact": "±1-3% según casa y magnitud",
     "keys": ["precio objetivo", "upgrade", "downgrade", "elevan", "recortan a"]},
    {"type": "expansion", "label": "🌎 Expansión", "dir": 0.4,
     "impact": "+0.5 a +2%",
     "keys": ["expande", "expansión", "nuevos mercados"]},
    {"type": "dividend", "label": "💰 Dividendo", "dir": 0.3,
     "impact": "+0.5 a +1.5% si sube; -3 a -8% si lo recorta",
     "keys": ["dividendo", "dividend"]},
]


def classify_event(text: str) -> dict | None:
    t = text.lower()
    for ev in EVENT_TYPES:
        if any(k in t for k in ev["keys"]):
            return {"type": ev["type"], "label": ev["label"],
                    "dir": ev["dir"], "impact": ev["impact"]}
    return None
