# api/feed.py
from fastapi import APIRouter, Depends, HTTPException
from db.db import get_db_conn
from config import FRONTEND_URLS

router = APIRouter()

@router.get("/{slug}")
async def project_feed(
    slug: str,
    db=Depends(get_db_conn),
):
    """Публичный фид проекта по slug. Не требует авторизации."""
    await db.execute(
        "SELECT * FROM projects WHERE slug = %s AND is_active = 1",
        (slug,),
    )
    project = await db.fetchone()

    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден или не активен")

    pid = project["id"]

    # Марки (только активные)
    await db.execute(
        "SELECT b.id, b.title, b.russ_title, b.path_img, b.slug "
        "FROM brands b "
        "JOIN project_brands pb ON pb.brand_id = b.id "
        "WHERE pb.project_id = %s AND b.is_active = 1",
        (pid,),
    )
    brands = await db.fetchall()
    active_brand_ids = [b["id"] for b in brands]

    # Модели (только активные и чьи марки активны)
    if active_brand_ids:
        placeholders = ",".join(["%s"] * len(active_brand_ids))
        await db.execute(
            f"SELECT m.id, m.title, m.russ_title, m.path_img, m.slug, m.brand_title "
            f"FROM models m "
            f"JOIN project_models pm ON pm.model_id = m.id "
            f"WHERE pm.project_id = %s AND m.is_active = 1 "
            f"AND m.brand_id IN ({placeholders})",
            (pid, *active_brand_ids),
        )
        models = await db.fetchall()
    else:
        models = []

    active_model_ids = [m["id"] for m in models]

    # Машины (только активных моделей)
    if active_model_ids:
        placeholders = ",".join(["%s"] * len(active_model_ids))
        await db.execute(
            f"SELECT c.id, c.brand_id, c.model_id, c.brand_title, c.model_title, "
            f"c.car_name, c.body_type, c.seats, c.mileage, c.engine, c.transmission, c.drive_type, "
            f"c.fuel_consumption, c.acceleration, c.year, c.color, c.photos "
            f"FROM cars c "
            f"WHERE c.model_id IN ({placeholders})",
            (*active_model_ids,),
        )
        cars = await db.fetchall()
    else:
        cars = []

    return {
        "project": {
            "id": project["id"],
            "title": project["russ_name"],
            "description": project["description"],
            "slug": project["slug"],
            "created_at": project["created_at"],
            "updated_at": project["updated_at"],
        },
        "brands": brands,
        "models": models,
        "cars": cars,
        "brands_count": len(brands),
        "models_count": len(models),
        "cars_count": len(cars),
    }