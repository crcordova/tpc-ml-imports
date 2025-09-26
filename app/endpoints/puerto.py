from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.puerto import PuertoCreate, PuertoResponse
from app.services.puerto import PuertoService
from app.database import get_db_public

router = APIRouter()

@router.post("/", response_model=PuertoResponse)
async def create_puerto(puerto: PuertoCreate, db: AsyncSession = Depends(get_db_public)):
    return await PuertoService.create(db, puerto)

@router.get("/", response_model=list[PuertoResponse])
async def list_puertos(db: AsyncSession = Depends(get_db_public)):
    return await PuertoService.get_all(db)

@router.get("/{puerto_id}", response_model=PuertoResponse)
async def get_puerto(puerto_id: int, db: AsyncSession = Depends(get_db_public)):
    result = await PuertoService.get_by_id(db, puerto_id)
    if not result:
        raise HTTPException(status_code=404, detail="Puerto no encontrado")
    return result

@router.put("/{puerto_id}", response_model=PuertoResponse)
async def update_puerto(puerto_id: int, puerto: PuertoCreate, db: AsyncSession = Depends(get_db_public)):
    result = await PuertoService.update(db, puerto_id, puerto.dict())
    if not result:
        raise HTTPException(status_code=404, detail="Puerto no encontrado")
    return result

@router.delete("/{puerto_id}")
async def delete_puerto(puerto_id: int, db: AsyncSession = Depends(get_db_public)):
    success = await PuertoService.delete(db, puerto_id)
    if not success:
        raise HTTPException(status_code=404, detail="Puerto no encontrado")
    return {"ok": True}
