import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

conn = psycopg.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS image TEXT;")
    cur.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS en_descuento BOOLEAN DEFAULT FALSE;")
    cur.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock INTEGER DEFAULT 10;")
    conn.commit()
    print("Migration successful")
except Exception as e:
    conn.rollback()
    print("Migration failed:", e)

cur.close()
conn.close()
