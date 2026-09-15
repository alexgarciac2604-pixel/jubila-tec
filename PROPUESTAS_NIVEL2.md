# 🚀 AL-X — Propuestas para el siguiente nivel

*Septiembre 2026 · Investigación externa + síntesis sobre el código real (v0.23.1).*
*Complementa PLAN_MAESTRO.md, ANALISIS_COMPETITIVO.md e INVESTIGACION_MERCADO.md — no los repite.*

---

## 0. Dónde estás y qué mueve la frontera

Ya construiste los **tres pisos**: motores validados (Piso 1), inteligencia
(eventos tipados, régimen GMM, EDGAR, deep scan) (Piso 2) y buena parte de la capa
humana (copiloto, briefing, Simple/Pro, portal de clientes) (Piso 3). El núcleo está
sano y desplegado. **El "siguiente nivel" no es más motores: es hacer que la IA
orqueste lo que ya tienes, dueño del canal donde vive tu cliente (WhatsApp/MX), y
convertir tus motores en hábitos de cliente medibles.**

Lo que la investigación de sep-2026 confirma:

- **La IA agéntica es *la* tendencia de wealth management 2026.** Aladdin Copilot
  (BlackRock) orquesta cientos de APIs internas; el asistente de Goldman enruta entre
  OpenAI/Google/**Anthropic**. Gartner: agentes específicos en el 40% de apps
  empresariales para 2026. → Tu copiloto debe **orquestar tus motores**, y tu regla
  "traduce, nunca calcula" es el encaje perfecto: los motores son las herramientas.
- **Robinhood Cortex ya llegó a los asesores** (TradePMR): *digests* por cliente con
  insights fiscales, a nivel hogar y cuenta. La frontera se movió hacia tu modelo
  asesor+cliente → hay que igualar el *table-stake* (briefing por cliente) y ganar con
  lo que ellos no dan (Caja de Cristal, anti-pánico, forense).
- **WhatsApp = "infraestructura core" de la fintech en LatAm.** México: 2M+ catálogos
  de negocio activos, integración con CoDi en camino. → Tu canal hoy (Telegram) no es
  donde está el mexicano promedio.

---

## 0.5 Estado real tras auditar el código (sep-2026)

El código (v0.23.1→**0.24.0**) ya rebasó el doc de mercado de julio. Corrección honesta:

- ✅ **B2** (briefing por cliente) y ✅ **B4** (estado narrativo mensual) **ya existían**
  (v0.11/v0.20). El portal ya muestra "¿Qué pasó con tu dinero?".
- 🟡 **C1** (canastas del asesor) existe; **falta ligarlas al Deep Scan**.
- ✅ **A2** (arnés anti-alucinación) **entregado** en v0.24.0 + se corrigió un bug que
  ocultaba 13/42 tests al CI.
- ✅ **A1** (copiloto agéntico) **entregado** en v0.25.0: motores como herramientas +
  bucle tool-use + guardián de números; degrada sin clave. Ya compara dos acciones.
- ✅ **B3** (anti-pánico **medible**) **entregado** en v0.26.0: `coaching.panic_check`
  puro y testeado + bitácora (`panic_log`) + panel del asesor con "$ pérdida evitada".
  *(La intervención en la UI ya existía; ahora es DRY y medible.)*
- ✅ **C4** (panel de salud/observabilidad) **entregado** en v0.27.0: `report/health.py`
  + sección "🩺 Salud del sistema" en 🛰️ Fuentes.
- ❌ Siguen nuevos: **A3 (RAG citas), B1 (WhatsApp), C2 (2FA), C3 (PDF/fiscal SAT)**.

---

## 1. Tema A — El copiloto que **orquesta** (el foso de confianza con IA)

### A1. 🧠 Copiloto agéntico (tool-calling sobre tus motores) — *el salto de nivel*
Evolucionar `copilot/copilot.py` de "detección de intención + plantilla" a un
**orquestador con herramientas**: expones cada motor (`scoring/composite`,
`valuation/dcf`, `forensic/scores`, `models/risk`, `portfolio/optimizer`,
`retirement/planner`, `screener/deepscan`, `advisor/profile`) como una *tool* que
Claude puede invocar (Anthropic tool-use / tool_runner). El LLM **planea y compone**,
los motores calculan. Así responde preguntas compuestas que hoy no puede:
*"compara NVDA vs AMD en forense y valoración y dime cuál le va a un cliente conservador"*.
- **Sube de nivel porque:** pasa de "chat que explica una cosa" a "analista que
  encadena varios motores" — exactamente lo que hacen Aladdin/GS Copilot, pero
  auditable. La regla de oro se mantiene: **orquesta, nunca calcula.**
- **Construye sobre:** `copilot/`, `advisor/profile.py` (ya integra varios motores).
- **Esfuerzo:** medio-alto · **Impacto:** muy alto.

### A2. ✅ Arnés de evaluación anti-alucinación (en CI)
Suite de preguntas *golden* Q→A donde **cada número de la respuesta debe trazar a un
motor**; corre junto a los 42 tests en `ci.yml`. Un chequeo que falla si el copiloto
inventa una cifra o cita un número que ningún motor produjo.
- **Sube de nivel porque:** convierte "cero alucinación numérica" de promesa a
  **garantía verificada en cada push** — es un argumento de venta anti-AI-washing.
- **Construye sobre:** `tests/`, `copilot/`. **Prerrequisito real de A1** (sin esto,
  darle herramientas al LLM es más riesgo).
- **Esfuerzo:** medio · **Impacto:** alto.

### A3. 🔮 Caja de Cristal textual con citas (RAG sobre 10-K de EDGAR)
El copiloto cita el **párrafo oficial** de riesgos/MD&A del 10-K cuando habla de una
empresa ("según el 10-K 2025, sección Riesgos: …"). Ya bajas *companyfacts*; falta el
texto narrativo del filing + embeddings + recuperación con cita.
- **Sube de nivel porque:** es la "Caja de Cristal" de tu doc, pero textual y con
  fuente oficial verificable. Nadie retail lo da.
- **Construye sobre:** `data/edgar.py`, `report/plain.py`.
- **Esfuerzo:** medio-alto · **Impacto:** alto.

---

## 2. Tema B — Dueños del canal mexicano y del **hábito**

### B1. 📲 WhatsApp (Business API) para briefing, alertas y copiloto
Llevar el briefing diario, las alertas y el copiloto conversacional a **WhatsApp**
(hoy solo Telegram). En México WhatsApp es *core infrastructure*, no un extra.
- **Construye sobre:** `alerts/engine.py`, `report/briefing.py`, `copilot/` (misma
  lógica, nuevo transporte). Empezar por notificaciones salientes (más simple), luego
  conversación entrante.
- **Esfuerzo:** medio · **Impacto:** muy alto (es acceso al mercado real).

### B2. ☀️ Briefing diario **por cliente** ("¿Qué pasó con TU dinero?") — *quick win*
La portada del portal muestra, cada mañana: qué se movió de SUS posiciones, por qué
(noticias tipadas), y qué viene. Tu propio doc lo marca *"esfuerzo bajo, impacto
brutal"* — y ahora es *table-stake* (Cortex ya lo da a asesores).
- **Construye sobre:** `report/briefing.py` (`client_briefing` ya existe),
  `clients/manager.py`, `cliente.py`.
- **Esfuerzo:** bajo · **Impacto:** muy alto.

### B3. 🧘 Copiloto anti-pánico **con bitácora medible**
Cuando el régimen entra en turbulencia y el cliente intenta vender con pérdida, la app
lo frena 10 s con números reales ("vender hoy cristaliza −$4,200…"). Nuevo: **registrar
cada intervención** y mostrar al asesor un panel de "decisiones de pánico evitadas".
- **Sube de nivel porque:** el hueco emocional está documentado y **nadie lo ataca**;
  la bitácora lo vuelve un activo de datos y una historia de valor demostrable.
- **Construye sobre:** `models/regime.py`, `clients/manager.py`.
- **Esfuerzo:** medio · **Impacto:** alto (foso emocional).

### B4. 📖 Estado de cuenta **narrativo** mensual — *quick win*
El mes del cliente contado en palabras: "Ganaste $3,400. Tu mejor decisión fue no
vender en abril. JNJ te pagó dividendos como renta."
- **Construye sobre:** `report/briefing.py` (`monthly_story`), `report/plain.py`.
- **Esfuerzo:** bajo-medio · **Impacto:** alto.

---

## 3. Tema C — De herramienta a **producto** (grado producto)

### C1. 🧺 Canastas del asesor ↔ Deep Scan (copy-del-asesor con respaldo)
Publicar "canastas" con tesis en español y botón *"Invertir en esta canasta"*, y
**auto-generarlas/refrescarlas desde los ganadores del deep scan** (con su validación
walk-forward como respaldo). Copy-trading, pero copias a TU asesor con su porqué y su
backtest — no a un extraño con suerte.
- **Construye sobre:** `screener/deepscan.py`, `clients/manager.py` (`create_basket`).
- **Esfuerzo:** medio · **Impacto:** alto.

### C2. 🔐 Seguridad para clientes reales (bloqueante pre-lanzamiento)
PIN de 6+ dígitos, 2FA ligero por Telegram/WhatsApp/correo, y expiración de sesión.
- **Construye sobre:** `clients/manager.py`, `cliente.py`.
- **Esfuerzo:** medio · **Impacto:** alto (bloqueante para abrir a clientes reales).

### C3. 📄 Reporte PDF profesional + 🧾 Reporte fiscal MX (SAT)
PDF real (WeasyPrint/reportlab; hay skill `pdf`) y resumen anual de G/P realizadas para
el SAT (ya congelas precio de entrada → tienes la base).
- **Construye sobre:** `report/`, `clients/manager.py` (movimientos/órdenes).
- **Esfuerzo:** medio · **Impacto:** medio-alto (necesario con clientes reales).

### C4. 🩺 Panel de salud / observabilidad
Una página que muestra frescura de datos, tasa de failover por proveedor, candados de
integridad disparados, estado de tests/CI y crecimiento del historial de scores.
- **Sube de nivel porque:** auditabilidad **operativa** — coherente con "no nos creas,
  revísanos" y necesario para operar con confianza al escalar.
- **Construye sobre:** `data/quality.py`, `data/dbx.py`, `jobs/daily_update.py`.
- **Esfuerzo:** bajo-medio · **Impacto:** medio.

---

## 4. Tema D — Negocio y escala (decisiones, no solo código)

### D1. 🏛️ Producto monetizable: API + tiers + datos con licencia + dinero real
FastAPI envolviendo los motores; tiers free/premium (alertas, PDF, screeners
ilimitados = premium); **proveedor de datos con licencia** (FMP/Polygon) porque
yfinance es zona gris para monetizar; y la decisión mayor: alianza con broker regulado
(GBM/Alpaca) + registro CNBV para mover dinero real.
- **Esfuerzo:** alto · **Impacto:** estratégico. (Fase 5 del Plan Maestro.)

> ⚖️ Recordatorio de compliance: cuanto más recomiendas al público, más te acercas a
> asesoría regulada (CNBV). Antes de cobrar o abrir más allá de conocidos: abogado
> financiero. Los disclaimers no se quitan.

---

## 5. Matriz impacto × esfuerzo (por dónde entrar)

| | **Esfuerzo bajo** | **Esfuerzo medio** | **Esfuerzo alto** |
|---|---|---|---|
| **Impacto muy alto** | **B2** briefing por cliente | **B1** WhatsApp | **A1** copiloto agéntico |
| **Impacto alto** | **B4** estado narrativo | **A2** eval · **B3** anti-pánico · **C1** canastas · **C2** seguridad | **A3** RAG con citas |
| **Impacto medio** | **C4** observabilidad | **C3** PDF/fiscal | **D1** negocio/escala |

## 6. Secuencia recomendada

- **Sprint 1 — "Enganche + confianza en la IA" (rápido):** B2 (briefing por cliente)
  + B4 (estado narrativo) + A2 (arnés anti-alucinación). Bajo esfuerzo, valor de
  cliente inmediato, y blinda la IA antes de darle poder.
- **Sprint 2 — "El copiloto que orquesta + el canal":** A1 (copiloto agéntico) + B1
  (WhatsApp). **Aquí está el verdadero salto de nivel.**
- **Sprint 3 — "Armas únicas + grado producto":** B3 (anti-pánico con bitácora) + C1
  (canastas↔deep scan) + C2 (seguridad).
- **Continuo / decisión:** A3 (RAG citas), C3 (PDF/fiscal), C4 (observabilidad),
  D1 (negocio).

**Por dónde empezaría yo:** B2 + A2 en la primera semana (ya existen `client_briefing`
y 42 tests: es cablear y blindar → valor visible ya), y en paralelo **prototipar A1**,
que es el diferenciador que define 2026.

---

## Fuentes (investigación sep-2026)

- [Deloitte — The agentic AI productivity wave is heading for wealth management](https://www.deloitte.com/us/en/insights/industry/financial-services/financial-services-industry-predictions/2026/agentic-ai-wealth-management-productivity.html)
- [InvestSuite — Top Wealth Management Trends 2026: Agentic AI](https://www.investsuite.com/insights/blogs/top-wealth-management-trends-in-2026-the-shift-to-agentic-ai-and-private-markets)
- [InvestmentNews — Robinhood brings AI-powered Cortex to RIAs on TradePMR](https://www.investmentnews.com/transformation/robinhood-brings-ai-powered-cortex-to-rias-on-tradepmr/266861)
- [Robinhood — Cortex Digests](https://robinhood.com/gb/en/learn/articles/cortex-digests-is-here/)
- [Emerging Fintech — WhatsApp: The OS Powering Latin America's Fintech Revolution](https://www.emergingfintech.co/p/whatsapp-the-operating-system-powering)
- [Mexico Business News — WhatsApp, AI Power Next Wave of Digital Transformation](https://mexicobusiness.news/ecommerce/news/whatsapp-ai-power-next-wave-digital-transformation)
