"""Smoke tests del núcleo (sin Streamlit). Corre: python tests/test_smoke.py"""
from __future__ import annotations

import os
import sys

os.environ["JT_FORCE_SAMPLE"] = "1"
os.environ.setdefault("JT_DB_PATH", "/tmp/jt_test.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_data():
    from src.data import market_data as md
    h = md.get_history("AAPL")
    assert len(h) > 200 and (h.High >= h.Low).all()
    f = md.get_fundamentals("AAPL")
    assert f["revenue"] > 0 and f["revenue"] > f["ebit"] > 0
    q = md.get_quote("AAPL")
    assert q["price"] > 0


def test_technical():
    from src.data.market_data import get_history
    from src.technical.signals import technical_summary
    t = technical_summary(get_history("MSFT"))
    assert 0 <= t["score"] <= 100 and 0 <= t["rsi"] <= 100 and t["atr"] > 0
    assert "mom_1m" in t and "mom_12m" in t


def test_fundamental():
    from src.data.market_data import get_fundamentals
    from src.fundamental.metrics import analyze
    m = analyze(get_fundamentals("NVDA"))
    assert 0 <= m["quality_score"] <= 100
    assert m["gross_margin"] > m["net_margin"]  # coherencia contable


def test_valuation():
    from src.valuation.dcf import dcf_value, monte_carlo_dcf, reverse_dcf
    v = dcf_value(100.0, 0.08, 0.10, shares=10)
    assert v["per_share"] > 0
    # golden: FCF=100, g=5%, WACC=10%, tg=2.5%, 5 años → EV ≈ 1518.9 (verificado a mano:
    # suma flujos descontados 435.8 + TV descontado 1083.1)
    ev = dcf_value(100.0, 0.05, 0.10, 0.025, 5)["ev"]
    assert 1510 < ev < 1528, ev
    g = reverse_dcf(v["equity_value"], 100.0, 0.10)
    assert g is not None and abs(g - 0.08) < 0.005  # recupera el growth original
    mc = monte_carlo_dcf(100.0, 0.08, 0.10, shares=10, n=500)
    assert mc["p10"] < mc["p50"] < mc["p90"]


def test_forensic():
    from src.data.market_data import get_fundamentals
    from src.forensic.scores import full_forensic
    fo = full_forensic(get_fundamentals("JPM"))
    assert 0 <= fo["score"] <= 100 and 0 <= fo["piotroski"]["score"] <= 9


def test_risk():
    from src.data.market_data import get_history
    from src.models.risk import monte_carlo_paths, risk_summary
    r = risk_summary(get_history("TSLA").Close)
    assert r["ann_vol"] > 0 and r["cvar95_d"] >= r["var95_d"]  # propiedad: CVaR ≥ VaR
    mc = monte_carlo_paths(0.07, 0.18, years=1, n_paths=300)
    assert mc["p10"] < mc["p50"] < mc["p90"]


def test_portfolio():
    import numpy as np
    import pandas as pd
    from src.data.market_data import get_history
    from src.portfolio import optimizer as opt
    prices = pd.DataFrame({t: get_history(t).Close for t in ["AAPL", "MSFT", "XOM", "JNJ"]}).dropna()
    rets = opt.returns_matrix(prices)
    for fn in (opt.max_sharpe, opt.min_variance, opt.risk_parity, opt.equal_weight):
        w = fn(rets)
        assert abs(w.sum() - 1) < 1e-6 and (w >= -1e-9).all()  # propiedad: suma 1, long-only
    st = opt.portfolio_stats(opt.equal_weight(rets), rets)
    assert st["ann_vol"] > 0 and abs(float(np.sum(st["risk_contrib_pct"])) - 1) < 1e-6


def test_news_macro_geo():
    from src.news.news_feed import aggregate_sentiment, get_news
    from src.macro.macro import get_macro_series, yield_curve
    from src.geopolitics.events import classify_text, sector_bias
    news = get_news("AAPL")
    assert len(news) > 0 and all(-1 <= i["sentiment"] <= 1 for i in news)
    assert aggregate_sentiment(news)["n"] == len(news)
    series = get_macro_series()
    assert "Desempleo (%)" in series and len(yield_curve()) == 8
    assert classify_text("Nuevos aranceles a China golpean al sector") is not None
    assert isinstance(sector_bias("Tecnología"), float)


def test_underdog_scoring_report():
    from src.underdog.underdog import scan
    from src.scoring.composite import composite_score
    from src.report.generator import build_report
    df = scan(["AAPL", "PFE", "BA", "T"])
    assert len(df) == 4 and df.score.between(0, 100).all()
    a = composite_score("AAPL")
    assert 0 <= a["total"] <= 100 and a["semaforo"] in "🟢🟡🔴"
    assert "data_quality" in a and 0 <= a["data_quality"]["score"] <= 100
    md = build_report(a)
    assert "Score de inversión" in md and a["ticker"] in md


def test_fase1_quality_store():
    from src.data.market_data import get_history
    from src.data.quality import assess
    from src.data import store
    dq = assess(get_history("AAPL"))
    assert 0 <= dq["score"] <= 100 and "badge" in dq
    store.save_score("TEST", 77, {"fundamental": 80}, 123.4, "0.2.0", "sample")
    hist = store.score_history("TEST")
    assert hist and hist[-1]["total"] == 77


def test_fase1_hrp_stress():
    import pandas as pd
    from src.data.market_data import get_history
    from src.portfolio import optimizer as opt
    from src.models.stress import portfolio_stress, SCENARIOS
    tickers = ["AAPL", "MSFT", "XOM", "JNJ", "JPM"]
    prices = pd.DataFrame({t: get_history(t).Close for t in tickers}).dropna()
    rets = opt.returns_matrix(prices)
    w = opt.hrp(rets)
    assert abs(w.sum() - 1) < 1e-6 and (w >= -1e-9).all() and (w < 0.9).all()
    sdf = portfolio_stress(tickers, w)
    assert len(sdf) == len(SCENARIOS)
    crisis = sdf[sdf.Escenario.str.contains("2008")]["P&L estimado %"].iloc[0]
    assert crisis < -10  # una crisis de crédito nunca puede salir positiva


def test_fase1_ratios():
    from src.data.market_data import get_history
    from src.models.risk import risk_summary
    r = risk_summary(get_history("KO").Close)
    assert r["ulcer"] >= 0
    assert r["omega"] is None or r["omega"] > 0


def test_fase2_retirement():
    from src.retirement.planner import (compare_withdrawal_rules, glide_path_equity,
                                        required_monthly, simulate_accumulation)
    assert glide_path_equity(30) > glide_path_equity(64)  # más joven, más equity
    sim = simulate_accumulation(35, 65, 50_000, 500, goal=1_000_000, n=500)
    assert sim["p10"] < sim["p50"] < sim["p90"]
    assert 0.0 <= sim["prob_goal"] <= 1.0
    assert sim["bands"].shape[0] == 3 and sim["bands"].shape[1] == sim["months"]
    req = required_monthly(200_000, 40, 65, 50_000, target_prob=0.8, n=300)
    assert req is not None and req >= 0
    rules = compare_withdrawal_rules(1_000_000, years=30, n=500)
    by = {r["rule"]: r for r in rules}
    assert by["percent"]["ruin_prob"] == 0.0        # % del saldo nunca quiebra
    assert 0.0 <= by["fixed_real"]["ruin_prob"] <= 1.0
    assert by["guyton"]["ruin_prob"] <= by["fixed_real"]["ruin_prob"] + 0.05


def test_fase2_backtest():
    from src.backtest.engine import backtest_momentum, backtest_portfolio, block_bootstrap_ci
    import numpy as np
    lo, hi = block_bootstrap_ci(np.array([1.0] * 40))
    assert abs(lo - 1) < 1e-9 and abs(hi - 1) < 1e-9  # serie constante → IC degenerado
    r = backtest_momentum(["AAPL", "MSFT", "NVDA", "XOM", "JNJ", "JPM", "KO", "BA", "T"])
    assert r["ok"] and r["n_obs"] > 3
    assert len(r["quantile_returns_ann"]) == 3 and 0 <= r["hit_rate"] <= 1
    from src.portfolio import optimizer as opt
    p = backtest_portfolio(["AAPL", "MSFT", "XOM", "JNJ"], opt.hrp)
    assert len(p["curve_method"]) == len(p["curve_equal"]) > 2
    assert p["stats_method"]["final"] > 0 and p["stats_equal"]["final"] > 0


def test_fase2_sizing():
    from src.models.sizing import kelly_fraction, suggested_position
    assert kelly_fraction(0.10, 0.20) > 0          # edge positivo → Kelly positivo
    s = suggested_position(0.10, 0.20)
    assert 0 <= s["suggested"] <= s["cap"]
    s_neg = suggested_position(0.01, 0.20)         # retorno < rf
    assert s_neg["suggested"] == 0.0


def test_fase2b_alerts():
    from src.alerts import engine as al
    before = {a["id"] for a in al.list_alerts()}
    al.add_alert("AAPL", "price_above", 0.01)   # siempre dispara (precio > 0.01)
    al.add_alert("AAPL", "price_below", 0.01)   # nunca dispara
    alerts = [a for a in al.list_alerts() if a["id"] not in before]
    assert len(alerts) == 2
    fired = al.evaluate_alerts()
    msgs = [f["message"] for f in fired if f["ticker"] == "AAPL"]
    assert any("supera" in m for m in msgs)
    assert not any(f["kind"] == "price_below" and f["ticker"] == "AAPL" for f in fired)
    for a in alerts:
        al.delete_alert(a["id"])
    assert all(a["id"] not in {x["id"] for x in al.list_alerts()} for a in alerts)
    assert al.send_telegram("test") is False    # sin token → False, sin explotar


def test_fase2b_fx():
    from src.data.market_data import get_fx_history, get_history
    from src.models.fx import currency_decomposition
    from src.portfolio import optimizer as opt
    import pandas as pd
    fx = get_fx_history("MXN=X")
    assert len(fx) > 200 and (fx.Close > 5).all()  # rango realista USD/MXN
    prices = pd.DataFrame({t: get_history(t).Close for t in ["AAPL", "JNJ", "XOM"]}).dropna()
    rets = opt.returns_matrix(prices)
    port = opt.portfolio_stats(opt.equal_weight(rets), rets)["daily_returns"]
    dec = currency_decomposition(port, fx)
    assert dec["ok"] and -1 <= dec["corr"] <= 1
    # composición: (1+usd)(1+fx) ≈ 1+mxn en promedio anualizado (tolerancia por interacción)
    approx = (1 + dec["ann_usd"]) * (1 + dec["ann_fx"]) - 1
    assert abs(approx - dec["ann_mxn"]) < 0.05
    assert dec["vol_mxn"] > 0


def test_fase3_events():
    from src.news.events import classify_event
    ev = classify_event("Apple recorta su guía anual por debilidad de demanda")
    assert ev is not None and ev["type"] == "guidance_cut" and ev["dir"] < 0
    ev2 = classify_event("Microsoft anuncia recompra de acciones")
    assert ev2["type"] == "buyback" and ev2["dir"] > 0
    assert classify_event("El clima estuvo agradable hoy") is None
    from src.news.news_feed import get_news
    items = get_news("AAPL")
    assert any(i.get("event") for i in items)  # el feed sintético contiene eventos


def test_fase3_regime():
    import numpy as np
    from src.models.regime import fit_gmm2, market_regime, regime_weights
    rng = np.random.default_rng(1)
    calm = rng.normal(0, 0.005, 300)
    turb = rng.normal(0, 0.03, 100)
    g = fit_gmm2(np.concatenate([calm, turb]))
    assert g["sigma_calm"] < g["sigma_turb"]           # separa los dos estados
    reg = market_regime()
    assert 0.0 <= reg["p_turbulent"] <= 1.0
    assert reg["vol_state"] in ("calma", "turbulencia")
    assert reg["trend"] in ("alcista", "bajista")
    from src.scoring.composite import WEIGHTS
    w = regime_weights(WEIGHTS, reg)
    assert abs(sum(w.values()) - 1) < 1e-9             # pesos siempre suman 1
    w_turb = regime_weights(WEIGHTS, {"vol_state": "turbulencia"})
    assert w_turb["technical"] < WEIGHTS["technical"]  # turbulencia castiga momentum


def test_fase3_edgar_fallback():
    from src.data.edgar import insider_activity, fundamentals_overlay
    ins = insider_activity("AAPL")
    assert "summary" in ins and ins["form4_90d"] >= 0
    assert ins["source"] in ("SEC EDGAR", "sample")
    ov = fundamentals_overlay("AAPL")   # sin red devuelve {} sin lanzar
    assert isinstance(ov, dict)
    a_ins = insider_activity("AAPL")
    assert a_ins == ins                 # determinista con caché/fallback


def test_fase4_copilot():
    from src.copilot.copilot import answer, build_context, detect_intent
    assert detect_intent("como ves AAPL hoy?")["ticker"] == "AAPL"
    assert detect_intent("¿Qué te parece apple?")["ticker"] == "AAPL"      # nombre común
    assert detect_intent("analiza tesla por favor")["ticker"] == "TSLA"
    assert detect_intent("¿cómo ves coca cola?")["ticker"] == "KO"
    assert detect_intent("¿cómo ves Spacex?")["ticker"] == "SPCX"         # IPO jun-2026
    assert detect_intent("analiza SPCX")["ticker"] == "SPCX"
    assert detect_intent("¿cómo ves openai?")["kind"] == "private"         # IPO pospuesta
    ut = detect_intent("¿cómo ves QWZX?")                                  # ticker inventado
    assert ut["kind"] == "unknown_ticker" and ut["token"] == "QWZX"
    assert detect_intent("quiero jubilarme a los 60")["kind"] == "retirement"
    assert detect_intent("mi meta es un millon")["kind"] == "retirement"   # 'meta' ≠ META
    assert detect_intent("como ves META")["ticker"] == "META"              # mayúsculas sí
    assert detect_intent("como esta el mercado")["kind"] == "market"
    assert detect_intent("hola")["kind"] == "greeting"
    ctx = build_context({"kind": "ticker", "ticker": "AAPL"})
    assert "Score" in ctx and "DCF" in ctx and "VaR95" in ctx  # el contexto trae los números
    res = answer("¿Qué te parece apple?")   # sin API key → plantilla determinista
    assert res["mode"] == "plantilla" and "AAPL" in res["text"] and "/100" in res["text"]
    assert "asesoría" in res["text"]        # siempre recuerda el disclaimer
    assert "/100" in answer("¿cómo ves spacex?")["text"]     # análisis completo
    assert "QWZX" in answer("¿cómo ves QWZX?")["text"]
    assert "👋" in answer("hola")["text"]


def test_fase4_briefing():
    from src.report.briefing import daily_briefing
    b = daily_briefing(["AAPL", "MSFT", "XOM"])
    assert "Briefing AL-X" in b
    assert any(w in b for w in ("calma", "turbulencia", "Calma", "Turbulencia"))
    assert "%" in b and len(b) > 200
    assert daily_briefing(["AAPL", "MSFT", "XOM"]) == b  # determinista con datos sample


def test_daily_update_job():
    from jobs.daily_update import run
    from src.config import DEFAULT_UNIVERSE
    from src.data.market_data import lookup_ticker
    r = run(verbose=False)
    assert r["scores_ok"] == len(DEFAULT_UNIVERSE) and not r["errors"]
    assert r["alerts_fired"] >= 0 and "seconds" in r
    from src.data import store
    assert store.score_history("SPCX")          # el job persistió el score de hoy
    assert lookup_ticker("AAPL") is False       # offline → False, sin explotar


def test_v08_watchlist_peers():
    from src.data import store
    for x in store.watchlist():
        store.watchlist_remove(x)               # estado limpio
    store.watchlist_add("AAPL")
    store.watchlist_add("MSFT")
    store.watchlist_add("aapl")                 # duplicado (case-insensitive) ignorado
    assert store.watchlist() == ["AAPL", "MSFT"]
    from src.report.briefing import daily_briefing
    b = daily_briefing()                        # sin argumento → usa Mi Lista
    assert "AAPL" in b or "MSFT" in b
    store.watchlist_remove("AAPL")
    assert store.watchlist() == ["MSFT"]
    store.watchlist_remove("MSFT")
    from src.fundamental.metrics import peer_comparison
    df = peer_comparison("AAPL")
    assert len(df) >= 2 and df.iloc[0]["Ticker"].startswith("⭐")
    assert "P/E" in df.columns and "Calidad" in df.columns


def test_v081_short_history_ipo():
    """Una IPO con pocos días debe usar datos reales y avisar, no inventar historia."""
    from src.data.market_data import get_history
    from src.data.quality import assess
    from src.technical.signals import technical_summary
    from src.models.risk import risk_summary
    h15 = get_history("AAPL").tail(15)              # simula IPO de 3 semanas
    dq = assess(h15)
    assert any("historial corto" in i for i in dq["issues"])
    ts = technical_summary(h15)                      # los motores no deben explotar
    assert 0 <= ts["score"] <= 100
    r = risk_summary(h15.Close)
    assert r["ann_vol"] > 0


def test_v082_resolve_symbol():
    """El buscador entiende nombres y typos; jamás resuelve a algo inventado."""
    from src.data.market_data import resolve_symbol
    assert resolve_symbol("TSLA") == "TSLA"
    assert resolve_symbol("TESLA") == "TSLA"       # el bug reportado
    assert resolve_symbol("tesla") == "TSLA"
    assert resolve_symbol("apple") == "AAPL"
    assert resolve_symbol("coca cola") == "KO"
    assert resolve_symbol("APPLE") == "AAPL"
    assert resolve_symbol("microsft") == "MSFT"    # typo cercano
    assert resolve_symbol("") is None
    assert resolve_symbol("XQZWV") is None          # sin red no se inventa nada
    from src.copilot.copilot import detect_intent   # el copiloto sigue funcionando
    assert detect_intent("¿qué te parece tesla?")["ticker"] == "TSLA"


def test_v09_sector_map_and_workflow():
    from src.data.market_data import SECTOR_EN_ES
    from src.config import SECTOR_OF
    ours = set(SECTOR_OF.values())
    assert SECTOR_EN_ES["Technology"] == "Tecnología"
    assert all(v in ours for v in SECTOR_EN_ES.values())  # siempre cae en un bucket válido
    import os
    assert os.path.exists(".github/workflows/daily.yml")   # cron del briefing en la nube


def test_v010_screener():
    import os
    os.environ["JT_SCREENER_PATH"] = "/tmp/jt_screener.json"
    from src.screener.engine import load_screener, run_screener, save_screener, screen_ticker
    from src.config import SCREENER_UNIVERSE
    assert len(SCREENER_UNIVERSE) >= 100 and "SPCX" in SCREENER_UNIVERSE
    r = screen_ticker("AAPL")
    assert r and 0 <= r["score"] <= 100 and r["price"] > 0
    data = run_screener(["AAPL", "MSFT", "XOM", "JNJ", "KO"])
    assert data["n"] == 5
    scores = [row["score"] for row in data["rows"]]
    assert scores == sorted(scores, reverse=True)   # ordenado de mejor a peor
    save_screener(data)
    back = load_screener()
    assert back and back["n"] == 5 and back["date"] == data["date"]


def test_v011_clients():
    from src.clients import manager as cm
    for c in cm.list_clients():
        cm.delete_client(c["id"])                       # estado limpio
    assert cm.create_client("C-001", "Juan Pérez", "1234", "moderado", 100_000)
    assert not cm.create_client("c-001", "Otro", "9999")  # id duplicado → False
    assert cm.verify_client("C-001", "1234")["name"] == "Juan Pérez"
    assert cm.verify_client("juan pérez", "1234")["id"] == "C-001"  # login por nombre
    assert cm.verify_client("C-001", "0000") is None       # PIN incorrecto
    cm.set_portfolio("C-001", ["AAPL", "MSFT", "JNJ"], [0.4, 0.35, 0.25],
                     {"AAPL": 200.0, "MSFT": 400.0, "JNJ": 150.0})
    h = cm.get_portfolio("C-001")
    assert len(h) == 3 and abs(sum(x["weight"] for x in h) - 1) < 1e-9
    assert h[0]["price_at"] > 0                            # precio de entrada congelado
    backup = cm.export_all()
    cm.delete_client("C-001")
    assert cm.list_clients() == [] and cm.get_portfolio("C-001") == []
    assert cm.import_all(backup) == 1                      # respaldo restaura todo
    assert cm.verify_client("C-001", "1234") is not None
    cm.delete_client("C-001")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok {fn.__name__}")
    print("All smoke tests passed.")


def test_dbx_dual_layer():
    """Capa dual: codificación Hrana simétrica + routing a Turso con secrets."""
    from unittest.mock import patch
    from src.data import dbx

    # 1) encode/decode simétricos (los enteros viajan como string en Hrana)
    assert dbx._decode(dbx._encode(42)) == 42
    assert dbx._decode(dbx._encode(3.14)) == 3.14
    assert dbx._decode(dbx._encode("AAPL")) == "AAPL"
    assert dbx._decode(dbx._encode(None)) is None
    assert dbx._decode(dbx._encode(True)) == 1

    # 2) sin secrets → SQLite local
    assert dbx.backend() == "sqlite"

    # 3) con secrets → llamadas HTTP al pipeline, filas decodificadas
    calls = []

    class _Resp:
        status_code = 200

        def json(self):
            n = len(calls[-1]["json"]["requests"]) - 1  # sin contar el close
            ok = {"type": "ok", "response": {"type": "execute", "result": {
                "cols": [], "rows": [[{"type": "text", "value": "AAPL"},
                                      {"type": "integer", "value": "77"}]]}}}
            return {"results": [ok] * n}

    def _post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers})
        return _Resp()

    env = {"TURSO_DATABASE_URL": "libsql://alx-db-test.turso.io",
           "TURSO_AUTH_TOKEN": "tok"}
    with patch.dict(os.environ, env), patch("requests.post", _post):
        dbx._TURSO_READY = False
        assert dbx.backend() == "turso"
        rows = dbx.query("SELECT ticker, total FROM score_history")
        assert rows == [("AAPL", 77)]
        assert calls[0]["url"] == "https://alx-db-test.turso.io/v2/pipeline"
        assert calls[0]["headers"]["Authorization"] == "Bearer tok"
        assert len(calls) == 3          # 1ª esquema + 2ª migraciones + 3ª query
        dbx.execute_many([("DELETE FROM watchlist WHERE ticker=?", ("A",)),
                          ("INSERT INTO watchlist VALUES (?,?)", ("A", "hoy"))])
        assert len(calls) == 4          # lote de 2 escrituras = 1 sola llamada
    dbx._TURSO_READY = False            # no contaminar otros tests
    assert dbx.backend() == "sqlite"    # secrets fuera de scope → local otra vez


