"""Configuración global: settings, universos, sectores, disclaimer."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

try:  # .env opcional
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def get_secret(name: str) -> str:
    """Lee una clave de entorno o de st.secrets (Streamlit Cloud).

    En la nube, los secrets viven en st.secrets y no siempre llegan como
    variables de entorno; localmente vienen del .env. Este helper cubre ambos.
    """
    v = os.getenv(name, "")
    if v:
        return v
    try:
        import streamlit as st
        return str(st.secrets.get(name, "") or "")
    except Exception:
        return ""


DISCLAIMER = (
    "⚠️ AL-X ofrece análisis informativo y educativo con datos públicos. "
    "No es asesoría financiera personalizada ni garantiza rendimientos. "
    "Cada modelo tiene supuestos y limitaciones (ver 📚 Modelos & Compliance)."
)

TICKER_NAMES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "GOOGL": "Alphabet",
    "AMZN": "Amazon", "META": "Meta", "TSLA": "Tesla", "AVGO": "Broadcom",
    "JPM": "JPMorgan", "BAC": "Bank of America", "V": "Visa", "MA": "Mastercard",
    "JNJ": "Johnson & Johnson", "PFE": "Pfizer", "UNH": "UnitedHealth", "LLY": "Eli Lilly",
    "XOM": "Exxon Mobil", "CVX": "Chevron", "WMT": "Walmart", "PG": "Procter & Gamble",
    "KO": "Coca-Cola", "PEP": "PepsiCo", "HD": "Home Depot", "MCD": "McDonald's",
    "DIS": "Disney", "NFLX": "Netflix", "CAT": "Caterpillar", "BA": "Boeing",
    "GE": "GE Aerospace", "LMT": "Lockheed Martin", "SPCX": "SpaceX", "T": "AT&T", "VZ": "Verizon",
    "SPY": "S&P 500 ETF", "QQQ": "Nasdaq 100 ETF", "DIA": "Dow Jones ETF", "GLD": "Gold ETF",
}

SECTOR_OF = {
    "AAPL": "Tecnología", "MSFT": "Tecnología", "NVDA": "Tecnología", "AVGO": "Tecnología",
    "GOOGL": "Comunicación", "META": "Comunicación", "NFLX": "Comunicación",
    "T": "Comunicación", "VZ": "Comunicación", "DIS": "Comunicación",
    "AMZN": "Consumo Disc.", "TSLA": "Consumo Disc.", "HD": "Consumo Disc.", "MCD": "Consumo Disc.",
    "JPM": "Financiero", "BAC": "Financiero", "V": "Financiero", "MA": "Financiero",
    "JNJ": "Salud", "PFE": "Salud", "UNH": "Salud", "LLY": "Salud",
    "XOM": "Energía", "CVX": "Energía",
    "WMT": "Consumo Básico", "PG": "Consumo Básico", "KO": "Consumo Básico", "PEP": "Consumo Básico",
    "CAT": "Industrial", "BA": "Industrial", "GE": "Industrial", "LMT": "Industrial",
    "SPCX": "Industrial",
}

# nombre común (minúsculas, sin acentos) → ticker
NAME_TO_TICKER = {
    "apple": "AAPL", "spacex": "SPCX", "space x": "SPCX", "microsoft": "MSFT", "nvidia": "NVDA", "google": "GOOGL",
    "alphabet": "GOOGL", "amazon": "AMZN", "facebook": "META", "meta platforms": "META",
    "tesla": "TSLA", "broadcom": "AVGO", "jpmorgan": "JPM", "jp morgan": "JPM",
    "bank of america": "BAC", "visa": "V", "mastercard": "MA",
    "johnson": "JNJ", "pfizer": "PFE", "unitedhealth": "UNH", "eli lilly": "LLY",
    "lilly": "LLY", "exxon": "XOM", "chevron": "CVX", "walmart": "WMT",
    "procter": "PG", "coca cola": "KO", "coca-cola": "KO", "pepsi": "PEP",
    "home depot": "HD", "mcdonalds": "MCD", "mcdonald": "MCD", "disney": "DIS",
    "netflix": "NFLX", "caterpillar": "CAT", "boeing": "BA",
    "general electric": "GE", "lockheed": "LMT", "at&t": "T", "verizon": "VZ",
}


DEFAULT_UNIVERSE = [t for t in SECTOR_OF]
TAPE_TICKERS = ["SPY", "QQQ", "DIA", "AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "JPM", "XOM", "GLD"]

# universo AMPLIADO para el screener nocturno (S&P-100 aprox + SPCX)
SCREENER_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "BRK-B",
    "LLY", "JPM", "V", "UNH", "XOM", "MA", "JNJ", "PG", "HD", "COST", "MRK",
    "ABBV", "CVX", "CRM", "AMD", "PEP", "KO", "WMT", "BAC", "NFLX", "ACN",
    "TMO", "MCD", "CSCO", "ABT", "LIN", "ADBE", "ORCL", "DIS", "WFC", "INTC",
    "VZ", "CAT", "QCOM", "IBM", "GE", "TXN", "CMCSA", "AMGN", "INTU", "NOW",
    "PFE", "UNP", "PM", "SPGI", "HON", "RTX", "NKE", "LOW", "T", "UPS",
    "COP", "SCHW", "BA", "MS", "ELV", "BLK", "GS", "AXP", "DE", "BKNG",
    "MDT", "LMT", "SBUX", "PLD", "ADP", "GILD", "BMY", "MDLZ", "ADI", "TJX",
    "MMC", "CVS", "SYK", "VRTX", "AMT", "C", "ZTS", "CI", "MO", "SO",
    "TMUS", "CB", "REGN", "PGR", "BSX", "ETN", "EOG", "SLB", "DUK", "CL",
    "FDX", "ITW", "EMR", "NOC", "SPCX",
]

RISK_FREE = 0.042  # tasa libre de riesgo anual por defecto


@dataclass(frozen=True)
class Settings:
    newsapi_key: str = ""
    fred_api_key: str = ""
    force_sample: bool = False

    def has_news(self) -> bool:
        return bool(self.newsapi_key)

    def has_fred(self) -> bool:
        return bool(self.fred_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        newsapi_key=get_secret("NEWSAPI_KEY"),
        fred_api_key=get_secret("FRED_API_KEY"),
        force_sample=os.getenv("JT_FORCE_SAMPLE", "0") == "1",
    )
