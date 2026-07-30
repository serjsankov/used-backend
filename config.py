import os
import json
from dotenv import load_dotenv
import boto3

load_dotenv()  # Загружаем .env

DB_USER = os.getenv("DB_USER", "")
DB_PASS = os.getenv("DB_PASS", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "")
DB_PORT = int(os.getenv("DB_PORT", "3306"))

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS", "24"))

S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")

# --- S3 клиент ---
if S3_ENDPOINT and S3_ACCESS_KEY and S3_SECRET_KEY:
    S3_CLIENT = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
    )
else:
    S3_CLIENT = None
    print("⚠️ S3 не настроен")

BUCKET_NAME = os.getenv("S3_BUCKET", "")

# --- CORS origins (список через запятую или JSON-массивом) ---
_raw = os.getenv("FRONTEND_URLS", "http://localhost:5173,http://127.0.0.1:5173")
if _raw.startswith("["):
    FRONTEND_URLS = json.loads(_raw)
else:
    FRONTEND_URLS = [u.strip() for u in _raw.split(",") if u.strip()]