def test_v014_cuenta_viva():
    """Movimientos, depósitos, solicitudes y nota del asesor (Portal v0.14)."""
    from src.clients import manager as cm
    for c in cm.list_clients():
        cm.delete_client(c["id"])
    assert cm.create_client("C-014", "Ana Gómez", "2468", "conservador", 50_000)

    # el alta registró el depósito inicial
    movs = cm.get_movements("C-014")
    assert movs and movs[-1]["tipo"] == "Depósito inicial" and movs[-1]["monto"] == 50_000

    # asignar congela MONTO invertido; el depósito posterior no lo distorsiona
    cm.set_portfolio("C-014", ["JNJ", "KO"], [0.6, 0.4],
                     {"JNJ": 150.0, "KO": 60.0})
    h = cm.get_portfolio("C-014")
    assert {x["ticker"]: x["invested"] for x in h} == {"JNJ": 30_000.0, "KO": 20_000.0}
    assert len(cm.get_movements("C-014")) == 3          # depósito + 2 compras

    cm.add_deposit("C-014", 10_000, "aportación")
    assert cm.get_capital("C-014") == 60_000            # capital creció
    assert cm.get_portfolio("C-014")[0]["invested"] == 30_000.0  # invertido intacto
    cm.add_deposit("C-014", -5_000, "retiro parcial")
    assert cm.get_capital("C-014") == 55_000
    tipos = [m["tipo"] for m in cm.get_movements("C-014")]
    assert "Retiro" in tipos and "Depósito" in tipos

    # solicitudes: crear → pendiente → atendida
    cm.create_request("C-014", "Quiero un portafolio con más dividendos.")
    reqs = cm.get_requests("C-014")
    assert reqs and reqs[0]["estado"] == "pendiente"
    cm.close_request(reqs[0]["id"])
    assert cm.get_requests("C-014")[0]["estado"] == "atendida"

    # nota del asesor
    cm.set_note("C-014", "Mantén el rumbo; rebalanceamos en octubre.")
    assert "rumbo" in cm.get_note("C-014")["nota"]

    cm.delete_client("C-014")


