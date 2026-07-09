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


# ------------------------------------------- v0.16: órdenes al asesor ----
def create_order(cid: str, side: str, ticker: str, monto: float,
                 nota: str = "") -> None:
    """El cliente PIDE comprar/vender; nada se ejecuta hasta que el asesor
    aprueba. Registro y reporte — la app no custodia dinero ni valores."""
    import uuid
    execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?)",
            (uuid.uuid4().hex[:12], cid.upper(), str(date.today()),
             side, ticker.upper(), float(monto), "pendiente", nota[:400]))


def get_orders(cid: str | None = None) -> list[dict]:
    try:
        if cid:
            rows = query("SELECT id, client_id, date, side, ticker, monto, "
                         "estado, nota FROM orders WHERE client_id=? "
                         "ORDER BY date DESC, rowid DESC", (cid.upper(),))
        else:
            rows = query("SELECT id, client_id, date, side, ticker, monto, "
                         "estado, nota FROM orders ORDER BY estado DESC, date DESC, rowid DESC")
        return [{"id": r[0], "client_id": r[1], "date": r[2], "side": r[3],
                 "ticker": r[4], "monto": r[5], "estado": r[6], "nota": r[7]}
                for r in rows]
    except Exception:
        return []


def reject_order(order_id: str, motivo: str = "") -> None:
    execute("UPDATE orders SET estado=?, nota=? WHERE id=?",
            (f"rechazada", (motivo or "Rechazada por el asesor")[:400], order_id))


def _holdings_map(cid: str) -> dict[str, dict]:
    return {h["ticker"]: h for h in get_portfolio(cid)}


def _reweigh(cid: str) -> None:
    """Recalcula pesos = invertido_i / total invertido (informativo)."""
    hs = get_portfolio(cid)
    total = sum(h.get("invested") or 0.0 for h in hs)
    if total <= 0:
        return
    execute_many([
        ("UPDATE holdings SET weight=? WHERE client_id=? AND ticker=?",
         (float((h.get("invested") or 0.0) / total), cid.upper(), h["ticker"]))
        for h in hs
    ])


def _execute_trade(cid: str, side: str, ticker: str,
                   monto: float) -> tuple[bool, str]:
    """Núcleo de ejecución a precio actual, con matemática de efectivo."""
    from src.data.market_data import get_quote
    cid, ticker = cid.upper(), ticker.upper()
    monto = float(monto)
    px = float(get_quote(ticker)["price"])
    if px <= 0:
        return False, f"Sin precio para {ticker}."
    hoy = str(date.today())
    hs = _holdings_map(cid)
    capital = get_capital(cid)
    invertido = sum(h.get("invested") or 0.0 for h in hs.values())
    efectivo = max(capital - invertido, 0.0)

    if side == "compra":
        if monto > efectivo + 0.01:
            return False, (f"Efectivo insuficiente: tiene ${efectivo:,.0f} y "
                           f"pide ${monto:,.0f}. Registra un depósito primero.")
        h = hs.get(ticker)
        if h:
            old_inv = h.get("invested") or 0.0
            old_units = old_inv / h["price_at"] if h["price_at"] else 0.0
            new_units = old_units + monto / px
            new_inv = old_inv + monto
            new_px = new_inv / new_units if new_units else px
            execute("UPDATE holdings SET invested=?, price_at=?, assigned=? "
                    "WHERE client_id=? AND ticker=?",
                    (new_inv, new_px, hoy, cid, ticker))
        else:
            execute("INSERT INTO holdings VALUES (?,?,?,?,?,?)",
                    (cid, ticker, 0.0, px, hoy, monto))
        execute("INSERT INTO movements VALUES (?,?,?,?,?)",
                (cid, hoy, "Compra", monto, f"{ticker} @ ${px:,.2f} (orden aprobada)"))
    else:                                                   # venta
        h = hs.get(ticker)
        if not h:
            return False, f"El cliente no tiene {ticker}."
        inv = h.get("invested") or 0.0
        units = inv / h["price_at"] if h["price_at"] else 0.0
        pos_value = units * px
        if monto > pos_value + 0.01:
            return False, (f"Posición insuficiente: {ticker} vale "
                           f"${pos_value:,.0f} y pide vender ${monto:,.0f}.")
        units_sold = monto / px
        inv_sold = units_sold * h["price_at"]
        realized = monto - inv_sold                         # G/P realizada → efectivo
        rest = inv - inv_sold
        if rest < 1.0:
            execute("DELETE FROM holdings WHERE client_id=? AND ticker=?",
                    (cid, ticker))
        else:
            execute("UPDATE holdings SET invested=? WHERE client_id=? AND ticker=?",
                    (rest, cid, ticker))
        execute_many([
            ("UPDATE clients SET capital = capital + ? WHERE id=?",
             (float(realized), cid)),
            ("INSERT INTO movements VALUES (?,?,?,?,?)",
             (cid, hoy, "Venta", monto,
              f"{ticker} @ ${px:,.2f} · G/P realizada ${realized:+,.2f}")),
        ])
    _reweigh(cid)
    lado = "Compra" if side == "compra" else "Venta"
    return True, f"{lado} de {ticker} por ${monto:,.0f} ejecutada @ ${px:,.2f}."


