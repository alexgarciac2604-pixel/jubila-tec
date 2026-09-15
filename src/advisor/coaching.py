"""Coaching conductual — el copiloto anti-pánico (B3).

La única app del mercado que te FRENA antes de vender en pánico. La matemática
es pura y auditable: vender una posición en pérdida convierte en definitiva una
pérdida que hoy solo está "en papel" (cristalización). Este módulo centraliza
esa decisión para que la vista y la bitácora usen la MISMA verdad.
"""
from __future__ import annotations

UMBRAL_PERDIDA = -2.0   # % desde el precio de entrada para intervenir


def panic_check(precio_entrada: float, precio_actual: float, monto: float,
                turbulento: bool = False) -> dict | None:
    """Devuelve la intervención, o None si vender NO realiza una pérdida.

    `cristalizado` es negativo: la pérdida (en $) que se vuelve definitiva al
    vender `monto` de la posición al precio actual.
    """
    if not precio_actual or not precio_entrada or monto <= 0:
        return None
    rend_pct = (precio_actual / precio_entrada - 1) * 100
    if rend_pct >= UMBRAL_PERDIDA:
        return None
    # $ vendidos − costo original de esas unidades = pérdida realizada (<0)
    cristalizado = monto - (monto / precio_actual) * precio_entrada
    return {
        "rend_pct": round(rend_pct, 1),
        "cristalizado": round(cristalizado, 2),
        "turbulento": bool(turbulento),
    }
