from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File, Form
from db.db import get_db_conn
from uuid import uuid4
from config import S3_CLIENT, BUCKET_NAME, S3_ENDPOINT
import os
import json

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


async def _cascade_delete_model(model_id, db):
    """Каскадно удаляет всё связанное с моделью: машины, связи проектов."""
    # 1. Удаляем машины этой модели (и их фото)
    await db.execute("SELECT id, photos FROM cars WHERE model_id = %s", (model_id,))
    cars = await db.fetchall()
    for car in cars:
        await _delete_car_photos(car, db)
    await db.execute("DELETE FROM cars WHERE model_id = %s", (model_id,))

    # 2. Удаляем связи в проектах
    await db.execute("DELETE FROM project_models WHERE model_id = %s", (model_id,))

@router.get("/")
async def brands(db=Depends(get_db_conn)):
    await db.execute("""
        SELECT *
        FROM models
        ORDER BY brand_title ASC, title ASC
    """)
    rows = await db.fetchall()
    return rows

# --- Загрузка картинки модели в S3 ---
# @router.post("/add")
# async def upload_model_image(
#     model_id: int = Form(...),
#     file: UploadFile = File(...),
#     db=Depends(get_db_conn),
# ):
#     # простая валидация
#     if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
#         raise HTTPException(status_code=400, detail="Допустимы только jpg, png, webp")

#     ext = os.path.splitext(file.filename)[1] or ".jpg"
#     key = f"models/{model_id}/main_image/{uuid4()}{ext}"

#     data = await file.read()

#     try:
#         S3_CLIENT.put_object(
#             Bucket=BUCKET_NAME,
#             Key=key,
#             Body=data,
#             ContentType=file.content_type,
#             ACL="public-read",  # если нужно открывать по прямой ссылке
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Ошибка загрузки в S3: {e}")

#     # URL может отличаться, опирайтесь на endpoint из ЛК
#     file_url = f"{S3_ENDPOINT.rstrip('/')}/{BUCKET_NAME}/{key}"

#     # при необходимости — сохранить ссылку в БД
#     # пример (таблицу/поле подправьте под свою схему):
#     await db.execute(
#         "UPDATE models SET path_imd = %s WHERE id = %s",
#         (file_url, model_id),
#     )
#     await db.commit()

#     return {
#         "model_id": model_id,
#         "url": file_url,
#         "key": key,
#     }
@router.post("/add")
async def create_model(
    title: str = Form(...),
    russ_title: str = Form(...),
    slug: str = Form(...),
    brand_id: int = Form(...),
    brand_title: str = Form(...),
    file: UploadFile = File(...),
    db=Depends(get_db_conn),
):
    # 1. создаём запись модели без картинки
    await db.execute(
        """
        INSERT INTO models (title, russ_title, slug, brand_id, brand_title, path_img)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (title, russ_title, slug, brand_id, brand_title, None),
    )

    model_id = db.lastrowid

    if not model_id:
        raise HTTPException(status_code=500, detail="Не удалось получить ID модели")

    # 2. валидация файла
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Допустимы только jpg, png, webp")

    ext = os.path.splitext(file.filename)[1] or ".jpg"
    key = f"models/{model_id}/main_image/{uuid4()}{ext}"

    data = await file.read()

    # 3. загрузка в S3
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

    # 4. обновляем модель ссылкой на картинку
    await db.execute(
        "UPDATE models SET path_img = %s WHERE id = %s",
        (file_url, model_id),
    )

    # 5. получаем список моделей
    await db.execute("SELECT * FROM models ORDER BY brand_title ASC, title ASC")
    models = await db.fetchall()

    await db.connection.commit()

    return {
        "models": models,
    }



@router.post("/change")
async def change_model(
    id: int = Form(...),
    title: str = Form(...),
    russ_title: str = Form(...),
    slug: str = Form(...),
    is_active: bool = Form(...),
    file: UploadFile = File(None),  # файл необязательный
    db=Depends(get_db_conn),
):
    # 1. проверяем, существует ли модель
    await db.execute(
        "SELECT id, path_img FROM models WHERE id = %s",
        (id,),
    )
    model = await db.fetchone()

    if not model:
        raise HTTPException(status_code=404, detail="Модель не найдена")

    file_url = model["path_img"]

    # 2. если передан файл — загружаем новый
    if file:
        if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
            raise HTTPException(status_code=400, detail="Допустимы только jpg, png, webp")

        ext = os.path.splitext(file.filename)[1] or ".jpg"
        key = f"models/{id}/main_image/{uuid4()}{ext}"

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

    # 3. обновляем модель
    await db.execute(
        """
        UPDATE models
        SET title = %s,
            russ_title = %s,
            slug = %s,
            path_img = %s,
            is_active = %s
        WHERE id = %s
        """,
        (title, russ_title, slug, file_url, is_active, id),
    )

    await db.connection.commit()

    await db.execute(
        """
        SELECT *
        FROM models
        WHERE id = %s
        """,
        (id,),
    )

    models = await db.fetchone()

    return models


@router.post("/delete")
async def delete_model(
    request: Request,
    db=Depends(get_db_conn),
):
    data = await request.json()
    model_id = data.get("id")

    if not model_id:
        raise HTTPException(status_code=400, detail="model_id обязателен")

    # 1. получаем модель
    await db.execute(
        "SELECT id, path_img FROM models WHERE id=%s",
        (model_id,)
    )
    model = await db.fetchone()

    if not model:
        raise HTTPException(
            status_code=404,
            detail="Модель не найдена"
        )

    file_url = model["path_img"]

    # 2. удаляем файл из S3 (если есть)
    if file_url:
        try:
            key = file_url.split(f"{BUCKET_NAME}/", 1)[1]

            S3_CLIENT.delete_object(
                Bucket=BUCKET_NAME,
                Key=key
            )
        except Exception as e:
            print("Ошибка удаления файла S3:", e)

    # 3. каскадно удаляем машины и связи проектов
    await _cascade_delete_model(model_id, db)

    # 4. удаляем модель из БД
    await db.execute(
        "DELETE FROM models WHERE id=%s",
        (model_id,)
    )

    await db.connection.commit()

    # 4. возвращаем обновлённый список моделей
    await db.execute(
        "SELECT * FROM models ORDER BY brand_title ASC, title ASC"
    )
    models = await db.fetchall()

    return {
        "models": models
    }