"""Componentes UI reutilizables: ticker tape, gauge, badges, velas."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.config import TAPE_TICKERS
from src.data.market_data import get_quote, using_sample


def render_ticker_tape() -> None:
    try:
        quotes = [get_quote(t) for t in TAPE_TICKERS]
    except Exception:
        return
    items = []
    for q in quotes:
        cls = "jt-up" if q["change_pct"] >= 0 else "jt-down"
        sign = "▲" if q["change_pct"] >= 0 else "▼"
        items.append(
            f"<span><b>{q['ticker']}</b> ${q['price']:.2f} "
            f"<span class='{cls}'>{sign}{abs(q['change_pct']):.2f}%</span></span>"
        )
    row = "".join(items)
    st.markdown(  # se duplica el contenido para loop continuo
        f"<div class='jt-tape'><div class='jt-tape-inner'>{row}{row}</div></div>",
        unsafe_allow_html=True,
    )


def source_caption() -> None:
    if using_sample():
        st.caption("🧪 Mostrando datos sintéticos deterministas (sin conexión o modo demo).")


def score_gauge(score: int, title: str = "Score de inversión") -> go.Figure:
    color = "#34d399" if score >= 70 else ("#fbbf24" if score >= 45 else "#f87171")
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        title={"text": title, "font": {"size": 15}},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 45], "color": "rgba(248,113,113,.18)"},
                {"range": [45, 70], "color": "rgba(251,191,36,.18)"},
                {"range": [70, 100], "color": "rgba(52,211,153,.18)"},
            ],
        },
    ))
    fig.update_layout(height=230, margin=dict(l=25, r=25, t=45, b=5),
                      paper_bgcolor="rgba(0,0,0,0)", font={"color": "#e2e8f0"})
    return fig


def candles_figure(df, title: str = "", sma50=None, sma200=None) -> go.Figure:
    fig = go.Figure(go.Candlestick(
        x=df.index, open=df.Open, high=df.High, low=df.Low, close=df.Close,
        name="OHLC", increasing_line_color="#34d399", decreasing_line_color="#f87171",
    ))
    if sma50 is not None:
        fig.add_scatter(x=df.index, y=sma50, name="SMA 50",
                        line=dict(color="#60a5fa", width=1.2))
    if sma200 is not None:
        fig.add_scatter(x=df.index, y=sma200, name="SMA 200",
                        line=dict(color="#fbbf24", width=1.2))
    fig.update_layout(
        title=title, height=420, xaxis_rangeslider_visible=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,.4)",
        font={"color": "#e2e8f0"}, margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", y=1.06),
    )
    return fig


def dark_fig(fig: go.Figure, height: int = 340) -> go.Figure:
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,.4)",
                      font={"color": "#e2e8f0"}, height=height,
                      margin=dict(l=10, r=10, t=40, b=10))
    return fig


def download_df(df, filename: str) -> None:
    """Botón de exportación CSV (UTF-8 con BOM para Excel)."""
    st.download_button("⬇️ Exportar CSV", df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=filename, mime="text/csv")
