# config.py
import os
from dotenv import load_dotenv
import boto3

load_dotenv()  # Загружаем .env

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT", 3306))

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS"))

S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY=os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY=os.getenv("S3_SECRET_KEY")

# --- S3 клиент ---
S3_CLIENT = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,          # пример: https://s3.timeweb.cloud
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
)
BUCKET_NAME = os.getenv("S3_BUCKET")

FRONTEND_URLS = [
    "https://itmastery.ru",     # продакшн
    "http://localhost:5173",    # локальный фронт
    "http://127.0.0.1:5173",     # на случай другого хоста
]
