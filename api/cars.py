# api/cars.py
import os
import json
from uuid import uuid4
from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File, Form
from db.db import get_db_conn
from config import S3_CLIENT, BUCKET_NAME, S3_ENDPOINT

router = APIRouter()

MAX_PHOTOS = 8
ALLOWED_TYPES = ("image/jpeg", "image/png", "image/webp")

# Поля характеристик машины
SPEC_FIELDS = [
    "body_type",
    "seats",
    "mileage",
    "engine",
    "transmission",
    "drive_type",
    "fuel_consumption",
    "acceleration",
    "year",
    "color",
]


def _parse_photos(row):
    """Парсит photos из JSON в массиве."""
    if row.get("photos") and isinstance(row["photos"], str):
        try:
            row["photos"] = json.loads(row["photos"])
        except (json.JSONDecodeError, TypeError):
            row["photos"] = []
    elif not row.get("photos"):
        row["photos"] = []
    return row


async def _upload_photo(file: UploadFile, car_id: int, index: int) -> str:
    """Загружает одно фото в S3 и возвращает URL."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Фото {index + 1}: допустимы только jpg, png, webp")

    ext = os.path.splitext(file.filename)[1] or ".jpg"
    key = f"cars/{car_id}/{uuid4()}{ext}"
    data = await file.read()

    try:
        S3_CLIENT.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=file.content_type,
            ACL="public-read",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки фото {index + 1}: {e}")

    return f"{S3_ENDPOINT.rstrip('/')}/{BUCKET_NAME}/{key}"


# Столбцы для INSERT (без id, created_at, updated_at, photos — photos отдельно)
INSERT_COLS = ["brand_id", "model_id", "brand_title", "model_title", "car_name"] + SPEC_FIELDS
INSERT_PLACEHOLDERS = ", ".join([f"%s"] * len(INSERT_COLS))
INSERT_COLS_STR = ", ".join(INSERT_COLS)


@router.get("/")
async def list_cars(db=Depends(get_db_conn)):
    await db.execute("""
        SELECT *
        FROM cars
        ORDER BY created_at DESC
    """)
    rows = await db.fetchall()
    for row in rows:
        row = _parse_photos(row)
    return rows


@router.post("/add")
async def create_car(
    request: Request,
    db=Depends(get_db_conn),
):
    data = await request.json()
    brand_id = data.get("brand_id")
    model_id = data.get("model_id")
    brand_title = data.get("brand_title", "")
    model_title = data.get("model_title", "")
    car_name = data.get("car_name", "")
    photos = data.get("photos", [])

    if not all([brand_id, model_id, car_name]):
        raise HTTPException(status_code=400, detail="brand_id, model_id и car_name обязательны")

    values = [brand_id, model_id, brand_title, model_title, car_name]
    for f in SPEC_FIELDS:
        values.append(data.get(f, ""))

    await db.execute(
        f"INSERT INTO cars ({INSERT_COLS_STR}, photos) VALUES ({INSERT_PLACEHOLDERS}, %s)",
        (*values, json.dumps(photos[:MAX_PHOTOS])),
    )

    car_id = db.lastrowid
    await db.connection.commit()

    await db.execute("SELECT * FROM cars WHERE id = %s", (car_id,))
    car = await db.fetchone()
    car = _parse_photos(car)
    return car


@router.post("/upload-photos")
async def upload_car_photos(
    brand_id: int = Form(...),
    model_id: int = Form(...),
    brand_title: str = Form(""),
    model_title: str = Form(""),
    car_name: str = Form(...),
    body_type: str = Form(""),
    seats: str = Form(""),
    mileage: str = Form(""),
    engine: str = Form(""),
    transmission: str = Form(""),
    drive_type: str = Form(""),
    fuel_consumption: str = Form(""),
    acceleration: str = Form(""),
    year: str = Form(""),
    color: str = Form(""),
    files: list[UploadFile] = File(...),
    db=Depends(get_db_conn),
):
    if len(files) > MAX_PHOTOS:
        raise HTTPException(status_code=400, detail=f"Максимум {MAX_PHOTOS} фото")

    if not car_name:
        raise HTTPException(status_code=400, detail="car_name обязателен")

    values = [brand_id, model_id, brand_title, model_title, car_name,
              body_type, seats, mileage, engine, transmission, drive_type, fuel_consumption, acceleration, year, color]

    await db.execute(
        f"INSERT INTO cars ({INSERT_COLS_STR}, photos) VALUES ({INSERT_PLACEHOLDERS}, %s)",
        (*values, "[]"),
    )

    car_id = db.lastrowid

    # загружаем фото
    photo_urls = []
    for i, file in enumerate(files):
        url = await _upload_photo(file, car_id, i)
        photo_urls.append(url)

    await db.execute("UPDATE cars SET photos = %s WHERE id = %s", (json.dumps(photo_urls), car_id))
    await db.connection.commit()

    await db.execute("SELECT * FROM cars WHERE id = %s", (car_id,))
    car = await db.fetchone()
    car = _parse_photos(car)
    return car


@router.post("/change")
async def change_car(
    request: Request,
    db=Depends(get_db_conn),
):
    data = await request.json()
    car_id = data.get("id")
    car_name = data.get("car_name")
    photos = data.get("photos")

    if not car_id:
        raise HTTPException(status_code=400, detail="id обязателен")

    await db.execute("SELECT id FROM cars WHERE id = %s", (car_id,))
    car = await db.fetchone()
    if not car:
        raise HTTPException(status_code=404, detail="Машина не найдена")

    updates = []
    params = []
    if car_name is not None:
        updates.append("car_name = %s")
        params.append(car_name)
    if photos is not None:
        updates.append("photos = %s")
        params.append(json.dumps(photos[:MAX_PHOTOS]))
    # Обновление полей характеристик
    for f in SPEC_FIELDS:
        if f in data:
            updates.append(f"{f} = %s")
            params.append(data[f])

    if updates:
        params.append(car_id)
        await db.execute(
            f"UPDATE cars SET {', '.join(updates)} WHERE id = %s",
            tuple(params),
        )

    await db.connection.commit()

    await db.execute("SELECT * FROM cars WHERE id = %s", (car_id,))
    car = await db.fetchone()
    car = _parse_photos(car)
    return car


@router.post("/delete")
async def delete_car(
    request: Request,
    db=Depends(get_db_conn),
):
    data = await request.json()
    car_id = data.get("id")

    if not car_id:
        raise HTTPException(status_code=400, detail="id обязателен")

    await db.execute("SELECT id, photos FROM cars WHERE id = %s", (car_id,))
    car = await db.fetchone()
    if not car:
        raise HTTPException(status_code=404, detail="Машина не найдена")

    if car.get("photos"):
        try:
            photo_urls = json.loads(car["photos"]) if isinstance(car["photos"], str) else car["photos"]
            for url in photo_urls:
                try:
                    key = url.split(f"{BUCKET_NAME}/", 1)[1]
                    S3_CLIENT.delete_object(Bucket=BUCKET_NAME, Key=key)
                except Exception:
                    pass
        except Exception:
            pass

    await db.execute("DELETE FROM cars WHERE id = %s", (car_id,))
    await db.connection.commit()

    return {"status": "ok"}