def test_v016_ordenes_y_practica():
    """Órdenes al asesor (aprobar/rechazar con matemática de efectivo) y paper."""
    from src.clients import manager as cm
    for c in cm.list_clients():
        cm.delete_client(c["id"])
    assert cm.create_client("C-016", "Leo Ruiz", "1357", "moderado", 50_000)

    # compra que excede el efectivo → rechazo con mensaje claro
    cm.create_order("C-016", "compra", "AAPL", 80_000, "test")
    oid = [o for o in cm.get_orders("C-016") if o["estado"] == "pendiente"][0]["id"]
    ok, msg = cm.approve_order(oid)
    assert not ok and "Efectivo insuficiente" in msg
    cm.reject_order(oid)
    assert cm.get_orders("C-016")[0]["estado"] == "rechazada"

    # compra válida → holding creado, efectivo baja, movimiento registrado
    cm.create_order("C-016", "compra", "AAPL", 10_000, "test")
    oid = [o for o in cm.get_orders("C-016") if o["estado"] == "pendiente"][0]["id"]
    ok, msg = cm.approve_order(oid)
    assert ok, msg
    h = cm.get_portfolio("C-016")
    assert len(h) == 1 and abs(h[0]["invested"] - 10_000) < 0.01
    assert abs(h[0]["weight"] - 1.0) < 1e-9              # pesos recalculados
    assert cm.get_capital("C-016") == 50_000             # comprar no toca capital
    assert any(m["tipo"] == "Compra" for m in cm.get_movements("C-016"))

    # segunda aprobación de la misma orden → bloqueada
    ok, msg = cm.approve_order(oid)
    assert not ok and "aprobada" in msg

    # venta parcial al mismo precio → invertido baja, sin G/P realizada
    cm.create_order("C-016", "venta", "AAPL", 4_000, "test")
    oid = [o for o in cm.get_orders("C-016") if o["estado"] == "pendiente"][0]["id"]
    ok, msg = cm.approve_order(oid)
    assert ok, msg
    h = cm.get_portfolio("C-016")[0]
    assert abs(h["invested"] - 6_000) < 1.0
    assert abs(cm.get_capital("C-016") - 50_000) < 1.0   # px estable → G/P ≈ 0

    # venta de lo que no tiene → error honesto
    cm.create_order("C-016", "venta", "MSFT", 1_000, "test")
    oid = [o for o in cm.get_orders("C-016") if o["estado"] == "pendiente"][0]["id"]
    ok, msg = cm.approve_order(oid)
    assert not ok and "no tiene MSFT" in msg

    # simulador: 100k ficticios, compra, venta y reset
    ps = cm.paper_state("C-016")
    assert ps["cash"] == 100_000 and ps["positions"] == []
    ok, _ = cm.paper_trade("C-016", "compra", "NVDA", 20_000)
    assert ok
    ps = cm.paper_state("C-016")
    assert abs(ps["cash"] - 80_000) < 0.01 and len(ps["positions"]) == 1
    ok, _ = cm.paper_trade("C-016", "venta", "NVDA", 5_000)
    assert ok and abs(cm.paper_state("C-016")["cash"] - 85_000) < 1.0
    cm.paper_reset("C-016")
    ps = cm.paper_state("C-016")
    assert ps["cash"] == 100_000 and ps["positions"] == []

    cm.delete_client("C-016")


