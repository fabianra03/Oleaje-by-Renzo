# Oleaje

Tienda React/Vite con un acceso protegido al panel **Administrar**. El frontend
no tiene acceso directo a PostgreSQL: se comunica con una API Flask local que
valida al usuario contra la tabla `users` de Supabase y mantiene la sesión en
una cookie HTTP-only.

## Estructura añadida

```text
backend/
  app.py             # API Flask: login, sesión y logout
  .env.example       # variables requeridas, sin secretos
  requirements.txt   # dependencias Python fijadas
  README.md          # detalle del backend
```

## Puesta en marcha

1. Instala Python 3.11 o superior si no está disponible en tu equipo.
2. Copia `backend/.env.example` como `backend/.env`.
3. En `backend/.env`, pega la contraseña real en `DATABASE_URL`, genera una
   clave aleatoria para `FLASK_SECRET_KEY` y confirma los nombres de columnas
   `AUTH_*` de la tabla `users` (por defecto usa `username`).
4. Inicia el backend:

   ```powershell
   cd backend
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python app.py
   ```

5. En otra terminal, desde la raíz del proyecto, inicia el frontend:

   ```powershell
   npm.cmd install
   npm.cmd run dev
   ```

6. Abre la URL que muestra Vite, elige **Administrar** y usa un correo y una
   contraseña ya registrados en la tabla.

Vite reenvía `/api/*` al backend en `http://127.0.0.1:5000`. Para producción,
coloca ambos servicios bajo el mismo dominio y usa HTTPS con
`SESSION_COOKIE_SECURE=true`.

## Seguridad

- Nunca incluyas `DATABASE_URL`, contraseñas ni una `service_role key` en `src/`.
- Las contraseñas deben guardarse con bcrypt. `AUTH_PASSWORD_MODE=plain` está
  disponible solo para una migración temporal de una tabla heredada.
- `backend/.env` y `backend/.venv/` están ignorados por Git.
