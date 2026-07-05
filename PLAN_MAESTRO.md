# 🧭 JUBILA-TEC — Plan Maestro de Producto

> Documento de trabajo permanente. Consolida la visión, arquitectura y backlog
> priorizado acordados. Toda sesión de desarrollo parte de aquí.
> **Versión 1.0 — 2026-07-03**

---

## 1. Visión

Una terminal financiera **de nivel institucional que cualquier persona entiende**.
Tres pisos:

| Piso | Qué es | Ejemplo |
|---|---|---|
| **3. Capa humana** | Copiloto conversacional, briefing diario, escenarios narrados, modo Simple/Pro | "¿Por qué bajó mi portafolio hoy?" → respuesta en 4 frases con números reales |
| **2. Inteligencia** | Noticias→eventos tipados, grafo de relaciones, narrativas, earnings calls, datos alternativos | Arancel a China → alerta en AAPL por exposición de ingresos |
| **1. Motores** | Fundamental, valoración, técnico, forense, riesgo, portafolio, macro, jubilación — validados y con backtest | DCF + EPV + Monte Carlo fat-tailed con metodología publicada |

**Regla de oro:** el LLM traduce, **nunca calcula**. Todo número sale de los motores
(auditables, testeados). Cero alucinación numérica.

---

## 2. Principios de diseño

1. **Validado o no existe**: ningún score se muestra sin backtest honesto (sesgos controlados, intervalos de confianza).
2. **Explicable**: cada score con desglose waterfall + fórmula + referencia bibliográfica.
3. **Dos registros**: modo Simple (semáforo, analogías, consecuencias vivibles) y modo Pro (tablas, sensibilidades, metodología). Misma verdad, dos lenguajes.
4. **Degradación elegante**: multi-proveedor con failover → sintético determinista. La app nunca se rompe.
5. **Términos reales**: proyecciones de jubilación deflactadas por inflación estocástica.
6. **Pocas cosas correctas > muchas a medias.**

---

## 3. Estado actual y gap crítico

- ✅ En esta carpeta: `app.py` (shell), `requirements.txt`, README, BACKLOG, DEPLOY.
- ⚠️ **Falta `src/` completo** (motores, vistas, config, styles), `tests/`, `.streamlit/`, `landing/`.
  La app no corre sin eso. → **Fase 0 obligatoria.**

---

## 4. Roadmap por fases

### Fase 0 — Base funcional *(bloqueante)* — ✅ COMPLETADA 2026-07-03
- [x] Reconstruir `src/` completo (25 módulos, núcleo numpy-puro con scipy/sklearn opcionales).
- [x] `tests/test_smoke.py` verde (12/12) + app lista para `streamlit run app.py`.
- [ ] CI GitHub Actions (tests + lint en cada push) — *pendiente de subir a GitHub*.

### Fase 1 — Confianza (2-4 sem) — ✅ NÚCLEO COMPLETADO 2026-07-04
- [x] **Multi-proveedor con failover**: yfinance → Stooq → sintético (`source_of()` rastrea quién respondió); badge de calidad por ticker (congelados, gaps, outliers >10σ, frescura) en `data/quality.py`.
- [x] **Persistencia SQLite**: historial de scores por ticker (`data/store.py`, ruta configurable JT_DB_PATH); gráfica de evolución del score en la vista de acción.
- [x] Quick wins cuant: shrinkage Ledoit-Wolf, **HRP numpy-puro** (López de Prado), contribución al riesgo por activo, **stress tests** con 5 escenarios de shock sectorial, momentum 1/3/6/12m.
- [x] **Explicabilidad**: desglose por pilar con pesos en la vista de acción.
- [x] **Cornish-Fisher VaR** + skew/kurtosis; **Omega, Ulcer Index, Calmar** en risk_summary.
- [x] Tests de oro (DCF verificado a mano) + tests de propiedades (CVaR≥VaR, pesos suman 1, crisis nunca positiva).
- [ ] Esquemas pydantic en fronteras de datos; tooltips educativos por métrica — *siguiente tanda*.

