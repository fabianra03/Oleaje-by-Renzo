"""Script de migración one-shot: hashea con bcrypt las contraseñas en texto plano.

Uso:
    cd backend
    python hash_passwords.py

Ejecuta este script UNA VEZ antes de cambiar AUTH_PASSWORD_MODE=bcrypt en .env.
Es seguro volver a ejecutarlo: omite las filas que ya tienen hash bcrypt ($2b$...).
"""

from __future__ import annotations

import os
import sys

import bcrypt
import psycopg
from dotenv import load_dotenv
from psycopg import sql

load_dotenv()


def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        sys.exit("ERROR: La variable DATABASE_URL no está definida en .env")

    auth_table = os.getenv("AUTH_TABLE", "users")
    password_col = os.getenv("AUTH_PASSWORD_COLUMN", "password")
    # Asume que la tabla tiene una columna primaria llamada 'id'.
    # Ajusta PRIMARY_KEY_COLUMN si el nombre es distinto.
    pk_col = os.getenv("AUTH_PK_COLUMN", "id")

    table_id = sql.Identifier(auth_table)
    pwd_id = sql.Identifier(password_col)
    pk_id = sql.Identifier(pk_col)

    select_query = sql.SQL("SELECT {pk}, {pwd} FROM {table}").format(
        pk=pk_id, pwd=pwd_id, table=table_id
    )
    update_query = sql.SQL(
        "UPDATE {table} SET {pwd} = %s WHERE {pk} = %s"
    ).format(pwd=pwd_id, table=table_id, pk=pk_id)

    migrated = 0
    skipped = 0

    try:
        with psycopg.connect(database_url, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute(select_query)
                rows = cur.fetchall()

            for row in rows:
                pk_value, plain_password = row[0], str(row[1])

                # Omitir filas que ya tienen hash bcrypt
                if plain_password.startswith("$2b$") or plain_password.startswith("$2a$"):
                    skipped += 1
                    continue

                hashed = bcrypt.hashpw(
                    plain_password.encode("utf-8"), bcrypt.gensalt()
                ).decode("utf-8")

                with conn.cursor() as cur:
                    cur.execute(update_query, (hashed, pk_value))

                migrated += 1

            conn.commit()

    except psycopg.Error as exc:
        sys.exit(f"ERROR de base de datos: {exc}")

    print(f"✓ Migración completa — {migrated} contraseña(s) hasheada(s), {skipped} ya estaban hasheadas.")
    if migrated > 0:
        print("  Ahora puedes cambiar AUTH_PASSWORD_MODE=bcrypt en tu archivo .env y reiniciar el backend.")


if __name__ == "__main__":
    main()
