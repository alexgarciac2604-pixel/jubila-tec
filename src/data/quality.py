"""Validador de calidad de datos: detecta series sospechosas antes de calcular."""
from __future__ import annotations

import numpy as np
import pandas as pd


def assess(df: pd.DataFrame) -> dict:
    """Checks: longitud, precios congelados, gaps, outliers, frescura. Score 0-100."""
    issues: list[str] = []
    n = len(df)
    if n < 200:
        issues.append(f"historial corto ({n} días)")

    # precios congelados (posible fuente rota)
    frozen = int((df.Close.diff() == 0).astype(int)
                 .groupby((df.Close.diff() != 0).cumsum()).sum().max() or 0)
    if frozen >= 5:
        issues.append(f"{frozen} días consecutivos sin cambio de precio")

    # gaps de calendario > 7 días hábiles
    max_gap = int(df.index.to_series().diff().dt.days.max() or 0)
    if max_gap > 10:
        issues.append(f"hueco de {max_gap} días en la serie")

    # outliers extremos (>10σ) — posible split mal ajustado
    r = df.Close.pct_change().dropna()
    sd = r.std()
    outliers = int((np.abs(r - r.mean()) > 10 * sd).sum()) if sd else 0
    if outliers:
        issues.append(f"{outliers} retornos >10σ (¿split mal ajustado?)")

    # frescura
    age = (pd.Timestamp.today().normalize() - df.index[-1].tz_localize(None)
           if df.index.tz else pd.Timestamp.today().normalize() - df.index[-1]).days
    if age > 7:
        issues.append(f"último dato de hace {age} días")

    score = max(0, 100 - 25 * len(issues))
    badge = "🟢 datos OK" if score >= 75 else ("🟡 datos con avisos" if score >= 50 else "🔴 datos dudosos")
    return {"score": score, "badge": badge, "issues": issues}
