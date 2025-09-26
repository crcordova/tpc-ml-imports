from fastapi import APIRouter, Depends, HTTPException
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
