"""API de autenticación y catálogo para el panel de administración de Oleaje."""

from __future__ import annotations

import os
import re
import threading
import time
from datetime import timedelta
from typing import Any

import bcrypt
import json
import uuid
import psycopg
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session, send_from_directory
from pathlib import Path
from psycopg import sql


load_dotenv()

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# ---------------------------------------------------------------------------
# Rate limiting — en memoria, por IP. Reinicia al reiniciar el proceso.
# Para producción con múltiples workers usa Redis o similar.
# ---------------------------------------------------------------------------
_login_attempts: dict[str, list[float]] = {}
_attempts_lock = threading.Lock()

LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "300"))  # 5 minutos


def _check_rate_limit(ip: str) -> bool:
    """Devuelve True si la IP ha superado el límite de intentos."""
    now = time.monotonic()
    cutoff = now - LOGIN_WINDOW_SECONDS
    with _attempts_lock:
        attempts = [t for t in _login_attempts.get(ip, []) if t > cutoff]
        if len(attempts) >= LOGIN_MAX_ATTEMPTS:
            _login_attempts[ip] = attempts
            return True
        attempts.append(now)
        _login_attempts[ip] = attempts
        return False


def _clear_rate_limit(ip: str) -> None:
    """Elimina el historial de intentos tras un login exitoso."""
    with _attempts_lock:
        _login_attempts.pop(ip, None)


# ---------------------------------------------------------------------------
# Helpers de configuración
# ---------------------------------------------------------------------------

def setting(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name}.")
    return value


def identifier(name: str, default: str | None = None) -> sql.Identifier:
    """Evita interpolar identificadores SQL no confiables desde el entorno."""
    value = setting(name, default)
    if not IDENTIFIER.fullmatch(value):
        raise RuntimeError(f"{name} debe ser un identificador SQL simple.")
    return sql.Identifier(value)


def verify_password(provided_password: str, stored_password: str) -> bool:
    """Comprueba contraseñas bcrypt; el modo plain solo existe para migraciones."""
    mode = os.getenv("AUTH_PASSWORD_MODE", "bcrypt").lower()
    if mode == "bcrypt":
        try:
            return bcrypt.checkpw(
                provided_password.encode("utf-8"), stored_password.encode("utf-8")
            )
        except (ValueError, TypeError):
            return False
    if mode == "plain":
        import hmac

        return hmac.compare_digest(provided_password, stored_password)
    raise RuntimeError("AUTH_PASSWORD_MODE debe ser bcrypt o plain.")


# ---------------------------------------------------------------------------
# Constantes — sobreescribibles desde .env
# ---------------------------------------------------------------------------

CATEGORY_IMAGES = {
    "Bolsos": "https://images.unsplash.com/photo-1594223274512-ad4803739b7c?auto=format&fit=crop&w=900&q=85",
    "Amigurumis": "https://images.unsplash.com/photo-1559454403-b8fb88521f11?auto=format&fit=crop&w=900&q=85",
    "Decoración": "https://images.unsplash.com/photo-1618220179428-22790b461013?auto=format&fit=crop&w=900&q=85",
    "Accesorios": "https://images.unsplash.com/photo-1521369909029-2afed882baee?auto=format&fit=crop&w=900&q=85",
    "Hogar": "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?auto=format&fit=crop&w=900&q=85",
}

DEFAULT_PRODUCT_IMAGE = CATEGORY_IMAGES["Hogar"]
DEFAULT_PRODUCT_DESCRIPTION = os.getenv(
    "DEFAULT_PRODUCT_DESCRIPTION", "Pieza artesanal tejida a mano en Oleaje."
)
DEFAULT_PRODUCT_STOCK = int(os.getenv("DEFAULT_PRODUCT_STOCK", "10"))

UPLOAD_FOLDER = Path(__file__).parent / "uploads"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

def db_connect():
    return psycopg.connect(setting("DATABASE_URL"), connect_timeout=10)


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

def require_admin() -> tuple[Any, int] | None:
    if not session.get("admin_user"):
        return jsonify({"message": "No autorizado."}), 401
    return None


# ---------------------------------------------------------------------------
# Serialización
# ---------------------------------------------------------------------------

