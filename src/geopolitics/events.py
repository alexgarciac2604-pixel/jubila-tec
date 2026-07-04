"""Motor geopolítico: evento → impacto sectorial esperado (dirección, no magnitud)."""
from __future__ import annotations

# impacto: -2 muy negativo … +2 muy positivo
EVENTS = [
    {"event": "Escalada arancelaria EE.UU.–China", "region": "Global",
     "impacts": {"Tecnología": -2, "Industrial": -1, "Consumo Disc.": -1, "Energía": 0, "Salud": 0},
     "note": "Cadenas de suministro tech y hardware son las más expuestas."},
    {"event": "Conflicto en Medio Oriente / shock petrolero", "region": "MENA",
     "impacts": {"Energía": 2, "Industrial": -1, "Consumo Disc.": -1, "Financiero": -1},
     "note": "Oil al alza beneficia energía; encarece insumos y transporte al resto."},
    {"event": "Recorte de tasas de la Fed", "region": "EE.UU.",
     "impacts": {"Tecnología": 2, "Financiero": -1, "Consumo Disc.": 1, "Comunicación": 1},
     "note": "Duración larga (growth) se beneficia; margen de bancos se comprime."},
    {"event": "Subida de tasas / inflación persistente", "region": "EE.UU.",
     "impacts": {"Tecnología": -2, "Financiero": 1, "Consumo Básico": 1, "Salud": 0},
     "note": "Rotación hacia value/defensivos; growth descuenta a mayor tasa."},
    {"event": "Tensión en el estrecho de Taiwán", "region": "Asia",
     "impacts": {"Tecnología": -2, "Industrial": -1, "Consumo Básico": 1},
     "note": "Riesgo de semiconductores concentrado; defensivos como refugio."},
    {"event": "Aumento de gasto en defensa (OTAN)", "region": "Global",
     "impacts": {"Industrial": 2, "Tecnología": 1, "Energía": 1},
     "note": "Contratistas de defensa y ciberseguridad capturan presupuesto."},
    {"event": "Crisis bancaria regional", "region": "EE.UU./UE",
     "impacts": {"Financiero": -2, "Consumo Disc.": -1, "Consumo Básico": 1, "Salud": 1},
     "note": "Contracción de crédito golpea cíclicos; huida a calidad."},
    {"event": "Estímulo fiscal en China", "region": "Asia",
     "impacts": {"Industrial": 2, "Energía": 1, "Consumo Disc.": 1, "Tecnología": 1},
     "note": "Materiales, maquinaria y lujo con exposición a demanda china."},
]

_KEYWORDS = {
    "arancel": 0, "tarifa": 0, "china": 0,
    "petróleo": 1, "oil": 1, "medio oriente": 1,
    "recorte": 2, "fed": 2, "dovish": 2,
    "inflación": 3, "tasas": 3, "hawkish": 3,
    "taiwán": 4, "taiwan": 4, "semiconductor": 4,
    "defensa": 5, "otan": 5, "nato": 5,
    "banco": 6, "banking": 6, "crédito": 6,
    "estímulo": 7, "stimulus": 7,
}


def classify_text(text: str) -> dict | None:
    """Mapea un titular a un evento geopolítico conocido (o None)."""
    t = text.lower()
    for kw, idx in _KEYWORDS.items():
        if kw in t:
            return EVENTS[idx]
    return None


def sector_bias(sector: str) -> float:
    """Sesgo promedio del entorno actual de eventos sobre un sector (-2..2)."""
    vals = [e["impacts"].get(sector, 0) for e in EVENTS]
    return sum(vals) / len(vals)
