"""Generador de reportes Markdown descargables (auditables: fuente + supuestos)."""
from __future__ import annotations

from datetime import date

from src import __version__
from src.config import DISCLAIMER
from src.utils.formatting import fmt_money, fmt_num, fmt_pct


def build_report(a: dict) -> str:
    """a = salida de scoring.composite.composite_score()."""
    v, r, t, fo = a["valuation"], a["risk"], a["technical"], a["forensic"]
    lines = [
        f"# 📈 AL-X — Reporte: {a['name']} ({a['ticker']})",
        f"*Generado: {date.today()} · Motor v{__version__} · Fuente: {a['data_source']}*",
        "",
        f"## Score de inversión: {a['total']}/100 {a['semaforo']}",
        f"Postura del modelo: **{a['thesis']['stance']}**",
        "",
        "| Pilar | Score | Peso |",
        "|---|---|---|",
    ]
    for k, s in a["pillars"].items():
        lines.append(f"| {k.capitalize()} | {s}/100 | {a['weights'][k]:.0%} |")
    lines += [
        "",
        "## Valoración (DCF)",
        f"- Valor justo estimado: **{fmt_money(v['fair_value'])}** "
        f"(precio actual {fmt_money(a['quote']['price'])}, upside {fmt_pct(v['upside'] * 100)})",
        f"- Supuestos: WACC {v['wacc']:.1%} · crecimiento {v['growth']:.1%} · "
        f"crecimiento implícito en el precio: "
        + (f"{v['implied_growth']:.1%}" if v["implied_growth"] is not None else "n/d"),
        f"- Monte Carlo (n=1500, seed={v['mc']['seed']}): P10 {fmt_money(v['mc']['p10'])} · "
        f"P50 {fmt_money(v['mc']['p50'])} · P90 {fmt_money(v['mc']['p90'])}",
        "",
        "## Riesgo",
        f"- Volatilidad anual {fmt_pct(r['ann_vol'] * 100, signed=False)} · "
        f"Sharpe {fmt_num(r['sharpe'])} · Máx. drawdown {fmt_pct(r['max_drawdown'] * 100)}",
        f"- VaR 95% diario {fmt_pct(r['var95_d'] * 100, signed=False)} · "
        f"CVaR {fmt_pct(r['cvar95_d'] * 100, signed=False)} · "
        f"VaR Cornish-Fisher {fmt_pct(r['var95_cf_d'] * 100, signed=False)}",
        "",
        "## Técnico",
        f"- Score {t['score']}/100 · RSI {t['rsi']:.0f} · ADX {t['adx']:.0f} · "
        f"Momentum 6m {fmt_pct(t['mom_6m'])}",
        "",
        "## Forense",
        f"- Altman Z: {fo['altman']['z']} (zona {fo['altman']['zone']}) · "
        f"Piotroski F: {fo['piotroski']['score']}/9 · "
        f"Beneish M: {fo['beneish']['m']} ({'⚠️ bandera' if fo['beneish']['flag'] else 'sin bandera'}) · "
        f"Accruals: {fo['sloan']['level']}",
        "",
        "## Tesis",
        f"- **Alcista:** {a['thesis']['bull']}",
        f"- **Base:** {a['thesis']['base']}",
        f"- **Bajista:** {a['thesis']['bear']}",
        "",
        "---",
        f"> {DISCLAIMER}",
    ]
    return "\n".join(lines)
