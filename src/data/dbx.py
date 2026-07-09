"""Capa de persistencia dual AL-X: SQLite local ↔ Turso (libSQL) en la nube.

Si existen los secrets TURSO_DATABASE_URL y TURSO_AUTH_TOKEN, todas las
lecturas/escrituras van a Turso vía su API HTTP (v2/pipeline): así AL-X
Studio y el Portal de Clientes comparten la MISMA base aunque sean dos
apps desplegadas por separado, y los datos sobreviven a cada redeploy.
Sin secrets: SQLite local como siempre (ruta configurable con JT_DB_PATH).

Mismo SQL en ambos backends — libSQL es 100% compatible con SQLite.
"""
from __future__ import annotations

import os
import sqlite3

_SCHEMA = (
    """CREATE TABLE IF NOT EXISTS score_history (
        ticker TEXT, date TEXT, total INTEGER, pillars TEXT,
        price REAL, version TEXT, source TEXT,
        PRIMARY KEY (ticker, date))""",
    "CREATE TABLE IF NOT EXISTS watchlist (ticker TEXT PRIMARY KEY, added TEXT)",
    """CREATE TABLE IF NOT EXISTS clients (
        id TEXT PRIMARY KEY, name TEXT, pin_hash TEXT,
        perfil TEXT, capital REAL, created TEXT)""",
    """CREATE TABLE IF NOT EXISTS holdings (
        client_id TEXT, ticker TEXT, weight REAL,
        price_at REAL, assigned TEXT, invested REAL,
        PRIMARY KEY (client_id, ticker))""",
    """CREATE TABLE IF NOT EXISTS movements (
        client_id TEXT, date TEXT, tipo TEXT, monto REAL, nota TEXT)""",
    """CREATE TABLE IF NOT EXISTS requests (
        id TEXT PRIMARY KEY, client_id TEXT, date TEXT,
        mensaje TEXT, estado TEXT)""",
    """CREATE TABLE IF NOT EXISTS notes (
        client_id TEXT PRIMARY KEY, nota TEXT, updated TEXT)""",
)

# columnas agregadas después del primer despliegue (fallan si ya existen: ok)
_MIGRATIONS = ("ALTER TABLE holdings ADD COLUMN invested REAL",)


def _turso_creds() -> tuple[str, str] | None:
    from src.config import get_secret
    url, tok = get_secret("TURSO_DATABASE_URL"), get_secret("TURSO_AUTH_TOKEN")
    return (url, tok) if url and tok else None


def backend() -> str:
    """'turso' (nube compartida) o 'sqlite' (local)."""
    return "turso" if _turso_creds() else "sqlite"


# ---------------------------------------------------------------- SQLite ----
def _db_path() -> str:
    env = os.getenv("JT_DB_PATH")
    if env:
        return env
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "jubilatec.db")


def _sqlite_conn() -> sqlite3.Connection:
    con = sqlite3.connect(_db_path())
    for ddl in _SCHEMA:
        con.execute(ddl)
    for mig in _MIGRATIONS:
        try:
            con.execute(mig)
        except sqlite3.OperationalError:
            pass
    return con


# ----------------------------------------------------------------- Turso ----
def _encode(v) -> dict:
    """Python → valor tipado del protocolo Hrana de Turso."""
    if v is None:
        return {"type": "null"}
    if isinstance(v, bool):
        return {"type": "integer", "value": str(int(v))}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": v}
    return {"type": "text", "value": str(v)}


def _decode(cell: dict):
    """Valor tipado de Turso → Python (los enteros llegan como string)."""
    t = cell.get("type")
    if t == "integer":
        return int(cell["value"])
    if t == "float":
        return float(cell["value"])
    if t == "null":
        return None
    return cell.get("value")


_TURSO_READY = False  # esquema creado una sola vez por proceso


def _turso_pipeline(stmts: list[tuple[str, tuple]]) -> list[list[tuple]]:
    """Varias sentencias en UNA llamada HTTP. Lanza excepción si Turso falla."""
    import requests
    url, tok = _turso_creds()
    http = url.replace("libsql://", "https://").rstrip("/") + "/v2/pipeline"
    reqs = [{"type": "execute",
             "stmt": {"sql": s, "args": [_encode(p) for p in ps]}}
            for s, ps in stmts]
    r = requests.post(http, json={"requests": reqs + [{"type": "close"}]},
                      headers={"Authorization": f"Bearer {tok}"}, timeout=12)
    if r.status_code != 200:
        raise RuntimeError(f"Turso HTTP {r.status_code}: {r.text[:300]}")
    out: list[list[tuple]] = []
    for res in r.json()["results"][:len(stmts)]:
        if res.get("type") != "ok":
            raise RuntimeError(str(res.get("error", "Turso error")))
        rows = res["response"].get("result", {}).get("rows", [])
        out.append([tuple(_decode(c) for c in row) for row in rows])
    return out


def _turso_run(stmts: list[tuple[str, tuple]]) -> list[list[tuple]]:
    global _TURSO_READY
    if not _TURSO_READY:
        _turso_pipeline([(ddl, ()) for ddl in _SCHEMA])
        for mig in _MIGRATIONS:
            try:
                _turso_pipeline([(mig, ())])
            except Exception:
                pass                      # la columna ya existe
        _TURSO_READY = True
    return _turso_pipeline(stmts)


# ------------------------------------------------------------- API única ----
def query(sql: str, params: tuple = ()) -> list[tuple]:
    if backend() == "turso":
        return _turso_run([(sql, params)])[0]
    with _sqlite_conn() as con:
        return con.execute(sql, params).fetchall()


def execute(sql: str, params: tuple = ()) -> None:
    execute_many([(sql, params)])


def execute_many(stmts: list[tuple[str, tuple]]) -> None:
    """Lote de escrituras: 1 sola llamada HTTP en Turso, 1 conexión en SQLite."""
    if backend() == "turso":
        _turso_run(stmts)
        return
    with _sqlite_conn() as con:
        for sql, params in stmts:
            con.execute(sql, params)


def ping() -> tuple[bool, str]:
    """Prueba real de conexión. (ok, mensaje) — el mensaje trae el error exacto."""
    try:
        query("SELECT 1")
        return True, "conexión OK"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
