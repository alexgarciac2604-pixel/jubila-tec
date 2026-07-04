"""Vista: catálogo de modelos, metodología y compliance."""
from __future__ import annotations

import streamlit as st

from src import __version__
from src.config import DISCLAIMER

_MODELS = [
    ("DCF dos etapas + reverse DCF", "Valoración",
     "Flujos descontados 5 años + valor terminal Gordon. El reverse resuelve el crecimiento implícito en el precio (bisección).",
     "Damodaran, *Investment Valuation*"),
    ("Monte Carlo de valoración", "Valoración",
     "Distribución del valor por acción con incertidumbre normal en g y WACC (n=2000, seed fija → reproducible).",
     "Damodaran; simulación estándar"),
    ("Altman Z-Score", "Forense",
     "Riesgo de quiebra: 5 razones contables. Zonas: >2.99 segura, 1.81-2.99 gris, <1.81 peligro.",
     "Altman (1968)"),
    ("Piotroski F-Score", "Forense",
     "9 checks de salud financiera (rentabilidad, apalancamiento, eficiencia). ≥7 fuerte, ≤3 débil.",
     "Piotroski (2000)"),
    ("Beneish M-Score (reducido)", "Forense",
     "Probabilidad de manipulación contable con 5 de los 8 índices originales. M > -1.78 = bandera.",
     "Beneish (1999)"),
    ("Accruals de Sloan", "Forense",
     "(Utilidad − CFO)/Activos: utilidades sin respaldo de caja predicen reversión.",
     "Sloan (1996)"),
    ("VaR/CVaR histórico + Cornish-Fisher", "Riesgo",
     "Pérdida en percentil 5 y promedio de la cola; CF ajusta por skew/curtosis (retornos no normales).",
     "RiskMetrics; Cornish-Fisher (1938)"),
    ("Monte Carlo t-Student", "Riesgo",
     "Proyección de riqueza con colas gordas (df=5) — más realista que el supuesto gaussiano.",
     "Literatura de fat tails"),
    ("Optimización media-varianza con shrinkage", "Portafolio",
     "Tangencia (máx. Sharpe) con covarianza Ledoit-Wolf/shrinkage a identidad; proyección long-only.",
     "Markowitz (1952); Ledoit-Wolf (2004)"),
    ("Risk parity", "Portafolio",
     "Iguala la contribución de riesgo de cada activo (punto fijo iterativo).",
     "Qian (2005)"),
    ("Score técnico compuesto", "Técnico",
     "SMA/EMA, RSI, MACD, Bollinger, ATR, OBV, ADX, Fibonacci → señales ponderadas 0-100.",
     "Murphy, *Technical Analysis*"),
    ("Underdog Score", "Screening",
     "Valor + calidad + castigo (condicionado a calidad, anti value-trap) + giro de momentum.",
     "Propio; inspirado en Piotroski + momentum"),
    ("Régimen de mercado (GMM 2 estados)", "Macro",
     "Mezcla gaussiana vía EM sobre retornos del benchmark: prob. de turbulencia + tendencia (SMA200). En turbulencia el score baja el peso del momentum (momentum crashes).",
     "Hamilton (1989); Daniel & Moskowitz (2016)"),
    ("Eventos tipados de noticias", "Noticias",
     "Clasificador titular→evento (recorte de guía, buyback, M&A, regulatorio…) con dirección e impacto típico de event studies. Un evento pesa 60% vs. 40% del tono léxico.",
     "MacKinlay (1997)"),
    ("Fundamentales SEC EDGAR", "Datos",
     "10-K oficiales vía companyfacts (XBRL) con año previo para forense; actividad de insiders vía conteo de Form 4 (90 días). Point-in-time real, sin API key.",
     "SEC EDGAR (data.sec.gov)"),
    ("Score de inversión 0-100", "Síntesis",
     "Fundamental 25% · Valoración 20% · Técnico 20% · Forense 20% · Sentimiento 15%. Semáforo: ≥70 🟢, 45-69 🟡, <45 🔴.",
     "Propio; desglose visible en cada análisis"),
]


def render() -> None:
    st.title("📚 Modelos & Compliance")
    st.caption(f"Motor analítico v{__version__} — cada salida registra fuente, supuestos y seed.")

    st.subheader("Catálogo de modelos")
    for name, cat, desc, ref in _MODELS:
        with st.expander(f"**{name}** · {cat}"):
            st.markdown(desc)
            st.caption(f"Referencia: {ref}")

    st.subheader("⚖️ Compliance")
    st.markdown(
        "- Solo **información pública, legal y accesible**; sin scraping que viole ToS.\n"
        "- **No** es asesoría financiera personalizada; lenguaje no imperativo "
        "(\"el modelo indica\", nunca \"compra\").\n"
        "- **No** se prometen rendimientos; todo backtest futuro reportará sus sesgos.\n"
        "- Reproducibilidad: seeds fijas y versión del motor en cada reporte."
    )
    st.info(DISCLAIMER)
