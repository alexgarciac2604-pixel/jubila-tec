"""Vista: análisis integral de una acción (score, valoración, técnico, forense…)."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.report.generator import build_report
from src.scoring.composite import composite_score
from src.technical import indicators as ind
from src.utils.formatting import fmt_money, fmt_num, fmt_pct
from src.valuation.dcf import dcf_value, monte_carlo_dcf, sensitivity_table
from src.views.components import candles_figure, dark_fig, score_gauge, source_caption


def render(ticker: str) -> None:
    with st.status(f"Analizando {ticker}…", expanded=False):
        try:
            a = composite_score(ticker)
        except Exception as e:  # noqa: BLE001
            st.error(f"No pude analizar `{ticker}`: {e}")
            return

    q = a["quote"]
    st.title(f"🔍 {a['name']} ({a['ticker']})")
    dq = a["data_quality"]
    st.markdown(
        f"<span class='jt-badge'>{a['sector']}</span> "
        f"<span class='jt-badge'>{a['data_source']}</span> "
        f"<span class='jt-badge'>{dq['badge']} ({dq['score']}/100)</span> "
        f"<span class='jt-badge'>{a['regime']['emoji']} {a['regime']['name']}</span>",
        unsafe_allow_html=True,
    )
    if dq["issues"]:
        st.warning("Calidad de datos: " + " · ".join(dq["issues"]))
    source_caption()

    c1, c2, c3 = st.columns([1.1, 1, 1.4])
    with c1:
        st.plotly_chart(score_gauge(a["total"]), use_container_width=True)
        st.markdown(f"### {a['semaforo']} Postura: **{a['thesis']['stance']}**")
    with c2:
        st.metric("Precio", f"${q['price']:.2f}", f"{q['change_pct']:+.2f}%")
        st.metric("Valor justo (DCF)", fmt_money(a["valuation"]["fair_value"]),
                  fmt_pct(a["valuation"]["upside"] * 100))
        st.metric("Desde máx. 52s", fmt_pct(q["from_52w_high_pct"]))
    with c3:
        st.markdown("**Desglose del score** (explicable)")
        for k, s in a["pillars"].items():
            st.progress(s / 100, text=f"{k.capitalize()} — {s}/100 (peso {a['weights'][k]:.0%})")

    if not st.session_state.get("pro_mode", True):
        th = a["thesis"]
        v = a["valuation"]
        st.markdown("### 🧭 En sencillo")
        st.markdown(
            f"El modelo le da a **{a['name']}** un **{a['total']}/100** {a['semaforo']} "
            f"(postura {th['stance']}). Cotiza a ${q['price']:.2f} y el análisis de flujos "
            f"la valúa en ${v['fair_value']:.2f} — es decir, "
            f"{'parece tener descuento' if v['upside'] > 0.05 else ('parece cara' if v['upside'] < -0.05 else 'parece en precio justo')}."
        )
        st.markdown(f"**Si sale bien:** {th['bull']}")
        st.markdown(f"**Si sale mal:** {th['bear']}")
        st.caption("Activa el Modo Pro en la barra lateral para ver las 8 pestañas de detalle.")
        return

    tabs = st.tabs(["📊 Fundamental", "💰 Valoración", "📈 Técnico",
                    "🕵️ Forense", "⚖️ Riesgo", "📰 Noticias", "🧭 Tesis", "📄 Reporte"])

    with tabs[0]:
        m = a["fundamental"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Margen bruto", fmt_pct((m["gross_margin"] or 0) * 100, signed=False))
        c2.metric("Margen neto", fmt_pct((m["net_margin"] or 0) * 100, signed=False))
        c3.metric("ROIC", fmt_pct((m["roic"] or 0) * 100, signed=False))
        c4.metric("Calidad", f"{m['quality_score']}/100")
        st.markdown("**DuPont (ROE descompuesto)**")
        d = m["dupont"]
        st.markdown(
            f"ROE {fmt_pct((d['roe'] or 0) * 100, signed=False)} = "
            f"margen {fmt_pct((d['margen_neto'] or 0) * 100, signed=False)} × "
            f"rotación {fmt_num(d['rotacion_activos'])} × "
            f"apalancamiento {fmt_num(d['apalancamiento'])}"
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("P/E", fmt_num(m["pe"]))
        c2.metric("EV/EBIT", fmt_num(m["ev_ebit"]))
        c3.metric("Conversión de caja", fmt_num(m["fcf_conversion"]))

    with tabs[1]:
        v = a["valuation"]
        f = a["fundamentals_raw"]
        st.markdown("Ajusta los supuestos — todo recalcula en vivo:")
        c1, c2, c3 = st.columns(3)
        wacc = c1.slider("WACC", 0.05, 0.20, float(round(v["wacc"], 3)), 0.005, format="%.3f")
        growth = c2.slider("Crecimiento FCF (5a)", -0.10, 0.35, float(v["growth"]), 0.01, format="%.2f")
        tg = c3.slider("Crecimiento terminal", 0.0, 0.04, 0.025, 0.005, format="%.3f")
        res = dcf_value(v["fcf"], growth, wacc, tg, net_debt=v["net_debt"],
                        shares=f.get("shares") or 1)
        up = res["per_share"] / q["price"] - 1 if q["price"] else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Valor por acción", fmt_money(res["per_share"]), fmt_pct(up * 100))
        c2.metric("% del valor en terminal", fmt_pct((res["terminal_pct"] or 0) * 100, signed=False))
        c3.metric("Crecimiento implícito en precio",
                  fmt_pct((v["implied_growth"] or 0) * 100) if v["implied_growth"] is not None else "n/d")
        st.markdown("**Sensibilidad WACC × crecimiento** (valor por acción)")
        st.dataframe(
            sensitivity_table(v["fcf"], wacc, growth, tg, net_debt=v["net_debt"],
                              shares=f.get("shares") or 1).style.format("{:.2f}"),
            use_container_width=True,
        )
        mc = monte_carlo_dcf(v["fcf"], growth, wacc, tg, net_debt=v["net_debt"],
                             shares=f.get("shares") or 1, n=2000)
        fig = go.Figure(go.Histogram(x=mc["values"], nbinsx=60, marker_color="#60a5fa"))
        fig.add_vline(x=q["price"], line_color="#f87171",
                      annotation_text="precio actual")
        fig.update_layout(title=f"Monte Carlo del valor (P10 {fmt_money(mc['p10'])} · "
                                f"P50 {fmt_money(mc['p50'])} · P90 {fmt_money(mc['p90'])})")
        st.plotly_chart(dark_fig(fig), use_container_width=True)

    with tabs[2]:
        from src.data.market_data import get_history
        h = get_history(ticker)
        t = a["technical"]
        st.plotly_chart(
            candles_figure(h.tail(252), sma50=ind.sma(h.Close, 50).tail(252),
                           sma200=ind.sma(h.Close, 200).tail(252)),
            use_container_width=True,
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("RSI 14", f"{t['rsi']:.0f}")
        c2.metric("ADX 14", f"{t['adx']:.0f}")
        c3.metric("Score técnico", f"{t['score']}/100")
        st.markdown("**Momentum multi-timeframe**")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("1 mes", fmt_pct(t["mom_1m"]))
        m2.metric("3 meses", fmt_pct(t["mom_3m"]))
        m3.metric("6 meses", fmt_pct(t["mom_6m"]))
        m4.metric("12 meses", fmt_pct(t["mom_12m"]))
        st.markdown("**Señales**")
        for name, reading, pts in t["signals"]:
            icon = "🟢" if pts > 0 else ("🔴" if pts < 0 else "⚪")
            st.markdown(f"{icon} **{name}**: {reading}")
        st.markdown("**Niveles Fibonacci (52 semanas)**")
        st.dataframe({k: [f"${v:.2f}"] for k, v in t["fib"].items()},
                     hide_index=True, use_container_width=True)

    with tabs[3]:
        fo = a["forensic"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Altman Z", fo["altman"]["z"], fo["altman"]["zone"], delta_color="off")
        c2.metric("Piotroski F", f"{fo['piotroski']['score']}/9")
        c3.metric("Beneish M", fo["beneish"]["m"],
                  "⚠️ bandera" if fo["beneish"]["flag"] else "sin bandera", delta_color="off")
        c4.metric("Accruals (Sloan)", fo["sloan"]["level"])
        st.caption(fo["beneish"]["note"])
        from src.data.edgar import insider_activity
        ins = insider_activity(a["ticker"])
        st.markdown("**Actividad de insiders (SEC Form 4)**")
        st.markdown(f"{ins['badge']} {ins['summary']}")
        st.caption(f"{ins['note']} Fuente: {ins['source']}.")
        st.markdown("**Checklist Piotroski**")
        for name, ok in fo["piotroski"]["checks"].items():
            st.markdown(f"{'✅' if ok else '❌'} {name}")

    with tabs[4]:
        r = a["risk"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Volatilidad anual", fmt_pct(r["ann_vol"] * 100, signed=False))
        c2.metric("Sharpe", fmt_num(r["sharpe"]))
        c3.metric("Máx. drawdown", fmt_pct(r["max_drawdown"] * 100))
        c1, c2, c3 = st.columns(3)
        c1.metric("VaR 95% (día)", fmt_pct(r["var95_d"] * 100, signed=False))
        c2.metric("CVaR 95% (día)", fmt_pct(r["cvar95_d"] * 100, signed=False))
        c3.metric("VaR Cornish-Fisher", fmt_pct(r["var95_cf_d"] * 100, signed=False))
        c1, c2, c3 = st.columns(3)
        c1.metric("Omega", fmt_num(r["omega"]))
        c2.metric("Ulcer Index", fmt_num(r["ulcer"]))
        c3.metric("Calmar", fmt_num(r["calmar"]))
        st.caption(
            f"Los retornos muestran skew {r['skew']:.2f} y curtosis {r['kurtosis']:.2f}; "
            "por eso reportamos VaR ajustado (Cornish-Fisher) además del histórico. "
            f"**En sencillo:** en un día malo de 1 entre 20, este activo pierde "
            f"≈{r['var95_d'] * 100:.1f}% o más."
        )
        from src.models.sizing import suggested_position
        sz = suggested_position(r["ann_return"], r["ann_vol"])
        st.markdown("**Tamaño de posición sugerido (½ Kelly)**")
        st.progress(min(sz["suggested"] / sz["cap"], 1.0),
                    text=f"{sz['suggested']:.0%} del portafolio")
        st.caption(sz["note"])

    with tabs[5]:
        s = a["sentiment"]
        st.markdown(f"**Sentimiento agregado:** {s['label']} ({s['avg']:+.2f}, {s['n']} notas)")
        for item in a["news"]:
            st.markdown(
                f"{item['label']} **{item['title']}**  \n"
                f"<span style='color:#64748b'>{item['publisher']} · {item['date']}</span>",
                unsafe_allow_html=True,
            )

    with tabs[6]:
        th = a["thesis"]
        st.markdown(f"### 🐂 Alcista\n{th['bull']}")
        st.markdown(f"### ⚖️ Base\n{th['base']}")
        st.markdown(f"### 🐻 Bajista\n{th['bear']}")
        hist = a.get("score_history", [])
        if len(hist) > 1:
            import pandas as pd
            st.markdown("**Evolución del score** (persistido en cada análisis)")
            hdf = pd.DataFrame(hist).set_index("date")
            st.line_chart(hdf["total"], height=180)

    with tabs[7]:
        md = build_report(a)
        st.download_button("⬇️ Descargar reporte (Markdown)", md,
                           file_name=f"jubilatec_{a['ticker']}.md")
        st.markdown(md)
