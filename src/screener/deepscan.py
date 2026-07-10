"""🔭 Deep Scan AL-X: calificación cuantitativa del S&P 500 por bloques.

Inspirado en los sistemas institucionales (Zacks Rank, Morningstar Quant,
Seeking Alpha Quant): procesar TODO el universo por lotes, estudiar el
histórico de cada acción y emitir una etiqueta de recomendación.

Nuestro toque honesto: además del score, cada acción se VALIDA contra su
propio pasado (walk-forward): "cuando esta acción estuvo en condiciones
parecidas, ¿qué pasó los 3 meses siguientes?" → la confianza no es opinión,
es su historial.

Etiquetas: 🟢 Comprar · 🔵 Acumular · 🟡 Esperar · 🔴 Evitar
"""
from __future__ import annotations

import json
import os
from datetime import date


def _path() -> str:
    env = os.getenv("JT_DEEPSCAN_PATH")
    if env:
        return env
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.makedirs(os.path.join(root, "data"), exist_ok=True)
    return os.path.join(root, "data", "deepscan.json")


def _sp500_cache() -> str:
    return os.path.join(os.path.dirname(_path()), "sp500.json")


_IVV_CSV = ("https://www.ishares.com/us/products/239726/"
            "ishares-core-sp-500-etf/1467271812596.ajax"
            "?fileType=csv&fileName=IVV_holdings&dataType=fund")


def _parse_ivv_csv(texto: str) -> list[str]:
    """Tickers de renta variable del CSV oficial de posiciones de IVV."""
    import csv
    import io
    lineas = texto.splitlines()
    inicio = next((i for i, ln in enumerate(lineas)
                   if ln.startswith("Ticker")), None)
    if inicio is None:
        return []
    tks = set()
    for fila in csv.DictReader(io.StringIO("\n".join(lineas[inicio:]))):
        t = (fila.get("Ticker") or "").strip()
        clase = (fila.get("Asset Class") or "").strip().lower()
        if t and t.isascii() and t not in {"-", "USD"} and "equity" in clase:
            tks.add(t.replace(".", "-").replace(" ", ""))
    return sorted(tks)


def sp500_universe() -> list[str]:
    """S&P 500 en cadena de confianza:
    1º BlackRock (CSV oficial diario de posiciones del ETF IVV),
    2º Wikipedia (respaldo), 3º universo estático. Cacheado con su fuente."""
    try:
        with open(_sp500_cache(), encoding="utf-8") as fh:
            data = json.load(fh)
            if (len(data.get("tickers", [])) > 300
                    and data.get("date") == str(date.today())):
                return data["tickers"]
    except Exception:
        pass

    def _guardar(tks: list[str], fuente: str) -> list[str]:
        with open(_sp500_cache(), "w", encoding="utf-8") as fh:
            json.dump({"date": str(date.today()), "source": fuente,
                       "tickers": tks}, fh)
        return tks

    try:
        import requests
        r = requests.get(_IVV_CSV, timeout=20,
                         headers={"User-Agent": "AL-X research"})
        tks = _parse_ivv_csv(r.text) if r.status_code == 200 else []
        if len(tks) > 400:
            return _guardar(tks, "iShares IVV (BlackRock)")
    except Exception:
        pass
    try:
        import re
        import requests
        r = requests.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
                         timeout=15, headers={"User-Agent": "AL-X research"})
        tks = re.findall(r'href="/wiki/[^"]+"[^>]*>([A-Z]{1,5}(?:\.[A-Z])?)</a></td>',
                         r.text)
        tks = sorted({t.replace(".", "-") for t in tks if t.isupper()})
        if len(tks) > 300:
            return _guardar(tks, "Wikipedia (respaldo)")
    except Exception:
        pass
    from src.config import SCREENER_UNIVERSE
    return list(SCREENER_UNIVERSE)


def own_history_validation(close) -> dict:
    """Walk-forward sobre el propio histórico: cortes mensuales de ~3 años.

    Señal 'en condiciones como hoy': momentum 12-1 positivo Y precio sobre
    su SMA200. Mide el retorno a 3 meses después de cada señal.
    """
    import numpy as np
    c = close.dropna()
    if len(c) < 320:
        return {"n": 0, "win_rate": None, "avg_fwd_3m": None}
    sma200 = c.rolling(200).mean()
    hoy_senal = bool(c.iloc[-1] > sma200.iloc[-1]
                     and c.iloc[-22] / c.iloc[-252] > 1.0)
    fwd = []
    for i in range(252, len(c) - 63, 21):          # cortes mensuales
        senal = (c.iloc[i] > sma200.iloc[i]
                 and c.iloc[i - 21] / c.iloc[max(i - 252, 0)] > 1.0)
        if senal == hoy_senal:                     # condiciones parecidas a hoy
            fwd.append(float(c.iloc[i + 63] / c.iloc[i] - 1.0))
    if len(fwd) < 6:
        return {"n": len(fwd), "win_rate": None, "avg_fwd_3m": None}
    fwd_a = np.array(fwd)
    return {"n": len(fwd), "win_rate": round(float((fwd_a > 0).mean()) * 100),
            "avg_fwd_3m": round(float(fwd_a.mean()) * 100, 1),
            "senal_hoy": hoy_senal}


