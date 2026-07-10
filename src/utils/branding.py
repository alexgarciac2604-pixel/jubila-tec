"""Marca AL-X Capital: logo vectorial (SVG inline, nítido a cualquier tamaño).

Recreación fiel del logo oficial: monograma "A" en oro con flecha ascendente
integrada, wordmark AL-X en azul medianoche y CAPITAL espaciado debajo.
"""
from __future__ import annotations

ORO = "#C6A75E"
MEDIANOCHE = "#14235C"


def logo_svg(width: int = 190, con_texto: bool = True,
             color_texto: str = MEDIANOCHE) -> str:
    """SVG del logo. `con_texto=False` devuelve solo el monograma."""
    texto = (f"""
  <text x="200" y="316" text-anchor="middle" font-family="Inter,Arial,sans-serif"
        font-weight="800" font-size="64" letter-spacing="2" fill="{color_texto}">AL-X</text>
  <text x="200" y="352" text-anchor="middle" font-family="Inter,Arial,sans-serif"
        font-weight="700" font-size="26" letter-spacing="10" fill="{color_texto}">CAPITAL</text>"""
             if con_texto else "")
    alto = 380 if con_texto else 270
    return f"""<svg width="{width}" viewBox="0 0 400 {alto}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="AL-X Capital">
  <g stroke="{ORO}" stroke-width="17" fill="none" stroke-linecap="square">
    <path d="M96 252 L184 80 L272 252"/>
    <path d="M131 252 L184 148 L237 252"/>
    <path d="M118 258 L292 96"/>
  </g>
  <path d="M258 78 L306 84 L282 128 Z" fill="{ORO}"/>{texto}
</svg>"""


def logo_html(width: int = 190, centrado: bool = True,
              con_texto: bool = True, color_texto: str = MEDIANOCHE) -> str:
    svg = logo_svg(width, con_texto, color_texto)
    if centrado:
        return f"<div style='text-align:center'>{svg}</div>"
    return svg
