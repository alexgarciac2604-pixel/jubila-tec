"""Capa "para todos": explica cada número en tres niveles.

🧒 En corto  — como se lo contarías a un niño o a tu abuela.
📚 El detalle — para quien quiere entender el mecanismo.
🔬 La cuenta  — la matemática exacta, con fuentes y fechas: auditable.

Misión AL-X: que un trabajador de la construcción y un doctor en finanzas
lean la MISMA pantalla y ambos salgan sabiendo más.
"""
from __future__ import annotations

GLOSARIO = {
    "Acción": "Un pedacito de una empresa. Si a la tienda le va bien y vende "
              "más, tu pedacito vale más. Si le va mal, vale menos.",
    "Portafolio": "Tu colección de pedacitos de empresas. Como un equipo de "
                  "futbol: no juegas con 11 porteros — mezclas defensas, "
                  "medios y delanteros.",
    "Diversificar": "No poner todos los huevos en una canasta. Si se cae una "
                    "canasta, las demás te salvan el desayuno.",
    "Dividendo": "La renta que te paga una empresa por ser su dueño, como un "
                 "inquilino te paga por usar tu casa.",
    "Volatilidad": "Los brincos del camino. Un camino con muchos baches te "
                   "sacude más aunque llegue al mismo lugar. Volatilidad alta "
                   "= más sustos en el trayecto, no necesariamente peor "
                   "destino.",
    "Sharpe": "Cuánto premio te dan por cada susto que aguantas. Arriba de 1 "
              "te están pagando bien los sustos; abajo de 0.5, aguantas mucho "
              "brinco para poca ganancia.",
    "Drawdown": "La peor bajada desde la cima. Si tu dinero llegó a $100 y "
                "cayó a $70 antes de recuperarse, aguantaste un drawdown de "
                "30%. Saberlo ANTES te prepara para no vender en pánico.",
    "Interés compuesto": "La bola de nieve: tu ganancia también genera "
                         "ganancia. Pequeña al inicio, imparable con los "
                         "años. Por eso el tiempo es tu mejor socio.",
    "Score AL-X": "La calificación de 0 a 100 que le ponemos a cada empresa, "
                  "como una boleta escolar: mide si el negocio está sano, si "
                  "su precio es justo y cómo viene su ánimo en la bolsa.",
    "Régimen de mercado": "El clima de la bolsa. A veces está soleado (calma) "
                          "y a veces hay tormenta (turbulencia). No puedes "
                          "cambiar el clima, pero sí decidir si sales con "
                          "paraguas.",
    "Monte Carlo": "Ensayar el futuro 800 veces. Como un entrenador que "
                   "simula el partido muchas veces: te decimos qué pasa en "
                   "el escenario del medio, en uno malo y en uno bueno.",
    "Efectivo": "Dinero que está en tu cuenta esperando órdenes. No brinca, "
                "pero tampoco crece.",
    "Precio de entrada": "Lo que costaba la acción el día que la compraste. "
                         "Tu rendimiento se mide desde ahí — congelado, sin "
                         "trampas.",
}


def _nivel(score) -> tuple[str, str]:
    if score >= 70:
        return "🟢", "pasa con honores"
    if score >= 45:
        return "🟡", "pasa, pero sin sobresalir"
    return "🔴", "va reprobando este examen"


def explica_score(tk: str, row: dict, fecha: str = "") -> str:
    """Explicación larga del score en tres niveles. Pura y testeable."""
    sc = row.get("score", 50)
    cal, tec, val = (row.get("calidad", 0), row.get("tecnico", 0),
                     row.get("valoracion", 0))
    emoji, frase = _nivel(sc)
    p1 = (f"**🧒 En corto:** piensa en {tk} como una tiendita del barrio. "
          f"Nosotros le hacemos un examen de tres materias y hoy saca "
          f"**{sc} de 100** {emoji} — {frase}.")
    p2 = ("**📚 Las tres materias:** "
          f"**Calidad ({cal}/100)** pregunta: ¿la tienda gana dinero de "
          "verdad, o solo lo aparenta? Miramos cuánto le queda de cada peso "
          "que vende, cuánto debe y cuánto guarda en la caja. "
          f"**Técnico ({tec}/100)** pregunta: ¿cómo viene su ánimo en la "
          "bolsa? Si mucha gente la está comprando, viene con impulso; si "
          "todos la sueltan, viene cuesta abajo. "
          f"**Valoración ({val}/100)** pregunta: ¿el precio de hoy es justo? "
          "Hasta la mejor tienda del mundo es mala compra si te la venden "
          "carísima — y una tienda regular puede ser gran negocio si te la "
          "dan barata.")
    p3 = (f"**🔬 La cuenta exacta (audítanos):** Score = Calidad×0.35 + "
          f"Técnico×0.35 + Valoración×0.30 = {cal}×0.35 + {tec}×0.35 + "
          f"{val}×0.30 = **{cal * 0.35 + tec * 0.35 + val * 0.30:.0f}**. "
          + (f"Calculado con datos del {fecha}. " if fecha else "")
          + "Precios: Yahoo Finance/Stooq · Estados financieros: reportes "
            "oficiales ante la SEC (EDGAR) · Fórmulas documentadas en "
            "📚 Modelos. Ninguna parte es opinión a ojo: todo es "
            "reproducible.")
    return "\n\n".join([p1, p2, p3])


