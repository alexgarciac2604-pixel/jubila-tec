"""Feed de noticias con failover: NewsAPI → yfinance → sintético determinista."""
from __future__ import annotations

from src.data import sample_data as sd
from src.data.market_data import using_sample
from src.news.events import classify_event
from src.news.sentiment import label, score_text
from src.utils.cache import ttl_cache

try:
    import yfinance as yf
    _HAS_YF = True
except Exception:
    _HAS_YF = False


def _newsapi_items(ticker: str, n: int) -> list[dict]:
    """Noticias reales de NewsAPI (requiere NEWSAPI_KEY). [] si falla."""
    from src.config import TICKER_NAMES, get_secret
    key = get_secret("NEWSAPI_KEY")
    if not key:
        return []
    try:
        import requests
        name = TICKER_NAMES.get(ticker.upper(), ticker)
        r = requests.get(
            "https://newsapi.org/v2/everything",
            params={"q": f'"{name}"', "sortBy": "publishedAt",
                    "pageSize": n, "language": "en", "apiKey": key},
            timeout=8,
        )
        if r.status_code != 200:
            return []
        return [{
            "title": a.get("title", ""),
            "publisher": (a.get("source") or {}).get("name", ""),
            "link": a.get("url", ""),
            "date": str(a.get("publishedAt", ""))[:10],
        } for a in r.json().get("articles", []) if a.get("title")]
    except Exception:
        return []


@ttl_cache(ttl=900)
def get_news(ticker: str, n: int = 8) -> list[dict]:
    from src.config import get_settings
    items: list[dict] = []
    if not get_settings().force_sample:
        items = _newsapi_items(ticker, n)          # 1º NewsAPI (si hay clave)
    if not items and not using_sample() and _HAS_YF:
        try:
            raw = yf.Ticker(ticker).news or []
            for it in raw[:n]:
                c = it.get("content", it)
                title = c.get("title", "")
                if title:
                    items.append({
                        "title": title,
                        "publisher": (c.get("provider") or {}).get("displayName", "") if isinstance(c.get("provider"), dict) else str(c.get("publisher", "")),
                        "link": (c.get("canonicalUrl") or {}).get("url", "") if isinstance(c.get("canonicalUrl"), dict) else str(c.get("link", "")),
                        "date": str(c.get("pubDate", ""))[:10],
                    })
        except Exception:
            items = []
    if not items:
        items = sd.sample_news(ticker, n)
    for it in items:
        s = score_text(it["title"])
        if "tone_hint" in it:  # el sintético trae tono conocido
            s = (s + it.pop("tone_hint")) / 2
        ev = classify_event(it["title"])
        if ev:
            s = 0.4 * s + 0.6 * ev["dir"]   # un evento tipado pesa más que el tono
        it["event"] = ev
        it["sentiment"] = round(s, 2)
        it["label"] = label(s)
    return items


def aggregate_sentiment(items: list[dict]) -> dict:
    if not items:
        return {"avg": 0.0, "label": "🟡 neutral", "n": 0}
    avg = sum(i["sentiment"] for i in items) / len(items)
    return {"avg": round(avg, 2), "label": label(avg), "n": len(items)}
