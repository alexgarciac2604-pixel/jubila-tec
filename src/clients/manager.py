"""Gestor de clientes: perfiles, PIN hasheado y portafolios asignados.

El cliente entra con su NÚMERO o NOMBRE + PIN. El PIN nunca se guarda en
claro (SHA-256 con el id como sal). Al asignar un portafolio se congela el
precio de entrada de cada posición → el cliente ve su rendimiento real
desde la asignación.

⚖️ Esta es una herramienta de REGISTRO y REPORTE. No constituye asesoría
de inversión; el uso comercial con clientes puede requerir registro como
asesor ante CNBV/SEC según la jurisdicción.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date

from src.data.store import _conn as _base_conn


def _conn():
    con = _base_conn()
    con.execute("""CREATE TABLE IF NOT EXISTS clients (
        id TEXT PRIMARY KEY, name TEXT, pin_hash TEXT,
        perfil TEXT, capital REAL, created TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS holdings (
        client_id TEXT, ticker TEXT, weight REAL,
        price_at REAL, assigned TEXT,
        PRIMARY KEY (client_id, ticker))""")
    return con


def _hash_pin(cid: str, pin: str) -> str:
    return hashlib.sha256(f"{cid.upper()}:{pin}".encode()).hexdigest()


def create_client(cid: str, name: str, pin: str, perfil: str = "moderado",
                  capital: float = 0.0) -> bool:
    """False si el id ya existe."""
    cid = cid.strip().upper()
    try:
        with _conn() as con:
            con.execute("INSERT INTO clients VALUES (?,?,?,?,?,?)",
                        (cid, name.strip(), _hash_pin(cid, pin),
                         perfil, float(capital), str(date.today())))
        return True
    except Exception:
        return False


def verify_client(id_or_name: str, pin: str) -> dict | None:
    """Login por número de cliente O nombre (insensible a mayúsculas)."""
    q = (id_or_name or "").strip()
    if not q or not pin:
        return None
    try:
        with _conn() as con:
            rows = con.execute(
                "SELECT id, name, pin_hash, perfil, capital, created FROM clients"
            ).fetchall()
        # comparación en Python: SQLite UPPER() no maneja acentos (é, ñ…)
        qf = q.casefold()
        for row in rows:
            if row[0].casefold() == qf or row[1].casefold() == qf:
                if row[2] == _hash_pin(row[0], pin):
                    return {"id": row[0], "name": row[1], "perfil": row[3],
                            "capital": row[4], "created": row[5]}
                return None                    # cliente correcto, PIN incorrecto
    except Exception:
        pass
    return None


def list_clients() -> list[dict]:
    try:
        with _conn() as con:
            rows = con.execute(
                "SELECT id, name, perfil, capital, created FROM clients ORDER BY name"
            ).fetchall()
        return [{"id": r[0], "name": r[1], "perfil": r[2],
                 "capital": r[3], "created": r[4]} for r in rows]
    except Exception:
        return []


def delete_client(cid: str) -> None:
    try:
        with _conn() as con:
            con.execute("DELETE FROM clients WHERE id=?", (cid.upper(),))
            con.execute("DELETE FROM holdings WHERE client_id=?", (cid.upper(),))
    except Exception:
        pass


def set_portfolio(cid: str, tickers: list[str], weights: list[float],
                  prices: dict[str, float]) -> None:
    """Asigna el portafolio congelando el precio de entrada de cada posición."""
    cid = cid.upper()
    hoy = str(date.today())
    with _conn() as con:
        con.execute("DELETE FROM holdings WHERE client_id=?", (cid,))
        for t, w in zip(tickers, weights):
            con.execute("INSERT INTO holdings VALUES (?,?,?,?,?)",
                        (cid, t.upper(), float(w),
                         float(prices.get(t.upper(), 0.0)), hoy))


def get_portfolio(cid: str) -> list[dict]:
    try:
        with _conn() as con:
            rows = con.execute(
                "SELECT ticker, weight, price_at, assigned FROM holdings "
                "WHERE client_id=? ORDER BY weight DESC", (cid.upper(),),
            ).fetchall()
        return [{"ticker": r[0], "weight": r[1], "price_at": r[2],
                 "assigned": r[3]} for r in rows]
    except Exception:
        return []


def export_all() -> str:
    """Respaldo completo (clientes + portafolios) como JSON."""
    with _conn() as con:
        clients = con.execute("SELECT * FROM clients").fetchall()
        holdings = con.execute("SELECT * FROM holdings").fetchall()
    return json.dumps({"clients": clients, "holdings": holdings},
                      ensure_ascii=False)


def import_all(payload: str) -> int:
    """Restaura un respaldo. Devuelve nº de clientes importados."""
    data = json.loads(payload)
    with _conn() as con:
        for c in data.get("clients", []):
            con.execute("INSERT OR REPLACE INTO clients VALUES (?,?,?,?,?,?)", tuple(c))
        for h in data.get("holdings", []):
            con.execute("INSERT OR REPLACE INTO holdings VALUES (?,?,?,?,?)", tuple(h))
    return len(data.get("clients", []))
