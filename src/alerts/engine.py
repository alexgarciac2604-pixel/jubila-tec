"""Motor de alertas: condiciones sobre precio/RSI/score, persistidas en SQLite.

Notificación por Telegram opcional (TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID en
`.env`). Sin token, las alertas se evalúan y muestran en la app igualmente.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import date

from src.data.store import _db_path

KINDS = {
    "price_above": "Precio supera",
    "price_below": "Precio cae bajo",
    "rsi_above": "RSI supera",
    "rsi_below": "RSI cae bajo",
    "score_above": "Score supera",
    "score_below": "Score cae bajo",
}


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(_db_path())
    con.execute("""CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT, kind TEXT, level REAL, created TEXT, active INTEGER DEFAULT 1)""")
    return con


def add_alert(ticker: str, kind: str, level: float) -> None:
    assert kind in KINDS, f"kind inválido: {kind}"
    with _conn() as con:
        con.execute("INSERT INTO alerts (ticker, kind, level, created) VALUES (?,?,?,?)",
                    (ticker.upper(), kind, float(level), str(date.today())))


def list_alerts() -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT id, ticker, kind, level, created FROM alerts WHERE active=1 ORDER BY id"
        ).fetchall()
    return [{"id": i, "ticker": t, "kind": k, "level": lv, "created": c}
            for i, t, k, lv, c in rows]


def delete_alert(alert_id: int) -> None:
    with _conn() as con:
        con.execute("UPDATE alerts SET active=0 WHERE id=?", (alert_id,))


def _current_value(ticker: str, kind: str) -> float:
    from src.data.market_data import get_history, get_quote
    if kind.startswith("price"):
        return float(get_quote(ticker)["price"])
    if kind.startswith("rsi"):
        from src.technical.indicators import rsi
        return float(rsi(get_history(ticker).Close).iloc[-1])
    from src.scoring.composite import composite_score
    return float(composite_score(ticker)["total"])


def evaluate_alerts() -> list[dict]:
    """Evalúa todas las alertas activas; devuelve las disparadas con su mensaje."""
    triggered = []
    for a in list_alerts():
        try:
            value = _current_value(a["ticker"], a["kind"])
        except Exception:
            continue
        fired = value > a["level"] if a["kind"].endswith("above") else value < a["level"]
        if fired:
            metric = a["kind"].split("_")[0].upper().replace("PRICE", "Precio")
            a["value"] = round(value, 2)
            a["message"] = (f"🔔 {a['ticker']}: {KINDS[a['kind']]} {a['level']:g} — "
                            f"{metric} actual: {value:.2f}")
            triggered.append(a)
    return triggered


def telegram_configured() -> bool:
    return bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))


def send_telegram(text: str) -> bool:
    if not telegram_configured():
        return False
    try:
        import requests
        r = requests.post(
            f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage",
            json={"chat_id": os.getenv("TELEGRAM_CHAT_ID"), "text": text},
            timeout=8,
        )
        return r.status_code == 200
    except Exception:
        return False


def check_and_notify() -> dict:
    fired = evaluate_alerts()
    sent = sum(send_telegram(a["message"]) for a in fired) if telegram_configured() else 0
    return {"triggered": fired, "sent": sent, "telegram": telegram_configured()}
