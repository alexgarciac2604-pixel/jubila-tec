# 🚀 Deploy permanente de Jubila-Tec (nube)

Dos piezas, dos plataformas gratuitas. Resultado: URL fija 24/7.

| Pieza | Carpeta | Plataforma | Costo |
|---|---|---|---|
| **Terminal** (Streamlit/Python) | raíz (`app.py`) | **Streamlit Community Cloud** | Gratis |
| **Landing** (React/Vite) | `landing/` | **Vercel** (o Netlify) | Gratis |

El repo ya está **listo para deploy** (requirements.txt en la raíz, `app.py`, tema,
URLs del landing configurables por variable de entorno). Lo único que requiere
**tu cuenta** es subir a GitHub y conectar las dos plataformas.

---

## Paso 0 — Subir el código a GitHub (una sola vez)

Necesitas una cuenta en https://github.com . Luego, en este repo:

**Opción A — con GitHub CLI (recomendado).** Instala `gh` desde https://cli.github.com , y:
```powershell
gh auth login                       # inicia sesión en tu GitHub (navegador)
gh repo create jubila-tec --private --source . --remote origin --push
```
Eso crea el repo y sube todo. (Usa `--public` si lo quieres público.)

**Opción B — manual.** Crea un repo vacío en github.com llamado `jubila-tec`, y:
```powershell
git remote add origin https://github.com/TU_USUARIO/jubila-tec.git
git branch -M main
git push -u origin main
```

> `.venv/`, `landing/node_modules/` y `dist/` ya están en `.gitignore`, no se suben.

---

## Paso 1 — Desplegar el TERMINAL (Streamlit Community Cloud)

1. Entra a https://share.streamlit.io y **Sign in with GitHub**.
2. **New app** → elige el repo `jubila-tec`, rama `main`.
3. **Main file path:** `app.py`
4. **Advanced settings → Python version:** `3.12` (o 3.13).
   - *(Opcional)* en **Secrets** puedes pegar claves si las tienes:
     ```toml
     FRED_API_KEY = "..."
     NEWSAPI_KEY  = "..."
     ```
     No son obligatorias: la app corre con fallback.
5. **Deploy**. En 2-4 min tendrás una URL como
   `https://jubila-tec.streamlit.app`. **Cópiala.**

---

## Paso 2 — Desplegar el LANDING (Vercel)

1. Entra a https://vercel.com y **Sign in with GitHub**.
2. **Add New… → Project** → importa el repo `jubila-tec`.
3. **Root Directory:** selecciona `landing`  ← importante (el landing vive en esa subcarpeta).
4. Framework: **Vite** (se detecta solo). Build: `npm run build`, Output: `dist`.
5. **Environment Variables** → agrega:
   | Name | Value |
   |---|---|
   | `VITE_TERMINAL_URL` | la URL del Paso 1 (ej. `https://jubila-tec.streamlit.app`) |
   | `VITE_HLS_URL` | *(opcional)* tu stream financiero `.m3u8` |
6. **Deploy**. Tendrás una URL como `https://jubila-tec.vercel.app`.

Ahora los botones del landing (**Open Market Terminal**, **Launch Terminal**, nav)
abren tu terminal desplegado. 🎉

---

## Actualizaciones futuras
Cada `git push` a `main` re-despliega **ambas** automáticamente (Streamlit Cloud y
Vercel observan el repo). No tienes que volver a configurar nada.

## Notas
- **Netlify** funciona igual que Vercel: Base directory `landing`, build `npm run build`,
  publish `landing/dist`, y la misma variable `VITE_TERMINAL_URL`.
- La terminal en la nube usa datos en vivo (yfinance) y degrada a fallback sintético
  si una fuente falla. Sin claves API obligatorias.
- Recordatorio de cumplimiento: la app es informativa/educativa, **no** asesoría
  financiera. Ese aviso ya está visible en la app y el landing.
