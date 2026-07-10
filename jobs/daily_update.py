"""Actualización diaria de AL-X.

Refresca los datos, recalcula el score de todo el universo (alimentando el
historial en SQLite día a día), evalúa las alertas y envía el briefing a
Telegram si está configurado.

Correr a mano:      .venv\\Scripts\\python.exe jobs\\daily_update.py
Programar (8:30am): ver actualizacion_diaria.bat + Task Scheduler.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def clear_caches() -> None:
    """Vacía todas las cachés TTL para forzar datos frescos."""
    from src.data import market_data as md
    from src.data.edgar import fundamentals_overlay, insider_activity
    from src.macro.macro import get_macro_series, yield_curve
    from src.models.regime import market_regime
    from src.news.news_feed import get_news
    for fn in (md.get_history, md.get_fundamentals, md.get_quote, md.get_fx_history,
               get_news, get_macro_series, yield_curve, market_regime,
               fundamentals_overlay, insider_activity):
        try:
            fn.cache_clear()
        except Exception:
            pass


def run(verbose: bool = True) -> dict:
    from src.alerts.engine import check_and_notify, send_telegram, telegram_configured
    from src.config import DEFAULT_UNIVERSE
    from src.report.briefing import daily_briefing

    started = datetime.now()
    clear_caches()

    from src.scoring.composite import composite_score
    result = {"date": str(started.date()), "scores_ok": 0, "errors": []}
    for t in DEFAULT_UNIVERSE:
        try:
            composite_score(t)          # calcula y PERSISTE el score del día
            result["scores_ok"] += 1
        except Exception as e:          # noqa: BLE001
            result["errors"].append(f"{t}: {e}")

    alerts = check_and_notify()
    result["alerts_fired"] = len(alerts["triggered"])
    result["alerts_sent_telegram"] = alerts["sent"]

    brief = daily_briefing()
    result["briefing_sent"] = (
        send_telegram(brief.replace("**", "").replace("*", ""))
        if telegram_configured() else False
    )
    try:                                # screener nocturno del universo amplio
        from src.data.market_data import yf_status
        ok_yf, err_yf = yf_status()
        if verbose and not ok_yf:
            print(f"⚠️ yfinance NO importó: {err_yf} — siguiendo con Stooq")
        from src.screener.engine import save_screener, run_screener
        scr = run_screener()
        if verbose:
            print(f"screener: {scr['n']} filas · fuente {scr['source']}")
        save_screener(scr)          # lanza si es sintético o casi vacío
        result["screener_n"] = scr["n"]
    except Exception as e:              # noqa: BLE001
        result["errors"].append(f"screener: {e}")

    result["seconds"] = round((datetime.now() - started).total_seconds(), 1)

    line = (f"[{started:%Y-%m-%d %H:%M}] scores {result['scores_ok']}/{len(DEFAULT_UNIVERSE)} · "
            f"alertas {result['alerts_fired']} · briefing_tg {result['briefing_sent']} · "
            f"screener {result.get('screener_n', 0)} · "
            f"{result['seconds']}s · errores {len(result['errors'])}")
    try:                                # bitácora persistente
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "update.log"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    if verbose:
        print(line)
        for e in result["errors"][:5]:
            print("  !", e)
    return result


if __name__ == "__main__":
    run()
