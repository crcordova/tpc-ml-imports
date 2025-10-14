from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db_public
from app.services.producto import ProductoService
from app.services.analytics import AnalyticsService
from app.schemas.analytics import TopImportadoresRequest, ImportadorDetalleRequest
from app.utils.analytics import build_boxplot_data


router = APIRouter()

@router.get("/products")
async def productos_unicos(db: AsyncSession = Depends(get_db_public)):
    """Devuelve todos los nombres de productos únicos"""
    nombres = await ProductoService.get_unique_names(db)
    return {"productos": nombres}

@router.get("/top-importadores")
async def top_importadores(
    producto_nombre: str,
    n: int = 5,
    fecha_start: str | None = None,
    fecha_end: str | None = None,
    db: AsyncSession = Depends(get_db_public)
):
    '''Top N importadores por producto en un rango de fechas'''
    resultados = await AnalyticsService.top_importadores_por_producto(
        db=db,
        producto_nombre=producto_nombre,
        n=n,
        fecha_inicio=fecha_start,
        fecha_fin=fecha_end
    )
    return resultados

@router.get("/top_importadores_detalle")
async def top_importadores_detalle(
    producto_nombre: str,
    n: int = 5,
    fecha_start: str | None = None,
    fecha_end: str | None = None,
    db: AsyncSession = Depends(get_db_public)
):
    '''Detalle de top N importadores por producto,  
    con detalle Pais y marca en un rango de fechas'''
    result = await AnalyticsService.top_importadores_detail(
        db, producto_nombre, n, fecha_start, fecha_end
    )
    return result

@router.get("/detalle-importador")
async def detalle_importador(
    ruts: List[str] = Query(default=None),
    nombres: List[str] = Query(default=None),
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
    db: AsyncSession = Depends(get_db_public)
):
    '''Detalle de importador por RUT o nombre  
    agrupa por producto marca y variedad devuelve valores fob_unit'''
    if not ruts and not nombres:
        raise HTTPException(status_code=400, detail="Se requiere al menos una lista de RUTs o nombres")

    resultados = await AnalyticsService.detalle_importador(
        db=db,
        ruts=ruts,
        nombres=nombres,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin
    )
    return resultados

@router.get("/importador_detalle/{rut}")
async def importador_detalle(
    rut: str,
    fecha_start: str | None = None,
    fecha_end: str | None = None,
    db: AsyncSession = Depends(get_db_public)
):
    '''Detalle de importador por RUT,   
    devuelve valores fob_unit y cantidad  
    agrupados por producto, pais, marca'''

    result = await AnalyticsService.importador_detalle_plus(
        db, rut, fecha_start, fecha_end
    )
    return result

@router.get("/histograma_fob_unit")
async def histograma_fob_unit(
    producto_nombre: str,
    fecha_start: str | None = None,
    fecha_end: str | None = None,
    db: AsyncSession = Depends(get_db_public)
):
    '''Genera el histogram de la distribucion de precios ponderado por cantidad de un producto dado'''
    histogram = await AnalyticsService.get_fob_unit_histogram(db, producto_nombre, fecha_start, fecha_end)
    return histogram

@router.get("/boxplot_fob_unit")
async def boxplot_fob_unit(
    producto_nombre: str,
    importadores_rut: list[str] = Query(..., description="Lista de RUTs de importadores"),
    fecha_start: str | None = None,
    fecha_end: str | None = None,
    db: AsyncSession = Depends(get_db_public)
):
    '''Genera los datos para un boxplot de distribucion de precios por importador,'''
    data = await AnalyticsService.get_fob_unit_by_importadores(db, producto_nombre, importadores_rut, fecha_start, fecha_end)
    box_data = build_boxplot_data(data)
    return box_data


@router.get("/mercado/tendencias-producto")
async def tendencias_producto(
    producto_nombre: str,
    granularidad: str = "month",  # month, quarter, year
    fecha_start: str | None = None,
    fecha_end: str | None = None,
    db: AsyncSession = Depends(get_db_public)
):
    """
    Evolución temporal de importaciones de un producto.
    Retorna series de tiempo de cantidad y fob_total agrupados por periodo.
    """
    result = await AnalyticsService.tendencias_producto(
        db, producto_nombre, granularidad, fecha_start, fecha_end
    )
    return result

@router.get("/mercado/share-importadores")
async def share_importadores(
    producto_nombre: str,
    top_n: int = 10,
    fecha_start: str | None = None,
    fecha_end: str | None = None,
    incluir_crecimiento: bool = True,
    db: AsyncSession = Depends(get_db_public)
):
    """
    Market share de importadores por producto.
    Incluye % del mercado y opcionalmente análisis de crecimiento.
    """
    result = await AnalyticsService.share_importadores(
        db, producto_nombre, top_n, fecha_start, fecha_end, incluir_crecimiento
    )
    return result

