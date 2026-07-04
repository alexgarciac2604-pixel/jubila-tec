"""Persistencia SQLite: historial de scores (nuestro dataset de validación futuro).

Ruta configurable con JT_DB_PATH (útil para tests y despliegues). Por defecto,
`jubilatec.db` en la raíz del proyecto. Si el filesystem no permite SQLite,
la app sigue funcionando sin persistencia (nunca rompe un análisis).
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import date


def _db_path() -> str:
    env = os.getenv("JT_DB_PATH")
    if env:
        return env
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "jubilatec.db")


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(_db_path())
    con.execute("""CREATE TABLE IF NOT EXISTS score_history (
        ticker TEXT, date TEXT, total INTEGER, pillars TEXT,
        price REAL, version TEXT, source TEXT,
        PRIMARY KEY (ticker, date))""")
    con.execute("CREATE TABLE IF NOT EXISTS watchlist (ticker TEXT PRIMARY KEY, added TEXT)")
    return con


def save_score(ticker: str, total: int, pillars: dict, price: float,
               version: str, source: str) -> None:
    try:
        with _conn() as con:
            con.execute(
                "INSERT OR REPLACE INTO score_history VALUES (?,?,?,?,?,?,?)",
                (ticker.upper(), str(date.today()), total, json.dumps(pillars),
                 price, version, source),
            )
    except Exception:
        pass  # la persistencia nunca debe romper un análisis


def score_history(ticker: str, limit: int = 90) -> list[dict]:
    try:
        with _conn() as con:
            rows = con.execute(
                "SELECT date, total, price FROM score_history WHERE ticker=? "
                "ORDER BY date DESC LIMIT ?", (ticker.upper(), limit),
            ).fetchall()
        return [{"date": d, "total": t, "price": p} for d, t, p in reversed(rows)]
    except Exception:
        return []


def watchlist() -> list[str]:
    """Tickers de Mi Lista (orden de agregado)."""
    try:
        with _conn() as con:
            rows = con.execute("SELECT ticker FROM watchlist ORDER BY added, ticker").fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []


def watchlist_add(ticker: str) -> None:
    try:
        with _conn() as con:
            con.execute("INSERT OR IGNORE INTO watchlist VALUES (?, ?)",
                        (ticker.upper(), str(date.today())))
    except Exception:
        pass


def watchlist_remove(ticker: str) -> None:
    try:
        with _conn() as con:
            con.execute("DELETE FROM watchlist WHERE ticker=?", (ticker.upper(),))
    except Exception:
        pass
