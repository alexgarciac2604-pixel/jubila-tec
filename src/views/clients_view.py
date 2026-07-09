"""Vista: 👥 Clientes — acceso por código/nombre + PIN, y administración."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.clients.manager import (create_client, delete_client, export_all,
                                 get_portfolio, import_all, list_clients,
                                 set_portfolio, verify_client)
from src.config import DEFAULT_UNIVERSE, RISK_FREE, get_secret
from src.data.market_data import get_history, get_quote
from src.models.risk import monte_carlo_paths
from src.models.stress import portfolio_stress
from src.portfolio import optimizer as opt
from src.utils.formatting import fmt_money, fmt_num, fmt_pct
from src.views.components import dark_fig

_METHODS = {
    "Máx. Sharpe": opt.max_sharpe,
    "HRP (Hierarchical Risk Parity)": opt.hrp,
    "Mínima varianza": opt.min_variance,
    "Risk parity": opt.risk_parity,
    "Pesos iguales": opt.equal_weight,
}


def _client_panel(client: dict) -> None:
    st.title(f"👋 Hola, {client['name']}")
    st.markdown(
        f"<span class='jt-badge'>Cliente {client['id']}</span> "
        f"<span class='jt-badge'>Perfil {client['perfil']}</span> "
        f"<span class='jt-badge'>Desde {client['created']}</span>",
        unsafe_allow_html=True,
    )
    if st.button("Cerrar sesión"):
        st.session_state.pop("client_auth", None)
        st.rerun()

    holdings = get_portfolio(client["id"])
    if not holdings:
        st.info("Tu asesor aún no te asigna un portafolio. Vuelve pronto. 🙂")
        return

    rows, total_now, total_in = [], 0.0, 0.0
    for h in holdings:
        px_now = get_quote(h["ticker"])["price"]
        invested = client["capital"] * h["weight"]
        units = invested / h["price_at"] if h["price_at"] else 0.0
        value = units * px_now
        rows.append({"Ticker": h["ticker"], "Peso": h["weight"],
                     "P. entrada": h["price_at"], "P. actual": px_now,
                     "Invertido": invested, "Valor hoy": value,
                     "Rend. %": (value / invested - 1) * 100 if invested else 0.0})
        total_now += value
        total_in += invested
    df = pd.DataFrame(rows)
    rend_total = (total_now / total_in - 1) * 100 if total_in else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Capital asignado", fmt_money(total_in))
    c2.metric("Valor hoy", fmt_money(total_now), fmt_pct(rend_total))
    c3.metric("Asignado el", holdings[0]["assigned"])

    a, b = st.columns([1, 1.4])
    with a:
        fig = px.pie(df, names="Ticker", values="Valor hoy", hole=0.45)
        st.plotly_chart(dark_fig(fig, 300), use_container_width=True)
    with b:
        st.dataframe(
            df.style.format({"Peso": "{:.0%}", "P. entrada": "${:.2f}",
                             "P. actual": "${:.2f}", "Invertido": "${:,.0f}",
                             "Valor hoy": "${:,.0f}", "Rend. %": "{:+.1f}%"}),
            hide_index=True, use_container_width=True,
        )

    tickers = [h["ticker"] for h in holdings]
    w_now = (df["Valor hoy"] / total_now).tolist() if total_now else df["Peso"].tolist()
    try:
        prices = pd.DataFrame({t: get_history(t).Close for t in tickers}).dropna()
        stats = opt.portfolio_stats(pd.Series(w_now).values, opt.returns_matrix(prices), RISK_FREE)
        c1, c2, c3 = st.columns(3)
        c1.metric("Volatilidad anual", fmt_pct(stats["ann_vol"] * 100, signed=False))
        c2.metric("Sharpe", fmt_num(stats["sharpe"]))
        c3.metric("Máx. drawdown histórico", fmt_pct(stats["max_drawdown"] * 100))

        mc = monte_carlo_paths(stats["ann_return"], stats["ann_vol"], years=5,
                               n_paths=800, start=total_now)
        st.caption(
            f"**Proyección a 5 años (Monte Carlo, colas gordas):** escenario mediano "
            f"{fmt_money(mc['p50'])}, pesimista (P10) {fmt_money(mc['p10'])}, "
            f"optimista (P90) {fmt_money(mc['p90'])}. "
            f"Prob. de terminar por debajo del valor actual: {mc['prob_loss']:.0%}."
        )
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
         f"**Capital asignado:** {fmt_money(total_in)}  ",
         f"**Valor hoy:** {fmt_money(total_now)} ({rend_total:+.1f}%)", "",
         "| Activo | Peso | P. entrada | P. actual | Valor hoy | Rend. |",
         "|---|---|---|---|---|---|"] +
        [f"| {r['Ticker']} | {r['Peso']:.0%} | ${r['P. entrada']:.2f} | "
         f"${r['P. actual']:.2f} | ${r['Valor hoy']:,.0f} | {r['Rend. %']:+.1f}% |"
         for r in rows] +
        ["", "> Reporte informativo y educativo con datos públicos; no constituye "
         "asesoría de inversión ni garantiza rendimientos."]
    )
    st.download_button("📄 Descargar mi estado de cuenta", reporte,
                       file_name=f"alx_{client['id']}_{_date.today()}.md")

    st.info("⚖️ Reporte informativo y educativo con datos públicos; no constituye "
            "asesoría de inversión ni garantiza rendimientos.")


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

    c1, c2, c3 = st.columns(3)
    c1.download_button("⬇️ Respaldar clientes", export_all(),
                       file_name="clientes_jubilatec.json")
    up = c2.file_uploader("Restaurar respaldo", type=["json"],
                          label_visibility="collapsed")
    if up is not None:
        n = import_all(up.read().decode())
        st.success(f"Respaldo restaurado: {n} clientes.")
    borrar = c3.selectbox("Eliminar cliente", ["—"] + [c["id"] for c in clientes])
    if borrar != "—" and c3.button(f"🗑️ Confirmar borrar {borrar}"):
        delete_client(borrar)
        st.rerun()
    from src.data.dbx import backend
    if backend() == "turso":
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
