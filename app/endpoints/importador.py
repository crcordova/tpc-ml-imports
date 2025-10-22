from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.importador import ImportadorCreate, ImportadorResponse
from app.services.importador import ImportadorService
from app.database import get_db_public

router = APIRouter()

@router.post("/", response_model=ImportadorResponse)
async def create_importador(
    importador: ImportadorCreate,
    db: AsyncSession = Depends(get_db_public)
):
    """Crea un nuevo importador"""
    return await ImportadorService.create(db, importador)


@router.get("/", response_model=list[ImportadorResponse])
async def list_importadores(
    db: AsyncSession = Depends(get_db_public)
):
    """Lista todos los importadores"""
    return await ImportadorService.get_all(db)


@router.get("/{importador_id}", response_model=ImportadorResponse)
async def get_importador(
    importador_id: int,
    db: AsyncSession = Depends(get_db_public)
):
    """Obtiene un importador por ID"""
    result = await ImportadorService.get_by_id(db, importador_id)
    if not result:
        raise HTTPException(status_code=404, detail="Importador no encontrado")
    return result

@router.get("/product/{product_name}", response_model=list[ImportadorResponse])
async def get_importers_by_product(
    product_name: str,
    db: AsyncSession = Depends(get_db_public)
):
    """Obtiene todos los importadores que han importado el producto consultado"""
    result = await ImportadorService.get_by_product(db, product_name)
    if not result:
        raise HTTPException(status_code=404, detail=f"There not importers for the product {product_name}")
    return result


@router.put("/{importador_id}", response_model=ImportadorResponse)
async def update_importador(
    importador_id: int,
    importador: ImportadorCreate,
    db: AsyncSession = Depends(get_db_public)
):
    """Actualiza un importador"""
    result = await ImportadorService.update(db, importador_id, importador.dict())
    if not result:
        raise HTTPException(status_code=404, detail="Importador no encontrado")
    return result


@router.delete("/{importador_id}")
async def delete_importador(
    importador_id: int,
    db: AsyncSession = Depends(get_db_public)
):
    """Elimina un importador"""
    success = await ImportadorService.delete(db, importador_id)
    if not success:
        raise HTTPException(status_code=404, detail="Importador no encontrado")
    return {"ok": True}
