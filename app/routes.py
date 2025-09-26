from fastapi import APIRouter
from app.endpoints import importador, producto, pais, puerto, importacion, load_excel

api_router = APIRouter()

api_router.include_router(load_excel.router, prefix="/excel", tags=["Load Excel"])
api_router.include_router(importador.router, prefix="/importadores", tags=["Importadores"])
api_router.include_router(producto.router, prefix="/productos", tags=["Productos"])
api_router.include_router(pais.router, prefix="/paises", tags=["Paises"])
api_router.include_router(puerto.router, prefix="/puertos", tags=["Puertos"])
api_router.include_router(importacion.router, prefix="/importaciones", tags=["Importaciones"])