### Fase 2 — Diferenciación (4-6 sem) — 🔄 NÚCLEO COMPLETADO 2026-07-04
- [x] **Motor de jubilación** (`retirement/planner.py` + vista 🎯): acumulación Monte Carlo fat-tailed en términos reales (inflación estocástica deflactada), glide path 120−edad, prob. de meta, aporte requerido para 80% (bisección), y comparador de reglas de retiro (4% Bengen vs % del saldo vs Guyton-Klinger) con prob. de ruina e ingreso P10.
- [x] **Backtesting** (`backtest/engine.py` + vista 🧪): momentum 12-1 walk-forward por terciles con IC bootstrap por bloques y hit rate; walk-forward de portafolios con costos de rotación vs pesos iguales. Limitaciones (survivorship, point-in-time) declaradas en la UI.
- [x] **Position sizing**: Kelly fraccionado (½, tope 20%) en la pestaña Riesgo de cada acción.
- [ ] Purging/embargo + Deflated Sharpe (cuando haya más historia y señales múltiples).
- [ ] Perfil CRRA por cuestionario; contexto fiscal MX/US; riesgo de secuencia con tablas actuariales.
- [x] **Alertas** (`alerts/engine.py` + vista 🔔): condiciones precio/RSI/score persistidas en SQLite, evaluación bajo demanda, notificación Telegram opcional (TELEGRAM_BOT_TOKEN/CHAT_ID en `.env`).
- [x] **Export CSV** (UTF-8 BOM para Excel) en Mercados y Underdog.
- [x] **Riesgo cambiario** (`models/fx.py`): descomposición USD/peso/MXN del portafolio con correlación y nota interpretativa; serie USDMXN con failover sintético.
- [ ] Reporte PDF profesional (el Markdown descargable ya existe).

### Fase 3 — Inteligencia (6-8 sem) — 🔄 NÚCLEO COMPLETADO 2026-07-04
- [x] **SEC EDGAR** (`data/edgar.py`, sin key): companyfacts 10-K oficiales (con año previo → forense real) encadenados en get_fundamentals (sample → EDGAR → yfinance); actividad de insiders por conteo de Form 4 en 90 días, en la pestaña Forense. Timeouts cortos + fallback sintético.
- [x] **Noticias → eventos tipados** (`news/events.py`): 13 tipos (recorte de guía, buyback, M&A, regulatorio, litigio, contrato…) con dirección e impacto típico de event studies; el evento pesa 60% vs. 40% del tono léxico en el sentimiento; chips visibles en Noticias.
- [x] **Régimen de mercado** (`models/regime.py`): GMM 2 estados vía EM numpy-puro sobre SPY + tendencia SMA200 → 4 regímenes con emoji/descripción en Dashboard y badge en cada análisis; **en turbulencia el score reduce el peso del técnico (10%) y sube fundamental/forense** (momentum crashes, Daniel-Moskowitz 2016).
- [ ] Dirección compra/venta de Form 4 (parsear filings individuales); 13F.
- [ ] Grafo de relaciones desde 10-K; narrativas; tono de earnings calls; FinBERT.
- [ ] Datos alternativos gratis: Google Trends, vacantes, rankings de apps.

### Fase 4 — Capa humana (el salto "de otro mundo") — 🔄 NÚCLEO COMPLETADO 2026-07-04
- [x] **Copiloto conversacional** (vista 🤖 + `copilot/copilot.py`): detección de intención (ticker/mercado/jubilación/portafolio), contexto empaquetado desde los motores, Claude API si hay ANTHROPIC_API_KEY con regla dura "traduce, nunca calcula", y respondedor de plantillas determinista sin clave. Cero alucinación numérica en ambos modos.
- [x] **Briefing diario** (`report/briefing.py`): régimen + mejores/peores de la lista + alertas disparadas + curva, en 3 párrafos llanos; expander en Dashboard con envío a Telegram.
- [x] **Toggle Simple/Pro** global en sidebar: en Simple, el análisis de acción muestra solo gauge, semáforo y tesis "en sencillo" (si sale bien / si sale mal).
- [x] Escenarios narrados: ya presentes en Riesgo ("en un día malo de 1 entre 20…"), Portafolio y Jubilación.
- [ ] Onboarding 3 pasos, responsive <700px, i18n ES/EN.

### Actualización diaria automática — ✅ COMPLETADA 2026-07-04
- [x] **Job diario** (`jobs/daily_update.py`): limpia cachés, recalcula y persiste el score de todo el universo (el historial crece día a día), evalúa alertas y envía el briefing a Telegram. Bitácora en `update.log`.
- [x] **`actualizacion_diaria.bat`** listo para el Programador de tareas de Windows.
- [x] **Botón 🔄 Actualizar datos** en la sidebar (vacía cachés al instante) + hora de última actualización.
- [x] **Lookup en vivo** (`market_data.lookup_ticker`): ante un ticker desconocido, el copiloto pregunta al proveedor antes de negar su existencia (lección SpaceX) — IPOs nuevas se analizan al vuelo.

