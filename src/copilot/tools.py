"""Herramientas del copiloto agéntico (A1).

Cada herramienta EJECUTA un motor de AL-X y devuelve SOLO hechos numéricos,
auditables. El LLM las orquesta (puede encadenar varias, p. ej. comparar dos
acciones); **nunca calcula** — esa es la regla de oro. El guardián
(`copilot/guard.py`) verifica luego que ninguna cifra de la respuesta salga
fuera de estos hechos.
"""
from __future__ import annotations


def _hechos_accion(ticker: str) -> dict:
    """Extrae del score compuesto un dict plano de cifras auditables."""
    from src.data.market_data import resolve_symbol
    from src.scoring.composite import composite_score

    tk = (resolve_symbol(ticker) or ticker or "").upper()
    a = composite_score(tk)
    v, r, t = a["valuation"], a["risk"], a["technical"]
    q = a["quote"]
    return {
        "ticker": a["ticker"], "nombre": a.get("name"), "sector": a.get("sector"),
        "score": a["total"], "semaforo": a["semaforo"],
        "postura": a["thesis"]["stance"], "pilares": a["pillars"],
        "precio": round(q["price"], 2),
        "cambio_dia_pct": round(q["change_pct"], 2),
        "valor_dcf": round(v["fair_value"], 2),
        "upside_pct": round(v["upside"] * 100, 1),
        "wacc_pct": round(v["wacc"] * 100, 1),
        "crecimiento_asumido_pct": round(v["growth"] * 100, 1),
        "vol_anual_pct": round(r["ann_vol"] * 100, 1),
        "var95_dia_pct": round(r["var95_d"] * 100, 1),
        "max_drawdown_pct": round(r["max_drawdown"] * 100, 1),
        "sharpe": round(r["sharpe"], 2),
        "rsi": round(t["rsi"]),
        "momentum_6m_pct": round(t["mom_6m"], 1),
        "altman_z": a["forensic"]["altman"]["z"],
        "altman_zona": a["forensic"]["altman"]["zone"],
        "piotroski_f": a["forensic"]["piotroski"]["score"],
        "sentimiento": a["sentiment"]["label"],
        "regimen": a["regime"]["name"],
        "fuente_datos": a["data_source"],
        "calidad_datos": a["data_quality"]["score"],
    }


def analizar_accion(ticker: str) -> dict:
    """Análisis integral de una acción (score de 5 pilares, DCF, riesgo, forense)."""
    return _hechos_accion(ticker)


def comparar_acciones(ticker_a: str, ticker_b: str) -> dict:
    """Compara dos acciones lado a lado y resume las diferencias clave."""
    A, B = _hechos_accion(ticker_a), _hechos_accion(ticker_b)
    return {
        "a": A, "b": B,
        "diferencias": {
            "score": A["score"] - B["score"],
            "upside_pct": round(A["upside_pct"] - B["upside_pct"], 1),
            "sharpe": round(A["sharpe"] - B["sharpe"], 2),
            "vol_anual_pct": round(A["vol_anual_pct"] - B["vol_anual_pct"], 1),
        },
    }


def estado_mercado() -> dict:
    """Régimen actual del mercado (calma/turbulencia) y señal de la curva."""
    from src.macro.macro import curve_signal, yield_curve
    from src.models.regime import market_regime
    reg = market_regime()
    return {
        "regimen": reg["name"], "descripcion": reg["description"],
        "prob_turbulencia_pct": round(reg["p_turbulent"] * 100),
        "curva": curve_signal(yield_curve()),
    }


# --------------------------------------------------------------------------- #
# Registro para el LLM (esquema de herramientas de la API de Anthropic)
# --------------------------------------------------------------------------- #
TOOL_SPECS = [
    {"name": "analizar_accion",
     "description": "Analiza una acción con TODOS los motores de AL-X: score 0-100 "
                    "de 5 pilares, valor DCF y upside, riesgo (vol, VaR, drawdown, "
                    "Sharpe), técnico (RSI, momentum) y forense (Altman, Piotroski). "
                    "Úsala para cualquier pregunta sobre una empresa.",
     "input_schema": {"type": "object", "properties": {
         "ticker": {"type": "string",
                    "description": "Ticker o nombre de la empresa, p. ej. AAPL o apple."}},
         "required": ["ticker"]}},
    {"name": "comparar_acciones",
     "description": "Compara DOS acciones lado a lado y resume sus diferencias "
                    "(score, upside, Sharpe, volatilidad). Úsala cuando el usuario "
                    "pida comparar o elegir entre dos empresas.",
     "input_schema": {"type": "object", "properties": {
         "ticker_a": {"type": "string", "description": "Primera empresa (ticker o nombre)."},
         "ticker_b": {"type": "string", "description": "Segunda empresa (ticker o nombre)."}},
         "required": ["ticker_a", "ticker_b"]}},
    {"name": "estado_mercado",
     "description": "Régimen actual del mercado (calma o turbulencia), probabilidad "
                    "de turbulencia y señal de la curva de tasas. Sin argumentos.",
     "input_schema": {"type": "object", "properties": {}}},
]

_DISPATCH = {
    "analizar_accion": analizar_accion,
    "comparar_acciones": comparar_acciones,
    "estado_mercado": estado_mercado,
}


def dispatch(name: str, args: dict | None = None) -> dict:
    """Ejecuta una herramienta por nombre. Errores se devuelven como dato, no excepción."""
    fn = _DISPATCH.get(name)
    if fn is None:
        return {"error": f"herramienta desconocida: {name}"}
    try:
        return fn(**(args or {}))
    except Exception as exc:  # el motor falló → el LLM lo sabrá y lo dirá
        return {"error": f"{type(exc).__name__}: {exc}"}
