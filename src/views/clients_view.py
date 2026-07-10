"""Vista: 👥 Clientes — acceso por código/nombre + PIN, y administración.

Panel del cliente v0.15 — experiencia fintech: hero de saldo con variación
diaria, navegación tipo pills, evolución del portafolio con selector de
rango, benchmark vs S&P 500, franja de índices, movimientos con filtros y
solicitudes estructuradas. Paleta: marfil, carbón, oro, verde bosque.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from src.clients.manager import (add_deposit, approve_order, close_request,
                                 create_basket, create_client, create_order,
                                 create_request, delete_basket, delete_client,
                                 execute_order, export_all, get_capital,
                                 get_movements, get_note, get_orders,
                                 get_portfolio, get_requests, import_all,
                                 invest_basket, list_baskets, list_clients,
                                 paper_reset, paper_state, paper_trade,
                                 reject_order, set_note, set_portfolio,
                                 verify_client, watch_add, watch_list,
                                 watch_remove)
from src.clients.manager import (alert_text, badges, check_alerts,
                                 create_alert, delete_alert, delete_goal,
                                 get_goal, goal_eta, list_alerts, parse_alert,
                                 reto_semana, set_goal)
from src.config import DEFAULT_UNIVERSE, RISK_FREE, get_secret
from src.data.market_data import get_history, get_quote
from src.models.risk import monte_carlo_paths
from src.models.stress import portfolio_stress
from src.portfolio import optimizer as opt
from src.utils.formatting import fmt_money, fmt_num, fmt_pct
from src.report.briefing import client_briefing as _briefing_cliente
from src.views.components import dark_fig, render_ticker_tape

_METHODS = {
    "Máx. Sharpe": opt.max_sharpe,
    "HRP (Hierarchical Risk Parity)": opt.hrp,
    "Mínima varianza": opt.min_variance,
    "Risk parity": opt.risk_parity,
    "Pesos iguales": opt.equal_weight,
}

_PROFILE_SECTORS = {          # ideas del screener acordes al perfil
    "conservador": {"Consumo Básico", "Salud", "Financiero"},
    "moderado": None,          # todos los sectores
    "agresivo": {"Tecnología", "Comunicación", "Consumo Disc."},
}

_VERDE, _ROJO = "#0E6B45", "#B42318"
_BOSQUE, _ORO = "#14235C", "#C6A75E"   # _BOSQUE ahora es azul medianoche

_PANEL_CSS = """
<style>
/* hero de saldo: verde bosque profundo con filo de oro */
.alx-hero { background:linear-gradient(160deg,#1E2F72 0%,#14235C 55%,#0B1330 100%);
  border:1px solid rgba(214,183,110,.65); border-radius:22px; padding:26px 30px;
  color:#FAF7F0; box-shadow:0 14px 34px rgba(11,19,48,.25); }
.alx-hero-label { text-transform:uppercase; letter-spacing:.1em; font-size:.72rem;
  color:rgba(250,247,240,.75); }
.alx-hero-value { font-family:'Playfair Display',serif; font-size:2.9rem;
  font-weight:700; line-height:1.15; }
.alx-chip { display:inline-block; padding:3px 12px; border-radius:999px;
  font-size:.8rem; font-weight:600; background:rgba(250,247,240,.12);
  border:1px solid rgba(250,247,240,.25); }
.alx-chip.up { color:#7CE0B3; } .alx-chip.down { color:#F5A9A0; }
.alx-hero-row { display:flex; gap:14px; margin-top:18px; flex-wrap:wrap; }
.alx-mini { flex:1; min-width:132px; background:rgba(250,247,240,.08);
  border:1px solid rgba(214,183,110,.35); border-radius:14px; padding:10px 14px; }
.alx-mini span { display:block; font-size:.68rem; text-transform:uppercase;
  letter-spacing:.07em; color:rgba(250,247,240,.7); }
.alx-mini b { font-size:1.05rem; }
.alx-mini b.up { color:#7CE0B3; } .alx-mini b.down { color:#F5A9A0; }

/* navegación tipo pills (radio sin círculos) */
div[role="radiogroup"] { gap:8px; }
div[role="radiogroup"] label > div:first-child { display:none; }
div[role="radiogroup"] label {
  background:#FFFEFA; border:1px solid rgba(198,167,94,.5); border-radius:999px;
  padding:7px 16px; transition:all .18s ease; cursor:pointer; }
div[role="radiogroup"] label:hover { border-color:#C6A75E; }
div[role="radiogroup"] label:has(input:checked) {
  background:#14235C; border-color:rgba(214,183,110,.9);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.25), 0 4px 14px rgba(20,35,92,.28); }
div[role="radiogroup"] label:has(input:checked) p { color:#FAF7F0 !important; }

/* tarjeta-mensaje del asesor */
.alx-note { background:#FFFEFA; border:1px solid rgba(198,167,94,.5);
  border-left:3px solid #14235C; border-radius:14px; padding:14px 18px; }
.alx-note small { color:#78716C; }
</style>
"""

_NAV = ["💼 Resumen", "📊 Mi portafolio", "🛒 Invertir", "🎓 Práctica",
        "🧾 Movimientos", "💡 Ideas & noticias", "✉️ Solicitudes"]

_ROL_SECTOR = {
    "Consumo Básico": "darte estabilidad: la gente compra sus productos "
                      "en las buenas y en las malas",
    "Salud": "darte estabilidad: la salud no depende del ciclo económico",
    "Financiero": "generar ingresos sólidos ligados a la economía",
    "Tecnología": "darte crecimiento a largo plazo",
    "Comunicación": "darte crecimiento con marcas que usas a diario",
    "Consumo Disc.": "crecer cuando la economía va bien",
    "Energía": "protegerte cuando sube el petróleo y la inflación",
    "Industrial": "acompañar el crecimiento de la economía real",
}


def _semaforo(score) -> tuple[str, str]:
    if score >= 70:
        return "🟢", "sólida"
    if score >= 45:
        return "🟡", "aceptable"
    return "🔴", "débil"


def _veredicto(row: dict | None) -> tuple[str, str]:
    """(titular, razón) en lenguaje simple — el 'por qué' de la oportunidad."""
    if not row:
        return ("🟡 Sin análisis nocturno",
                "Esta empresa no está en nuestro screener de hoy. Puedes operar, "
                "pero te sugerimos consultarlo con tu asesor.")
    sc, dd = row.get("score", 50), row.get("desde_max_pct", 0) or 0
    if sc >= 70 and dd <= -15:
        return ("🟢 Posible oportunidad",
                f"empresa sólida que el mercado castigó: cotiza {abs(dd):.0f}% "
                "debajo de su máximo del año con fundamentos de calidad. "
                "Comprar calidad con descuento es la receta clásica.")
    if sc >= 70:
        return ("🟢 Empresa sólida",
                "buenos fundamentos y precio razonable según nuestro análisis "
                "de hoy. Apta para acumular con horizonte largo.")
    if sc >= 45:
        return ("🟡 Aceptable, sin prisa",
                "no destaca hoy: ni barata ni con gran impulso. Si te gusta, "
                "considera entrar por partes o esperar mejor punto.")
    return ("🔴 Cautela",
            "nuestro análisis de hoy no la favorece (fundamentos o precio "
            "flojos). No la recomendamos en este momento.")


def _por_que(ticker: str, sector: str, row: dict | None) -> str:
    """Explica una posición en lenguaje que cualquiera entiende."""
    rol = _ROL_SECTOR.get(sector, "diversificar tu portafolio")
    partes = [f"Está en tu portafolio para **{rol}**."]
    if row:
        emoji, calif = _semaforo(row.get("score", 50))
        partes.insert(0, f"Nuestro análisis la califica **{calif} "
                         f"({row.get('score', '—')}/100 {emoji})**.")
        if row.get("calidad", 0) >= 60:
            partes.append("Gana dinero de forma consistente (buena calidad).")
        if row.get("valoracion", 0) >= 60:
            partes.append("Su precio luce razonable frente a lo que gana.")
        elif row.get("valoracion", 0) < 40:
            partes.append("Su precio está algo exigente: por eso pesa lo que pesa.")
        if row.get("tecnico", 0) >= 60:
            partes.append("Además viene con buen impulso de mercado.")
    return " ".join(partes)


def _tint(v) -> str:
    try:
        return (f"color:{_VERDE};font-weight:600" if float(v) >= 0
                else f"color:{_ROJO};font-weight:600")
    except (TypeError, ValueError):
        return ""


def _paint(styler, subset):
    """Styler.map con fallback a applymap (pandas viejos)."""
    fn = getattr(styler, "map", None) or styler.applymap
    return fn(_tint, subset=subset)


def _series_portafolio(holdings: list[dict], capital: float,
                       efectivo: float) -> pd.Series | None:
    """Valor diario del portafolio (posiciones a precios de cierre + efectivo)."""
    try:
        partes = []
        for h in holdings:
            inv = h.get("invested") or capital * h["weight"]
            units = inv / h["price_at"] if h["price_at"] else 0.0
            partes.append(get_history(h["ticker"]).Close * units)
        if not partes:
            return None
        serie = pd.concat(partes, axis=1).dropna().sum(axis=1) + efectivo
        return serie if len(serie) > 2 else None
    except Exception:
        return None


# ============================================================ PANEL CLIENTE =
def _client_panel(client: dict) -> None:
    st.markdown(_PANEL_CSS, unsafe_allow_html=True)
    render_ticker_tape()

    c1, c2 = st.columns([5, 1])
    with c1:
        from src.utils.branding import logo_html
        st.markdown(logo_html(96, centrado=False, con_texto=False),
                    unsafe_allow_html=True)
        st.title(f"Bienvenido, {client['name']}")
        st.markdown(
            f"<span class='jt-badge'>Cliente {client['id']}</span> "
            f"<span class='jt-badge'>Perfil {client['perfil']}</span> "
            f"<span class='jt-badge'>{datetime.now():%d·%b·%Y}</span>",
            unsafe_allow_html=True,
        )
    with c2:
        if st.button("Cerrar sesión", use_container_width=True):
            st.session_state.pop("client_auth", None)
            st.rerun()

    if "alx_alertas_vistas" not in st.session_state:
        for _msg in check_alerts(client["id"]):
            st.toast(_msg, icon="🔔")
        st.session_state["alx_alertas_vistas"] = True

    capital = get_capital(client["id"]) or float(client.get("capital") or 0.0)
    holdings = get_portfolio(client["id"])

    # -- valuación ------------------------------------------------------------
    rows, total_now, total_in = [], 0.0, 0.0
    for h in holdings:
        q = get_quote(h["ticker"])
        invested = h.get("invested") or capital * h["weight"]
        units = invested / h["price_at"] if h["price_at"] else 0.0
        value = units * q["price"]
        rows.append({"Ticker": h["ticker"], "Peso": h["weight"],
                     "P. entrada": h["price_at"], "P. actual": q["price"],
                     "Invertido": invested, "Valor hoy": value,
                     "% Día": q.get("change_pct", 0.0),
                     "Rend. %": (value / invested - 1) * 100 if invested else 0.0})
        total_now += value
        total_in += invested
    df = pd.DataFrame(rows)
    efectivo = max(capital - total_in, 0.0)
    saldo = efectivo + total_now
    gp = total_now - total_in
    rend_total = (total_now / total_in - 1) * 100 if total_in else 0.0

    serie = _series_portafolio(holdings, capital, efectivo)
    dia_pct = ((serie.iloc[-1] / serie.iloc[-2] - 1) * 100
               if serie is not None and len(serie) > 1 else 0.0)

    # -- navegación pills -------------------------------------------------------
    if st.session_state.pop("alx_goto", None):
        st.session_state["alx_nav"] = "✉️ Solicitudes"
    nav = st.radio("Sección", _NAV, key="alx_nav", horizontal=True,
                   label_visibility="collapsed")

    # ------------------------------------------------------------- Resumen --
    if nav == _NAV[0]:
        arrow = "▲" if dia_pct >= 0 else "▼"
        cls = "up" if dia_pct >= 0 else "down"
        gcls = "up" if gp >= 0 else "down"
        st.markdown(
            f"""<div class='alx-hero'>
            <div class='alx-hero-label'>Saldo total</div>
            <div class='alx-hero-value'>{fmt_money(saldo)}</div>
            <span class='alx-chip {cls}'>{arrow} {dia_pct:+.2f}% hoy</span>
            <div class='alx-hero-row'>
              <div class='alx-mini'><span>Efectivo</span><b>{fmt_money(efectivo)}</b></div>
              <div class='alx-mini'><span>Inversiones</span><b>{fmt_money(total_now)}</b></div>
              <div class='alx-mini'><span>Ganancia / pérdida</span>
                <b class='{gcls}'>{fmt_money(gp)} ({rend_total:+.1f}%)</b></div>
            </div></div>""",
            unsafe_allow_html=True,
        )

        dia_dinero = (serie.iloc[-1] - serie.iloc[-2]
                      if serie is not None and len(serie) > 1 else 0.0)
        st.markdown(
            f"<div class='alx-note'>🌅 <b>¿Qué pasó con tu dinero?</b><br>"
            f"{_briefing_cliente(rows, dia_pct, dia_dinero)}</div>",
            unsafe_allow_html=True)

        b1, b2 = st.columns(2)
        if b1.button("💵 Solicitar depósito / retiro", use_container_width=True):
            st.session_state["alx_goto"] = True
            st.rerun()
        if b2.button("✉️ Hablar con tu asesor", use_container_width=True):
            st.session_state["alx_goto"] = True
            st.rerun()

        meta = get_goal(client["id"])
        if meta:
            avance = min(saldo / meta["monto_meta"], 1.0) if meta["monto_meta"] else 0
            st.markdown(f"**🎯 {meta['nombre']}** — {fmt_money(saldo)} de "
                        f"{fmt_money(meta['monto_meta'])} ({avance:.0%})")
            st.progress(avance)
            eta = goal_eta(saldo, meta["monto_meta"], meta["aporte_mensual"])
            if eta == 0:
                st.caption("🏆 ¡Meta alcanzada! Habla con tu asesor para "
                           "definir la siguiente.")
            elif eta:
                st.caption(f"Aportando {fmt_money(meta['aporte_mensual'])}/mes "
                           f"llegarías en ~{eta // 12} años y {eta % 12} meses "
                           "(supuesto 7% anual — estimación, no promesa).")
            with st.expander("Editar mi meta"):
                gn = st.text_input("Nombre", value=meta["nombre"], key="g_n")
                gm = st.number_input("Meta ($)", 1000.0, 1e9,
                                     float(meta["monto_meta"]), key="g_m")
                ga = st.number_input("Aporte mensual ($)", 0.0, 1e7,
                                     float(meta["aporte_mensual"]), key="g_a")
                cgg1, cgg2 = st.columns(2)
                if cgg1.button("Guardar meta"):
                    set_goal(client["id"], gn, gm, ga)
                    st.rerun()
                if cgg2.button("Borrar meta"):
                    delete_goal(client["id"])
                    st.rerun()
        else:
            with st.expander("🎯 Define tu meta (retiro, casa, libertad…)"):
                gn = st.text_input("¿Para qué inviertes?",
                                   placeholder="Mi retiro", key="g_n0")
                gm = st.number_input("¿Cuánto necesitas? ($)", 1000.0, 1e9,
                                     1_000_000.0, step=50_000.0, key="g_m0")
                ga = st.number_input("¿Cuánto puedes aportar al mes? ($)",
                                     0.0, 1e7, 2_000.0, step=500.0, key="g_a0")
                if st.button("Crear mi meta", type="primary") and gn.strip():
                    set_goal(client["id"], gn, gm, ga)
                    st.rerun()

        if serie is not None:
            st.markdown("**📈 Evolución de tu portafolio**")
            rango = st.radio("Rango", ["30 días", "90 días", "1 año"], index=1,
                             horizontal=True, label_visibility="collapsed")
            n = {"30 días": 30, "90 días": 90, "1 año": 252}[rango]
            s = serie.tail(n)
            up = s.iloc[-1] >= s.iloc[0]
            fig = px.area(s, labels={"value": "", "index": ""})
            fig.update_traces(line_color=_VERDE if up else _ROJO,
                              fillcolor=("rgba(14,107,69,.10)" if up
                                         else "rgba(180,35,24,.10)"))
            fig.update_layout(showlegend=False)
            st.plotly_chart(dark_fig(fig, 280), use_container_width=True)

        st.markdown("**🌐 El mercado hoy**")
        icols = st.columns(4)
        for col, t in zip(icols, ["SPY", "QQQ", "DIA", "GLD"]):
            try:
                q = get_quote(t)
                col.metric(q["name"], f"${q['price']:,.2f}",
                           f"{q['change_pct']:+.2f}%")
            except Exception:
                pass

        if not holdings:
            st.info("Tu asesor aún no te asigna un portafolio. Pide uno "
                    "personalizado en **✉️ Solicitudes**. 🙂")
        else:
            a, b = st.columns([1, 1.2])
            with a:
                st.markdown("**Composición**")
                fig = px.pie(df, names="Ticker", values="Valor hoy", hole=0.55,
                             color_discrete_sequence=["#14235C", _ORO, "#4A5FA8",
                                                      "#8C7845", "#1E2F72",
                                                      "#A99457"])
                st.plotly_chart(dark_fig(fig, 300), use_container_width=True)
            with b:
                best = df.loc[df["% Día"].idxmax()]
                st.markdown("**⭐ Tu posición del día**")
                st.markdown(
                    f"<div class='alx-note'><b>{best['Ticker']}</b> "
                    f"<span style='{_tint(best['% Día'])}'>"
                    f"{best['% Día']:+.2f}% hoy</span> · "
                    f"{fmt_money(best['Valor hoy'])} en tu portafolio</div>",
                    unsafe_allow_html=True)
                st.markdown("**Tus posiciones**")
                mini = df[["Ticker", "Valor hoy", "% Día", "Rend. %"]]
                st.dataframe(
                    _paint(mini.style.format({"Valor hoy": "${:,.0f}",
                                              "% Día": "{:+.2f}%",
                                              "Rend. %": "{:+.1f}%"}),
                           ["% Día", "Rend. %"]),
                    hide_index=True, use_container_width=True)
            nota = get_note(client["id"])
            if nota:
                st.markdown(
                    f"<div class='alx-note'>📝 <b>Nota de tu asesor</b> "
                    f"<small>· {nota['updated']}</small><br>{nota['nota']}</div>",
                    unsafe_allow_html=True)

    # ---------------------------------------------------------- Portafolio --
    elif nav == _NAV[1]:
        if not holdings:
            st.info("Sin portafolio asignado todavía.")
        else:
            st.caption(f"Asignado el {holdings[0]['assigned']} · precios de "
                       "entrada congelados ese día: tu rendimiento es real.")
            st.dataframe(
                _paint(df.drop(columns=["% Día"]).style.format(
                    {"Peso": "{:.0%}", "P. entrada": "${:.2f}",
                     "P. actual": "${:.2f}", "Invertido": "${:,.0f}",
                     "Valor hoy": "${:,.0f}", "Rend. %": "{:+.1f}%"}),
                    ["Rend. %"]),
                hide_index=True, use_container_width=True)

            with st.expander("💬 ¿Por qué tengo estas empresas?"):
                from src.screener.engine import load_screener as _ls
                _scr = _ls()
                _map = ({r["ticker"]: r for r in _scr["rows"]}
                        if _scr and _scr.get("rows") else {})
                from src.config import SECTOR_OF
                for h in holdings:
                    t = h["ticker"]
                    sec = (_map.get(t) or {}).get("sector") or SECTOR_OF.get(t, "")
                    st.markdown(f"**{t}** — {_por_que(t, sec, _map.get(t))}")

            if serie is not None:
                try:
                    spy = get_history("SPY").Close
                    comp = pd.concat([serie, spy], axis=1).dropna().tail(252)
                    comp.columns = ["Tu portafolio", "S&P 500 (SPY)"]
                    comp = comp / comp.iloc[0] * 100
                    st.markdown("**⚖️ Tu portafolio vs. S&P 500** (base 100, 1 año)")
                    fig = px.line(comp, labels={"value": "", "index": ""},
                                  color_discrete_map={"Tu portafolio": _BOSQUE,
                                                      "S&P 500 (SPY)": _ORO})
                    st.plotly_chart(dark_fig(fig, 300), use_container_width=True)
                except Exception:
                    pass

            tickers = [h["ticker"] for h in holdings]
            w_now = ((df["Valor hoy"] / total_now).tolist() if total_now
                     else df["Peso"].tolist())
            try:
                prices = pd.DataFrame(
                    {t: get_history(t).Close for t in tickers}).dropna()
                stats = opt.portfolio_stats(pd.Series(w_now).values,
                                            opt.returns_matrix(prices), RISK_FREE)
                c1, c2, c3 = st.columns(3)
                c1.metric("Volatilidad anual",
                          fmt_pct(stats["ann_vol"] * 100, signed=False),
                          help="Cuánto se mueve tu portafolio en un año típico. "
                               "Menos = más estable.")
                c2.metric("Sharpe", fmt_num(stats["sharpe"]),
                          help="Rendimiento por unidad de riesgo. Más de 1 es bueno.")
                c3.metric("Máx. drawdown histórico",
                          fmt_pct(stats["max_drawdown"] * 100),
                          help="La peor caída desde un máximo. Lo que habrías "
                               "aguantado en el peor momento.")
                with st.expander("🧒 ¿Qué significan estos tres números?"):
                    from src.report.plain import explica_riesgo
                    st.markdown(explica_riesgo(stats["ann_vol"] * 100,
                                               stats["sharpe"],
                                               stats["max_drawdown"] * 100))
                mc = monte_carlo_paths(stats["ann_return"], stats["ann_vol"],
                                       years=5, n_paths=800, start=total_now)
                st.markdown(
                    f"**🔮 Proyección a 5 años:** escenario del medio "
                    f"{fmt_money(mc['p50'])} · malo (P10) {fmt_money(mc['p10'])} "
                    f"· bueno (P90) {fmt_money(mc['p90'])}.")
                with st.expander("🧒 ¿Cómo adivinamos el futuro? (no lo "
                                 "adivinamos)"):
                    from src.report.plain import explica_mc
                    st.markdown(explica_mc(mc["p10"], mc["p50"], mc["p90"],
                                           mc["prob_loss"]))
                st.markdown("**🧨 ¿Y si el mercado se estresa?**")
                st.dataframe(portfolio_stress(tickers, w_now), hide_index=True,
                             use_container_width=True)
            except Exception:
                st.caption("Métricas de riesgo no disponibles en este momento.")

            from datetime import date as _date
            reporte = "\n".join(
                [f"# ◆ AL-X — Estado de cuenta: {client['name']} ({client['id']})",
                 f"*Generado: {_date.today()} · Perfil: {client['perfil']} · "
                 f"Asignado: {holdings[0]['assigned']}*", "",
                 f"**Saldo total:** {fmt_money(saldo)}  ",
                 f"**Efectivo:** {fmt_money(efectivo)}  ",
                 f"**Inversiones:** {fmt_money(total_now)} ({rend_total:+.1f}%)", "",
                 "| Activo | Peso | P. entrada | P. actual | Valor hoy | Rend. |",
                 "|---|---|---|---|---|---|"] +
                [f"| {r['Ticker']} | {r['Peso']:.0%} | ${r['P. entrada']:.2f} | "
                 f"${r['P. actual']:.2f} | ${r['Valor hoy']:,.0f} | "
                 f"{r['Rend. %']:+.1f}% |" for r in rows] +
                ["", "> Reporte informativo y educativo con datos públicos; no "
                 "constituye asesoría de inversión ni garantiza rendimientos."]
            )
            st.download_button("📄 Descargar mi estado de cuenta", reporte,
                               file_name=f"alx_{client['id']}_{_date.today()}.md")

            with st.expander("📖 Tu mes contado en palabras"):
                try:
                    from src.report.briefing import monthly_story
                    s21 = serie.tail(22) if serie is not None else None
                    pct_mes = ((s21.iloc[-1] / s21.iloc[0] - 1) * 100
                               if s21 is not None and len(s21) > 2 else 0.0)
                    delta_mes = (s21.iloc[-1] - s21.iloc[0]
                                 if s21 is not None and len(s21) > 2 else 0.0)
                    try:
                        _spy = get_history("SPY").Close.tail(22)
                        spy_pct = (_spy.iloc[-1] / _spy.iloc[0] - 1) * 100
                    except Exception:
                        spy_pct = None
                    cambios = {}
                    for h in holdings:
                        try:
                            c = get_history(h["ticker"]).Close.tail(22)
                            cambios[h["ticker"]] = (c.iloc[-1] / c.iloc[0] - 1) * 100
                        except Exception:
                            pass
                    from datetime import date as _dd, timedelta as _td
                    corte = str(_dd.today() - _td(days=30))
                    movs_mes = [m for m in get_movements(client["id"])
                                if m["date"] >= corte]
                    deps = sum(m["monto"] for m in movs_mes
                               if m["tipo"].startswith("Depósito"))
                    ncom = len([m for m in movs_mes if m["tipo"] == "Compra"])
                    nven = len([m for m in movs_mes if m["tipo"] == "Venta"])
                    caida = (s21 is not None and len(s21) > 2 and
                             (s21 / s21.cummax() - 1).min() < -0.05)
                    historia = monthly_story(
                        client["name"].split()[0], saldo, delta_mes, pct_mes,
                        spy_pct, cambios, deps, ncom, nven,
                        get_goal(client["id"]), bool(caida))
                    st.markdown(historia)
                    from datetime import date as _d3
                    st.download_button("⬇️ Guardar mi historia del mes",
                                       historia,
                                       file_name=f"alx_mes_{client['id']}_"
                                                 f"{_d3.today()}.md")
                except Exception:
                    st.caption("La historia del mes estará lista cuando haya "
                               "suficientes datos.")

    # ------------------------------------------------------------- Invertir --
    elif nav == _NAV[2]:
        st.markdown("**🛒 Invertir**")
        st.caption("Ejecutas al precio actual del mercado y queda registrado al "
                   "instante. Los depósitos y retiros de dinero real se "
                   "coordinan con tu asesor.")
        canastas = list_baskets()
        if canastas:
            st.markdown("**🧺 Canastas de tu asesor** — portafolios armados "
                        "con una tesis, listos para invertir con un clic")
            for b in canastas:
                with st.container(border=True):
                    comp = " · ".join(f"{t} {w:.0%}" for t, w in
                                      zip(b["tickers"], b["weights"]))
                    st.markdown(f"**{b['name']}**  \n{b['tesis']}  \n"
                                f"<small style='color:#78716C'>{comp}</small>",
                                unsafe_allow_html=True)
                    cc1, cc2 = st.columns([1, 1])
                    m_b = cc1.number_input("Monto ($)", 100.0, 1e8, 5_000.0,
                                           step=500.0, key=f"bk_m_{b['id']}",
                                           label_visibility="collapsed")
                    if cc2.button(f"⚡ Invertir en esta canasta",
                                  key=f"bk_{b['id']}", type="primary"):
                        ok, msg = invest_basket(client["id"], b["id"], m_b)
                        (st.success if ok else st.error)(msg)
                        if ok:
                            st.rerun()
            st.divider()

        st.markdown("**O elige una empresa individual:**")
        from src.screener.engine import load_screener
        scr = load_screener()
        scr_map = ({r["ticker"]: r for r in scr["rows"]}
                   if scr and scr.get("rows") else {})
        universo = sorted(set(DEFAULT_UNIVERSE)
                          | {h["ticker"] for h in holdings})
        c1, c2 = st.columns([1.6, 1])
        tk = c1.selectbox("Empresa", universo, key="inv_tk")
        side = c2.radio("Operación", ["compra", "venta"], horizontal=True,
                        format_func=str.capitalize, key="inv_side")

        # --- análisis AL-X en vivo de la empresa elegida -------------------
        row = scr_map.get(tk)
        titular, razon = _veredicto(row)
        try:
            q = get_quote(tk)
            precio_txt = (f"${q['price']:,.2f} "
                          f"<span style='{_tint(q['change_pct'])}'>"
                          f"{q['change_pct']:+.2f}% hoy</span> · "
                          f"{q['from_52w_high_pct']:+.0f}% desde su máximo de 52s")
        except Exception:
            precio_txt = ""
        pilares = ""
        if row:
            pilares = (f"<br><small>Calidad {row.get('calidad', '—')} · "
                       f"Técnico {row.get('tecnico', '—')} · "
                       f"Valoración {row.get('valoracion', '—')} → "
                       f"<b>Score {row.get('score', '—')}/100</b></small>")
        try:
            from src.models.regime import market_regime
            reg = market_regime()
            mercado = (f"<br><small>{reg['emoji']} Contexto: mercado en "
                       f"<b>{reg['name']}</b> (prob. de turbulencia "
                       f"{reg['p_turbulent']:.0%}).</small>")
        except Exception:
            mercado = ""
        st.markdown(
            f"<div class='alx-note'><b>{tk}</b> — {precio_txt}<br>"
            f"<b>{titular}</b>: {razon}{pilares}{mercado}</div>",
            unsafe_allow_html=True)

        with st.expander("🔮 Caja de Cristal — que cualquiera lo entienda, "
                         "que cualquiera lo audite"):
            from src.report.plain import explica_reverse_dcf, explica_score
            if row:
                st.markdown(explica_score(tk, row,
                                          scr.get("date", "") if scr else ""))
            try:
                from src.data.market_data import get_fundamentals, source_of
                fnd = get_fundamentals(tk)
                mc = fnd.get("market_cap") or 0
                fcf = fnd.get("fcf") or 0
                nd = (fnd.get("total_debt") or 0) - (fnd.get("cash") or 0)
                if mc > 0 and fcf > 0:
                    from src.valuation.dcf import reverse_dcf
                    g = reverse_dcf(mc, fcf, 0.09, net_debt=nd)
                    if g is not None:
                        st.markdown(explica_reverse_dcf(tk, g))
                st.caption(f"Fuente de precios: {source_of(tk)} · "
                           "Fundamentales: SEC EDGAR/yfinance · Modelos "
                           "documentados en 📚 Modelos del Studio.")
            except Exception:
                st.caption("Reverse DCF no disponible para esta empresa "
                           "en este momento.")

        monto = st.number_input("Monto ($)", 100.0, 1e8, 5_000.0, step=500.0,
                                key="inv_monto")
        adelante = True
        if row and row.get("score", 50) < 45 and side == "compra":
            adelante = st.checkbox("Entiendo que el análisis de hoy sugiere "
                                   "cautela y quiero comprar de todos modos.")
        if side == "venta":
            hpos = next((h for h in holdings if h["ticker"] == tk), None)
            if hpos:
                try:
                    _pxv = get_quote(tk)["price"]
                    _inv = hpos.get("invested") or capital * hpos["weight"]
                    _units = _inv / hpos["price_at"] if hpos["price_at"] else 0
                    _val = _units * _pxv
                    _rend = (_val / _inv - 1) * 100 if _inv else 0
                    if _rend < -2:
                        _m = min(monto if "inv_monto" in st.session_state
                                 else 5_000.0, _val)
                        _cristaliza = _m - (_m / _pxv) * hpos["price_at"]
                        turb = ""
                        try:
                            from src.models.regime import market_regime
                            _reg = market_regime()
                            if _reg.get("p_turbulent", 0) > 0.5:
                                turb = (" Además el mercado está en plena "
                                        "turbulencia: vender en pánico durante "
                                        "la tormenta es, históricamente, la "
                                        "forma #1 de perder dinero.")
                        except Exception:
                            pass
                        st.markdown(
                            f"<div class='alx-note' style='border-left-color:"
                            f"#B42318'>🧘 <b>Un momento — respira.</b><br>"
                            f"{tk} va {_rend:+.1f}% desde tu compra. Vender "
                            f"ahora <b>convierte en definitiva una pérdida de "
                            f"~${abs(_cristaliza):,.0f}</b> que hoy solo está "
                            f"en papel.{turb} Los mercados se han recuperado "
                            f"de cada crisis de su historia — la pregunta no "
                            f"es si duele hoy, sino si la empresa sigue "
                            f"siendo buena.</div>",
                            unsafe_allow_html=True)
                        adelante = st.checkbox(
                            "Lo pensé con calma (no es pánico) y decido vender.")
                        if st.button("✉️ Mejor lo hablo con mi asesor"):
                            st.session_state["alx_goto"] = True
                            st.rerun()
                except Exception:
                    pass
        if st.button(f"⚡ Ejecutar {side} ahora", type="primary",
                     disabled=not adelante):
            nota = (f"Score AL-X {row.get('score', '—')}/100 · {titular}"
                    if row else "sin análisis nocturno")
            ok, msg = execute_order(client["id"], side, tk, monto, nota)
            (st.success if ok else st.error)(msg)
            if ok:
                st.rerun()
        st.caption(f"💵 Efectivo disponible: {fmt_money(efectivo)}. "
                   "⚖️ Registro informativo: la app no custodia dinero ni valores.")

        ords = get_orders(client["id"])
        if ords:
            st.markdown("**Tus operaciones recientes**")
            iconos = {"pendiente": "🟡", "aprobada": "✅",
                      "ejecutada": "⚡", "rechazada": "🔴"}
            for o in ords[:10]:
                st.markdown(
                    f"{iconos.get(o['estado'], '·')} *{o['date']}* — "
                    f"{o['side'].capitalize()} **{o['ticker']}** "
                    f"${o['monto']:,.0f} · {o['estado']}")

    # ------------------------------------------------------------- Práctica --
    elif nav == _NAV[3]:
        st.markdown("**🎓 Cartera de práctica — aprende sin arriesgar**")
        st.caption("Te regalamos **$100,000 ficticios** para practicar con "
                   "precios reales. Aquí las operaciones son instantáneas y "
                   "equivocarse no cuesta nada.")
        ps = paper_state(client["id"])
        prows, pval = [], 0.0
        for pp in ps["positions"]:
            pxn = get_quote(pp["ticker"])["price"]
            val = pp["units"] * pxn
            cost = pp["units"] * pp["price_at"]
            prows.append({"Ticker": pp["ticker"], "Unidades": pp["units"],
                          "P. compra": pp["price_at"], "P. actual": pxn,
                          "Valor": val,
                          "Rend. %": (val / cost - 1) * 100 if cost else 0.0})
            pval += val
        ptotal = ps["cash"] + pval
        ppl = ptotal - 100_000.0
        c1, c2, c3 = st.columns(3)
        c1.metric("Valor total (ficticio)", fmt_money(ptotal),
                  fmt_pct(ppl / 100_000.0 * 100))
        c2.metric("Efectivo virtual", fmt_money(ps["cash"]))
        c3.metric("Invertido", fmt_money(pval))
        with st.form("paper"):
            c1, c2, c3 = st.columns([1, 1.4, 1])
            pside = c1.radio("Operación", ["compra", "venta"],
                             format_func=str.capitalize, horizontal=True,
                             key="paper_side")
            ptk = c2.selectbox("Empresa", sorted(DEFAULT_UNIVERSE),
                               key="paper_tk")
            pmonto = c3.number_input("Monto ($)", 100.0, 1e6, 5_000.0,
                                     step=500.0, key="paper_monto")
            if st.form_submit_button("Ejecutar (práctica)", type="primary"):
                ok, msg = paper_trade(client["id"], pside, ptk, pmonto)
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()
        if prows:
            pdf_ = pd.DataFrame(prows)
            st.dataframe(
                _paint(pdf_.style.format(
                    {"Unidades": "{:.3f}", "P. compra": "${:.2f}",
                     "P. actual": "${:.2f}", "Valor": "${:,.0f}",
                     "Rend. %": "{:+.1f}%"}), ["Rend. %"]),
                hide_index=True, use_container_width=True)
        if st.button("🔄 Reiniciar mi cartera de práctica"):
            paper_reset(client["id"])
            st.rerun()
        st.markdown("**🏅 Tus insignias** — se ganan aprendiendo, no operando")
        bds = badges(client["id"])
        bcols = st.columns(4)
        for i, bd in enumerate(bds):
            estilo = ("" if bd["ganada"]
                      else "opacity:.38;filter:grayscale(1);")
            bcols[i % 4].markdown(
                f"<div class='alx-note' style='text-align:center;{estilo}'>"
                f"<div style='font-size:1.6rem'>{bd['emoji']}</div>"
                f"<b>{bd['nombre']}</b><br><small>{bd['desc']}</small></div>",
                unsafe_allow_html=True)
        st.markdown(f"**📌 Reto de la semana:** {reto_semana()}")
        st.caption("💡 Consejo: antes de invertir de verdad, practica aquí una "
                   "estrategia durante unas semanas y compárala con tu "
                   "portafolio real.")

    # ---------------------------------------------------------- Movimientos --
    elif nav == _NAV[4]:
        movs = get_movements(client["id"])
        if not movs:
            st.info("Aún no hay movimientos registrados.")
        else:
            mdf = pd.DataFrame(movs).rename(columns={
                "date": "Fecha", "tipo": "Tipo", "monto": "Monto",
                "nota": "Detalle"})[["Fecha", "Tipo", "Monto", "Detalle"]]
            f1, f2 = st.columns([2, 1])
            tipos = f1.multiselect("Tipo", sorted(mdf["Tipo"].unique()),
                                   placeholder="Todos los tipos")
            desde = f2.date_input("Desde", value=None, format="YYYY-MM-DD")
            if tipos:
                mdf = mdf[mdf["Tipo"].isin(tipos)]
            if desde:
                mdf = mdf[mdf["Fecha"] >= str(desde)]
            st.dataframe(
                _paint(mdf.style.format({"Monto": "${:,.2f}"}), ["Monto"]),
                hide_index=True, use_container_width=True)
            st.caption(f"Registro oficial de tu asesor — no editable · "
                       f"Actualizado {datetime.now():%H:%M}")

    # ------------------------------------------------------ Ideas & noticias --
    elif nav == _NAV[5]:
        st.markdown("**⭐ Empresas que sigo**")
        wl = watch_list(client["id"])
        cw1, cw2 = st.columns([2, 1])
        nuevo_w = cw1.selectbox("Agregar empresa a mi lista",
                                [t for t in sorted(DEFAULT_UNIVERSE)
                                 if t not in wl], key="watch_new")
        if cw2.button("⭐ Seguir"):
            watch_add(client["id"], nuevo_w)
            st.rerun()
        if wl:
            from src.screener.engine import load_screener as _lsw
            _sw = _lsw()
            _mw = ({r["ticker"]: r for r in _sw["rows"]}
                   if _sw and _sw.get("rows") else {})
            wrows = []
            for t in wl:
                try:
                    qw = get_quote(t)
                    rw = _mw.get(t)
                    wrows.append({"Ticker": t, "Precio": qw["price"],
                                  "% Día": qw["change_pct"],
                                  "Score": (rw or {}).get("score", "—"),
                                  "Veredicto": _veredicto(rw)[0]})
                except Exception:
                    pass
            if wrows:
                st.dataframe(
                    _paint(pd.DataFrame(wrows).style.format(
                        {"Precio": "${:,.2f}", "% Día": "{:+.2f}%"}),
                        ["% Día"]),
                    hide_index=True, use_container_width=True)
            quitar = st.selectbox("Dejar de seguir", ["—"] + wl, key="watch_rm")
            if quitar != "—":
                watch_remove(client["id"], quitar)
                st.rerun()
        st.divider()
        st.markdown("**🔔 Mis alertas** — escríbelas como se las dirías a "
                    "un amigo")
        frase = st.text_input("Alerta", placeholder="Avísame si Apple cae 5%",
                              key="alx_alert_txt", label_visibility="collapsed")
        if frase:
            intento = parse_alert(frase)
            if intento:
                st.caption(f"Entendí: avisarte **{alert_text(intento)}** ✓")
                if st.button("🔔 Crear alerta", type="primary"):
                    create_alert(client["id"], intento["ticker"],
                                 intento["cond"], intento["umbral"])
                    st.success("Alerta creada. Te avisaré al entrar al portal.")
                    st.rerun()
            else:
                st.caption("No entendí 🤔 — prueba: «avísame si Tesla cae 7%» "
                           "o «avísame si Apple llega a $280».")
        activas = list_alerts(client["id"])
        for a in activas[:10]:
            ic = "🟢" if a["estado"] == "activa" else "🔔"
            ca1, ca2 = st.columns([5, 1])
            ca1.caption(f"{ic} Avisarme {alert_text(a)}"
                        + (f" — se cumplió el {a['disparo']}"
                           if a["estado"] == "disparada" else ""))
            if ca2.button("🗑️", key=f"dal_{a['id']}"):
                delete_alert(a["id"])
                st.rerun()
        st.divider()

        nota = get_note(client["id"])
        if nota:
            st.markdown(
                f"<div class='alx-note'>📝 <b>Recomendación de tu asesor</b> "
                f"<small>· {nota['updated']}</small><br>{nota['nota']}</div>",
                unsafe_allow_html=True)

        from src.screener.engine import load_screener
        scr = load_screener()
        if scr and scr.get("rows"):
            sdf = pd.DataFrame(scr["rows"])
            allowed = _PROFILE_SECTORS.get(client["perfil"])
            if allowed:
                sdf = sdf[sdf["sector"].isin(allowed)]
            top = sdf.head(5)[["ticker", "name", "sector", "price", "score"]]
            top.columns = ["Ticker", "Empresa", "Sector", "Precio", "Score"]
            st.markdown(f"**💡 Ideas del mercado para tu perfil "
                        f"({client['perfil']})** · actualizado {scr['date']}")
            st.dataframe(top.style.format({"Precio": "${:,.2f}"}),
                         hide_index=True, use_container_width=True)
            st.caption("Screening cuantitativo educativo (calidad + técnico + "
                       "valoración). No es una orden de compra: coméntalo con "
                       "tu asesor.")

        with st.expander("📚 Diccionario del inversionista — sin palabras "
                         "raras"):
            from src.report.plain import GLOSARIO
            for term, deff in GLOSARIO.items():
                st.markdown(f"**{term}** — {deff}")

        if holdings:
            st.markdown("**📰 Noticias de tus empresas**")
            from src.news.news_feed import get_news
            shown = 0
            for t in [h["ticker"] for h in holdings][:4]:
                for it in get_news(t, n=3)[:2]:
                    st.markdown(
                        f"{it.get('label', '')} **[{t}]** {it['title']}  \n"
                        f"<span style='color:#78716C;font-size:.85rem'>"
                        f"{it.get('publisher', '')} · {it.get('date', '')}</span>",
                        unsafe_allow_html=True)
                    shown += 1
            if not shown:
                st.caption("Sin noticias recientes de tus posiciones.")

    # ----------------------------------------------------------- Solicitudes --
    else:
        st.markdown("**✉️ Pide un portafolio personalizado, un depósito/retiro "
                    "o haz una consulta**")
        with st.form("solicitud"):
            c1, c2 = st.columns(2)
            objetivo = c1.selectbox("Objetivo", [
                "Portafolio personalizado", "Depósito", "Retiro",
                "Más crecimiento", "Ingresos por dividendos",
                "Preservar capital", "Consulta general"])
            horizonte = c2.selectbox("Horizonte", [
                "No aplica", "Menos de 1 año", "1-3 años", "3-5 años",
                "5-10 años", "Más de 10 años"])
            c1, c2 = st.columns(2)
            riesgo = c1.select_slider("Nivel de riesgo deseado",
                                      ["Muy bajo", "Bajo", "Medio", "Alto",
                                       "Muy alto"], value="Medio")
            monto = c2.number_input("Monto aproximado ($, opcional)",
                                    0.0, 1e9, 0.0, step=5_000.0)
            msg = st.text_area("Cuéntale más a tu asesor", max_chars=600,
                               height=100, placeholder="Ej. Sin tabacaleras; "
                               "me interesan dividendos y algo de tecnología.")
            if st.form_submit_button("Enviar solicitud", type="primary"):
                detalle = (f"[{objetivo}] Horizonte: {horizonte} · "
                           f"Riesgo: {riesgo}"
                           + (f" · Monto: ${monto:,.0f}" if monto else "")
                           + (f". {msg.strip()}" if msg.strip() else ""))
                create_request(client["id"], detalle)
                st.success("✅ Enviada — tu asesor la verá en su bandeja del "
                           "Studio y te responderá pronto.")
        prev = get_requests(client["id"])
        if prev:
            st.markdown("**Tus solicitudes**")
            estados = {"pendiente": "🟡 en revisión", "atendida": "✅ respondida"}
            for r in prev[:8]:
                st.markdown(f"*{r['date']}* — {r['mensaje']}  \n"
                            f"<span style='color:#78716C;font-size:.85rem'>"
                            f"{estados.get(r['estado'], r['estado'])}</span>",
                            unsafe_allow_html=True)
        contacto = get_secret("ALX_CONTACTO")
        if contacto:
            st.caption(f"¿Prefieres hablar directo? Contacta a {contacto}.")

    st.info("⚖️ Reporte informativo y educativo con datos públicos; no constituye "
            "asesoría de inversión ni garantiza rendimientos.")


# ============================================================== ADMIN =======
def _admin_panel() -> None:
    st.subheader("🛠️ Administración de clientes")
    st.caption("⚖️ Herramienta de registro y reporte. El uso comercial con clientes "
               "puede requerir registro como asesor (CNBV/SEC).")
    from src.data.dbx import backend, ping
    if backend() == "turso":
        ok, msg = ping()
        if ok:
            st.caption("☁️ Turso conectado — base compartida con el Portal.")
        else:
            st.error(f"☁️ Turso configurado pero SIN conexión: {msg}\n\n"
                     "Revisa que TURSO_DATABASE_URL empiece con libsql:// y que el "
                     "token sea el de ESTA base (crea uno nuevo si hace falta).")

    todas = get_orders()
    ord_pend = [o for o in todas if o["estado"] == "pendiente"]
    with st.expander(f"🛒 Operaciones de clientes ({len(ord_pend)} por aprobar)",
                     expanded=bool(ord_pend)):
        ejecutadas = [o for o in todas if o["estado"] == "ejecutada"][:8]
        if ejecutadas:
            st.markdown("**⚡ Ejecutadas por los clientes (auditoría)**")
            for o in ejecutadas:
                st.markdown(f"⚡ **{o['client_id']}** · *{o['date']}* — "
                            f"{o['side'].capitalize()} **{o['ticker']}** "
                            f"${o['monto']:,.0f} · {o['nota']}")
            st.divider()
        if not ord_pend:
            st.caption("Sin órdenes pendientes de aprobación.")
        for o in ord_pend:
            c1, c2, c3 = st.columns([4, 1, 1])
            c1.markdown(f"**{o['client_id']}** · *{o['date']}* — "
                        f"{o['side'].capitalize()} **{o['ticker']}** "
                        f"${o['monto']:,.0f} · {o['nota']}")
            if c2.button("✅ Aprobar", key=f"ok_{o['id']}"):
                ok, msg = approve_order(o["id"])
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()
            if c3.button("🔴 Rechazar", key=f"no_{o['id']}"):
                reject_order(o["id"])
                st.rerun()

    pendientes = [r for r in get_requests() if r["estado"] == "pendiente"]
    with st.expander(f"✉️ Solicitudes de clientes ({len(pendientes)} pendientes)",
                     expanded=bool(pendientes)):
        if not pendientes:
            st.caption("Bandeja limpia. 🎉")
        for r in pendientes:
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**{r['client_id']}** · *{r['date']}* — {r['mensaje']}")
            if c2.button("✅ Atendida", key=f"req_{r['id']}"):
                close_request(r["id"])
                st.rerun()

    with st.expander("➕ Nuevo cliente"):
        c1, c2 = st.columns(2)
        cid = c1.text_input("Número de cliente (único)", placeholder="C-001")
        name = c2.text_input("Nombre completo")
        c1, c2, c3 = st.columns(3)
        pin = c1.text_input("PIN (4-6 dígitos)", type="password")
        perfil = c2.selectbox("Perfil", ["conservador", "moderado", "agresivo"])
        capital = c3.number_input("Capital ($)", 0.0, 1e9, 100_000.0, step=10_000.0)
        if st.button("Crear cliente", type="primary"):
            if not (cid and name and len(pin) >= 4):
                st.error("Completa número, nombre y un PIN de al menos 4 dígitos.")
            else:
                try:
                    if create_client(cid, name, pin, perfil, capital):
                        st.success(f"Cliente {name} ({cid.upper()}) creado.")
                    else:
                        st.error("Ese número de cliente ya existe.")
                except Exception as e:
                    st.error(f"⚠️ La base de datos falló (no es un duplicado): {e}")

    clientes = list_clients()
    if not clientes:
        st.info("Sin clientes todavía. Crea el primero arriba.")
        return

    st.markdown(f"**Clientes ({len(clientes)})**")
    st.dataframe(pd.DataFrame(clientes).rename(columns={
        "id": "Número", "name": "Nombre", "perfil": "Perfil",
        "capital": "Capital", "created": "Alta"}),
        hide_index=True, use_container_width=True)

    st.markdown("**📐 Armar y asignar portafolio**")
    sel = st.selectbox("Cliente", [f"{c['id']} — {c['name']}" for c in clientes])
    cid_sel = sel.split(" — ")[0]
    cli = next(c for c in clientes if c["id"] == cid_sel)
    sugerido = {"conservador": ["JNJ", "KO", "PG", "WMT", "VZ"],
                "moderado": ["AAPL", "MSFT", "JNJ", "JPM", "XOM"],
                "agresivo": ["NVDA", "TSLA", "META", "AMZN", "AVGO"]}[cli["perfil"]]
    tickers = st.multiselect("Activos", DEFAULT_UNIVERSE, default=sugerido)
    metodo = st.selectbox("Método de optimización", list(_METHODS))
    if len(tickers) >= 3 and st.button(f"⚙️ Calcular y asignar a {cli['name']}",
                                       type="primary"):
        with st.status("Optimizando y congelando precios de entrada…"):
            prices_df = pd.DataFrame({t: get_history(t).Close for t in tickers}).dropna()
            w = _METHODS[metodo](opt.returns_matrix(prices_df))
            precios = {t: get_quote(t)["price"] for t in tickers}
            set_portfolio(cid_sel, tickers, list(map(float, w)), precios)
        st.success(f"Portafolio {metodo} asignado a {cli['name']}: " +
                   " · ".join(f"{t} {wi:.0%}" for t, wi in zip(tickers, w)))
        st.caption(f"El cliente ya puede entrar con su número ({cid_sel}) o nombre + PIN.")

    with st.expander("🧺 Canastas modelo (los clientes las ven en Invertir)"):
        cb1, cb2 = st.columns([1, 2])
        b_name = cb1.text_input("Nombre", placeholder="🛡️ Escudo defensivo")
        b_tesis = cb2.text_input("Tesis (el porqué, en simple)",
                                 placeholder="Empresas que venden lo que la "
                                 "gente compra en las buenas y en las malas.")
        b_ticks = st.multiselect("Componentes (pesos iguales)",
                                 DEFAULT_UNIVERSE, key="bk_ticks")
        if st.button("Crear canasta") and b_name and len(b_ticks) >= 2:
            w = 1.0 / len(b_ticks)
            create_basket(b_name, b_tesis, b_ticks, [w] * len(b_ticks))
            st.success(f"Canasta «{b_name}» publicada.")
            st.rerun()
        for b in list_baskets():
            cbx1, cbx2 = st.columns([5, 1])
            cbx1.caption(f"**{b['name']}** — {', '.join(b['tickers'])}")
            if cbx2.button("🗑️", key=f"delbk_{b['id']}"):
                delete_basket(b["id"])
                st.rerun()

    with st.expander("💰 Depósito / retiro"):
        c1, c2, c3 = st.columns([1.4, 1, 2])
        tipo = c1.radio("Operación", ["Depósito", "Retiro"], horizontal=True)
        monto = c2.number_input("Monto ($)", 0.0, 1e9, 10_000.0, step=1_000.0)
        nota_mov = c3.text_input("Nota (opcional)", placeholder="Aportación mensual")
        if st.button(f"Registrar {tipo.lower()} a {cli['name']}"):
            add_deposit(cid_sel, monto if tipo == "Depósito" else -monto, nota_mov)
            st.success(f"{tipo} de {fmt_money(monto)} registrado para {cli['name']}.")
            st.rerun()

    with st.expander("📝 Nota del asesor (el cliente la ve en su portal)"):
        actual = get_note(cid_sel)
        texto = st.text_area("Recomendación / comentario", height=100,
                             value=(actual or {}).get("nota", ""),
                             key=f"nota_{cid_sel}")
        if st.button("Guardar nota"):
            set_note(cid_sel, texto)
            st.success("Nota guardada; el cliente la verá al entrar.")

    c1, c2, c3 = st.columns(3)
    c1.download_button("⬇️ Respaldar clientes", export_all(),
                       file_name="clientes_alx.json")
    up = c2.file_uploader("Restaurar respaldo", type=["json"],
                          label_visibility="collapsed")
    if up is not None:
        n = import_all(up.read().decode())
        st.success(f"Respaldo restaurado: {n} clientes.")
    borrar = c3.selectbox("Eliminar cliente", ["—"] + [c["id"] for c in clientes])
    if borrar != "—" and c3.button(f"🗑️ Confirmar borrar {borrar}"):
        delete_client(borrar)
        st.rerun()
    from src.data.dbx import backend as _bk
    if _bk() == "turso":
        st.caption("☁️ Base Turso compartida: los datos persisten y el Portal "
                   "los ve al instante. El respaldo JSON es tu red de seguridad.")
    else:
        st.caption("💾 Base local: en la nube se reinicia con cada redeploy; "
                   "respalda después de cambios y restaura al entrar.")


def render() -> None:
    if "client_auth" in st.session_state:
        _client_panel(st.session_state["client_auth"])
        return

    st.title("👥 Portal de clientes")
    tab_cli, tab_adm = st.tabs(["🔑 Acceso de cliente", "🛠️ Administración"])

    with tab_cli:
        st.markdown("Entra con tu **número de cliente o tu nombre** y tu PIN.")
        who = st.text_input("Número de cliente o nombre", placeholder="C-001 o Juan Pérez")
        pin = st.text_input("PIN", type="password")
        if st.button("Entrar", type="primary"):
            cli = verify_client(who, pin)
            if cli:
                st.session_state["client_auth"] = cli
                st.rerun()
            st.error("Cliente o PIN incorrectos.")

    with tab_adm:
        admin_pin = get_secret("JT_ADMIN_PIN")
        if admin_pin:
            entered = st.text_input("PIN de administrador", type="password",
                                    key="adm_pin")
            if entered != admin_pin:
                st.info("Introduce el PIN de administrador (secret JT_ADMIN_PIN).")
                return
        else:
            st.warning("⚠️ Administración sin protección: define JT_ADMIN_PIN en "
                       "Secrets para exigir PIN aquí.")
        _admin_panel()
