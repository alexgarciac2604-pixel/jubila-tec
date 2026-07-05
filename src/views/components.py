"""Componentes UI reutilizables — tema claro premium (mismas firmas de siempre)."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.config import TAPE_TICKERS
from src.data.market_data import get_quote, using_sample

# paleta del sistema de diseño
INK = "#0F172A"
MUTED = "#64748B"
GRID = "#F1F5F9"
UP = "#059669"      # esmeralda
DOWN = "#DC2626"
ACCENT = "#10B981"
BLUE = "#2563EB"
AMBER = "#D97706"


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
    st.markdown(
        f"<div class='jt-tape'><div class='jt-tape-inner'>{row}{row}</div></div>",
        unsafe_allow_html=True,
    )


def source_caption() -> None:
    if using_sample():
        st.caption("🧪 Mostrando datos sintéticos deterministas (sin conexión o modo demo).")


def score_gauge(score: int, title: str = "Score de inversión") -> go.Figure:
    color = UP if score >= 70 else ("#D97706" if score >= 45 else DOWN)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        title={"text": title, "font": {"size": 15, "color": MUTED}},
        number={"font": {"color": INK}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": MUTED},
            "bar": {"color": color},
            "bordercolor": "#E2E8F0",
            "steps": [
                {"range": [0, 45], "color": "#FEF2F2"},
                {"range": [45, 70], "color": "#FFFBEB"},
                {"range": [70, 100], "color": "#ECFDF5"},
            ],
        },
    ))
    fig.update_layout(height=230, margin=dict(l=25, r=25, t=45, b=5),
                      paper_bgcolor="rgba(0,0,0,0)", font={"color": INK})
    return fig


def candles_figure(df, title: str = "", sma50=None, sma200=None) -> go.Figure:
    fig = go.Figure(go.Candlestick(
        x=df.index, open=df.Open, high=df.High, low=df.Low, close=df.Close,
        name="OHLC", increasing_line_color=UP, decreasing_line_color=DOWN,
    ))
    if sma50 is not None:
        fig.add_scatter(x=df.index, y=sma50, name="SMA 50",
                        line=dict(color=BLUE, width=1.4))
    if sma200 is not None:
        fig.add_scatter(x=df.index, y=sma200, name="SMA 200",
                        line=dict(color=AMBER, width=1.4))
    fig.update_layout(
        title=title, height=420, xaxis_rangeslider_visible=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF",
        font={"color": INK, "family": "Inter"},
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", y=1.06),
        xaxis=dict(gridcolor=GRID), yaxis=dict(gridcolor=GRID),
    )
    return fig


def dark_fig(fig: go.Figure, height: int = 340) -> go.Figure:
    """Aplica el tema del sistema de diseño (nombre histórico; hoy es claro)."""
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF",
                      font={"color": INK, "family": "Inter"}, height=height,
                      margin=dict(l=10, r=10, t=40, b=10))
    fig.update_xaxes(gridcolor=GRID)
    fig.update_yaxes(gridcolor=GRID)
    return fig


def download_df(df, filename: str) -> None:
    """Botón de exportación CSV (UTF-8 con BOM para Excel)."""
    st.download_button("⬇️ Exportar CSV", df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=filename, mime="text/csv")