### v0.9 — Universo abierto + nube + diseño claro — ✅ 2026-07-04
- [x] **Universo abierto**: cualquier ticker que cotice se analiza al vuelo (resolve + lookup en vivo); sectores de yfinance traducidos a nuestra taxonomía para peers y stress tests.
- [x] **Briefing diario desde la nube**: `.github/workflows/daily.yml` corre `jobs/daily_update.py` en GitHub Actions L-V 8:30 CDMX (secrets del repo: TELEGRAM_*, FRED, NEWSAPI) — ya no depende de la PC encendida.
- [x] **Respaldo de Mi Lista**: export/import .txt en el Dashboard (sobrevive redeploys de Streamlit Cloud). BD externa (Turso/Supabase) pendiente — requiere cuenta del usuario.
- [x] **Rediseño claro premium**: fondo blanco, Inter + Playfair Display, esmeralda #10B981 como acento, tarjetas con hover suave, aire generoso, gráficas re-tematizadas (paleta esmeralda/rojo/azul/ámbar sobre blanco). Brief completo del sitio React (hero cinemático, etc.) archivado para Fase 5.

### Fase 5 — Escala como producto
- [ ] FastAPI envolviendo motores; auth (Supabase); tiers free/premium (alertas, PDF, screeners ilimitados como premium).
- [ ] Postgres + Redis + screeners nocturnos solo cuando haya usuarios reales.
- [ ] Proveedor de datos con licencia comercial (FMP/Polygon) — yfinance es zona gris para monetizar.
- [ ] Landing (Vercel) + deploy Streamlit Cloud (ver DEPLOY.md).

---

## 5. Backlog técnico ampliado (por disciplina, para tomar de aquí)

**Técnico:** S/R por clustering de pivots (DBSCAN), volume profile (POC/value area), divergencias automáticas RSI/MACD/OBV, patrones de velas y chartistas algorítmicos, Anchored VWAP, Ichimoku, Heikin-Ashi, breadth (%>SMA200, A/D, McClellan), fuerza relativa Mansfield vs sector/SPY, intermercado (DXY, 10Y, oil, cobre/oro), estacionalidad con test de significancia, confluencia multi-timeframe, IV vs RV, put/call, max pain, GEX.

**Cuant:** EVT para colas, cointegración Engle-Granger (pares), half-life OU, GARCH(1,1) propio vía MLE, Kalman 1D, Black-Litterman (preparación), PCA de factores, Fama-French 3/5 + momentum, Mahalanobis, entropía de retornos.

**Fundamental:** EPV (Greenwald), ingreso residual, múltiplos por regresión (P/E ~ growth+ROIC+margen), Moat Score (persistencia ROIC>WACC, estabilidad margen bruto — Novy-Marx), Merton distance-to-default, Ohlson O-Score, shareholder yield, conversión de caja, NOA (Hirshleifer), asset growth (Cooper), dividend safety score, anomalías (52-week high, low-vol, MAX effect).

**Portafolio:** optimización CVaR (Rockafellar-Uryasev, LP), Michaud resampling, costos de transacción + bandas de rebalanceo ±5pp, restricciones realistas (máx por posición/sector, cardinalidad), risk budgeting, Nelson-Siegel + duración/convexidad para bonos.

**Producto:** screener con query builder ("ROIC>15 y P/FCF<20 y F≥7"), watchlists persistentes, paper trading, comparador de pares (percentiles sectoriales), panel de metodología con LaTeX y referencias (Hull, Damodaran, López de Prado, Novy-Marx, Ledoit-Wolf).

---

## 6. Definición de "hecho" (toda feature)

1. Test numérico contra valor conocido o propiedad invariante.
2. Entrada validada (pydantic) y fallback definido.
3. Explicación en modo Simple escrita (no solo la tabla Pro).
4. Fórmula + referencia en el panel de metodología.
5. Versión de modelo + seed + timestamp registrados en cada salida.

## 7. Compliance

Solo datos públicos y ToS respetados. Lenguaje no imperativo ("el modelo indica", nunca "compra"). Disclaimer visible: no somos asesores registrados (CNBV/SEC). Auditabilidad total por versionado de modelos.
