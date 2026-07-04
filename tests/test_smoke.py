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
    assert "Briefing Jubila-Tec" in b
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


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok {fn.__name__}")
    print("All smoke tests passed.")
