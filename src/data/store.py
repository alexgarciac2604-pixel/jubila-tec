"""Persistencia AL-X: scores y watchlist sobre la capa dual dbx.

Backend automático: Turso (nube compartida) si hay secrets, SQLite local
si no — ver src/data/dbx.py. Si la persistencia falla por cualquier razón,
la app sigue funcionando: nunca rompe un análisis.
"""
from __future__ import annotations

import json
from datetime import date

from src.data.dbx import _db_path, backend, execute, query  # noqa: F401 (_db_path lo usa alerts)


def save_score(ticker: str, total: int, pillars: dict, price: float,
               version: str, source: str) -> None:
    try:
        execute(
            "INSERT OR REPLACE INTO score_history VALUES (?,?,?,?,?,?,?)",
            (ticker.upper(), str(date.today()), total, json.dumps(pillars),
             float(price), version, source),
        )
    except Exception:
        pass  # la persistencia nunca debe romper un análisis


def score_history(ticker: str, limit: int = 90) -> list[dict]:
    try:
        rows = query(
            "SELECT date, total, price FROM score_history WHERE ticker=? "
            "ORDER BY date DESC LIMIT ?", (ticker.upper(), int(limit)),
        )
        return [{"date": d, "total": t, "price": p} for d, t, p in reversed(rows)]
    except Exception:
        return []


def watchlist() -> list[str]:
    """Tickers de Mi Lista (orden de agregado)."""
    try:
        rows = query("SELECT ticker FROM watchlist ORDER BY added, ticker")
        return [r[0] for r in rows]
    except Exception:
        return []


def watchlist_add(ticker: str) -> None:
    try:
        execute("INSERT OR IGNORE INTO watchlist VALUES (?, ?)",
                (ticker.upper(), str(date.today())))
    except Exception:
        pass


def watchlist_remove(ticker: str) -> None:
    try:
        execute("DELETE FROM watchlist WHERE ticker=?", (ticker.upper(),))
    except Exception:
        pass