def explica_riesgo(vol_pct: float, sharpe: float, dd_pct: float) -> str:
    """Volatilidad, Sharpe y drawdown en lenguaje de camino y baches."""
    baches = ("pocos baches: viaje tranquilo" if vol_pct < 15 else
              "baches normales: te sacudirá de vez en cuando" if vol_pct < 25
              else "terracería: agárrate, habrá sustos grandes")
    premio = ("te pagan bien cada susto" if sharpe >= 1 else
              "el premio por susto es razonable" if sharpe >= 0.5 else
              "aguantas muchos brincos para poca ganancia")
    p1 = (f"**🧒 En corto:** tu portafolio brinca ±{vol_pct:.0f}% en un año "
          f"normal ({baches}). Por cada susto que aguantas, tu premio es de "
          f"{sharpe:.2f} ({premio}). Y en su peor momento histórico, este "
          f"equipo llegó a caer {abs(dd_pct):.0f}% desde la cima antes de "
          "recuperarse — si eso vuelve a pasar, ya sabes que es parte del "
          "viaje, no el fin del mundo.")
    p2 = ("**🔬 La cuenta:** volatilidad = desviación estándar de los "
          "rendimientos diarios × √252 · Sharpe = (rendimiento − tasa libre "
          "de riesgo) / volatilidad · Drawdown máximo = mayor caída "
          "pico-a-valle de la serie histórica de 2 años.")
    return "\n\n".join([p1, p2])


def explica_mc(p10: float, p50: float, p90: float, prob_loss: float) -> str:
    return (f"**🧒 ¿Qué es esto?** Ensayamos tu futuro **800 veces**, como un "
            f"entrenador que simula el partido una y otra vez. En el futuro "
            f"del medio terminas con **${p50:,.0f}**; si el partido sale mal "
            f"(peor 10%), con **${p10:,.0f}**; si sale muy bien (mejor 10%), "
            f"con **${p90:,.0f}**. De cada 100 ensayos, en {prob_loss * 100:.0f} "
            f"terminaste con menos de lo que tienes hoy — por eso ni "
            f"prometemos ni asustamos: te mostramos el mapa completo. "
            f"**🔬 La cuenta:** simulación t-Student (colas gordas — los "
            f"sustos existen) con el rendimiento y volatilidad históricos de "
            f"TU mezcla de empresas.")


def explica_reverse_dcf(tk: str, g: float) -> str:
    if g > 0.25:
        juicio = ("Eso es como pedirle a un niño que crezca 30 cm cada año "
                  "hasta los 20: **muy pocas empresas en la historia lo han "
                  "logrado**. Estás pagando por una promesa gigante.")
    elif g > 0.10:
        juicio = ("Es una promesa ambiciosa pero posible para un buen "
                  "negocio — como un estudiante aplicado que sube sus notas "
                  "cada año.")
    else:
        juicio = ("Es una vara baja: el mercado espera poquito. Si la "
                  "empresa lo supera, la sorpresa es a tu favor — las "
                  "mejores compras suelen esconderse aquí.")
    return (f"**🧒 El precio es una promesa.** Cuando pagas el precio de hoy "
            f"por {tk}, estás comprando una promesa: que su flujo de dinero "
            f"crecerá **~{g:.0%} cada año durante 5 años**. {juicio} "
            f"**🔬 La cuenta:** invertimos el modelo DCF (flujos descontados "
            f"al 9% anual, crecimiento terminal 2.5%) y despejamos el "
            f"crecimiento que iguala el valor presente al precio de mercado "
            f"actual. La pregunta final no es nuestra, es tuya: **¿tú le "
            f"crees esa promesa?**")
