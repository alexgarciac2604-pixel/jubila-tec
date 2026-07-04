"""Motor forense: Altman Z, Piotroski F, Beneish M (aprox.), accruals de Sloan.

Referencias: Altman (1968), Piotroski (2000), Beneish (1999), Sloan (1996).
Beneish se calcula en versión reducida (5 índices) por disponibilidad de datos.
"""
from __future__ import annotations


def _d(a, b):
    try:
        return a / b if b else None
    except TypeError:
        return None


def altman_z(f: dict) -> dict:
    ta = f.get("total_assets") or 1
    wc = (f.get("current_assets") or 0) - (f.get("current_liabilities") or 0)
    z = (1.2 * wc / ta
         + 1.4 * (f.get("retained_earnings") or 0) / ta
         + 3.3 * (f.get("ebit") or 0) / ta
         + 0.6 * (f.get("market_cap") or 0) / (f.get("total_liabilities") or 1)
         + 1.0 * (f.get("revenue") or 0) / ta)
    zone = "segura" if z > 2.99 else ("gris" if z > 1.81 else "peligro")
    return {"z": round(z, 2), "zone": zone}


def piotroski_f(f: dict) -> dict:
    ta, tap = f.get("total_assets"), f.get("total_assets_prev")
    ni, nip = f.get("net_income"), f.get("net_income_prev")
    roa = _d(ni, ta)
    roa_prev = _d(nip, tap)
    cfo = f.get("cfo")
    checks = {
        "ROA positivo": roa is not None and roa > 0,
        "CFO positivo": cfo is not None and cfo > 0,
        "ROA creciente": roa is not None and roa_prev is not None and roa > roa_prev,
        "CFO > utilidad (calidad)": cfo is not None and ni is not None and cfo > ni,
        "Menos deuda LP": (f.get("lt_debt") or 0) <= (f.get("lt_debt_prev") or 0),
        "Liquidez mejora": (_d(f.get("current_assets"), f.get("current_liabilities")) or 0)
                           >= (_d(f.get("current_assets_prev"), f.get("current_liabilities_prev")) or 0),
        "Sin dilución": (f.get("shares") or 0) <= (f.get("shares_prev") or 0) * 1.005,
        "Margen bruto mejora": (_d(f.get("gross_profit"), f.get("revenue")) or 0)
                               >= (_d(f.get("gross_profit_prev"), f.get("revenue_prev")) or 0),
        "Rotación mejora": (_d(f.get("revenue"), ta) or 0) >= (_d(f.get("revenue_prev"), tap) or 0),
    }
    return {"score": sum(checks.values()), "max": 9, "checks": checks}


def beneish_m(f: dict) -> dict:
    """Versión reducida: DSRI, GMI, AQI(SGI proxy), SGI, DEPI. Umbral -1.78."""
    dsri = _d(_d(f.get("receivables"), f.get("revenue")),
              _d(f.get("receivables_prev"), f.get("revenue_prev"))) or 1.0
    gm = _d(f.get("gross_profit"), f.get("revenue")) or 0.3
    gmp = _d(f.get("gross_profit_prev"), f.get("revenue_prev")) or gm
    gmi = gmp / gm if gm else 1.0
    sgi = _d(f.get("revenue"), f.get("revenue_prev")) or 1.0
    dep = _d(f.get("depreciation"), f.get("total_assets")) or 0.03
    depp = _d(f.get("depreciation_prev"), f.get("total_assets_prev")) or dep
    depi = depp / dep if dep else 1.0
    sga = _d(_d(f.get("sga"), f.get("revenue")), _d(f.get("sga_prev"), f.get("revenue_prev"))) or 1.0
    # coeficientes Beneish (1999) sobre los índices disponibles + intercepto
    m = -4.84 + 0.92 * dsri + 0.528 * gmi + 0.892 * sgi + 0.115 * depi - 0.172 * sga
    return {"m": round(m, 2), "flag": m > -1.78,
            "note": "Versión reducida (5 de 8 índices) por disponibilidad de datos."}


def sloan_accruals(f: dict) -> dict:
    ni, cfo, ta = f.get("net_income"), f.get("cfo"), f.get("total_assets")
    ratio = _d((ni or 0) - (cfo or 0), ta)
    level = "bajo" if ratio is not None and abs(ratio) < 0.05 else (
        "moderado" if ratio is not None and abs(ratio) < 0.10 else "alto")
    return {"accruals": round(ratio, 4) if ratio is not None else None, "level": level}


def full_forensic(f: dict) -> dict:
    alt = altman_z(f)
    pio = piotroski_f(f)
    ben = beneish_m(f)
    slo = sloan_accruals(f)
    pts = 0
    pts += {"segura": 30, "gris": 15, "peligro": 0}[alt["zone"]]
    pts += round(30 * pio["score"] / 9)
    pts += 0 if ben["flag"] else 25
    pts += {"bajo": 15, "moderado": 8, "alto": 0}[slo["level"]]
    return {"altman": alt, "piotroski": pio, "beneish": ben, "sloan": slo,
            "score": min(100, pts)}
