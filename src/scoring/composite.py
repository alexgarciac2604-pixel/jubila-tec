"""Score compuesto 0-100 + semáforo + tesis. Orquesta todos los motores.

Pesos: fundamental 25 · valoración 20 · técnico 20 · forense 20 · sentimiento 15.
Cada salida incluye el desglose (explicabilidad) y los supuestos usados.
"""
from __future__ import annotations

from src import __version__
from src.config import RISK_FREE
from src.data import quality, store
from src.data.market_data import (get_fundamentals, get_history, get_quote,
                                  source_of, using_sample)
from src.forensic.scores import full_forensic
from src.fundamental.metrics import analyze
from src.models.regime import market_regime, regime_weights
from src.models.risk import risk_summary
from src.news.news_feed import aggregate_sentiment, get_news
from src.technical.signals import technical_summary
from src.valuation.dcf import dcf_value, monte_carlo_dcf, reverse_dcf

WEIGHTS = {"fundamental": 0.25, "valuation": 0.20, "technical": 0.20,
           "forensic": 0.20, "sentiment": 0.15}


def _valuation_block(f: dict) -> dict:
    fcf = f.get("fcf") or 0.0
    shares = f.get("shares") or 1.0
    net_debt = (f.get("total_debt") or 0) - (f.get("cash") or 0)
    mc = f.get("market_cap") or 1.0
    beta = f.get("beta") or 1.0
    wacc = max(RISK_FREE + beta * 0.05, 0.06)          # CAPM con ERP 5%
    growth = 0.08
    base = dcf_value(fcf, growth, wacc, net_debt=net_debt, shares=shares)
    price = f.get("price") or 1.0
    upside = base["per_share"] / price - 1 if price else 0.0
    implied_g = reverse_dcf(mc, fcf, wacc, net_debt=net_debt) if fcf > 0 else None
    mc_dist = monte_carlo_dcf(fcf, growth, wacc, net_debt=net_debt, shares=shares, n=1500)
    # score: upside ±40% mapea a 0-100
    score = round(max(0.0, min(100.0, 50 + upside * 125)))
    return {"score": score, "wacc": wacc, "growth": growth, "fair_value": base["per_share"],
            "upside": upside, "implied_growth": implied_g, "mc": mc_dist,
            "net_debt": net_debt, "fcf": fcf}


def _thesis(total: int, name: str, val: dict, fund: dict, tech: dict) -> dict:
    up = val["upside"]
    bull = (f"{name} cotiza {abs(up):.0%} {'debajo' if up > 0 else 'encima'} de su valor DCF base. "
            f"Calidad fundamental {fund['quality_score']}/100 y técnico {tech['score']}/100. "
            "Si ejecuta el crecimiento asumido, hay margen de revalorización.")
    bear = ("Los supuestos del DCF pueden ser optimistas; una compresión de múltiplos o "
            "deterioro de márgenes invalidaría la tesis. Revisar el crecimiento implícito "
            "vs. el histórico antes de actuar.")
    base = ("Escenario central: retorno en línea con el mercado. Vigilar catalizadores "
            "(resultados, guía, tasas) y el semáforo de este score.")
    stance = "alcista" if total >= 70 else ("neutral" if total >= 45 else "bajista")
    return {"stance": stance, "bull": bull, "base": base, "bear": bear}


def composite_score(ticker: str) -> dict:
    f = get_fundamentals(ticker)
    h = get_history(ticker)
    q = get_quote(ticker)

    fund = analyze(f)
    tech = technical_summary(h)
    fore = full_forensic(f)
    val = _valuation_block(f)
    news = get_news(ticker)
    sent = aggregate_sentiment(news)
    sent_score = round(max(0.0, min(100.0, 50 + sent["avg"] * 50)))
    risk = risk_summary(h.Close)

    pillars = {
        "fundamental": fund["quality_score"],
        "valuation": val["score"],
        "technical": tech["score"],
        "forensic": fore["score"],
        "sentiment": sent_score,
    }
    regime = market_regime()
    weights = regime_weights(WEIGHTS, regime)
    total = round(sum(pillars[k] * weights[k] for k in weights))
    semaforo = "🟢" if total >= 70 else ("🟡" if total >= 45 else "🔴")

    dq = quality.assess(h)
    src = source_of(ticker)
    store.save_score(ticker, total, pillars, q["price"], __version__, src)

    return {
        "ticker": ticker.upper(), "name": f.get("name"), "sector": f.get("sector"),
        "quote": q, "total": total, "semaforo": semaforo,
        "pillars": pillars, "weights": weights, "regime": regime,
        "fundamental": fund, "technical": tech, "forensic": fore,
        "valuation": val, "sentiment": sent, "news": news, "risk": risk,
        "thesis": _thesis(total, f.get("name", ticker), val, fund, tech),
        "data_quality": dq,
        "score_history": store.score_history(ticker),
        "data_source": {"sample": "🧪 sintético", "stooq": "🟢 Stooq",
                        "yfinance": "🟢 yfinance"}.get(src, src),
        "fundamentals_raw": f,
    }