def deep_label(score: int, f_score: int | None, win_rate: int | None) -> dict:
    """Score + salud + historial propio → etiqueta con confianza y porqué."""
    if f_score is not None and f_score <= 1:
        return {"label": "Evitar", "emoji": "🔴", "confianza": "alta",
                "razon": f"F-Score {f_score}/9: salud financiera crítica — "
                         "el paper de Piotroski manda evitarlas a toda costa."}
    if score >= 70 and (win_rate or 0) >= 60:
        return {"label": "Comprar", "emoji": "🟢", "confianza": "alta",
                "razon": f"Score {score}/100 y su propio historial respalda: "
                         f"en condiciones como hoy ganó el {win_rate}% de "
                         "las veces a 3 meses."}
    if score >= 70:
        return {"label": "Acumular", "emoji": "🔵", "confianza": "media",
                "razon": f"Score {score}/100 sólido, pero su historial en "
                         "condiciones como hoy no es concluyente — entrar "
                         "por partes."}
    if score >= 45:
        return {"label": "Esperar", "emoji": "🟡", "confianza": "media",
                "razon": f"Score {score}/100: ni barata ni con impulso "
                         "claro. Paciencia."}
    return {"label": "Evitar", "emoji": "🔴",
            "confianza": "media" if (win_rate or 50) > 45 else "alta",
            "razon": f"Score {score}/100: fundamentos o precio en contra."}


def analyze_deep(ticker: str) -> dict | None:
    """Fila del Deep Scan: screener + F-Score + validación histórica propia."""
    from src.data.market_data import get_fundamentals, get_history
    from src.forensic.scores import piotroski_f
    from src.screener.engine import screen_ticker

    row = screen_ticker(ticker)
    if row is None:
        return None
    try:
        fs = piotroski_f(get_fundamentals(ticker)).get("score")
    except Exception:
        fs = None
    val = own_history_validation(get_history(ticker, period="5y").Close)
    lab = deep_label(row.get("score", 0), fs, val.get("win_rate"))
    return {**row, "f_score": fs, **{k: val.get(k) for k in
            ("n", "win_rate", "avg_fwd_3m")}, **lab}


# ------------------------------------------------ procesamiento por bloques --
def load_state() -> dict:
    try:
        with open(_path(), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"date": "", "done": {}, "pending": [], "universe_n": 0}


def save_state(st: dict) -> None:
    with open(_path(), "w", encoding="utf-8") as fh:
        json.dump(st, fh, ensure_ascii=False)


def start_or_resume(universe: list[str] | None = None,
                    force: bool = False) -> dict:
    """Prepara el estado: hoy se retoma; force=True reinicia SIEMPRE."""
    st = load_state()
    hoy = str(date.today())
    if force or st.get("date") != hoy or not (st.get("pending") or st.get("done")):
        uni = universe or sp500_universe()
        st = {"date": hoy, "done": {}, "pending": list(uni),
              "universe_n": len(uni)}
        save_state(st)
    return st


def run_block(block: int = 20, analyze_fn=None) -> dict:
    """Procesa el siguiente bloque y guarda. Devuelve el estado (resumible)."""
    fn = analyze_fn or analyze_deep
    st = start_or_resume()
    lote, st["pending"] = st["pending"][:block], st["pending"][block:]
    for t in lote:
        try:
            r = fn(t)
            if r:
                st["done"][t] = r
        except Exception:
            continue
    save_state(st)
    return st


def run_full(universe: list[str] | None = None, block: int = 25,
             analyze_fn=None, log=print, force: bool = False) -> dict:
    """Corre TODO por bloques (job semanal). force=True regenera desde cero."""
    st = start_or_resume(universe, force=force)
    while st["pending"]:
        st = run_block(block, analyze_fn)
        log(f"deepscan: {len(st['done'])}/{st['universe_n']}")
    return st
