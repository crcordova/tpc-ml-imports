from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.pais import PaisCreate, PaisResponse
from app.services.pais import PaisService
from app.database import get_db_public

router = APIRouter()

@router.post("/", response_model=PaisResponse)
async def create_pais(pais: PaisCreate, db: AsyncSession = Depends(get_db_public)):
    return await PaisService.create(db, pais)

@router.get("/", response_model=list[PaisResponse])
async def list_paises(db: AsyncSession = Depends(get_db_public)):
    return await PaisService.get_all(db)

@router.get("/{pais_id}", response_model=PaisResponse)
async def get_pais(pais_id: int, db: AsyncSession = Depends(get_db_public)):
    result = await PaisService.get_by_id(db, pais_id)
    if not result:
        raise HTTPException(status_code=404, detail="Pais no encontrado")
    return result

@router.put("/{pais_id}", response_model=PaisResponse)
async def update_pais(pais_id: int, pais: PaisCreate, db: AsyncSession = Depends(get_db_public)):
    result = await PaisService.update(db, pais_id, pais.dict())
    if not result:
        raise HTTPException(status_code=404, detail="Pais no encontrado")
    return result

@router.delete("/{pais_id}")
async def delete_pais(pais_id: int, db: AsyncSession = Depends(get_db_public)):
    success = await PaisService.delete(db, pais_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pais no encontrado")
    return {"ok": True}
