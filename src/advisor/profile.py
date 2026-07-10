"""Ficha del Asesor: sintetiza TODOS los análisis de AL-X en un perfil
accionable — a qué cliente recomendarla, qué decirle y qué vigilar.

Modelos integrados (ver INVESTIGACION de origen):
- Score compuesto 5 pilares (con régimen de mercado)
- Piotroski F-Score como estrategia (Piotroski 2000: baratas con F≥8)
- Lente factorial (Fama-French pragmático: valor/calidad/momentum/tendencia)
- Actividad de insiders (Form 4, EDGAR)
"""
from __future__ import annotations

DEFENSIVOS = {"Consumo Básico", "Salud"}
CRECIMIENTO = {"Tecnología", "Comunicación", "Consumo Disc."}


def factor_lens(ticker: str, rows: list[dict]) -> dict | None:
    """Percentiles de exposición factorial vs. el universo del screener."""
    if not rows:
        return None
    fila = next((r for r in rows if r.get("ticker") == ticker.upper()), None)
    if not fila:
        return None

    def pct(campo: str, valor) -> int:
        vals = sorted(r.get(campo) or 0 for r in rows)
        if not vals or valor is None:
            return 50
        pos = sum(1 for v in vals if v <= valor)
        return round(100 * pos / len(vals))

    return {
        "Valor": pct("valoracion", fila.get("valoracion")),
        "Calidad": pct("calidad", fila.get("calidad")),
        "Momentum": pct("mom_6m", fila.get("mom_6m")),
        "Tendencia": pct("tecnico", fila.get("tecnico")),
    }


def piotroski_value_screen(rows: list[dict], fundamentals_getter,
                           piotroski_fn, max_n: int = 12) -> list[dict]:
    """La estrategia del paper: tercil barato → F-Score → conservar F≥8."""
    if not rows:
        return []
    ordenadas = sorted(rows, key=lambda r: r.get("valoracion") or 0,
                       reverse=True)
    baratas = ordenadas[:max(len(ordenadas) // 3, 5)][:max_n]
    out = []
    for r in baratas:
        try:
            f = piotroski_fn(fundamentals_getter(r["ticker"]))
            fs = f.get("score", f) if isinstance(f, dict) else int(f)
            out.append({**r, "f_score": fs,
                        "apta": fs >= 8, "evitar": fs <= 1})
        except Exception:
            continue
    out.sort(key=lambda r: (r["f_score"], r.get("valoracion") or 0),
             reverse=True)
    return out


def suitability(total: int, sector: str, forense: int, momentum: float,
                desde_max: float) -> dict:
    """¿A qué perfil de cliente se la recomendarías? Con su porqué."""
    out = {}
    if total >= 60 and forense >= 55 and sector in DEFENSIVOS | {"Financiero"}:
        out["conservador"] = (True, "sector estable, buen score y "
                                    "contabilidad sin banderas")
    elif sector in CRECIMIENTO:
        out["conservador"] = (False, "sector de crecimiento: demasiado "
                                     "brinco para dormir tranquilo")
    else:
        out["conservador"] = (False, "score o forense por debajo del "
                                     "estándar defensivo")
    if total >= 55 and forense >= 45:
        out["moderado"] = (True, "equilibrio razonable entre calidad y precio")
    else:
        out["moderado"] = (False, "hoy no supera nuestro filtro de equilibrio")
    if total >= 45 and (momentum > 5 or (desde_max < -20 and forense >= 55)):
        motivo = ("viene con impulso" if momentum > 5
                  else "castigada con fundamentos sanos: apuesta contraria")
        out["agresivo"] = (True, motivo)
    elif total >= 60:
        out["agresivo"] = (True, "empresa sólida; upside razonable")
    else:
        out["agresivo"] = (False, "ni impulso ni descuento que la justifique")
    return out


def talking_points(comp: dict, f_score: int | None) -> tuple[list[str], list[str]]:
    """(qué decirle al cliente, qué vigilar) — en español de sobremesa."""
    p, r = [], []
    pil = comp["pillars"]
    fnd = comp.get("fundamentals_raw", {})
    if pil["fundamental"] >= 65:
        p.append("Gana dinero de forma consistente: negocio de calidad "
                 f"({pil['fundamental']}/100).")
    if comp["valuation"].get("upside", 0) > 0.10:
        p.append(f"El precio luce razonable: nuestro modelo le ve "
                 f"~{comp['valuation']['upside']:.0%} de margen.")
    dy = fnd.get("dividend_yield") or 0
    if dy > 0.02:
        p.append(f"Te paga renta: dividendo de {dy:.1%} anual por esperar.")
    if pil["technical"] >= 60:
        p.append("Viene con impulso: el mercado la está acompañando.")
    if f_score is not None and f_score >= 8:
        p.append(f"Salud financiera de libro: F-Score {f_score}/9 "
                 "(la señal favorita de los académicos).")
    if not p:
        p.append("Hoy no tiene argumentos fuertes de compra — a veces la "
                 "mejor recomendación es esperar.")
    if pil["forensic"] < 50:
        r.append("La contabilidad muestra banderas: revisar el forense "
                 "antes de recomendar.")
    if pil["valuation"] < 40:
        r.append("Precio exigente: paga hoy mucho futuro.")
    if comp["quote"].get("from_52w_high_pct", 0) < -30:
        r.append("Muy castigada (-30% desde máximos): confirmar que la "
                 "caída no tenga razón de fondo.")
    if comp.get("data_quality", {}).get("issues"):
        r.append("Datos con observaciones (historial corto u otros): "
                 "tomar métricas de largo plazo con pinzas.")
    if not r:
        r.append("Sin focos rojos relevantes hoy; vigilar resultados "
                 "trimestrales y el semáforo.")
    return p, r


def advisor_profile(ticker: str) -> dict:
    """La ficha completa: todos los análisis → recomendación fácil."""
    from src.data.edgar import insider_activity
    from src.forensic.scores import piotroski_f
    from src.scoring.composite import composite_score
    from src.screener.engine import load_screener

    comp = composite_score(ticker)
    try:
        fs = piotroski_f(comp["fundamentals_raw"]).get("score")
    except Exception:
        fs = None
    scr = load_screener()
    rows = scr.get("rows", []) if scr else []
    fila = next((r for r in rows if r.get("ticker") == ticker.upper()), {})
    lens = factor_lens(ticker, rows)
    insider = insider_activity(ticker)
    aptos = suitability(comp["total"], comp.get("sector") or "",
                        comp["pillars"]["forensic"],
                        fila.get("mom_6m") or 0,
                        comp["quote"].get("from_52w_high_pct") or 0)
    puntos, riesgos = talking_points(comp, fs)
    return {"comp": comp, "f_score": fs, "factores": lens,
            "insider": insider, "aptos": aptos,
            "puntos": puntos, "riesgos": riesgos}
