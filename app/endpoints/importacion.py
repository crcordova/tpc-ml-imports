from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.importacion import ImportacionCreate, ImportacionResponse
from app.services.importacion import ImportacionService
from app.database import get_db_public

router = APIRouter()

@router.post("/", response_model=ImportacionResponse)
async def create_importacion(importacion: ImportacionCreate, db: AsyncSession = Depends(get_db_public)):
    return await ImportacionService.create(db, importacion)

@router.get("/", response_model=list[ImportacionResponse])
async def list_importaciones(db: AsyncSession = Depends(get_db_public)):
    return await ImportacionService.get_all(db)

@router.get("/{importacion_id}", response_model=ImportacionResponse)
async def get_importacion(importacion_id: int, db: AsyncSession = Depends(get_db_public)):
    result = await ImportacionService.get_by_id(db, importacion_id)
    if not result:
        raise HTTPException(status_code=404, detail="Importacion no encontrada")
    return result


@router.get("/query/")
async def listar_importaciones(
    fecha_start: date | None = Query(None, description="Fecha inicial (YYYY-MM-DD)"),
    fecha_end: date | None = Query(None, description="Fecha final (YYYY-MM-DD)"),
    nombre_importador: str | None = Query(None),
    rut_importador: str | None = Query(None),
    producto: str | None = Query(None),
    pais_origen: str | None = Query(None),
    db: AsyncSession = Depends(get_db_public)
):
    # Si hay fecha inicio pero no fecha fin → usar hoy
    if fecha_start and not fecha_end:
        fecha_end = datetime.now().date()

    data = await ImportacionService.get_importaciones(
        db=db,
        fecha_start=fecha_start,
        fecha_end=fecha_end,
        nombre_importador=nombre_importador,
        rut_importador=rut_importador,
        producto=producto,
        pais_origen=pais_origen
    )
    return {"count": len(data), "results": data}

@router.put("/{importacion_id}", response_model=ImportacionResponse)
async def update_importacion(importacion_id: int, importacion: ImportacionCreate, db: AsyncSession = Depends(get_db_public)):
    result = await ImportacionService.update(db, importacion_id, importacion.dict())
    if not result:
        raise HTTPException(status_code=404, detail="Importacion no encontrada")
    return result

@router.delete("/{importacion_id}")
async def delete_importacion(importacion_id: int, db: AsyncSession = Depends(get_db_public)):
    success = await ImportacionService.delete(db, importacion_id)
    if not success:
        raise HTTPException(status_code=404, detail="Importacion no encontrada")
    return {"ok": True}
