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
