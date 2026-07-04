# BACKLOG — Jubila-Tec Terminal

Pendientes priorizados para retomar en otra sesión. Esta tanda de trabajo completó
**Prioridad 1** (sistema visual + confianza/calidad de datos + semáforo) y buena parte
de **Prioridad 2** (régimen de mercado, volatilidad/riesgo avanzado, técnicos, métricas
de portafolio). Lo de abajo quedó fuera por gestión de contexto/tiempo, no por bloqueo
técnico, salvo donde se indica.

> Nota de investigación: en esta sesión **no hubo acceso verificable a internet**, así que
> no se citaron fuentes externas. Todo se implementó con conocimiento interno. Validar las
> fórmulas/umbrales contra literatura estándar (Hull, RiskMetrics, Ledoit-Wolf 2004,
> López de Prado HRP/2016) antes de uso productivo.

---

## Prioridad 2 — Métodos cuantitativos pendientes (sin deps nuevas, viables)
- [ ] **Ledoit-Wolf shrinkage covariance** en `portfolio/optimizer.py` (usar `sklearn.covariance.LedoitWolf`,
      ya es dependencia). Mejora estabilidad de la optimización media-varianza. *Riesgo: bajo.*
- [ ] **Component VaR / Marginal risk contribution** por activo en el portafolio
      (MCR_i = (Σw)_i / σ_p; CVaR_i = w_i·MCR_i). Mostrar barra de contribución al riesgo.
- [ ] **Rolling VaR / Rolling Sharpe** como series (ya existe `risk.rolling_var`; falta graficarlo).
- [ ] **Correlación dinámica** (rolling corr de pares clave) y matriz de correlación con dendrograma.
- [ ] **PCA de factores** (`sklearn.decomposition.PCA`) sobre retornos del universo → varianza explicada,
      exposición a factores latentes. *Riesgo: bajo.*
- [ ] **Mahalanobis distance** para detección de anomalías de mercado (turbulence index de Kritzman).
- [ ] **Entropía de retornos** (Shannon sobre histograma de retornos) como proxy de incertidumbre.
- [ ] **Kalman filter** para tendencia suavizada (implementación 1D simple, sin deps).
- [ ] **Hierarchical Risk Parity (HRP)** — requiere `scipy.cluster.hierarchy` (ya disponible).
- [ ] **Risk budgeting** explícito (target risk contributions configurable).
- [ ] **Stress testing / scenario shocks**: aplicar shocks (tasas +100bp, -20% equity, +oil)
      al portafolio y mostrar P&L estimado.
- [ ] **Liquidity risk proxy**: usar volumen·precio (ADV) y spread aproximado por activo.
- [ ] **Momentum multi-timeframe** (1m/3m/6m/12m) y **mean-reversion z-score signals** consolidados
      en un panel de señales (z-score ya existe en `indicators.zscore`).

## Modelos que requieren validación/deps — evaluar antes de implementar
- [ ] **GARCH(1,1)**: viable solo con implementación propia (MLE con scipy) para evitar `arch`.
      Si se acepta `arch` como dep, es directo. Documentar trade-off. *Pendiente de decisión.*
- [ ] **Black-Litterman**: dejar solo preparación (priors + views API), sin activar por defecto.
- [ ] **Ichimoku Kinko Hyo**: viable con pandas; pendiente por presupuesto visual.
- [ ] **Anchored VWAP**: requiere elegir ancla (evento/fecha) en UI; VWAP simple ya existe.
- [ ] **Volatility surface / superficie WACC×crecimiento×valor** (Plotly 3D) — **Prioridad 4**,
      descartado por rendimiento; reconsiderar solo si no degrada la app.

## Prioridad 1/3 — UX/visual pendiente
- [ ] **Onboarding corto** (primera visita): modal/expander con 3 pasos y tour de la terminal.
- [ ] Usar `styles.empty_state()` en estados vacíos reales (Underdog sin resultados, Portafolio
      sin selección, Noticias sin filtros). Los helpers ya existen, falta cablearlos en cada vista.
- [ ] **Error states diseñados** cuando una fuente falla (hoy degrada a sample con aviso; falta
      tarjeta de error dedicada con acción de reintento).
- [ ] **Panel de metodología** dedicado (cómo se calcula cada score, con fórmulas) — hoy está en
      About; mover/expandir a un panel contextual por score.
- [ ] Microinteracciones extra (emil-design-eng): transición de tabs, fade-in de cards al cargar,
      skeleton durante el primer fetch de cada vista (hoy hay `st.status` por fases).
- [ ] Responsive fino: revisar < 700px (cards apiladas, tablas con scroll horizontal).

## Datos y fuentes (sin scraping dudoso, respetando ToS)
- [ ] **SEC EDGAR** (público, sin key): parser de `submissions` y `companyfacts` para Form 4
      (insiders) y 13F. Endpoint: `https://data.sec.gov/`. Requiere header User-Agent. *Viable.*
- [ ] **USAspending.gov** (API pública): contratos por empresa (mapear ticker→CIK→recipiente).
- [ ] **FRED**: ampliar series (curva completa, spreads de crédito, condiciones financieras).
- [ ] Conectar clientes opcionales ya registrados en `sources.py`: Alpha Vantage, FMP, Finnhub,
      Polygon (todos con key en `.env`). Cada uno detrás de la misma firma que `market_data.py`.
- [ ] Cache persistente en disco (hoy es TTL en memoria) para acelerar arranque.

## Reportes
- [ ] **PDF real**: vía `weasyprint` (HTML→PDF) o `reportlab`. Hoy: HTML→Imprimir→PDF (placeholder).
      Evaluar peso de la dep. Skill `/mnt/skills/public/pdf` para guía.
- [ ] Excel: añadir hojas de Régimen, Riesgo avanzado (ES/DaR/diversification) y Noticias clasificadas.
- [ ] Reporte: incrustar el panel de confianza de datos y el régimen (ya en HTML parcialmente).

## Calidad / QA
- [ ] Tests para `regime` con series construidas (bull/bear/lateral deterministas), no solo sample.
- [ ] Tests de los nuevos paneles de UI vía AppTest con aserciones de contenido (no solo "sin excepción").
- [ ] Linting (ruff/flake8) y limpieza de imports no usados (p. ej. `band` importado en algunas vistas).
- [ ] Validación numérica de Hurst y vol cone contra un dataset de referencia conocido.

## Notas de arquitectura
- El núcleo `src/` sigue siendo Python puro (sin Streamlit) salvo `utils/styles.py` y `views/`.
  Mantener esa separación para poder exponer FastAPI más adelante.
- No romper firmas: `conclusion.build` y `scorecards.build` se ampliaron con parámetros
  **opcionales** para no romper llamadas existentes. Mantener ese patrón.
