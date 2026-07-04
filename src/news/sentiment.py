"""Sentimiento léxico bilingüe (ES/EN) para titulares financieros."""
from __future__ import annotations

POSITIVE = {
    "supera", "récord", "record", "crece", "crecimiento", "sube", "alza", "gana",
    "beneficio", "recompra", "buyback", "expande", "expansión", "acuerdo", "contrato",
    "aprueba", "eleva", "mejora", "innovación", "lanza", "éxito", "beats", "surge",
    "growth", "profit", "upgrade", "wins", "strong", "raises", "buena", "recepción",
    "insignia", "multianual", "firma", "positivo", "optimista", "rally",
}
NEGATIVE = {
    "cae", "caída", "pierde", "pérdida", "recorta", "demanda", "investigación",
    "multa", "fraude", "quiebra", "despidos", "debilidad", "riesgo", "baja",
    "downgrade", "misses", "falls", "lawsuit", "probe", "fine", "layoffs", "weak",
    "cuts", "venden", "colectiva", "tribunales", "regulatoria", "negativo",
    "advertencia", "sanción", "arancel",
}


def score_text(text: str) -> float:
    """Score en [-1, 1]."""
    words = text.lower().replace(",", " ").replace(".", " ").split()
    pos = sum(w in POSITIVE for w in words)
    neg = sum(w in NEGATIVE for w in words)
    total = pos + neg
    return (pos - neg) / total if total else 0.0


def label(score: float) -> str:
    if score > 0.15:
        return "🟢 positivo"
    if score < -0.15:
        return "🔴 negativo"
    return "🟡 neutral"
