"""Briefing diario en lenguaje llano: régimen, movimientos, alertas, curva."""
from __future__ import annotations

from datetime import date

from src.alerts.engine import evaluate_alerts
from src.config import DISCLAIMER, TAPE_TICKERS
from src.data.market_data import get_quotes
from src.macro.macro import curve_signal, yield_curve
from src.models.regime import market_regime


def daily_briefing(watchlist: list[str] | None = None) -> str:
    from src.data.store import watchlist as _my_list
    tickers = watchlist or _my_list() or TAPE_TICKERS[:8]
    reg = market_regime()
    df = get_quotes(tickers).sort_values("change_pct")
    worst, best = df.iloc[0], df.iloc[-1]
    curve = curve_signal(yield_curve())

    try:
        fired = evaluate_alerts()
    except Exception:
        fired = []
    if fired:
        alert_line = (f"🔔 Tienes {len(fired)} alerta(s) disparada(s): "
                      + "; ".join(a["message"].replace("🔔 ", "") for a in fired[:3])
                      + (" …" if len(fired) > 3 else ""))
    else:
        alert_line = "🔕 Ninguna de tus alertas se ha disparado — nada requiere acción hoy."

    return (
        f"**🌅 Briefing AL-X — {date.today():%d/%m/%Y}**\n\n"
        f"{reg['emoji']} El mercado está en **{reg['name'].lower()}**: {reg['description']} "
        f"La probabilidad de turbulencia reciente es {reg['p_turbulent']:.0%}. {curve}\n\n"
        f"En tu lista, lo mejor del día es **{best['ticker']}** ({best['change_pct']:+.2f}%) "
        f"y lo más débil **{worst['ticker']}** ({worst['change_pct']:+.2f}%). "
        f"{alert_line}\n\n"
        f"*{DISCLAIMER}*"
    )


def client_briefing(rows: list[dict], dia_pct: float,
                      dia_dinero: float) -> str:
    """'¿Qué pasó con TU dinero?' — el digest personal, en español simple."""
    if not rows:
        try:
            from src.models.regime import market_regime
            reg = market_regime()
            return (f"{reg['emoji']} El mercado está en **{reg['name'].lower()}**. "
                    "Cuando tengas posiciones, aquí te contaré cada día qué pasó "
                    "con tu dinero.")
        except Exception:
            return "Cuando tengas posiciones, aquí te contaré qué pasó con tu dinero."
    partes = [f"Tu portafolio se movió **{dia_pct:+.2f}%** hoy "
              f"({'+' if dia_dinero >= 0 else '−'}${abs(dia_dinero):,.0f})."]
    orden = sorted(rows, key=lambda r: r["% Día"], reverse=True)
    mejor, peor = orden[0], orden[-1]
    if mejor["% Día"] > 0.3:
        partes.append(f"Tu mejor carta fue **{mejor['Ticker']}** "
                      f"({mejor['% Día']:+.2f}%).")
    if peor["% Día"] < -0.3 and peor["Ticker"] != mejor["Ticker"]:
        partes.append(f"La más débil, **{peor['Ticker']}** "
                      f"({peor['% Día']:+.2f}%).")
        try:
            from src.news.news_feed import get_news
            for it in get_news(peor["Ticker"], n=3):
                ev = it.get("event")
                if ev:
                    partes.append(f"Posible razón: {ev['label'].lower()} "
                                  f"(impacto típico {ev['impact']}).")
                    break
        except Exception:
            pass
    try:
        from src.models.regime import market_regime
        reg = market_regime()
        partes.append(f"{reg['emoji']} Contexto: mercado en "
                      f"**{reg['name'].lower()}**.")
    except Exception:
        pass
    if abs(dia_pct) < 0.8:
        partes.append("Día normal: no hay nada que hacer — la paciencia paga. 🧘")
    return " ".join(partes)


def monthly_story(nombre: str, saldo: float, delta_mes: float, pct_mes: float,
                  spy_pct: float | None, cambios_30d: dict,
                  depositos: float, n_compras: int, n_ventas: int,
                  meta: dict | None = None, hubo_caida: bool = False) -> str:
    """📖 El mes del cliente contado en palabras — nadie más lo hace."""
    L = [f"## 📖 Tu mes en AL-X, {nombre}", ""]
    signo = "creció" if delta_mes >= 0 else "retrocedió"
    L.append(f"Tu patrimonio **{signo} {abs(pct_mes):.1f}%** este mes "
             f"({'+' if delta_mes >= 0 else '−'}${abs(delta_mes):,.0f}) y hoy "
             f"vale **${saldo:,.0f}**.")
    if spy_pct is not None:
        if pct_mes >= spy_pct:
            L.append(f"Le ganaste al S&P 500, que se movió {spy_pct:+.1f}%. "
                     "No te acostumbres — casi nadie lo logra siempre — "
                     "pero disfrútalo. 🏆")
        else:
            L.append(f"El S&P 500 se movió {spy_pct:+.1f}%; este mes te ganó. "
                     "Es normal: lo que importa es la década, no el mes.")
    if cambios_30d:
        orden = sorted(cambios_30d.items(), key=lambda kv: kv[1], reverse=True)
        mejor, peor = orden[0], orden[-1]
        L.append(f"Tu estrella fue **{mejor[0]}** ({mejor[1]:+.1f}%); "
                 f"la que más pesó, **{peor[0]}** ({peor[1]:+.1f}%). "
                 "Tener ambas en el mismo barco se llama diversificación: "
                 "por eso tu mes no depende de una sola carta.")
    if depositos > 0:
        L.append(f"Aportaste **${depositos:,.0f}** este mes. Cada aportación "
                 "compra tu libertad futura — el hábito le gana al timing.")
    if hubo_caida and n_ventas == 0:
        L.append("Hubo una caída en el camino y **no vendiste**. Esa decisión "
                 "silenciosa suele ser la más rentable del mes. 💎")
    elif n_ventas > 0 and hubo_caida:
        L.append("Vendiste durante una caída. A veces es necesario — pero si "
                 "fue por miedo, platícalo con tu asesor antes de la próxima.")
    if n_compras > 0:
        L.append(f"Hiciste {n_compras} compra{'s' if n_compras > 1 else ''} "
                 "nueva{}.".format("s" if n_compras > 1 else ""))
    if meta:
        avance = saldo / meta["monto_meta"] if meta.get("monto_meta") else 0
        L.append(f"**{meta['nombre']}** va en **{avance:.0%}**. "
                 "Paso a paso — así se llega.")
    L.append("")
    L.append("> Informativo y educativo; no constituye asesoría de inversión.")
    return "\n\n".join(L)
