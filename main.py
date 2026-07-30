# main.py
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.db import init_db_pool, close_db_pool
import db.db
from aiomysql import DictCursor
from config import FRONTEND_URLS

from api.brands import router as brands_router
from api.models import router as models_router
from api.projects import router as projects_router
from api.data import router as data_router
from api.registration import router as auth_router
from api.feed import router as feed_router
from api.cars import router as cars_router

app = FastAPI(title="DB Backend")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_URLS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Роутеры ---
app.include_router(brands_router, prefix="/brands")
app.include_router(models_router, prefix="/models")
app.include_router(projects_router, prefix="/projects")
app.include_router(data_router, prefix="/data")
app.include_router(auth_router, prefix="/api")  # /api/login, /api/dashboard и т.п.
app.include_router(feed_router, prefix="/feed")  # /feed/{slug} — публичный фид
app.include_router(cars_router, prefix="/cars")  # /cars/ — машины

# --- События приложения ---
@app.on_event("startup")
async def on_startup() -> None:
    """Инициализация ресурсов при старте приложения."""
    print("🚀 Запуск приложения...")
    try:
        await init_db_pool()
        print("✅ Пул БД инициализирован")
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        return

    try:
        # Получаем соединение напрямую
        async with db.db.pool.acquire() as conn:
            async with conn.cursor(DictCursor) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS cars (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        brand_id INT NOT NULL,
                        model_id INT NOT NULL,
                        brand_title VARCHAR(255) NOT NULL DEFAULT '',
                        model_title VARCHAR(255) NOT NULL DEFAULT '',
                        car_name VARCHAR(255) NOT NULL,
                        body_type VARCHAR(255) DEFAULT '',
                        seats VARCHAR(255) DEFAULT '',
                        mileage VARCHAR(255) DEFAULT '',
                        engine VARCHAR(255) DEFAULT '',
                        transmission VARCHAR(255) DEFAULT '',
                        drive_type VARCHAR(255) DEFAULT '',
                        fuel_consumption VARCHAR(255) DEFAULT '',
                        acceleration VARCHAR(255) DEFAULT '',
                        year VARCHAR(10) DEFAULT '',
                        color VARCHAR(255) DEFAULT '',
                        photos TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
                await conn.commit()
                print("✅ Таблица cars готова")

                # Миграция: добавляем новые колонки, если их нет
                for col in ["body_type", "seats", "mileage", "engine", "transmission", "drive_type", "fuel_consumption", "acceleration", "year", "color"]:
                    try:
                        await db.execute(f"ALTER TABLE cars ADD COLUMN {col} VARCHAR(255) DEFAULT ''")
                    except Exception:
                        pass
                # Удаляем устаревшую колонку characteristics, если есть
                try:
                    await db.execute("SELECT characteristics FROM cars LIMIT 1")
                    await db.execute("ALTER TABLE cars DROP COLUMN characteristics")
                except Exception:
                    pass
                await conn.commit()
    except Exception as e:
        print(f"⚠️ Миграция БД пропущена: {e}")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Очистка ресурсов при остановке."""
    await close_db_pool()


# --- Служебный эндпоинт ---
@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
