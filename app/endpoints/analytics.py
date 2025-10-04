from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_public
from app.services.producto import ProductoService
from app.services.analytics import AnalyticsService
from app.schemas.analytics import TopImportadoresRequest, ImportadorDetalleRequest


router = APIRouter()

@router.get("/products")
async def productos_unicos(db: AsyncSession = Depends(get_db_public)):
    """Devuelve todos los nombres de productos únicos"""
    nombres = await ProductoService.get_unique_names(db)
    return {"productos": nombres}

@router.post("/top-importadores")
async def top_importadores(
    request: TopImportadoresRequest,
    db: AsyncSession = Depends(get_db_public)
):
    resultados = await AnalyticsService.top_importadores_por_producto(
        db=db,
        producto_nombre=request.producto,
        n=request.n_importadores,
        fecha_inicio=request.fecha_inicio,
        fecha_fin=request.fecha_fin
    )
    return resultados

@router.post("/detalle-importador")
async def detalle_importador(
    request: ImportadorDetalleRequest,
    db: AsyncSession = Depends(get_db_public)
):
    if not request.rut and not request.nombre:
        raise HTTPException(status_code=400, detail="Se requiere al menos rut o nombre del importador")

    resultados = await AnalyticsService.detalle_importador(
        db=db,
        rut=request.rut,
        nombre=request.nombre,
        fecha_inicio=request.fecha_inicio,
        fecha_fin=request.fecha_fin
    )
    return resultados