@router.get("/mercado/nuevos-importadores")
async def nuevos_importadores(
    producto_nombre: str,
    meses_recientes: int = 6,
    min_cantidad: float = 0,
    db: AsyncSession = Depends(get_db_public)
):
    """
    Detecta importadores que comenzaron a importar un producto recientemente.
    Muestra primera importación, volumen y tendencia.
    """
    result = await AnalyticsService.nuevos_importadores(
        db, producto_nombre, meses_recientes, min_cantidad
    )
    return result

@router.get("/pricing/evolucion-precios")
async def evolucion_precios(
    producto_nombre: str,
    granularidad: str = "month",  # month, quarter
    agrupar_por: str = "global",  # global, pais, marca
    fecha_start: str | None = None,
    fecha_end: str | None = None,
    db: AsyncSession = Depends(get_db_public)
):
    """
    Evolución temporal de precios FOB unitarios por producto.
    Puede agrupar por país de origen o marca.
    """
    result = await AnalyticsService.evolucion_precios(
        db, producto_nombre, granularidad, agrupar_por, fecha_start, fecha_end
    )
    return result

@router.get("/pricing/comparativa-paises")
async def comparativa_paises(
    producto_nombre: str,
    fecha_start: str | None = None,
    fecha_end: str | None = None,
    min_transacciones: int = 3,  # Mínimo de transacciones para incluir país
    db: AsyncSession = Depends(get_db_public)
):
    """
    Compara precios FOB unitarios por país de origen.
    Incluye estadísticas y volumen importado.
    """
    result = await AnalyticsService.comparativa_paises(
        db, producto_nombre, fecha_start, fecha_end, min_transacciones
    )
    return result

@router.get("/prospeccion/cambios-proveedores")
async def cambios_proveedores(
    producto_nombre: str,
    meses_periodo_1: int = 6,  # Periodo anterior
    meses_periodo_2: int = 6,  # Periodo reciente
    umbral_cambio: float = 30.0,  # % de cambio en país de origen
    db: AsyncSession = Depends(get_db_public)
):
    """
    Detecta importadores que cambiaron significativamente de país proveedor.
    Compara dos periodos consecutivos.
    """
    result = await AnalyticsService.cambios_proveedores(
        db, producto_nombre, meses_periodo_1, meses_periodo_2, umbral_cambio
    )
    return result

@router.get("/prospeccion/lealtad-proveedor")
async def lealtad_proveedor(
    producto_nombre: str,
    fecha_start: str | None = None,
    fecha_end: str | None = None,
    min_transacciones: int = 3,
    db: AsyncSession = Depends(get_db_public)
):
    """
    Analiza diversificación y lealtad de importadores a países proveedores.
    Calcula concentración y frecuencia de cambios.
    """
    result = await AnalyticsService.lealtad_proveedor(
        db, producto_nombre, fecha_start, fecha_end, min_transacciones
    )
    return result

@router.get("/competencia/marcas-dominantes")
async def marcas_dominantes(
    producto_nombre: str,
    top_n: int = 10,
    fecha_start: str | None = None,
    fecha_end: str | None = None,
    incluir_tendencia: bool = True,
    db: AsyncSession = Depends(get_db_public)
):
    """
    Ranking de marcas por producto con market share.
    Incluye tendencia y principales importadores de cada marca.
    """
    result = await AnalyticsService.marcas_dominantes(
        db, producto_nombre, top_n, fecha_start, fecha_end, incluir_tendencia
    )
    return result

@router.get("/competencia/paises-origen")
async def paises_origen(
    producto_nombre: str,
    fecha_start: str | None = None,
    fecha_end: str | None = None,
    incluir_evolucion: bool = True,
    meses_evolucion: int = 12,
    db: AsyncSession = Depends(get_db_public)
):
    """
    Análisis de países proveedores por producto.
    Incluye volumen, valor, precios y evolución temporal.
    """
    result = await AnalyticsService.paises_origen(
        db, producto_nombre, fecha_start, fecha_end, incluir_evolucion, meses_evolucion
    )
    return result

@router.get("/segmentacion/clasificar-importadores")
async def clasificar_importadores(
    producto_nombre: str,
    fecha_start: str | None = None,
    fecha_end: str | None = None,
    min_transacciones: int = 2,
    db: AsyncSession = Depends(get_db_public)
):
    """
    Clasifica importadores por perfil de compra.
    Segmenta por volumen, precio, frecuencia y diversificación.
    """
    result = await AnalyticsService.clasificar_importadores(
        db, producto_nombre, fecha_start, fecha_end, min_transacciones
    )
    return result