from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.producto import ProductoCreate, ProductoResponse
from app.services.producto import ProductoService
from app.database import get_db_public

router = APIRouter()

@router.post("/", response_model=ProductoResponse)
async def create_producto(producto: ProductoCreate, db: AsyncSession = Depends(get_db_public)):
    return await ProductoService.create(db, producto)

@router.get("/", response_model=list[ProductoResponse])
async def list_productos(db: AsyncSession = Depends(get_db_public)):
    return await ProductoService.get_all(db)

@router.get("/{producto_id}", response_model=ProductoResponse)
async def get_producto(producto_id: int, db: AsyncSession = Depends(get_db_public)):
    result = await ProductoService.get_by_id(db, producto_id)
    if not result:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return result

@router.put("/{producto_id}", response_model=ProductoResponse)
async def update_producto(producto_id: int, producto: ProductoCreate, db: AsyncSession = Depends(get_db_public)):
    result = await ProductoService.update(db, producto_id, producto.dict())
    if not result:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return result

@router.delete("/{producto_id}")
async def delete_producto(producto_id: int, db: AsyncSession = Depends(get_db_public)):
    success = await ProductoService.delete(db, producto_id)
    if not success:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"ok": True}