def approve_order(order_id: str) -> tuple[bool, str]:
    """Flujo con aprobación (órdenes pendientes heredadas)."""
    rows = query("SELECT client_id, side, ticker, monto, estado FROM orders "
                 "WHERE id=?", (order_id,))
    if not rows:
        return False, "Orden no encontrada."
    cid, side, ticker, monto, estado = rows[0]
    if estado != "pendiente":
        return False, f"La orden ya está {estado}."
    ok, msg = _execute_trade(cid, side, ticker, float(monto))
    if ok:
        execute("UPDATE orders SET estado='aprobada' WHERE id=?", (order_id,))
    return ok, msg


def execute_order(cid: str, side: str, ticker: str, monto: float,
                  nota: str = "") -> tuple[bool, str]:
    """v0.17: el cliente ejecuta directo. Queda registrada como 'ejecutada'
    para la auditoría del asesor en el Studio."""
    ok, msg = _execute_trade(cid, side, ticker, monto)
    if ok:
        import uuid
        execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?)",
                (uuid.uuid4().hex[:12], cid.upper(), str(date.today()),
                 side, ticker.upper(), float(monto), "ejecutada", nota[:400]))
    return ok, msg


# ------------------------------------------ v0.16: simulador (paper) ----
PAPER_INICIAL = 100_000.0


def paper_state(cid: str) -> dict:
    """Cartera de práctica: efectivo virtual + posiciones."""
    cid = cid.upper()
    rows = query("SELECT cash FROM paper_cash WHERE client_id=?", (cid,))
    if not rows:
        execute("INSERT INTO paper_cash VALUES (?,?)", (cid, PAPER_INICIAL))
        cash = PAPER_INICIAL
    else:
        cash = float(rows[0][0])
    pos = query("SELECT ticker, units, price_at, date FROM paper "
                "WHERE client_id=? ORDER BY ticker", (cid,))
    return {"cash": cash,
            "positions": [{"ticker": r[0], "units": r[1],
                           "price_at": r[2], "date": r[3]} for r in pos]}


def paper_trade(cid: str, side: str, ticker: str, monto: float) -> tuple[bool, str]:
    """Compra/venta INSTANTÁNEA con dinero ficticio a precio real."""
    from src.data.market_data import get_quote
    cid, ticker = cid.upper(), ticker.upper()
    st_ = paper_state(cid)
    px = float(get_quote(ticker)["price"])
    if px <= 0:
        return False, f"Sin precio para {ticker}."
    monto = float(monto)
    pos = {p["ticker"]: p for p in st_["positions"]}
    if side == "compra":
        if monto > st_["cash"] + 0.01:
            return False, f"Efectivo virtual insuficiente (${st_['cash']:,.0f})."
        units = monto / px
        if ticker in pos:
            p = pos[ticker]
            nu = p["units"] + units
            npx = (p["units"] * p["price_at"] + monto) / nu
            execute("UPDATE paper SET units=?, price_at=? "
                    "WHERE client_id=? AND ticker=?", (nu, npx, cid, ticker))
        else:
            execute("INSERT INTO paper VALUES (?,?,?,?,?)",
                    (cid, ticker, units, px, str(date.today())))
        execute("UPDATE paper_cash SET cash = cash - ? WHERE client_id=?",
                (monto, cid))
        return True, f"Compraste {units:.3f} de {ticker} @ ${px:,.2f} (práctica)."
    p = pos.get(ticker)
    if not p:
        return False, f"No tienes {ticker} en tu cartera de práctica."
    pos_value = p["units"] * px
    monto = min(monto, pos_value)
    units_sold = monto / px
    rest = p["units"] - units_sold
    if rest * px < 1.0:
        execute("DELETE FROM paper WHERE client_id=? AND ticker=?", (cid, ticker))
    else:
        execute("UPDATE paper SET units=? WHERE client_id=? AND ticker=?",
                (rest, cid, ticker))
    execute("UPDATE paper_cash SET cash = cash + ? WHERE client_id=?", (monto, cid))
    return True, f"Vendiste {units_sold:.3f} de {ticker} @ ${px:,.2f} (práctica)."


