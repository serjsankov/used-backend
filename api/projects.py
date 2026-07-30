from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File, Form
from db.db import get_db_conn
from uuid import uuid4
from config import S3_CLIENT, BUCKET_NAME, S3_ENDPOINT
import os
from typing import List

router = APIRouter()

async def _enrich_projects(projects, db):
    """Обогащает список проектов данными о марках и моделях."""
    for project in projects:
        pid = project["id"]

        await db.execute(
            "SELECT b.id, b.title, b.russ_title, b.path_img, b.slug "
            "FROM brands b "
            "JOIN project_brands pb ON pb.brand_id = b.id "
            "WHERE pb.project_id = %s",
            (pid,),
        )
        project["brands"] = await db.fetchall()
        project["brands_count"] = len(project["brands"])

        await db.execute(
            "SELECT m.id, m.title, m.russ_title, m.path_img, m.slug, m.brand_title "
            "FROM models m "
            "JOIN project_models pm ON pm.model_id = m.id "
            "WHERE pm.project_id = %s",
            (pid,),
        )
        project["models"] = await db.fetchall()
        project["models_count"] = len(project["models"])
    return projects

async def _get_all_projects(db):
    """Возвращает все проекты с обогащёнными данными."""
    await db.execute("SELECT * FROM projects ORDER BY created_at ASC")
    projects = await db.fetchall()
    return await _enrich_projects(projects, db)


@router.get("/")
async def list_projects(db=Depends(get_db_conn)):
    return await _get_all_projects(db)


@router.post("/add")
async def create_project(
    request: Request,
    db=Depends(get_db_conn),
):
    data = await request.json()
    russ_name = data["title"]
    description = data["description"]

    # 1. создаём запись без slug
    await db.execute(
        """
        INSERT INTO projects (russ_name, description, slug)
        VALUES (%s, %s, %s)
        """,
        (russ_name, description, "temp"),
    )

    project_id = db.lastrowid

    # 2. формируем slug
    slug = f"project_{project_id}"

    # 3. обновляем slug
    await db.execute(
        "UPDATE projects SET slug=%s WHERE id=%s",
        (slug, project_id),
    )

    for brand_id in data["brand_ids"]:
        await db.execute(
            "INSERT INTO project_brands (project_id, brand_id) VALUES (%s, %s)",
            (project_id, brand_id),
        )

    for model_id in data["model_ids"]:
        await db.execute(
            "INSERT INTO project_models (project_id, model_id) VALUES (%s, %s)",
            (project_id, model_id),
        )

    await db.connection.commit()

    projects = await _get_all_projects(db)

    return {
        "projects": projects,
    }


@router.post("/change")
async def change_project(
    request: Request,
    db=Depends(get_db_conn),
):
    data = await request.json()
    project_id = data.get("id")
    russ_name = data.get("title")
    description = data.get("description")
    is_active = data.get("is_active")
    brand_ids = data.get("brand_ids")
    model_ids = data.get("model_ids")

    if not project_id:
        raise HTTPException(status_code=400, detail="id обязателен")

    # проверяем, существует ли проект
    await db.execute(
        "SELECT id FROM projects WHERE id = %s",
        (project_id,),
    )
    project = await db.fetchone()

    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    # обновляем проект
    await db.execute(
        """
        UPDATE projects
        SET russ_name = %s,
            description = %s,
            is_active = %s
        WHERE id = %s
        """,
        (russ_name, description, is_active, project_id),
    )

    # перезаписываем связи с марками
    if brand_ids is not None:
        await db.execute(
            "DELETE FROM project_brands WHERE project_id = %s",
            (project_id,),
        )
        for brand_id in brand_ids:
            await db.execute(
                "INSERT INTO project_brands (project_id, brand_id) VALUES (%s, %s)",
                (project_id, brand_id),
            )

    # перезаписываем связи с моделями
    if model_ids is not None:
        await db.execute(
            "DELETE FROM project_models WHERE project_id = %s",
            (project_id,),
        )
        for model_id in model_ids:
            await db.execute(
                "INSERT INTO project_models (project_id, model_id) VALUES (%s, %s)",
                (project_id, model_id),
            )

    await db.connection.commit()

    projects = await _get_all_projects(db)

    return {"projects": projects}


@router.post("/delete")
async def delete_project(
    request: Request,
    db=Depends(get_db_conn),
):
    data = await request.json()
    project_id = data.get("id")

    if not project_id:
        raise HTTPException(status_code=400, detail="id обязателен")

    # проверяем существование
    await db.execute(
        "SELECT id FROM projects WHERE id=%s",
        (project_id,)
    )
    project = await db.fetchone()

    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    # удаляем связи
    await db.execute(
        "DELETE FROM project_brands WHERE project_id=%s",
        (project_id,)
    )
    await db.execute(
        "DELETE FROM project_models WHERE project_id=%s",
        (project_id,)
    )

    # удаляем проект
    await db.execute(
        "DELETE FROM projects WHERE id=%s",
        (project_id,)
    )

    await db.connection.commit()

    projects = await _get_all_projects(db)

    return {"projects": projects}