from fastapi import APIRouter, Depends
from db.db import get_db_conn

router = APIRouter()

@router.post("/brand-project/")
async def brand_project_data(db=Depends(get_db_conn)):
    await db.execute("""
        SELECT id, russ_name, description, slug, created_at, updated_at, is_active
        FROM projects
        ORDER BY created_at ASC
    """)
    projects = await db.fetchall()

    await db.execute("""
        SELECT *
        FROM project_brands
    """)
    project_brands = await db.fetchall()

    await db.execute("""
        SELECT *
        FROM project_models
    """)
    project_models = await db.fetchall()

    return {
        "projects": projects,
        "project_brands": project_brands,
        "project_models": project_models,
    }