def paper_reset(cid: str) -> None:
    execute_many([
        ("DELETE FROM paper WHERE client_id=?", (cid.upper(),)),
        ("INSERT OR REPLACE INTO paper_cash VALUES (?,?)",
         (cid.upper(), PAPER_INICIAL)),
    ])


# --------------------------------- v0.18: canastas modelo del asesor ----
def create_basket(name: str, tesis: str, tickers: list[str],
                  weights: list[float]) -> None:
    import uuid
    execute("INSERT INTO baskets VALUES (?,?,?,?,?,?)",
            (uuid.uuid4().hex[:12], name.strip()[:60], tesis.strip()[:400],
             json.dumps([t.upper() for t in tickers]),
             json.dumps([float(w) for w in weights]), str(date.today())))


def list_baskets() -> list[dict]:
    try:
        rows = query("SELECT id, name, tesis, tickers, weights, created "
                     "FROM baskets ORDER BY created DESC")
        return [{"id": r[0], "name": r[1], "tesis": r[2],
                 "tickers": json.loads(r[3]), "weights": json.loads(r[4]),
                 "created": r[5]} for r in rows]
    except Exception:
        return []


def delete_basket(basket_id: str) -> None:
    execute("DELETE FROM baskets WHERE id=?", (basket_id,))


def invest_basket(cid: str, basket_id: str, monto: float) -> tuple[bool, str]:
    """Compra todos los componentes de la canasta según sus pesos."""
    b = next((x for x in list_baskets() if x["id"] == basket_id), None)
    if not b:
        return False, "Canasta no encontrada."
    cid = cid.upper()
    hs = {h["ticker"]: h for h in get_portfolio(cid)}
    invertido = sum(h.get("invested") or 0.0 for h in hs.values())
    efectivo = max(get_capital(cid) - invertido, 0.0)
    if monto > efectivo + 0.01:
        return False, (f"Efectivo insuficiente: tienes ${efectivo:,.0f} y la "
                       f"canasta pide ${monto:,.0f}.")
    hechos = 0
    for t, w in zip(b["tickers"], b["weights"]):
        ok, _ = _execute_trade(cid, "compra", t, monto * w)
        hechos += int(ok)
    if not hechos:
        return False, "No se pudo ejecutar ningún componente (¿sin precios?)."
    import uuid
    execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?)",
            (uuid.uuid4().hex[:12], cid, str(date.today()), "compra",
             f"🧺 {b['name']}"[:20], float(monto), "ejecutada",
             f"Canasta del asesor · {hechos}/{len(b['tickers'])} componentes"))
    return True, (f"Invertiste ${monto:,.0f} en «{b['name']}» "
                  f"({hechos} posiciones). Tu asesor armó esta canasta.")


# ------------------------------------- v0.18: watchlist del cliente ----
def watch_add(cid: str, ticker: str) -> None:
    execute("INSERT OR IGNORE INTO client_watch VALUES (?,?,?)",
            (cid.upper(), ticker.upper(), str(date.today())))


def watch_remove(cid: str, ticker: str) -> None:
    execute("DELETE FROM client_watch WHERE client_id=? AND ticker=?",
            (cid.upper(), ticker.upper()))


def watch_list(cid: str) -> list[str]:
    try:
        rows = query("SELECT ticker FROM client_watch WHERE client_id=? "
                     "ORDER BY added, ticker", (cid.upper(),))
        return [r[0] for r in rows]
    except Exception:
        return []