def test_v017_ejecucion_directa():
    """El cliente ejecuta directo; queda auditada como 'ejecutada'."""
    from src.clients import manager as cm
    for c in cm.list_clients():
        cm.delete_client(c["id"])
    assert cm.create_client("C-017", "Mia Solis", "8642", "agresivo", 30_000)

    ok, msg = cm.execute_order("C-017", "compra", "NVDA", 12_000, "Score 80")
    assert ok and "ejecutada" in msg.lower()
    assert cm.get_portfolio("C-017")[0]["invested"] == 12_000
    assert cm.get_orders("C-017")[0]["estado"] == "ejecutada"

    ok, msg = cm.execute_order("C-017", "compra", "NVDA", 25_000, "")
    assert not ok and "insuficiente" in msg          # 18k de efectivo, pide 25k
    assert len(cm.get_orders("C-017")) == 1          # el fallo NO se registra

    ok, _ = cm.execute_order("C-017", "venta", "NVDA", 2_000, "")
    assert ok and abs(cm.get_portfolio("C-017")[0]["invested"] - 10_000) < 1.0
    cm.delete_client("C-017")


def test_v018_canastas_y_watchlist():
    """Canastas del asesor (inversión multi-componente) y watchlist del cliente."""
    from src.clients import manager as cm
    for c in cm.list_clients():
        cm.delete_client(c["id"])
    for b in cm.list_baskets():
        cm.delete_basket(b["id"])
    assert cm.create_client("C-018", "Sam Rio", "9753", "moderado", 40_000)

    cm.create_basket("🛡️ Escudo", "Defensivas para dormir tranquilo",
                     ["JNJ", "KO", "PG"], [1 / 3] * 3)
    bs = cm.list_baskets()
    assert len(bs) == 1 and bs[0]["name"] == "🛡️ Escudo"

    ok, msg = cm.invest_basket("C-018", bs[0]["id"], 50_000)
    assert not ok and "insuficiente" in msg              # 40k de efectivo

    ok, msg = cm.invest_basket("C-018", bs[0]["id"], 9_000)
    assert ok, msg
    h = cm.get_portfolio("C-018")
    assert len(h) == 3
    assert abs(sum(x["invested"] for x in h) - 9_000) < 1.0
    assert any(o["ticker"].startswith("🧺") for o in cm.get_orders("C-018"))

    cm.watch_add("C-018", "NVDA")
    cm.watch_add("C-018", "nvda")                        # dup case-insensitive
    cm.watch_add("C-018", "AAPL")
    assert cm.watch_list("C-018") == ["AAPL", "NVDA"]  # mismo día → alfabético
    cm.watch_remove("C-018", "NVDA")
    assert cm.watch_list("C-018") == ["AAPL"]

    from src.report.briefing import client_briefing as _briefing_cliente
    rows = [{"Ticker": "JNJ", "% Día": 1.2}, {"Ticker": "KO", "% Día": -1.5}]
    b = _briefing_cliente(rows, 0.4, 160.0)
    assert "JNJ" in b and "KO" in b and "+0.40%" in b
    assert "portafolio" in b.lower()
    assert _briefing_cliente([], 0.0, 0.0)               # sin posiciones no truena

    cm.delete_basket(bs[0]["id"])
    cm.delete_client("C-018")
