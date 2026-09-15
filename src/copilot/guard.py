"""Guardián anti-alucinación del copiloto agéntico.

Regla de oro: el LLM orquesta, **nunca calcula**. Este módulo verifica que
cada cifra que el copiloto escribe provenga de los hechos que devolvieron las
herramientas (los motores). Se usa en los tests (arnés A2) y puede usarse en
runtime como bandera suave.
"""
from __future__ import annotations

import json
import re

_TOKEN = re.compile(r"\d+(?:\.\d+)?")

# Constantes estructurales de la prosa (no son datos de los motores):
# escalas ("/100"), "1 de cada 20", "5 pilares", años, etc.
_ALLOW = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
          "20", "52", "100", "2024", "2025", "2026", "2027"}


def _numeros(obj) -> set[str]:
    """Todos los tokens numéricos presentes en una estructura de hechos."""
    return set(_TOKEN.findall(json.dumps(obj, ensure_ascii=False, default=str)))


def numeros_sin_respaldo(texto: str, hechos) -> set[str]:
    """Cifras del `texto` que NO aparecen en `hechos` (ni en la lista blanca).

    Tolera diferencias de redondeo (84 ≈ 84.0, 12.3 ≈ 12.34) contra cualquier
    número de los hechos.
    """
    permitidos = _numeros(hechos) | _ALLOW
    vals_permitidos = []
    for p in permitidos:
        try:
            vals_permitidos.append(float(p))
        except ValueError:
            pass

    faltan: set[str] = set()
    for n in _TOKEN.findall(texto):
        if n in permitidos:
            continue
        try:
            val = float(n)
        except ValueError:
            continue
        # respaldada si coincide (con tolerancia de redondeo) con algún hecho
        if any(abs(val - v) <= max(0.05, abs(v) * 0.01) for v in vals_permitidos):
            continue
        faltan.add(n)
    return faltan
