"""Salud / observabilidad del sistema (C4).

La contraparte operativa de la Caja de Cristal: "no nos creas, revísanos".
Función pura que sondea cada subsistema (datos, BD, screener, deep scan,
historial, clientes) y devuelve un estado auditable. Cada sonda está aislada:
si una falla, el panel sigue mostrando el resto (degradación elegante).
"""
from __future__ import annotations


def system_health() -> dict:
    from src import __version__
    checks: list[dict] = []

    def add(nombre: str, estado: str, detalle: str) -> None:
        checks.append({"nombre": nombre, "estado": estado, "detalle": detalle})

    # 1) Datos de mercado + candado anti-sintético
    try:
        from src.data.market_data import using_sample, yf_status
        if using_sample():
            add("Datos de mercado", "warn",
                "🧪 Modo sintético (JT_FORCE_SAMPLE) — solo desarrollo/tests")
        else:
            ok, err = yf_status()
            add("Datos de mercado", "ok" if ok else "warn",
                "yfinance activo" if ok
                else f"yfinance caído → Stooq al rescate ({str(err)[:50]})")
    except Exception as e:
        add("Datos de mercado", "error", str(e)[:80])

    # 2) Base de datos (Turso o SQLite local)
    try:
        from src.data.dbx import backend, ping
        if backend() == "turso":
            ok, msg = ping()
            add("Base de datos", "ok" if ok else "error",
                "Turso conectada" if ok else f"Turso ERROR: {str(msg)[:60]}")
        else:
            add("Base de datos", "info", "SQLite local (sin Turso configurado)")
    except Exception as e:
        add("Base de datos", "error", str(e)[:80])

    # 3) Screener nocturno (frescura)
    try:
        from src.screener.engine import load_screener
        scr = load_screener() or {}
        n = len(scr.get("rows", []))
        fecha = scr.get("date") or scr.get("fecha") or scr.get("generated") or "—"
        add("Screener nocturno", "ok" if n else "warn",
            f"{n} empresas · {fecha}")
    except Exception as e:
        add("Screener nocturno", "warn", str(e)[:80])

    # 4) Deep Scan S&P 500 (progreso)
    try:
        from src.screener.deepscan import load_state
        ds = load_state() or {}
        done, uni = len(ds.get("done", {})), ds.get("universe_n", 0)
        add("Deep Scan S&P 500", "ok" if done else "info",
            f"{done}/{uni} analizadas · {ds.get('date', '—')}")
    except Exception as e:
        add("Deep Scan S&P 500", "warn", str(e)[:80])

    # 5) Historial de scores (crece día a día)
    try:
        from src.data.dbx import query
        r = query("SELECT COUNT(*), COUNT(DISTINCT ticker), MAX(date) "
                  "FROM score_history")
        total, tickers, ult = (r[0][0], r[0][1], r[0][2]) if r else (0, 0, None)
        add("Historial de scores", "ok" if total else "info",
            f"{total} registros · {tickers} tickers · último {ult or '—'}")
    except Exception as e:
        add("Historial de scores", "info", str(e)[:80])

    # 6) Clientes + coaching anti-pánico (tie-in con B3)
    try:
        from src.clients.manager import list_clients, panic_stats
        nc = len(list_clients())
        ps = panic_stats()
        add("Clientes", "info",
            f"{nc} cliente(s) · {ps['intervenciones']} frenos anti-pánico · "
            f"${ps['dinero_protegido']:,.0f} en pérdidas evitadas")
    except Exception as e:
        add("Clientes", "info", str(e)[:80])

    estados = [c["estado"] for c in checks]
    resumen = ("error" if "error" in estados
               else "warn" if "warn" in estados else "ok")
    return {"version": __version__, "checks": checks, "resumen": resumen}
