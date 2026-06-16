import os
from decouple import config
import psycopg  # Nota: psycopg, no psycopg2

print("🔌 Intentando conexión con psycopg (v3)...")
try:
    conn = psycopg.connect(
        dbname=config('DB_NAME'),
        user=config('DB_USER'),
        password=config('DB_PASSWORD'),
        host=config('DB_HOST'),
        port=config('DB_PORT')
    )
    print("✅ ¡Conexión exitosa a PostgreSQL!")
    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")