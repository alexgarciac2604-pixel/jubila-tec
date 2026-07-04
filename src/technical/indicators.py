"""Indicadores técnicos clásicos (pandas/numpy puro)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(close: pd.Series, n: int) -> pd.Series:
    return close.rolling(n).mean()


def ema(close: pd.Series, n: int) -> pd.Series:
    return close.ewm(span=n, adjust=False).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50.0)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    line = ema(close, fast) - ema(close, slow)
    sig = line.ewm(span=signal, adjust=False).mean()
    return line, sig, line - sig


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    mid = sma(close, n)
    sd = close.rolling(n).std()
    return mid + k * sd, mid, mid - k * sd


def true_range(df: pd.DataFrame) -> pd.Series:
    pc = df.Close.shift()
    return pd.concat(
        [df.High - df.Low, (df.High - pc).abs(), (df.Low - pc).abs()], axis=1
    ).max(axis=1)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    return true_range(df).ewm(alpha=1 / n, adjust=False).mean()


def obv(df: pd.DataFrame) -> pd.Series:
    direction = np.sign(df.Close.diff()).fillna(0)
    return (direction * df.Volume).cumsum()


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    up = df.High.diff()
    dn = -df.Low.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    atr_ = true_range(df).ewm(alpha=1 / n, adjust=False).mean()
    pdi = 100 * plus_dm.ewm(alpha=1 / n, adjust=False).mean() / atr_
    mdi = 100 * minus_dm.ewm(alpha=1 / n, adjust=False).mean() / atr_
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean().fillna(20.0)


def zscore(series: pd.Series, n: int = 60) -> pd.Series:
    m = series.rolling(n).mean()
    s = series.rolling(n).std()
    return (series - m) / s.replace(0, np.nan)


def fibonacci_levels(df: pd.DataFrame, lookback: int = 252) -> dict:
    w = df.Close.tail(lookback)
    hi, lo = float(w.max()), float(w.min())
    rng = hi - lo
    return {f"{r:.1%}": hi - r * rng for r in (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0)}
