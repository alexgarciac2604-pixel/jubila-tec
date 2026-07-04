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
        f"**🌅 Briefing Jubila-Tec — {date.today():%d/%m/%Y}**\n\n"
        f"{reg['emoji']} El mercado está en **{reg['name'].lower()}**: {reg['description']} "
        f"La probabilidad de turbulencia reciente es {reg['p_turbulent']:.0%}. {curve}\n\n"
        f"En tu lista, lo mejor del día es **{best['ticker']}** ({best['change_pct']:+.2f}%) "
        f"y lo más débil **{worst['ticker']}** ({worst['change_pct']:+.2f}%). "
        f"{alert_line}\n\n"
        f"*{DISCLAIMER}*"
    )
