# api/brands.py
import os
import json
from uuid import uuid4
from urllib.parse import urlparse

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Request,
)

from db.db import get_db_conn
from config import S3_CLIENT, BUCKET_NAME, S3_ENDPOINT

router = APIRouter()


async def _delete_car_photos(car, db):
    """Удаляет фото машины из S3."""
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


async def _cascade_delete_brand(brand_id, db):
    """Каскадно удаляет всё связанное с маркой: машины, модели, связи проектов."""
    # 1. Удаляем машины этой марки (и их фото)
    await db.execute("SELECT id, photos FROM cars WHERE brand_id = %s", (brand_id,))
    cars = await db.fetchall()
    for car in cars:
        await _delete_car_photos(car, db)
    await db.execute("DELETE FROM cars WHERE brand_id = %s", (brand_id,))

    # 2. Удаляем модели этой марки (и их фото)
    await db.execute("SELECT id, path_img FROM models WHERE brand_id = %s", (brand_id,))
    models = await db.fetchall()
    for model in models:
        if model.get("path_img"):
            try:
                key = model["path_img"].split(f"{BUCKET_NAME}/", 1)[1]
                S3_CLIENT.delete_object(Bucket=BUCKET_NAME, Key=key)
            except Exception:
                pass
    await db.execute("DELETE FROM models WHERE brand_id = %s", (brand_id,))

    # 3. Удаляем связи в проектах
    await db.execute("DELETE FROM project_brands WHERE brand_id = %s", (brand_id,))
    await db.execute("""
        DELETE FROM project_models
        WHERE model_id IN (SELECT id FROM models WHERE brand_id = %s)
    """, (brand_id,))

@router.get("/")
async def brands_list(db=Depends(get_db_conn)):
    await db.execute("""
        SELECT *
        FROM brands
        ORDER BY title ASC
    """)
    return await db.fetchall()

@router.post("/add")
async def create_brand(
    title: str = Form(...),
    russ_title: str = Form(...),
    slug: str = Form(...),
    file: UploadFile = File(...),
    db=Depends(get_db_conn),
):
    # 1. создаём запись бренда без картинки, id генерируется БД
    await db.execute(
        """
        INSERT INTO brands (title, russ_title, path_img, slug)
        VALUES (%s, %s, %s, %s)
        """,
        (title, russ_title, None, slug),
    )

    brand_id = db.lastrowid

    if not brand_id:
        raise HTTPException(status_code=500, detail="Не удалось получить ID бренда")

    # 2. валидация файла
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Допустимы только jpg, png, webp")

    ext = os.path.splitext(file.filename)[1] or ".jpg"
    key = f"brands/{brand_id}/{uuid4()}{ext}"

    data = await file.read()

    # 3. загрузка в S3
    try:
        S3_CLIENT.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=file.content_type,
            ACL="public-read",  # если нужен прямой доступ по ссылке
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки в S3: {e}")

    file_url = f"{S3_ENDPOINT.rstrip('/')}/{BUCKET_NAME}/{key}"

    # 4. обновляем запись бренда ссылкой на картинку
    await db.execute(
        "UPDATE brands SET path_img = %s WHERE id = %s",
        (file_url, brand_id),
    )

    await db.execute("SELECT * FROM brands")
    brands = await db.fetchall()

    await db.connection.commit()

    return {
        "brands": brands,
    }

@router.post("/change")
async def change_brand(
    brand_id: int = Form(...),
    title: str = Form(...),
    russ_title: str = Form(...),
    slug: str = Form(...),
    is_active: bool = Form(...),
    file: UploadFile = File(None),  # файл теперь необязательный
    db=Depends(get_db_conn),
):
    # 1. проверяем, существует ли бренд
    await db.execute(
        "SELECT id, path_img FROM brands WHERE id = %s",
        (brand_id,),
    )
    brand = await db.fetchone()

    if not brand:
        raise HTTPException(status_code=404, detail="Бренд не найден")

    file_url = brand["path_img"]

    # 2. если передан файл — валидируем и загружаем новый
    if file:
        if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
            raise HTTPException(status_code=400, detail="Допустимы только jpg, png, webp")

        ext = os.path.splitext(file.filename)[1] or ".jpg"
        key = f"brands/{brand_id}/{uuid4()}{ext}"

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
            raise HTTPException(status_code=500, detail=f"Ошибка загрузки в S3: {e}")

        file_url = f"{S3_ENDPOINT.rstrip('/')}/{BUCKET_NAME}/{key}"

    # 3. обновляем данные бренда
    await db.execute(
        """
        UPDATE brands
        SET title = %s,
            russ_title = %s,
            slug = %s,
            path_img = %s,
            is_active = %s
        WHERE id = %s
        """,
        (title, russ_title, slug, file_url, is_active, brand_id),
    )

    await db.connection.commit()

    await db.execute(
        """
        SELECT id, title, russ_title, slug, path_img,

            created_at, updated_at, is_active

        FROM brands
        WHERE id = %s
        """,
        (brand_id,),
    )

    updated_brand = await db.fetchone()

    return updated_brand


@router.post("/delete")
async def delete_brand(
    request: Request,
    db=Depends(get_db_conn),
):
    data = await request.json()
    brand_id = data.get("brand_id")

    # Получаем бренд
    await db.execute(
        "SELECT path_img FROM brands WHERE id=%s",
        (brand_id,)
    )
    brand = await db.fetchone()

    if not brand:
        raise HTTPException(
            status_code=404,
            detail="Марка не найдена"
        )

    # Каскадно удаляем всё связанное
    await _cascade_delete_brand(brand_id, db)

    # Удаляем файл логотипа марки из S3
    file_url = brand["path_img"]
    if file_url:
        try:
            key = file_url.split(f"{BUCKET_NAME}/", 1)[1]
            S3_CLIENT.delete_object(
                Bucket=BUCKET_NAME,
                Key=key
            )
        except Exception as e:
            print("Ошибка удаления файла S3:", e)

    # Удаляем бренд
    await db.execute(
        "DELETE FROM brands WHERE id=%s",
        (brand_id,)
    )

    await db.connection.commit()

    # Получаем обновлённый список брендов
    await db.execute(
        "SELECT * FROM brands ORDER BY title ASC"
    )
    brands = await db.fetchall()

    return {
        "brands": brands
    }