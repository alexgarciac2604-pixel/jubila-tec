"""Gestor de clientes: perfiles, PIN hasheado y portafolios asignados.

El cliente entra con su NÚMERO o NOMBRE + PIN. El PIN nunca se guarda en
claro (SHA-256 con el id como sal). Al asignar un portafolio se congela el
precio de entrada de cada posición → el cliente ve su rendimiento real
desde la asignación.

Persistencia vía src/data/dbx.py: con los secrets TURSO_* configurados,
Studio y el Portal comparten la MISMA base en la nube.

⚖️ Esta es una herramienta de REGISTRO y REPORTE. No constituye asesoría
de inversión; el uso comercial con clientes puede requerir registro como
asesor ante CNBV/SEC según la jurisdicción.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date

from src.data.dbx import execute, execute_many, query


def _hash_pin(cid: str, pin: str) -> str:
    return hashlib.sha256(f"{cid.upper()}:{pin}".encode()).hexdigest()


def create_client(cid: str, name: str, pin: str, perfil: str = "moderado",
                  capital: float = 0.0) -> bool:
    """False si el id ya existe. Lanza excepción si la base falla (el
    llamador la muestra: un error de conexión NO es "cliente duplicado")."""
    cid = cid.strip().upper()
    if query("SELECT id FROM clients WHERE id=?", (cid,)):
        return False
    execute_many([
        ("INSERT INTO clients VALUES (?,?,?,?,?,?)",
         (cid, name.strip(), _hash_pin(cid, pin),
          perfil, float(capital), str(date.today()))),
        ("INSERT INTO movements VALUES (?,?,?,?,?)",
         (cid, str(date.today()), "Depósito inicial", float(capital),
          "Apertura de cuenta")),
    ])
    return True


def verify_client(id_or_name: str, pin: str) -> dict | None:
    """Login por número de cliente O nombre (insensible a mayúsculas)."""
    q = (id_or_name or "").strip()
    if not q or not pin:
        return None
    try:
        rows = query("SELECT id, name, pin_hash, perfil, capital, created FROM clients")
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
        rows = query("SELECT id, name, perfil, capital, created FROM clients ORDER BY name")
        return [{"id": r[0], "name": r[1], "perfil": r[2],
                 "capital": r[3], "created": r[4]} for r in rows]
    except Exception:
        return []


def delete_client(cid: str) -> None:
    try:
        execute_many([
            ("DELETE FROM clients WHERE id=?", (cid.upper(),)),
            ("DELETE FROM holdings WHERE client_id=?", (cid.upper(),)),
        ])
    except Exception:
        pass


def set_portfolio(cid: str, tickers: list[str], weights: list[float],
                  prices: dict[str, float]) -> None:
    """Asigna el portafolio congelando precio de entrada Y monto invertido
    (así los depósitos posteriores no distorsionan el rendimiento)."""
    cid = cid.upper()
    hoy = str(date.today())
    row = query("SELECT capital FROM clients WHERE id=?", (cid,))
    capital = float(row[0][0]) if row else 0.0
    stmts: list[tuple[str, tuple]] = [("DELETE FROM holdings WHERE client_id=?", (cid,))]
    for t, w in zip(tickers, weights):
        px = float(prices.get(t.upper(), 0.0))
        inv = capital * float(w)
        stmts.append(("INSERT INTO holdings VALUES (?,?,?,?,?,?)",
                      (cid, t.upper(), float(w), px, hoy, inv)))
        stmts.append(("INSERT INTO movements VALUES (?,?,?,?,?)",
                      (cid, hoy, "Compra", inv,
                       f"{t.upper()} · {float(w):.0%} @ ${px:,.2f}")))
    execute_many(stmts)


def get_portfolio(cid: str) -> list[dict]:
    try:
        rows = query(
            "SELECT ticker, weight, price_at, assigned, invested FROM holdings "
            "WHERE client_id=? ORDER BY weight DESC", (cid.upper(),),
        )
        return [{"ticker": r[0], "weight": r[1], "price_at": r[2],
                 "assigned": r[3], "invested": r[4]} for r in rows]
    except Exception:
        return []


def export_all() -> str:
    """Respaldo completo (clientes + portafolios) como JSON."""
    clients = query("SELECT * FROM clients")
    holdings = query("SELECT * FROM holdings")
    return json.dumps({"clients": clients, "holdings": holdings},
                      ensure_ascii=False)


def import_all(payload: str) -> int:
    """Restaura un respaldo. Devuelve nº de clientes importados."""
    data = json.loads(payload)
    stmts: list[tuple[str, tuple]] = []
    for c in data.get("clients", []):
        stmts.append(("INSERT OR REPLACE INTO clients VALUES (?,?,?,?,?,?)", tuple(c)))
    for h in data.get("holdings", []):
        stmts.append(("INSERT OR REPLACE INTO holdings VALUES (?,?,?,?,?,?)",
                      tuple(h) + (None,) * (6 - len(h))))
    if stmts:
        execute_many(stmts)
    return len(data.get("clients", []))


# --------------------------------------------------- v0.14: cuenta viva ----
def add_deposit(cid: str, monto: float, nota: str = "") -> None:
    """Depósito (monto > 0) o retiro (monto < 0): ajusta capital y lo registra."""
    cid = cid.upper()
    tipo = "Depósito" if monto >= 0 else "Retiro"
    execute_many([
        ("UPDATE clients SET capital = capital + ? WHERE id=?", (float(monto), cid)),
        ("INSERT INTO movements VALUES (?,?,?,?,?)",
         (cid, str(date.today()), tipo, float(monto), nota)),
    ])


def get_movements(cid: str, limit: int = 200) -> list[dict]:
    try:
        rows = query(
            "SELECT date, tipo, monto, nota FROM movements WHERE client_id=? "
            "ORDER BY date DESC, rowid DESC LIMIT ?", (cid.upper(), int(limit)),
        )
        return [{"date": r[0], "tipo": r[1], "monto": r[2], "nota": r[3]}
                for r in rows]
    except Exception:
        return []


def get_capital(cid: str) -> float:
    """Capital vigente (los depósitos/retiros lo mueven; la sesión no lo ve)."""
    try:
        row = query("SELECT capital FROM clients WHERE id=?", (cid.upper(),))
        return float(row[0][0]) if row else 0.0
    except Exception:
        return 0.0


def create_request(cid: str, mensaje: str) -> None:
    import uuid
    execute("INSERT INTO requests VALUES (?,?,?,?,?)",
            (uuid.uuid4().hex[:12], cid.upper(), str(date.today()),
             mensaje.strip()[:800], "pendiente"))


def get_requests(cid: str | None = None) -> list[dict]:
    try:
        if cid:
            rows = query("SELECT id, client_id, date, mensaje, estado FROM requests "
                         "WHERE client_id=? ORDER BY date DESC", (cid.upper(),))
        else:
            rows = query("SELECT id, client_id, date, mensaje, estado FROM requests "
                         "ORDER BY estado DESC, date DESC")
        return [{"id": r[0], "client_id": r[1], "date": r[2],
                 "mensaje": r[3], "estado": r[4]} for r in rows]
    except Exception:
        return []


def close_request(req_id: str) -> None:
    execute("UPDATE requests SET estado='atendida' WHERE id=?", (req_id,))


def set_note(cid: str, nota: str) -> None:
    execute("INSERT OR REPLACE INTO notes VALUES (?,?,?)",
            (cid.upper(), nota.strip()[:1500], str(date.today())))


def get_note(cid: str) -> dict | None:
    try:
        rows = query("SELECT nota, updated FROM notes WHERE client_id=?",
                     (cid.upper(),))
        return {"nota": rows[0][0], "updated": rows[0][1]} if rows else None
    except Exception:
        return None
