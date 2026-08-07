"""API de autenticación y catálogo para el panel de administración de Oleaje."""

from __future__ import annotations

import os
import re
import threading
import time
from datetime import timedelta
from typing import Any

# pyrefly: ignore [missing-import]
import bcrypt
import json
import uuid
# pyrefly: ignore [missing-import]
import psycopg
import requests as http_requests
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session
from pathlib import Path
# pyrefly: ignore [missing-import]
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

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "productos")


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
    if len(row) >= 9:
        codigo, name, valor, category, image, en_descuento, stock_val, tallas_raw, descuento_fin_raw = row[:9]
        stock = int(stock_val) if stock_val is not None else DEFAULT_PRODUCT_STOCK
    elif len(row) >= 8:
        codigo, name, valor, category, image, en_descuento, stock_val, tallas_raw = row[:8]
        stock = int(stock_val) if stock_val is not None else DEFAULT_PRODUCT_STOCK
        descuento_fin_raw = None
    elif len(row) >= 7:
        codigo, name, valor, category, image, en_descuento, stock_val = row[:7]
        stock = int(stock_val) if stock_val is not None else DEFAULT_PRODUCT_STOCK
        tallas_raw = None
        descuento_fin_raw = None
    else:
        codigo, name, valor, category, image, en_descuento = row[:6]
        stock = DEFAULT_PRODUCT_STOCK
        tallas_raw = None
        descuento_fin_raw = None

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

    # Parse sizes (tallas) JSON
    sizes = None
    if tallas_raw:
        try:
            sizes = json.loads(str(tallas_raw))
            if not isinstance(sizes, dict):
                sizes = None
        except Exception:
            sizes = None

    # Parse descuento_fin
    descuento_fin = None
    if descuento_fin_raw:
        try:
            # Handle datetime objects
            if hasattr(descuento_fin_raw, "isoformat"):
                descuento_fin = descuento_fin_raw.isoformat()
            else:
                descuento_fin = str(descuento_fin_raw)
        except Exception:
            descuento_fin = None

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
        "descuento_fin": descuento_fin,
        "sizes": sizes,
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
        supabase_host = SUPABASE_URL.replace("https://", "").replace("http://", "").split("/")[0] if SUPABASE_URL else ""
        img_src = f"'self' data: https://images.unsplash.com blob: https://{supabase_host}" if supabase_host else "'self' data: https://images.unsplash.com blob:"
        response.headers["Content-Security-Policy"] = (
            f"default-src 'self'; "
            f"img-src {img_src}; "
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

        if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
            return jsonify({"message": "Supabase no está configurado en el servidor."}), 500

        filename = f"{uuid.uuid4().hex}.{ext}"
        content_type_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
            "gif": "image/gif",
        }
        content_type = content_type_map.get(ext, "application/octet-stream")

        storage_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{filename}"
        headers = {
            "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
            "Content-Type": content_type,
            "x-upsert": "true",
        }

        try:
            file_bytes = file.read()
            resp = http_requests.post(storage_url, headers=headers, data=file_bytes, timeout=30)
            if resp.status_code not in (200, 201):
                app.logger.error("Supabase Storage error %s: %s", resp.status_code, resp.text)
                return jsonify({"message": "No fue posible subir la imagen."}), 502
        except http_requests.RequestException:
            app.logger.exception("Error al conectar con Supabase Storage")
            return jsonify({"message": "No fue posible subir la imagen."}), 502

        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{filename}"
        return jsonify({"url": public_url}), 200

    @app.post("/api/upload/debug")
    def upload_debug() -> tuple[Any, int]:
        """Diagnóstico temporal — muestra el error exacto de Supabase Storage."""
        denied = require_admin()
        if denied:
            return denied

        info: dict[str, Any] = {
            "supabase_url_set": bool(SUPABASE_URL),
            "supabase_key_set": bool(SUPABASE_SECRET_KEY),
            "supabase_key_prefix": SUPABASE_SECRET_KEY[:20] + "..." if SUPABASE_SECRET_KEY else None,
            "bucket": SUPABASE_STORAGE_BUCKET,
        }

        if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
            return jsonify({"error": "Variables no configuradas", "info": info}), 500

        # Intentar subir un archivo de prueba de 1 byte
        test_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/_test_connection.txt"
        headers = {
            "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
            "Content-Type": "text/plain",
            "x-upsert": "true",
        }
        try:
            resp = http_requests.post(test_url, headers=headers, data=b"ok", timeout=10)
            info["supabase_status"] = resp.status_code
            info["supabase_response"] = resp.text[:500]
            info["success"] = resp.status_code in (200, 201)
        except http_requests.RequestException as exc:
            info["supabase_error"] = str(exc)
            info["success"] = False

        return jsonify(info), 200

    @app.get("/uploads/<filename>")
    def serve_upload_legacy(filename: str) -> tuple[Any, int]:
        """Ruta legacy — en producción las imágenes se sirven desde Supabase Storage."""
        return jsonify({"message": "Las imágenes ahora se sirven desde Supabase Storage."}), 410

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
            "SELECT {codigo}, {name}, {valor}, {category}, {image}, {en_descuento}, {stock}, {tallas}, {descuento_fin} "
            "FROM {table} ORDER BY {codigo} DESC"
        ).format(
            codigo=sql.Identifier("codigo"),
            name=sql.Identifier("name"),
            valor=sql.Identifier("valor"),
            category=sql.Identifier("category"),
            image=sql.Identifier("image"),
            en_descuento=sql.Identifier("en_descuento"),
            stock=sql.Identifier("stock"),
            tallas=sql.Identifier("tallas"),
            descuento_fin=sql.Identifier("descuento_fin"),
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
        
        descuento_fin_raw = payload.get("descuento_fin")
        descuento_fin_val = None
        if en_descuento and descuento_fin_raw:
            descuento_fin_val = str(descuento_fin_raw).strip() or None

        # Parse sizes (tallas)
        sizes_payload = payload.get("sizes")
        tallas_val = None
        if sizes_payload and isinstance(sizes_payload, dict):
            # Validate that all values are positive numbers
            valid_sizes = {}
            for size_key, size_price in sizes_payload.items():
                try:
                    p = float(size_price)
                    if p > 0:
                        valid_sizes[str(size_key)] = p
                except (TypeError, ValueError):
                    pass
            if valid_sizes:
                tallas_val = json.dumps(valid_sizes)

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
            "INSERT INTO {table} ({name}, {valor}, {category}, {image}, {en_descuento}, {stock}, {tallas}, {descuento_fin}) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
            "RETURNING {codigo}, {name}, {valor}, {category}, {image}, {en_descuento}, {stock}, {tallas}, {descuento_fin}"
        ).format(
            table=sql.Identifier("productos"),
            codigo=sql.Identifier("codigo"),
            name=sql.Identifier("name"),
            valor=sql.Identifier("valor"),
            category=sql.Identifier("category"),
            image=sql.Identifier("image"),
            en_descuento=sql.Identifier("en_descuento"),
            stock=sql.Identifier("stock"),
            tallas=sql.Identifier("tallas"),
            descuento_fin=sql.Identifier("descuento_fin"),
        )
        try:
            with db_connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(insert, (name, price, category, image_val, en_descuento, stock, tallas_val, descuento_fin_val))
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
            en_desc = bool(payload.get("en_descuento", False))
            update_fields["en_descuento"] = en_desc
            
            # Solo actualizar descuento_fin si en_descuento está en el payload
            if en_desc and "descuento_fin" in payload:
                df = str(payload.get("descuento_fin") or "").strip()
                update_fields["descuento_fin"] = df if df else None
            elif not en_desc:
                update_fields["descuento_fin"] = None

        if "stock" in payload:
            try:
                stock_val = int(payload.get("stock"))
                if stock_val >= 0:
                    update_fields["stock"] = stock_val
            except (TypeError, ValueError):
                return jsonify({"message": "El stock debe ser un número entero válido."}), 400

        if "sizes" in payload:
            sizes_payload = payload.get("sizes")
            if sizes_payload and isinstance(sizes_payload, dict):
                valid_sizes = {}
                for size_key, size_price in sizes_payload.items():
                    try:
                        p = float(size_price)
                        if p > 0:
                            valid_sizes[str(size_key)] = p
                    except (TypeError, ValueError):
                        pass
                update_fields["tallas"] = json.dumps(valid_sizes) if valid_sizes else None
            else:
                update_fields["tallas"] = None

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
            "RETURNING {codigo}, {name_col}, {valor_col}, {category_col}, {image_col}, {en_descuento_col}, {stock_col}, {tallas_col}, {descuento_fin_col}"
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
            tallas_col=sql.Identifier("tallas"),
            descuento_fin_col=sql.Identifier("descuento_fin"),
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
