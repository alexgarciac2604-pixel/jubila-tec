"""Síntesis técnica: señales interpretadas + score técnico 0-100."""
from __future__ import annotations

import pandas as pd

from src.technical import indicators as ind


def technical_summary(df: pd.DataFrame) -> dict:
    close = df.Close
    last = float(close.iloc[-1])
    sma50 = ind.sma(close, 50)
    sma200 = ind.sma(close, 200)
    rsi14 = float(ind.rsi(close).iloc[-1])
    macd_line, macd_sig, macd_hist = ind.macd(close)
    bb_up, bb_mid, bb_lo = ind.bollinger(close)
    atr14 = float(ind.atr(df).iloc[-1])
    adx14 = float(ind.adx(df).iloc[-1])
    obv_slope = float(ind.obv(df).diff().tail(20).mean())

    def _mom(days: int) -> float:
        return float(close.iloc[-1] / close.iloc[-days] - 1) * 100 if len(close) > days else 0.0

    mom_1m, mom_3m, mom_6m, mom_12m = _mom(21), _mom(63), _mom(126), _mom(252)

    signals: list[tuple[str, str, int]] = []  # (nombre, lectura, puntos ±)

    def add(name, ok, good, bad, pts=1):
        signals.append((name, good if ok else bad, pts if ok else -pts))

    s50 = float(sma50.iloc[-1]) if not pd.isna(sma50.iloc[-1]) else last
    s200 = float(sma200.iloc[-1]) if not pd.isna(sma200.iloc[-1]) else last
    add("Precio vs SMA50", last > s50, "alcista", "bajista")
    add("Precio vs SMA200", last > s200, "alcista", "bajista", 2)
    add("Cruce SMA50/200", s50 > s200, "golden (50>200)", "death (50<200)", 2)
    add("MACD", float(macd_hist.iloc[-1]) > 0, "impulso positivo", "impulso negativo")
    add("OBV (volumen)", obv_slope > 0, "acumulación", "distribución")
    add("Momentum 6m", mom_6m > 0, "positivo", "negativo")

    if rsi14 >= 70:
        signals.append(("RSI 14", f"{rsi14:.0f} — sobrecompra", -1))
    elif rsi14 <= 30:
        signals.append(("RSI 14", f"{rsi14:.0f} — sobreventa (rebote posible)", 1))
    else:
        signals.append(("RSI 14", f"{rsi14:.0f} — neutral", 0))

    trend_note = "tendencia fuerte" if adx14 >= 25 else "sin tendencia clara"
    signals.append(("ADX 14", f"{adx14:.0f} — {trend_note}", 0))

    raw = sum(p for _, _, p in signals)
    max_pts = sum(abs(p) for _, _, p in signals if p != 0) or 1
    score = round(50 + 50 * raw / max_pts)
    score = max(0, min(100, score))

    return {
        "score": score,
        "signals": signals,
        "rsi": rsi14, "adx": adx14, "atr": atr14,
        "sma50": s50, "sma200": s200,
        "macd_hist": float(macd_hist.iloc[-1]),
        "mom_1m": mom_1m, "mom_3m": mom_3m, "mom_6m": mom_6m, "mom_12m": mom_12m,
        "bb_upper": float(bb_up.iloc[-1]), "bb_lower": float(bb_lo.iloc[-1]),
        "fib": ind.fibonacci_levels(df),
    }
