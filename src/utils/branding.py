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


import base64
import functools
import os

_MIME = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".webp": "webp"}


@functools.lru_cache(maxsize=1)
def _logo_file_b64() -> tuple[str, str] | None:
    """(mime, base64) del logo oficial en assets/, si existe."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for ext, mime in _MIME.items():
        ruta = os.path.join(root, "assets", f"logo{ext}")
        if os.path.exists(ruta):
            with open(ruta, "rb") as fh:
                return mime, base64.b64encode(fh.read()).decode()
    return None


def logo_html(width: int = 190, centrado: bool = True,
              con_texto: bool = True, color_texto: str = MEDIANOCHE) -> str:
    """Logo oficial (assets/logo.png) si existe; monograma SVG si no."""
    archivo = _logo_file_b64()
    if archivo:
        mime, b64 = archivo
        pieza = (f"<img src='data:image/{mime};base64,{b64}' width='{width}' "
                 f"alt='AL-X Capital' style='border-radius:10px'/>")
    else:
        pieza = logo_svg(width, con_texto, color_texto)
    if centrado:
        return f"<div style='text-align:center'>{pieza}</div>"
    return pieza
