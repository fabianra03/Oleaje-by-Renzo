# Backend de autenticación

Este servicio Flask valida el acceso al panel **Administrar** contra la tabla
`users` de PostgreSQL/Supabase. La contraseña de la base de datos y la clave de
sesión se leen únicamente desde `backend/.env`; jamás se envían al navegador.

## Preparación

1. Copia `backend/.env.example` a `backend/.env`.
2. Reemplaza `[YOUR-PASSWORD]`, genera `FLASK_SECRET_KEY` y confirma los nombres
   reales de las columnas `AUTH_*`. Por defecto se usa `username` como usuario.
3. Si las contraseñas están guardadas con bcrypt, deja `AUTH_PASSWORD_MODE=bcrypt`.
   Para una tabla heredada con texto plano existe `plain` como compatibilidad
   temporal; migra las contraseñas a bcrypt antes de ponerlo en producción.
4. Crea un entorno virtual e instala las dependencias:

   ```powershell
   cd backend
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python app.py
   ```

El backend queda en `http://127.0.0.1:5000`. Vite redirige automáticamente
`/api/*` a ese servicio durante el desarrollo.

## Endpoints

- `POST /api/auth/login`: recibe `username` y `password`.
- `GET /api/auth/me`: informa si existe una sesión de administración.
- `POST /api/auth/logout`: elimina la sesión.

En producción, sirve el frontend y Flask bajo el mismo dominio (o configura un
proxy inverso equivalente) y habilita `SESSION_COOKIE_SECURE=true` al usar HTTPS.
