"""Position sizing: criterio de Kelly fraccionado.

Kelly completo maximiza crecimiento pero con volatilidad brutal; la práctica
profesional usa ½ o ¼ Kelly. Siempre con tope duro por posición.
"""
from __future__ import annotations

import numpy as np


def kelly_fraction(ann_ret: float, ann_vol: float, rf: float = 0.042) -> float:
    """f* = (μ − rf) / σ²  (aproximación continua de Kelly)."""
    if not ann_vol:
        return 0.0
    return float((ann_ret - rf) / ann_vol**2)


def suggested_position(ann_ret: float, ann_vol: float, rf: float = 0.042,
                       cap: float = 0.20) -> dict:
    k = kelly_fraction(ann_ret, ann_vol, rf)
    half = k / 2
    suggested = float(np.clip(half, 0.0, cap))
    if k <= 0:
        note = ("Kelly ≤ 0: el retorno esperado no compensa el riesgo — "
                "el modelo no asignaría capital a esta posición.")
    elif half > cap:
        note = (f"½ Kelly ({half:.0%}) excede el tope prudencial; "
                f"se sugiere el máximo de {cap:.0%} por posición.")
    else:
        note = f"½ Kelly = {half:.0%} del portafolio (tope {cap:.0%})."
    return {"kelly": k, "half_kelly": half, "suggested": suggested, "cap": cap, "note": note}
