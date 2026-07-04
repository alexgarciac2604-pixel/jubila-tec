# 📈 Jubila-Tec Terminal

Terminal financiera de nivel institucional **que cualquier persona entiende**.
Análisis de acciones, portafolios, planificación de jubilación, backtesting
honesto y un copiloto conversacional — con datos públicos, fallback sintético
determinista y cero promesas de rendimiento.

> ⚠️ Análisis informativo y educativo. **No es asesoría financiera personalizada.**

---

## 🧱 Los tres pisos

| Piso | Qué hace |
|---|---|
| **🤖 Capa humana** | Copiloto conversacional, briefing diario, modo Simple/Pro, escenarios narrados ("en un día malo de 1 entre 20…") |
| **🧠 Inteligencia** | Eventos tipados de noticias (recorte de guía, M&A…), régimen de mercado GMM que adapta los pesos del score, SEC EDGAR (10-K oficiales + insiders) |
| **⚙️ Motores** | Fundamental (DuPont, ROIC), valoración (DCF, reverse, Monte Carlo), técnico, forense (Altman/Piotroski/Beneish/Sloan), riesgo (VaR/CVaR/Cornish-Fisher, Omega/Ulcer/Calmar), portafolio (Máx. Sharpe, **HRP**, risk parity, stress tests), jubilación (colas gordas, reglas de retiro), backtesting con IC bootstrap, ½ Kelly |

**Regla de oro:** el copiloto traduce, **nunca calcula** — cada número sale de
motores auditables con tests numéricos.

## 🗺️ Las 13 páginas

🌐 Dashboard (régimen + briefing) · 🤖 Copiloto · 🔍 Análisis de Acción (8 pestañas)
· 🗺️ Mercados · 🐤 Underdog · 💼 Portafolio (+🇲🇽 riesgo cambiario) · 🎯 Jubilación
· 🧪 Backtesting · 🌍 Macro & Geopolítica · 📰 Noticias · 🔔 Alertas · 🛰️ Fuentes
· 📚 Modelos & Compliance

## 🚀 Instalación (Windows / PowerShell)

```powershell
cd C:\Users\Alex\Claude\Projects\Jubila-tec
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Abre en `http://localhost:8501`. **Funciona sin internet ni claves** (datos
sintéticos deterministas marcados 🧪); con internet usa yfinance → Stooq →
SEC EDGAR con failover automático.

### Claves opcionales (`.env`, ver `.env.example`)

| Clave | Activa |
|---|---|
| `ANTHROPIC_API_KEY` | Copiloto conversacional completo (Claude) |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Alertas y briefing a tu Telegram |
| `FRED_API_KEY` | Macro real (gratis en fred.stlouisfed.org) |
| `NEWSAPI_KEY` | Noticias enriquecidas |

### Actualización diaria automática

```powershell
schtasks /Create /SC DAILY /ST 08:30 /TN "JubilaTec Diario" /TR "C:\Users\Alex\Claude\Projects\Jubila-tec\actualizacion_diaria.bat"
```

Cada mañana: refresca datos, recalcula y persiste los scores del universo
(el historial crece día a día en SQLite), evalúa alertas y envía el briefing.
También hay botón **🔄 Actualizar datos** en la app. Bitácora: `update.log`.

### Tests

```powershell
.\.venv\Scripts\python.exe tests\test_smoke.py
```

23 tests: valores de oro verificados a mano (DCF), propiedades invariantes
(CVaR ≥ VaR, pesos suman 1, "una crisis nunca es positiva") y determinismo.

## 🧭 Filosofía de calidad

1. **Validado o no existe** — el backtesting declara sus sesgos en pantalla.
2. **Explicable** — cada score con desglose, fórmula y referencia (📚 Modelos).
3. **Dos registros** — modo Simple y Pro: misma verdad, dos lenguajes.
4. **Degradación elegante** — sin red, sin clave o con la SEC caída, la app
   nunca se rompe; degrada y lo dice.
5. **Reproducible** — seeds fijas y versión del motor en cada reporte.

## 🗂️ Estructura

```
app.py                  shell Streamlit (nav, tape, routing)
jobs/daily_update.py    actualización diaria programable
src/
├── config.py           settings, universo, sectores
├── data/               market_data (failover), edgar, quality, store, sintético
├── copilot/            conversación (LLM opcional, nunca calcula)
├── fundamental/ valuation/ technical/ forensic/ models/ (risk, regime,
│   sizing, stress, fx) portfolio/ retirement/ backtest/
├── news/ (feed, sentimiento, eventos) macro/ geopolitics/
├── underdog/ scoring/ alerts/ report/ (reporte, briefing)
└── views/              13 páginas + componentes
tests/test_smoke.py     23 tests deterministas
PLAN_MAESTRO.md         visión, roadmap y backlog priorizado
DEPLOY.md               guía de deploy (Streamlit Cloud + Vercel)
```

## ⚖️ Compliance

Solo información pública y legal. Lenguaje no imperativo ("el modelo indica").
Sin promesas de rendimiento. Disclaimer visible en toda la app y cada reporte.
Para uso comercial, migrar a un proveedor de datos con licencia (ver PLAN_MAESTRO, Fase 5).