def serialize_product(row: tuple[Any, ...]) -> dict[str, Any]:
    if len(row) >= 7:
        codigo, name, valor, category, image, en_descuento, stock_val = row[:7]
        stock = int(stock_val) if stock_val is not None else DEFAULT_PRODUCT_STOCK
    else:
        codigo, name, valor, category, image, en_descuento = row[:6]
        stock = DEFAULT_PRODUCT_STOCK

    category_name = str(category or "Hogar")
    price = float(valor or 0)
    image_str = str(image) if image else ""
    images_list = []
    if image_str:
        if image_str.startswith("[") and image_str.endswith("]"):
            try:
                images_list = json.loads(image_str)
            except Exception:
                images_list = [image_str]
        else:
            images_list = [image_str]

    primary_image = images_list[0] if images_list else CATEGORY_IMAGES.get(category_name, DEFAULT_PRODUCT_IMAGE)
    if not images_list:
        images_list = [primary_image]

    return {
        "id": int(codigo),
        "name": str(name),
        "category": category_name,
        "price": price,
        "description": DEFAULT_PRODUCT_DESCRIPTION,
        "image": primary_image,
        "images": images_list,
        "stock": stock,
        "en_descuento": bool(en_descuento),
    }


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=setting("FLASK_SECRET_KEY"),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=int(os.getenv("SESSION_HOURS", "8"))),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
    )

    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # Headers de seguridad HTTP — aplicados a todas las respuestas
    # -----------------------------------------------------------------------

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # CSP permisivo para dev; endurecer en producción según necesidades reales
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: https://images.unsplash.com blob:; "
            "connect-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self'; "
            "frame-ancestors 'none';"
        )
        return response

    # -----------------------------------------------------------------------
    # Endpoints
    # -----------------------------------------------------------------------

    @app.get("/api/health")
    def health() -> tuple[dict[str, str], int]:
        return {"status": "ok"}, 200

    @app.get("/api/config")
    def public_config() -> tuple[Any, int]:
        """Expone configuración pública (sin secretos) para el frontend."""
        resp = jsonify({
            "whatsapp": os.getenv("WHATSAPP_NUMBER", ""),
            "email": os.getenv("CONTACT_EMAIL", ""),
            "brand": os.getenv("BRAND_NAME", "Oleaje"),
            "city": os.getenv("BRAND_CITY", "Barranquilla, Colombia"),
        })
        resp.headers["Cache-Control"] = "public, max-age=300"
        return resp, 200

    @app.post("/api/upload")
    def upload_file() -> tuple[Any, int]:
        denied = require_admin()
        if denied:
            return denied

        if "file" not in request.files:
            return jsonify({"message": "No se recibió ningún archivo."}), 400

        file = request.files["file"]
        if not file or not file.filename:
            return jsonify({"message": "Archivo inválido."}), 400

        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({"message": f"Formato no permitido. Usa: {', '.join(ALLOWED_EXTENSIONS)}."}), 400

        filename = f"{uuid.uuid4().hex}.{ext}"
        save_path = UPLOAD_FOLDER / filename
        file.save(str(save_path))

        return jsonify({"url": f"/uploads/{filename}"}), 200

    @app.get("/uploads/<filename>")
    def serve_upload(filename: str) -> Any:
        resp = send_from_directory(str(UPLOAD_FOLDER), filename)
        resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resp

    @app.get("/api/auth/me")
    def current_user() -> tuple[Any, int]:
        user = session.get("admin_user")
        if not user:
            return jsonify({"authenticated": False}), 401
        return jsonify({"authenticated": True, "user": user}), 200

    @app.post("/api/auth/login")
    def login() -> tuple[Any, int]:
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()

        if _check_rate_limit(client_ip):
            return jsonify({"message": "Demasiados intentos. Intenta de nuevo en unos minutos."}), 429

        payload = request.get_json(silent=True) or {}
        username = str(payload.get("username") or payload.get("email") or "").strip()
        password = str(payload.get("password", ""))
        if not username or not password:
            return jsonify({"message": "Usuario y contraseña son obligatorios."}), 400

        query = sql.SQL(
            "SELECT {name}, {password} "
            "FROM {table} WHERE lower({login}) = lower(%s) LIMIT 1"
        ).format(
            login=identifier("AUTH_LOGIN_COLUMN", "name"),
            name=identifier("AUTH_NAME_COLUMN", "name"),
            password=identifier("AUTH_PASSWORD_COLUMN", "password"),
            table=identifier("AUTH_TABLE", "users"),
        )
        try:
            with db_connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (username,))
                    row = cursor.fetchone()
        except psycopg.Error:
            app.logger.exception("No fue posible consultar la base de datos")
            return jsonify({"message": "No fue posible validar el acceso."}), 503

        if not row or not verify_password(password, str(row[1])):
            return jsonify({"message": "Usuario o contraseña incorrectos."}), 401

        _clear_rate_limit(client_ip)
        session.clear()
        session.permanent = True
        session["admin_user"] = {
            "id": str(row[0]),
            "username": row[0],
            "name": row[0],
        }
        return jsonify({"authenticated": True, "user": session["admin_user"]}), 200

    @app.post("/api/auth/logout")
    def logout() -> tuple[dict[str, bool], int]:
        session.clear()
        return {"authenticated": False}, 200

    @app.post("/api/admin/close-connection")
    def close_connection() -> tuple[dict[str, str], int]:
        return {"status": "ok"}, 200

    @app.get("/api/products")
    def list_products() -> tuple[Any, int]:
        query = sql.SQL(
            "SELECT {codigo}, {name}, {valor}, {category}, {image}, {en_descuento}, {stock} "
            "FROM {table} ORDER BY {codigo} DESC"
        ).format(
            codigo=sql.Identifier("codigo"),
            name=sql.Identifier("name"),
            valor=sql.Identifier("valor"),
            category=sql.Identifier("category"),
            image=sql.Identifier("image"),
            en_descuento=sql.Identifier("en_descuento"),
            stock=sql.Identifier("stock"),
            table=sql.Identifier("productos"),
        )
        try:
            with db_connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    rows = cursor.fetchall()
        except psycopg.Error:
            app.logger.exception("No fue posible listar productos")
            return jsonify({"message": "No fue posible cargar los productos."}), 503

        resp = jsonify({"products": [serialize_product(row) for row in rows]})
        resp.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
        return resp, 200

    @app.post("/api/products")
    def create_product() -> tuple[Any, int]:
        denied = require_admin()
        if denied:
            return denied

        payload = request.get_json(silent=True) or {}
        name = str(payload.get("name", "")).strip()
        category = str(payload.get("category", "")).strip()
        price_raw = payload.get("price")
        stock_raw = payload.get("stock", DEFAULT_PRODUCT_STOCK)

        images_payload = payload.get("images", [])
        if not isinstance(images_payload, list):
            images_payload = [str(images_payload)] if images_payload else []

        image_val = json.dumps(images_payload) if images_payload else None
        en_descuento = bool(payload.get("en_descuento", False))

        if not name:
            return jsonify({"message": "El nombre es obligatorio."}), 400
        if not category:
            return jsonify({"message": "La categoría es obligatoria."}), 400
        try:
            price = float(price_raw)
        except (TypeError, ValueError):
            return jsonify({"message": "El precio debe ser un número válido."}), 400
        if price <= 0:
            return jsonify({"message": "El precio debe ser mayor que cero."}), 400

        try:
            stock = int(stock_raw)
            if stock < 0:
                stock = DEFAULT_PRODUCT_STOCK
        except (TypeError, ValueError):
            stock = DEFAULT_PRODUCT_STOCK

        insert = sql.SQL(
            "INSERT INTO {table} ({name}, {valor}, {category}, {image}, {en_descuento}, {stock}) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "RETURNING {codigo}, {name}, {valor}, {category}, {image}, {en_descuento}, {stock}"
        ).format(
            table=sql.Identifier("productos"),
            codigo=sql.Identifier("codigo"),
            name=sql.Identifier("name"),
            valor=sql.Identifier("valor"),
            category=sql.Identifier("category"),
            image=sql.Identifier("image"),
            en_descuento=sql.Identifier("en_descuento"),
            stock=sql.Identifier("stock"),
        )
        try:
            with db_connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(insert, (name, price, category, image_val, en_descuento, stock))
                    row = cursor.fetchone()
                conn.commit()
        except psycopg.Error:
            app.logger.exception("No fue posible crear el producto")
            return jsonify({"message": "No fue posible guardar el producto."}), 503

        product_data = serialize_product(row)
        return jsonify({"product": product_data}), 201

    @app.delete("/api/products/<int:codigo>")
    def delete_product(codigo: int) -> tuple[Any, int]:
        denied = require_admin()
        if denied:
            return denied

        query = sql.SQL("DELETE FROM {table} WHERE {codigo} = %s").format(
            table=sql.Identifier("productos"),
            codigo=sql.Identifier("codigo"),
        )
        try:
            with db_connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (codigo,))
                conn.commit()
        except psycopg.Error:
            app.logger.exception("No fue posible eliminar el producto")
            return jsonify({"message": "No fue posible eliminar el producto."}), 503

        return jsonify({"message": "Producto eliminado exitosamente."}), 200

    @app.patch("/api/products/<int:codigo>")
    def patch_product(codigo: int) -> tuple[Any, int]:
        denied = require_admin()
        if denied:
            return denied

        payload = request.get_json(silent=True) or {}

        update_fields = {}
        if "name" in payload:
            name = str(payload.get("name") or "").strip()
            if not name:
                return jsonify({"message": "El nombre es obligatorio."}), 400
            update_fields["name"] = name

        if "category" in payload:
            category = str(payload.get("category") or "").strip()
            if not category:
                return jsonify({"message": "La categoría es obligatoria."}), 400
            update_fields["category"] = category

        if "price" in payload:
            try:
                price = float(payload.get("price"))
            except (TypeError, ValueError):
                return jsonify({"message": "El precio debe ser un número válido."}), 400
            if price <= 0:
                return jsonify({"message": "El precio debe ser mayor que cero."}), 400
            update_fields["valor"] = price

        if "images" in payload:
            images_payload = payload.get("images", [])
            if not isinstance(images_payload, list):
                images_payload = [str(images_payload)] if images_payload else []
            update_fields["image"] = json.dumps(images_payload) if images_payload else None
        elif "image" in payload:
            update_fields["image"] = str(payload.get("image") or "").strip() or None

        if "en_descuento" in payload:
            update_fields["en_descuento"] = bool(payload.get("en_descuento", False))

        if "stock" in payload:
            try:
                stock_val = int(payload.get("stock"))
                if stock_val >= 0:
                    update_fields["stock"] = stock_val
            except (TypeError, ValueError):
                return jsonify({"message": "El stock debe ser un número entero válido."}), 400

        if not update_fields:
            return jsonify({"message": "No hay campos para actualizar."}), 400

        set_clauses = []
        values = []
        for field, value in update_fields.items():
            set_clauses.append(sql.SQL("{} = %s").format(sql.Identifier(field)))
            values.append(value)
        values.append(codigo)

        query = sql.SQL(
            "UPDATE {table} SET {clauses} WHERE {codigo} = %s "
            "RETURNING {codigo}, {name_col}, {valor_col}, {category_col}, {image_col}, {en_descuento_col}, {stock_col}"
        ).format(
            table=sql.Identifier("productos"),
            clauses=sql.SQL(", ").join(set_clauses),
            codigo=sql.Identifier("codigo"),
            name_col=sql.Identifier("name"),
            valor_col=sql.Identifier("valor"),
            category_col=sql.Identifier("category"),
            image_col=sql.Identifier("image"),
            en_descuento_col=sql.Identifier("en_descuento"),
            stock_col=sql.Identifier("stock"),
        )
        try:
            with db_connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, tuple(values))
                    row = cursor.fetchone()
                conn.commit()
        except psycopg.Error:
            app.logger.exception("No fue posible actualizar el producto")
            return jsonify({"message": "No fue posible actualizar el producto."}), 503

        if not row:
            return jsonify({"message": "Producto no encontrado."}), 404

        product_data = serialize_product(row)
        return jsonify({"product": product_data}), 200

    @app.post("/api/subscribe")
    def subscribe_newsletter() -> tuple[Any, int]:
        payload = request.get_json(silent=True) or {}
        email = str(payload.get("email", "")).strip()

        if not email:
            return jsonify({"message": "El correo electrónico es obligatorio."}), 400

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return jsonify({"message": "Ingresa un correo electrónico válido."}), 400

        select_query = sql.SQL("SELECT email FROM {table} WHERE lower(email) = lower(%s)").format(
            table=sql.Identifier("suscriptores")
        )
        insert_query = sql.SQL("INSERT INTO {table} (email) VALUES (%s)").format(
            table=sql.Identifier("suscriptores")
        )

        try:
            with db_connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(select_query, (email,))
                    row = cursor.fetchone()

                    if row:
                        return jsonify({"message": "Este correo ya está registrado."}), 409

                    cursor.execute(insert_query, (email,))
                conn.commit()
        except psycopg.Error:
            app.logger.exception("No fue posible registrar la suscripción")
            return jsonify({"message": "No fue posible registrar tu suscripción."}), 503

        return jsonify({"message": "Suscripción exitosa."}), 201

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=os.getenv("FLASK_DEBUG") == "true")
