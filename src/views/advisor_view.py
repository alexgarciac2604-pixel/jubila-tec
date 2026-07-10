"""Vista Studio: 🧠 Mesa del Asesor — analiza fácil, recomienda con respaldo."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.advisor.profile import factor_lens, piotroski_value_screen
from src.clients.manager import create_basket, list_clients, set_note
from src.screener.engine import load_screener

_PERFIL_ICON = {"conservador": "🛡️", "moderado": "⚖️", "agresivo": "🚀"}


def _ficha(ticker: str) -> None:
    from src.advisor.profile import advisor_profile
    with st.status(f"Armando la ficha de {ticker}…"):
        try:
            p = advisor_profile(ticker)
        except Exception as e:
            st.error(f"No pude armar la ficha de {ticker}: {e}")
            return
    comp = p["comp"]
    q = comp["quote"]

    st.markdown(f"## {comp['semaforo']} {comp.get('name') or ticker} "
                f"({ticker}) — {comp['total']}/100")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Precio", f"${q['price']:,.2f}", f"{q['change_pct']:+.2f}%")
    c2.metric("F-Score (Piotroski)",
              f"{p['f_score']}/9" if p["f_score"] is not None else "n/d")
    c3.metric("Forense", f"{comp['pillars']['forensic']}/100")
    c4.metric("Insiders 90d", p["insider"].get("form4_90d", "n/d"),
              help=p["insider"].get("summary", ""))

    from src.screener.deepscan import load_state
    ds = load_state().get("done", {}).get(ticker)
    if ds:
        extra = ""
        if ds.get("win_rate") is not None:
            extra = (f" Validación: {ds['n']} episodios similares en su "
                     f"historial, {ds['win_rate']}% ganadores a 3 meses "
                     f"(promedio {ds['avg_fwd_3m']:+.1f}%).")
        st.markdown(
            f"<div class='jt-badge' style='display:block;padding:12px'>"
            f"🔭 <b>Deep Scan:</b> {ds['emoji']} <b>{ds['label']}</b> "
            f"(confianza {ds['confianza']}) — {ds['razon']}{extra}</div>",
            unsafe_allow_html=True)

    st.markdown("**¿A quién se la recomiendas?**")
    cols = st.columns(3)
    for col, (perfil, (apto, razon)) in zip(cols, p["aptos"].items()):
        icono = _PERFIL_ICON[perfil]
        marca = "✅" if apto else "🚫"
        col.markdown(f"<div class='jt-badge' style='display:block;padding:10px'>"
                     f"{icono} <b>{perfil.capitalize()}</b> {marca}<br>"
                     f"<small>{razon}</small></div>", unsafe_allow_html=True)

    a, b = st.columns(2)
    with a:
        st.markdown("**💬 Qué decirle al cliente**")
        for x in p["puntos"]:
            st.markdown(f"- {x}")
    with b:
        st.markdown("**⚠️ Qué vigilar**")
        for x in p["riesgos"]:
            st.markdown(f"- {x}")

    if p["factores"]:
        st.markdown("**🔬 Lente factorial** (percentil vs. universo del screener)")
        fcols = st.columns(4)
        for col, (fac, pct) in zip(fcols, p["factores"].items()):
            col.metric(fac, f"P{pct}")
            col.progress(pct / 100)

    th = comp.get("thesis", {})
    if th:
        with st.expander("📜 Tesis completa (alcista / base / bajista)"):
            st.markdown(f"**Postura: {th.get('stance', 'n/d')}**")
            st.markdown(f"🐂 {th.get('bull', '')}")
            st.markdown(f"➖ {th.get('base', '')}")
            st.markdown(f"🐻 {th.get('bear', '')}")

    st.markdown("**⚡ Acciones rápidas**")
    clientes = list_clients()
    if clientes:
        dest = st.selectbox("Enviar como nota a…",
                            [f"{c['id']} — {c['name']}" for c in clientes])
        if st.button("📝 Enviar recomendación al cliente"):
            cid = dest.split(" — ")[0]
            perfil_cli = next(c["perfil"] for c in clientes if c["id"] == cid)
            apto, razon = p["aptos"].get(perfil_cli, (False, ""))
            nota = (f"{comp['semaforo']} {ticker} ({comp['total']}/100): "
                    + (f"apta para tu perfil {perfil_cli} — {razon}. "
                       if apto else
                       f"hoy NO la veo para tu perfil {perfil_cli} ({razon}). ")
                    + p["puntos"][0])
            set_note(cid, nota)
            st.success(f"Nota enviada a {dest}: la verá al entrar al portal.")
    else:
        st.caption("Sin clientes aún.")


def render() -> None:
    st.title("🧠 Mesa del Asesor")
    st.caption("Todos los modelos de AL-X → una recomendación fácil. "
               "⚖️ Herramienta de análisis para el asesor; no es asesoría "
               "automática al público.")

    tk = st.text_input("Analiza una acción", placeholder="AAPL, KO, NVDA…",
                       key="mesa_tk").upper().strip()
    if tk:
        from src.data.market_data import resolve_symbol
        real = resolve_symbol(tk)
        if real:
            _ficha(real)
        else:
            st.error(f"No encontré «{tk}» — ¿otro nombre o ticker?")

    st.divider()
    scr = load_screener()
    rows = scr.get("rows", []) if scr else []

    st.subheader("🔭 Deep Scan S&P 500")
    st.caption("Estilo Zacks/Morningstar Quant, versión AL-X: todo el índice "
               "por bloques; cada acción validada contra SU propio historial "
               "(walk-forward) antes de etiquetarla. Corre completo cada "
               "sábado; aquí puedes avanzar bloques manualmente.")
    from src.screener.deepscan import load_state, run_block, start_or_resume
    ds_st = load_state()
    n_done, n_uni = len(ds_st.get("done", {})), ds_st.get("universe_n", 0)
    if n_uni:
        st.progress(min(n_done / max(n_uni, 1), 1.0),
                    text=f"{n_done}/{n_uni} analizadas · {ds_st.get('date', '')}")
    cdd1, cdd2 = st.columns([1, 2])
    if cdd1.button("▶️ Procesar siguiente bloque (20)"):
        with st.status("Analizando bloque (histórico de 5 años por acción)…"):
            ds_st = run_block(20)
        st.rerun()
    if not ds_st.get("done") and cdd2.button("🔄 Iniciar escaneo de hoy"):
        start_or_resume()
        st.rerun()
    if ds_st.get("done"):
        ddf = pd.DataFrame(list(ds_st["done"].values()))
        cuenta = ddf["label"].value_counts()
        st.caption(" · ".join(
            f"{ddf[ddf.label == l]['emoji'].iloc[0]} {l}: {c}"
            for l, c in cuenta.items()))
        filtro = st.multiselect(
            "Ver etiquetas", list(cuenta.index),
            default=[l for l in ("Comprar", "Acumular") if l in cuenta.index]
                    or list(cuenta.index)[:1])
        vista = ddf[ddf["label"].isin(filtro)][
            ["emoji", "ticker", "name", "sector", "price", "score",
             "f_score", "win_rate", "avg_fwd_3m", "razon"]]
        vista.columns = ["", "Ticker", "Empresa", "Sector", "Precio",
                         "Score", "F", "Win %", "Fwd 3m %", "Por qué"]
        st.dataframe(vista.style.format({"Precio": "${:,.2f}"}, na_rep="—"),
                     hide_index=True, use_container_width=True, height=420)

    st.divider()
    st.subheader("🏆 Radar Piotroski-Value")
    st.caption("La estrategia del paper (Stanford, 2000): del tercil más "
               "barato del universo, solo las de salud financiera 8-9 de 9. "
               "Históricamente +7.5% anual sobre las baratas débiles.")
    if not rows:
        st.info("Necesita el screener nocturno (corre el workflow o espera "
                "a la madrugada).")
    elif st.button("🔎 Correr el radar (analiza el tercil barato)"):
        from src.data.market_data import get_fundamentals
        from src.forensic.scores import piotroski_f
        with st.status("F-Score sobre las baratas del universo…"):
            res = piotroski_value_screen(rows, get_fundamentals, piotroski_f)
        if res:
            df = pd.DataFrame(res)[["ticker", "name", "sector", "price",
                                    "valoracion", "f_score", "apta"]]
            df.columns = ["Ticker", "Empresa", "Sector", "Precio",
                          "Valoración", "F-Score", "Apta (F≥8)"]
            st.dataframe(df.style.format({"Precio": "${:,.2f}"}),
                         hide_index=True, use_container_width=True)
            evitar = [r["ticker"] for r in res if r["evitar"]]
            if evitar:
                st.warning("Evitar a toda costa (F≤1): " + ", ".join(evitar))
        else:
            st.info("Sin resultados (¿fundamentales no disponibles?).")

    st.divider()
    st.subheader("🔬 Lente Factorial → canasta con un clic")
    if rows:
        facs = st.multiselect("Factores a combinar",
                              ["Valor", "Calidad", "Momentum", "Tendencia"],
                              default=["Valor", "Calidad"])
        n = st.slider("Tamaño de la canasta", 3, 10, 5)
        if facs and st.button("⚙️ Generar canasta factorial"):
            rank = []
            for r in rows:
                lens = factor_lens(r["ticker"], rows) or {}
                rank.append((sum(lens.get(f, 0) for f in facs), r))
            rank.sort(key=lambda x: x[0], reverse=True)
            st.session_state["mesa_fact_top"] = [r for _, r in rank[:n]]
            st.session_state["mesa_fact_nombre"] = "📐 " + " + ".join(facs)
        top = st.session_state.get("mesa_fact_top")
        if top:
            st.dataframe(pd.DataFrame(top)[["ticker", "name", "sector",
                                            "price", "score"]],
                         hide_index=True, use_container_width=True)
            nombre = st.session_state["mesa_fact_nombre"]
            tesis = ("Canasta factorial (Fama-French pragmático): las "
                     "mejores del universo combinando "
                     f"{nombre.replace('📐 ', '')}. Pesos iguales, "
                     "revisión mensual sugerida.")
            if st.button(f"🧺 Publicar «{nombre}» a los clientes"):
                create_basket(nombre, tesis, [t["ticker"] for t in top],
                              [1 / len(top)] * len(top))
                st.session_state.pop("mesa_fact_top", None)
                st.success("Canasta publicada: tus clientes ya la ven en "
                           "Invertir.")
    else:
        st.info("El lente factorial también necesita el screener nocturno.")
