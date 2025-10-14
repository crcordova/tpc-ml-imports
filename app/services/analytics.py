from sqlalchemy import select, func, and_, or_, extract
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date as dt_date
from datetime import datetime, timedelta
from typing import List, Optional
from dateutil.relativedelta import relativedelta
from app.tables.importacion import Importacion 
from app.tables.importador import Importador
from app.tables.producto import Producto
from app.tables.pais import Pais
from app.utils.analytics import build_histogram

class AnalyticsService:

    @staticmethod
    async def top_importadores_por_producto(
        db: AsyncSession,
        producto_nombre: str,
        n: int,
        fecha_inicio,
        fecha_fin
    ):
        """
        Devuelve los N importadores que más importaron un producto en un rango de fechas.
        """
        conditions = [Producto.nombre_generico == producto_nombre]

        if fecha_inicio:
            conditions.append(Importacion.fecha >= fecha_inicio)
        if fecha_fin:
            conditions.append(Importacion.fecha <= fecha_fin)

        stmt = (
            select(
                Importador.nombre,
                Importador.rut,
                func.sum(Importacion.cantidad).label("total_cantidad")
            )
            .join(Importacion, Importacion.importador_id == Importador.id)
            .join(Producto, Producto.id == Importacion.producto_id)
            .where(and_(*conditions))
            .group_by(Importador.id)
            .order_by(func.sum(Importacion.cantidad).desc())
            .limit(n)
        )

        result = await db.execute(stmt)
        rows = result.fetchall()
        # Convertimos a lista de diccionarios
        return [
            {"nombre": r[0], "rut": r[1], "value": r[2]}
            for r in rows
        ]

    @staticmethod
    async def detalle_importador(
        db: AsyncSession,
        ruts: list[str] | None = None,
        nombres: list[str] | None = None,
        fecha_inicio: dt_date | None = None,
        fecha_fin: dt_date | None = None
    ):
        if not ruts and not nombres:
            raise ValueError("Se requiere al menos una lista de RUTs o nombres de importador")

        if fecha_inicio and isinstance(fecha_inicio, str):
            fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()

        if fecha_fin and isinstance(fecha_fin, str):
            fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        # Si solo hay fecha inicio, fecha_fin = hoy
        if fecha_inicio and not fecha_fin:
            fecha_fin = dt_date.today()

        stmt = (
            select(
                Importador.nombre.label("importador_nombre"),
                Importador.rut.label("importador_rut"),
                Producto.nombre_generico,
                Producto.marca,
                Producto.variedad,
                func.sum(Importacion.cantidad).label("cantidad_total"),
                func.sum(Importacion.fob_total).label("fob_total"),
                (
                    func.sum(Importacion.fob_unit * Importacion.cantidad)
                    / func.sum(Importacion.cantidad)
                ).label("fob_unit_ponderado"),
                func.max(Importacion.fob_unit).label("fob_unit_max"),
                func.min(Importacion.fob_unit).label("fob_unit_min")
            )
            .join(Importacion, Importacion.importador_id == Importador.id)
            .join(Producto, Producto.id == Importacion.producto_id)
        )

        # 🔹 Filtros dinámicos
        conditions = []
        if ruts:
            conditions.append(Importador.rut.in_(ruts))
        if nombres:
            # usamos ilike para coincidencias parciales
            conditions.append(or_(*[Importador.nombre.ilike(f"%{n}%") for n in nombres]))
        if fecha_inicio:
            conditions.append(Importacion.fecha >= fecha_inicio)
        if fecha_fin:
            conditions.append(Importacion.fecha <= fecha_fin)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.group_by(
            Importador.id,
            Producto.id
        ).order_by(func.sum(Importacion.cantidad).desc())

        result = await db.execute(stmt)
        rows = result.fetchall()

        # 🔹 Agrupar por importador
        data = {}
        for r in rows:
            nombre = r.importador_nombre
            rut = r.importador_rut
            if rut not in data:
                data[rut] = {
                    "nombre": nombre,
                    "rut": rut,
                    "detalle": []
                }

            data[rut]["detalle"].append({
                "producto": r.nombre_generico,
                "marca": r.marca,
                "variedad": r.variedad,
                "cantidad_total": r.cantidad_total,
                "fob_total": r.fob_total,
                "fob_unit_ponderado": r.fob_unit_ponderado,
                "fob_unit_max": r.fob_unit_max,
                "fob_unit_min": r.fob_unit_min
            })

        return list(data.values())
    
    @staticmethod
    async def top_importadores_detail(
        db: AsyncSession,
        producto_nombre: str,
        n: int = 5,
        fecha_start: Optional[str] = None,
        fecha_end: Optional[str] = None
    ):
        # Construir filtros base
        filters = [Producto.nombre_generico.ilike(f"%{producto_nombre}%")]
        
        if fecha_start:
            filters.append(Importacion.fecha >= datetime.strptime(fecha_start, "%Y-%m-%d").date())
        if fecha_end:
            filters.append(Importacion.fecha <= datetime.strptime(fecha_end, "%Y-%m-%d").date())
        
        # 1. Obtener top N importadores por cantidad total
        stmt_top = (
            select(
                Importador.id,
                Importador.nombre,
                Importador.rut,
                func.sum(Importacion.cantidad).label('total_cantidad')
            )
            .join(Importacion, Importacion.importador_id == Importador.id)
            .join(Producto, Importacion.producto_id == Producto.id)
            .where(and_(*filters))
            .group_by(Importador.id, Importador.nombre, Importador.rut)
            .order_by(func.sum(Importacion.cantidad).desc())
            .limit(n)
        )
        
        result = await db.execute(stmt_top)
        top_importadores = result.all()
        
        if not top_importadores:
            return []
        
        # Extraer IDs de los top importadores
        importador_ids = [imp.id for imp in top_importadores]
        
        # 2. Obtener detalle por países para estos importadores
        stmt_paises = (
            select(
                Importacion.importador_id,
                Pais.nombre.label('pais_nombre'),
                func.sum(Importacion.cantidad).label('cantidad_pais')
            )
            .join(Producto, Importacion.producto_id == Producto.id)
            .join(Pais, Importacion.pais_origen_id == Pais.id)
            .where(
                and_(
                    Importacion.importador_id.in_(importador_ids),
                    *filters
                )
            )
            .group_by(Importacion.importador_id, Pais.nombre)
        )
        
        result_paises = await db.execute(stmt_paises)
        paises_data = result_paises.all()
        
        # 3. Obtener detalle por marcas para estos importadores
        stmt_marcas = (
            select(
                Importacion.importador_id,
                Producto.marca,
                func.sum(Importacion.cantidad).label('cantidad_marca')
            )
            .join(Producto, Importacion.producto_id == Producto.id)
            .where(
                and_(
                    Importacion.importador_id.in_(importador_ids),
                    Producto.marca.isnot(None),  # Excluir marcas NULL
                    *filters
                )
            )
            .group_by(Importacion.importador_id, Producto.marca)
        )
        
        result_marcas = await db.execute(stmt_marcas)
        marcas_data = result_marcas.all()
        
        # 4. Organizar datos en diccionarios para fácil acceso
        paises_por_importador = {}
        for row in paises_data:
            if row.importador_id not in paises_por_importador:
                paises_por_importador[row.importador_id] = {}
            paises_por_importador[row.importador_id][row.pais_nombre] = float(row.cantidad_pais or 0)
        
        marcas_por_importador = {}
        for row in marcas_data:
            if row.importador_id not in marcas_por_importador:
                marcas_por_importador[row.importador_id] = {}
            marcas_por_importador[row.importador_id][row.marca] = float(row.cantidad_marca or 0)
        
        # 5. Construir respuesta final
        response = []
        for imp in top_importadores:
            response.append({
                "nombre": imp.nombre,
                "rut": imp.rut,
                "total_cantidad": float(imp.total_cantidad or 0),
                "detalle": {
                    "paises": paises_por_importador.get(imp.id, {}),
                    "marcas": marcas_por_importador.get(imp.id, {})
                }
            })
        
        return response
    
    @staticmethod
    async def importador_detalle_plus(
        db: AsyncSession,
        rut: str,
        fecha_start: Optional[str] = None,
        fecha_end: Optional[str] = None
    ):
        # Construir filtros base
        filters = [Importador.rut == rut]
        
        if fecha_start:
            filters.append(Importacion.fecha >= datetime.strptime(fecha_start, "%Y-%m-%d").date())
        if fecha_end:
            filters.append(Importacion.fecha <= datetime.strptime(fecha_end, "%Y-%m-%d").date())
        
        # 1. Verificar que el importador existe y obtener sus datos
        stmt_importador = select(Importador).where(Importador.rut == rut)
        result_imp = await db.execute(stmt_importador)
        importador = result_imp.scalar_one_or_none()
        
        if not importador:
            return {"error": "Importador no encontrado"}
        
        # 2. Obtener agregaciones por Producto -> País -> Marca
        stmt_detalle = (
            select(
                Producto.id.label('producto_id'),
                Producto.nombre_generico.label('producto_nombre'),
                Producto.partida_arancelaria,
                Pais.id.label('pais_id'),
                Pais.nombre.label('pais_nombre'),
                Producto.marca,
                # Agregaciones
                func.sum(Importacion.cantidad).label('cantidad_total'),
                func.sum(Importacion.fob_total).label('fob_total'),
                # Para promedio ponderado y min/max
                func.sum(Importacion.fob_total).label('sum_fob'),
                func.sum(Importacion.cantidad).label('sum_cantidad'),
                func.min(Importacion.fob_unit).label('fob_unit_min'),
                func.max(Importacion.fob_unit).label('fob_unit_max')
            )
            .join(Importacion, Importacion.producto_id == Producto.id)
            .join(Importador, Importacion.importador_id == Importador.id)
            .outerjoin(Pais, Importacion.pais_origen_id == Pais.id)
            .where(and_(*filters))
            .group_by(
                Producto.id,
                Producto.nombre_generico,
                Producto.partida_arancelaria,
                Pais.id,
                Pais.nombre,
                Producto.marca
            )
            .order_by(
                Producto.nombre_generico,
                Pais.nombre,
                Producto.marca
            )
        )
        
        result_detalle = await db.execute(stmt_detalle)
        rows = result_detalle.all()
        
        # 3. Organizar datos jerárquicamente
        productos_dict = {}
        
        for row in rows:
            # Calcular promedio ponderado
            fob_unit_promedio = None
            if row.sum_cantidad and row.sum_cantidad > 0:
                fob_unit_promedio = row.sum_fob / row.sum_cantidad
            
            # Nivel Producto
            if row.producto_id not in productos_dict:
                productos_dict[row.producto_id] = {
                    "producto_nombre": row.producto_nombre,
                    "partida_arancelaria": row.partida_arancelaria,
                    "paises": {}
                }
            
            # Nivel País
            pais_key = row.pais_nombre or "SIN_PAIS"
            if pais_key not in productos_dict[row.producto_id]["paises"]:
                productos_dict[row.producto_id]["paises"][pais_key] = {
                    "marcas": {}
                }
            
            # Nivel Marca
            marca_key = row.marca or "SIN_MARCA"
            productos_dict[row.producto_id]["paises"][pais_key]["marcas"][marca_key] = {
                "cantidad_total": float(row.cantidad_total or 0),
                "fob_total": float(row.fob_total or 0),
                "fob_unit": {
                    "minimo": float(row.fob_unit_min) if row.fob_unit_min else None,
                    "maximo": float(row.fob_unit_max) if row.fob_unit_max else None,
                    "promedio_ponderado": float(fob_unit_promedio) if fob_unit_promedio else None
                }
            }
        
        # 4. Calcular totales por país (sumando todas las marcas)
        for producto_id, producto_data in productos_dict.items():
            for pais_nombre, pais_data in producto_data["paises"].items():
                total_cantidad_pais = sum(
                    marca_data["cantidad_total"] 
                    for marca_data in pais_data["marcas"].values()
                )
                total_fob_pais = sum(
                    marca_data["fob_total"] 
                    for marca_data in pais_data["marcas"].values()
                )
                
                # Calcular promedio ponderado a nivel país
                fob_unit_promedio_pais = None
                if total_cantidad_pais > 0:
                    fob_unit_promedio_pais = total_fob_pais / total_cantidad_pais
                
                # Obtener min/max a nivel país
                fob_units_pais = [
                    m["fob_unit"]["minimo"] 
                    for m in pais_data["marcas"].values() 
                    if m["fob_unit"]["minimo"] is not None
                ]
                
                pais_data["total_cantidad"] = total_cantidad_pais
                pais_data["total_fob"] = total_fob_pais
                pais_data["fob_unit_promedio_ponderado"] = fob_unit_promedio_pais
                pais_data["fob_unit_minimo"] = min(fob_units_pais) if fob_units_pais else None
                pais_data["fob_unit_maximo"] = max(fob_units_pais) if fob_units_pais else None
        
        # 5. Calcular totales por producto (sumando todos los países)
        for producto_id, producto_data in productos_dict.items():
            total_cantidad_producto = sum(
                pais_data["total_cantidad"]
                for pais_data in producto_data["paises"].values()
            )
            total_fob_producto = sum(
                pais_data["total_fob"]
                for pais_data in producto_data["paises"].values()
            )
            
            # Promedio ponderado a nivel producto
            fob_unit_promedio_producto = None
            if total_cantidad_producto > 0:
                fob_unit_promedio_producto = total_fob_producto / total_cantidad_producto
            
            producto_data["total_cantidad"] = total_cantidad_producto
            producto_data["total_fob"] = total_fob_producto
            producto_data["fob_unit_promedio_ponderado"] = fob_unit_promedio_producto
        
        # 6. Construir respuesta final
        productos_list = []
        for producto_id, producto_data in productos_dict.items():
            paises_list = []
            for pais_nombre, pais_data in producto_data["paises"].items():
                paises_list.append({
                    "pais_nombre": pais_nombre,
                    "total_cantidad": pais_data["total_cantidad"],
                    "total_fob": pais_data["total_fob"],
                    "fob_unit": {
                        "minimo": pais_data.get("fob_unit_minimo"),
                        "maximo": pais_data.get("fob_unit_maximo"),
                        "promedio_ponderado": pais_data.get("fob_unit_promedio_ponderado")
                    },
                    "marcas": [
                        {
                            "marca_nombre": marca_nombre,
                            **marca_data
                        }
                        for marca_nombre, marca_data in pais_data["marcas"].items()
                    ]
                })
            
            productos_list.append({
                "producto_nombre": producto_data["producto_nombre"],
                "partida_arancelaria": producto_data["partida_arancelaria"],
                "total_cantidad": producto_data["total_cantidad"],
                "total_fob": producto_data["total_fob"],
                "fob_unit_promedio_ponderado": producto_data["fob_unit_promedio_ponderado"],
                "paises": paises_list
            })
        
        return {
            "importador": {
                "rut": importador.rut,
                "nombre": importador.nombre,
                "industria": importador.industria
            },
            "productos": productos_list
        }

    @staticmethod
    async def get_fob_unit_histogram(
            db: AsyncSession, 
            producto_nombre: str, 
            fecha_start: str = None, 
            fecha_end: str = None, 
            bins: int = 10):
        """
        Obtiene un histograma de los valores unitarios FOB de un producto en un rango de fechas.
        """
        query = select(Importacion.fob_unit, Importacion.cantidad).join(Producto).where(Producto.nombre_generico == producto_nombre)

        if fecha_start:
            query = query.where(Importacion.fecha >= fecha_start)
        if fecha_end:
            query = query.where(Importacion.fecha <= fecha_end)

        result = await db.execute(query)
        rows = result.fetchall()

        data = [(row.fob_unit, row.cantidad) for row in rows if row.fob_unit is not None and row.cantidad is not None]

        return build_histogram(data, bin_width=1)
        

    @staticmethod
    async def get_fob_unit_by_importadores(
        db: AsyncSession,
        producto_nombre: str,
        importadores_rut: List[str],
        fecha_start: Optional[str] = None,
        fecha_end: Optional[str] = None
    ):
        query = (
            select(
                Importacion.fob_unit,
                Importacion.cantidad,
                Importador.rut
            )
            .join(Producto)
            .join(Importador)
            .where(Producto.nombre_generico == producto_nombre)
            .where(Importador.rut.in_(importadores_rut))
        )

        if fecha_start:
            query = query.where(Importacion.fecha >= fecha_start)
        if fecha_end:
            query = query.where(Importacion.fecha <= fecha_end)

        result = await db.execute(query)
        rows = result.all()

        # Filtramos nulos
        # data = [
        #     {"rut": row.rut, "fob_unit": row.fob_unit, "cantidad": row.cantidad}
        #     for row in rows
        #     if row.fob_unit is not None and row.cantidad is not None
        # ]
        # return data
        result = []
        for row in rows:
            if row.fob_unit is not None and row.rut is not None:
                result.append({
                    "group": row.rut,  # RUT del importador
                    "value": float(row.fob_unit)  # Cada precio individual
                })
        return result
    
    #------------PRICING  ANALYTICS ----------------#
    @staticmethod
    async def evolucion_precios(
        db: AsyncSession,
        producto_nombre: str,
        granularidad: str = "month",
        agrupar_por: str = "global",
        fecha_start: Optional[str] = None,
        fecha_end: Optional[str] = None
    ):
        """Evolución temporal de precios FOB unitarios"""
        
        filters = [
            Producto.nombre_generico.ilike(f"%{producto_nombre}%"),
            Importacion.cantidad.isnot(None),
            Importacion.cantidad > 0,
            Importacion.fob_total.isnot(None)
        ]
        
        if fecha_start:
            filters.append(Importacion.fecha >= datetime.strptime(fecha_start, "%Y-%m-%d").date())
        if fecha_end:
            filters.append(Importacion.fecha <= datetime.strptime(fecha_end, "%Y-%m-%d").date())
        
        # Configurar agrupación temporal
        if granularidad == "month":
            year_col = extract('year', Importacion.fecha)
            month_col = extract('month', Importacion.fecha)
            time_group = [year_col, month_col]
            time_select = [
                year_col.label('year'),
                month_col.label('month')
            ]
        else:  # quarter
            year_col = extract('year', Importacion.fecha)
            quarter_col = extract('quarter', Importacion.fecha)
            time_group = [year_col, quarter_col]
            time_select = [
                year_col.label('year'),
                quarter_col.label('quarter')
            ]
        
        # Configurar agrupación adicional
        additional_group = []
        additional_select = []
        
        if agrupar_por == "pais":
            additional_group = [Pais.id, Pais.nombre]
            additional_select = [
                Pais.id.label('pais_id'),
                Pais.nombre.label('pais_nombre')
            ]
            filters.append(Importacion.pais_origen_id.isnot(None))
        elif agrupar_por == "marca":
            additional_group = [Producto.marca]
            additional_select = [Producto.marca.label('marca')]
            filters.append(Producto.marca.isnot(None))
        
        # Construir query
        stmt = (
            select(
                *time_select,
                *additional_select,
                func.sum(Importacion.fob_total).label('sum_fob'),
                func.sum(Importacion.cantidad).label('sum_cantidad'),
                func.min(Importacion.fob_unit).label('fob_unit_min'),
                func.max(Importacion.fob_unit).label('fob_unit_max'),
                func.count(Importacion.id).label('num_transacciones')
            )
            .join(Producto, Importacion.producto_id == Producto.id)
        )
        
        if agrupar_por == "pais":
            stmt = stmt.join(Pais, Importacion.pais_origen_id == Pais.id)
        
        stmt = (
            stmt.where(and_(*filters))
            .group_by(*time_group, *additional_group)
            .order_by(*time_group, *additional_group)
        )
        
        result = await db.execute(stmt)
        rows = result.all()
        
        # Procesar resultados
        if agrupar_por == "global":
            serie_temporal = []
            for row in rows:
                if granularidad == "month":
                    periodo = f"{int(row.year)}-{int(row.month):02d}"
                else:
                    periodo = f"{int(row.year)}-Q{int(row.quarter)}"
                
                fob_promedio_ponderado = row.sum_fob / row.sum_cantidad if row.sum_cantidad > 0 else None
                
                serie_temporal.append({
                    "periodo": periodo,
                    "fob_unit_promedio_ponderado": round(fob_promedio_ponderado, 4) if fob_promedio_ponderado else None,
                    "fob_unit_min": float(row.fob_unit_min) if row.fob_unit_min else None,
                    "fob_unit_max": float(row.fob_unit_max) if row.fob_unit_max else None,
                    "cantidad_total": float(row.sum_cantidad),
                    "num_transacciones": int(row.num_transacciones)
                })
            
            return {
                "producto": producto_nombre,
                "granularidad": granularidad,
                "agrupacion": agrupar_por,
                "serie_temporal": serie_temporal
            }
        
        else:  # Agrupado por país o marca
            datos_agrupados = {}
            
            for row in rows:
                if granularidad == "month":
                    periodo = f"{int(row.year)}-{int(row.month):02d}"
                else:
                    periodo = f"{int(row.year)}-Q{int(row.quarter)}"
                
                grupo_key = row.pais_nombre if agrupar_por == "pais" else row.marca
                
                if grupo_key not in datos_agrupados:
                    datos_agrupados[grupo_key] = []
                
                fob_promedio_ponderado = row.sum_fob / row.sum_cantidad if row.sum_cantidad > 0 else None
                
                datos_agrupados[grupo_key].append({
                    "periodo": periodo,
                    "fob_unit_promedio_ponderado": round(fob_promedio_ponderado, 4) if fob_promedio_ponderado else None,
                    "fob_unit_min": float(row.fob_unit_min) if row.fob_unit_min else None,
                    "fob_unit_max": float(row.fob_unit_max) if row.fob_unit_max else None,
                    "cantidad_total": float(row.sum_cantidad),
                    "num_transacciones": int(row.num_transacciones)
                })
            
            series = []
            for grupo_key, datos in datos_agrupados.items():
                series.append({
                    agrupar_por: grupo_key,
                    "serie_temporal": datos
                })
            
            return {
                "producto": producto_nombre,
                "granularidad": granularidad,
                "agrupacion": agrupar_por,
                "series": series
            }
    
    @staticmethod
    async def comparativa_paises(
        db: AsyncSession,
        producto_nombre: str,
        fecha_start: Optional[str] = None,
        fecha_end: Optional[str] = None,
        min_transacciones: int = 3
    ):
        """Compara precios FOB por país de origen"""
        
        filters = [
            Producto.nombre_generico.ilike(f"%{producto_nombre}%"),
            Importacion.pais_origen_id.isnot(None),
            Importacion.cantidad.isnot(None),
            Importacion.cantidad > 0,
            Importacion.fob_total.isnot(None)
        ]
        
        if fecha_start:
            filters.append(Importacion.fecha >= datetime.strptime(fecha_start, "%Y-%m-%d").date())
        if fecha_end:
            filters.append(Importacion.fecha <= datetime.strptime(fecha_end, "%Y-%m-%d").date())
        
        stmt = (
            select(
                Pais.nombre.label('pais_nombre'),
                func.sum(Importacion.fob_total).label('sum_fob'),
                func.sum(Importacion.cantidad).label('sum_cantidad'),
                func.min(Importacion.fob_unit).label('fob_unit_min'),
                func.max(Importacion.fob_unit).label('fob_unit_max'),
                func.count(Importacion.id).label('num_transacciones'),
                func.count(func.distinct(Importacion.importador_id)).label('num_importadores')
            )
            .join(Producto, Importacion.producto_id == Producto.id)
            .join(Pais, Importacion.pais_origen_id == Pais.id)
            .where(and_(*filters))
            .group_by(Pais.nombre)
            .having(func.count(Importacion.id) >= min_transacciones)
        )
        
        result = await db.execute(stmt)
        rows = result.all()
        
        # Calcular totales
        cantidad_total_mercado = sum(row.sum_cantidad for row in rows)
        
        # Procesar por país
        paises = []
        for row in rows:
            fob_promedio_ponderado = row.sum_fob / row.sum_cantidad if row.sum_cantidad > 0 else None
            share_cantidad = (row.sum_cantidad / cantidad_total_mercado * 100) if cantidad_total_mercado > 0 else 0
            
            paises.append({
                "pais": row.pais_nombre,
                "fob_unit": {
                    "promedio_ponderado": round(fob_promedio_ponderado, 4) if fob_promedio_ponderado else None,
                    "minimo": float(row.fob_unit_min) if row.fob_unit_min else None,
                    "maximo": float(row.fob_unit_max) if row.fob_unit_max else None,
                    "rango": round(row.fob_unit_max - row.fob_unit_min, 4) if row.fob_unit_min and row.fob_unit_max else None
                },
                "volumen": {
                    "cantidad_total": float(row.sum_cantidad),
                    "fob_total": float(row.sum_fob),
                    "share_mercado_porcentaje": round(share_cantidad, 2)
                },
                "num_transacciones": int(row.num_transacciones),
                "num_importadores": int(row.num_importadores)
            })
        
        # Ordenar por cantidad
        paises.sort(key=lambda x: x["volumen"]["cantidad_total"], reverse=True)
        
        # Encontrar país más competitivo (menor precio con volumen significativo)
        # Consideramos solo países con al menos 5% del mercado
        paises_relevantes = [p for p in paises if p["volumen"]["share_mercado_porcentaje"] >= 5]
        
        pais_mas_competitivo = None
        if paises_relevantes:
            pais_mas_competitivo = min(
                paises_relevantes, 
                key=lambda x: x["fob_unit"]["promedio_ponderado"] if x["fob_unit"]["promedio_ponderado"] else float('inf')
            )["pais"]
        
        return {
            "producto": producto_nombre,
            "total_paises": len(paises),
            "pais_mas_competitivo": pais_mas_competitivo,
            "comparativa_paises": paises
        }
    #------------COMPETENCIA ANALYTICS ----------------#
    @staticmethod
    async def marcas_dominantes(
        db: AsyncSession,
        producto_nombre: str,
        top_n: int = 10,
        fecha_start: Optional[str] = None,
        fecha_end: Optional[str] = None,
        incluir_tendencia: bool = True
    ):
        """Ranking de marcas por producto"""
        
        filters = [
            Producto.nombre_generico.ilike(f"%{producto_nombre}%"),
            Producto.marca.isnot(None)
        ]
        
        if fecha_start:
            filters.append(Importacion.fecha >= datetime.strptime(fecha_start, "%Y-%m-%d").date())
        if fecha_end:
            filters.append(Importacion.fecha <= datetime.strptime(fecha_end, "%Y-%m-%d").date())
        
        # Obtener total del mercado
        stmt_total = (
            select(func.sum(Importacion.cantidad).label('mercado_total'))
            .join(Producto, Importacion.producto_id == Producto.id)
            .where(and_(*filters))
        )
        
        result_total = await db.execute(stmt_total)
        mercado_total = result_total.scalar() or 0
        
        # Obtener top marcas
        stmt_marcas = (
            select(
                Producto.marca,
                func.sum(Importacion.cantidad).label('cantidad_total'),
                func.sum(Importacion.fob_total).label('fob_total'),
                func.count(func.distinct(Importacion.importador_id)).label('num_importadores'),
                func.count(Importacion.id).label('num_transacciones')
            )
            .join(Importacion, Importacion.producto_id == Producto.id)
            .where(and_(*filters))
            .group_by(Producto.marca)
            .order_by(func.sum(Importacion.cantidad).desc())
            .limit(top_n)
        )
        
        result_marcas = await db.execute(stmt_marcas)
        marcas = result_marcas.all()
        
        marcas_list = []
        
        for marca in marcas:
            share = (marca.cantidad_total / mercado_total * 100) if mercado_total > 0 else 0
            
            marca_data = {
                "marca": marca.marca,
                "cantidad_total": float(marca.cantidad_total or 0),
                "fob_total": float(marca.fob_total or 0),
                "market_share_porcentaje": round(share, 2),
                "num_importadores": int(marca.num_importadores),
                "num_transacciones": int(marca.num_transacciones)
            }
            
            # Obtener top 3 importadores de esta marca
            stmt_top_imp = (
                select(
                    Importador.rut,
                    Importador.nombre,
                    func.sum(Importacion.cantidad).label('cantidad')
                )
                .join(Importacion, Importacion.importador_id == Importador.id)
                .join(Producto, Importacion.producto_id == Producto.id)
                .where(and_(
                    Producto.marca == marca.marca,
                    *filters
                ))
                .group_by(Importador.rut, Importador.nombre)
                .order_by(func.sum(Importacion.cantidad).desc())
                .limit(3)
            )
            
            result_top_imp = await db.execute(stmt_top_imp)
            top_importadores = result_top_imp.all()
            
            marca_data["principales_importadores"] = [
                {
                    "rut": imp.rut,
                    "nombre": imp.nombre,
                    "cantidad": float(imp.cantidad)
                }
                for imp in top_importadores
            ]
            
            # Calcular tendencia si se solicita
            if incluir_tendencia and fecha_end:
                fecha_end_dt = datetime.strptime(fecha_end, "%Y-%m-%d").date()
                
                if fecha_start:
                    fecha_start_dt = datetime.strptime(fecha_start, "%Y-%m-%d").date()
                else:
                    fecha_start_dt = fecha_end_dt - relativedelta(years=1)
                
                dias_total = (fecha_end_dt - fecha_start_dt).days
                fecha_mid = fecha_start_dt + timedelta(days=dias_total // 2)
                
                # Primera mitad
                stmt_p1 = (
                    select(func.sum(Importacion.cantidad).label('cantidad'))
                    .join(Producto, Importacion.producto_id == Producto.id)
                    .where(and_(
                        Producto.marca == marca.marca,
                        Producto.nombre_generico.ilike(f"%{producto_nombre}%"),
                        Importacion.fecha >= fecha_start_dt,
                        Importacion.fecha < fecha_mid
                    ))
                )
                
                result_p1 = await db.execute(stmt_p1)
                cantidad_p1 = result_p1.scalar() or 0
                
                # Segunda mitad
                stmt_p2 = (
                    select(func.sum(Importacion.cantidad).label('cantidad'))
                    .join(Producto, Importacion.producto_id == Producto.id)
                    .where(and_(
                        Producto.marca == marca.marca,
                        Producto.nombre_generico.ilike(f"%{producto_nombre}%"),
                        Importacion.fecha >= fecha_mid,
                        Importacion.fecha <= fecha_end_dt
                    ))
                )
                
                result_p2 = await db.execute(stmt_p2)
                cantidad_p2 = result_p2.scalar() or 0
                
                if cantidad_p1 > 0:
                    crecimiento = ((cantidad_p2 - cantidad_p1) / cantidad_p1) * 100
                    marca_data["tendencia"] = {
                        "crecimiento_porcentaje": round(crecimiento, 2),
                        "interpretacion": (
                            "Creciendo fuertemente" if crecimiento > 30 else
                            "Creciendo" if crecimiento > 0 else
                            "Estable" if crecimiento > -10 else
                            "Decreciendo"
                        )
                    }
                else:
                    marca_data["tendencia"] = {
                        "crecimiento_porcentaje": None,
                        "interpretacion": "Sin datos suficientes"
                    }
            
            marcas_list.append(marca_data)
        
        return {
            "producto": producto_nombre,
            "mercado_total_cantidad": float(mercado_total),
            "total_marcas": len(marcas_list),
            "marcas": marcas_list
        }
    
    @staticmethod
    async def paises_origen(
        db: AsyncSession,
        producto_nombre: str,
        fecha_start: Optional[str] = None,
        fecha_end: Optional[str] = None,
        incluir_evolucion: bool = True,
        meses_evolucion: int = 12
    ):
        """Análisis de países proveedores"""
        
        filters = [
            Producto.nombre_generico.ilike(f"%{producto_nombre}%"),
            Importacion.pais_origen_id.isnot(None)
        ]
        
        if fecha_start:
            filters.append(Importacion.fecha >= datetime.strptime(fecha_start, "%Y-%m-%d").date())
        if fecha_end:
            filters.append(Importacion.fecha <= datetime.strptime(fecha_end, "%Y-%m-%d").date())
        
        # Obtener estadísticas por país
        stmt_paises = (
            select(
                Pais.id.label('pais_id'),
                Pais.nombre.label('pais_nombre'),
                func.sum(Importacion.cantidad).label('cantidad_total'),
                func.sum(Importacion.fob_total).label('fob_total'),
                func.count(func.distinct(Importacion.importador_id)).label('num_importadores'),
                func.count(Importacion.id).label('num_transacciones'),
                # Para precio promedio ponderado
                func.sum(Importacion.fob_total).label('sum_fob'),
                func.sum(Importacion.cantidad).label('sum_cantidad')
            )
            .join(Producto, Importacion.producto_id == Producto.id)
            .join(Pais, Importacion.pais_origen_id == Pais.id)
            .where(and_(*filters))
            .group_by(Pais.id, Pais.nombre)
            .order_by(func.sum(Importacion.cantidad).desc())
        )
        
        result_paises = await db.execute(stmt_paises)
        paises_data = result_paises.all()
        
        # Calcular total del mercado
        mercado_total = sum(p.cantidad_total for p in paises_data)
        
        paises_list = []
        
        for pais in paises_data:
            share = (pais.cantidad_total / mercado_total * 100) if mercado_total > 0 else 0
            fob_promedio = pais.sum_fob / pais.sum_cantidad if pais.sum_cantidad > 0 else None
            
            pais_info = {
                "pais": pais.pais_nombre,
                "volumen": {
                    "cantidad_total": float(pais.cantidad_total or 0),
                    "fob_total": float(pais.fob_total or 0),
                    "market_share_porcentaje": round(share, 2)
                },
                "precio": {
                    "fob_unit_promedio": round(fob_promedio, 4) if fob_promedio else None
                },
                "num_importadores": int(pais.num_importadores),
                "num_transacciones": int(pais.num_transacciones)
            }
            
            # Calcular evolución si se solicita
            if incluir_evolucion:
                fecha_actual = datetime.now().date()
                fecha_inicio_evolucion = fecha_actual - relativedelta(months=meses_evolucion)
                
                # Agrupar por trimestre
                stmt_evolucion = (
                    select(
                        extract('year', Importacion.fecha).label('year'),
                        extract('quarter', Importacion.fecha).label('quarter'),
                        func.sum(Importacion.cantidad).label('cantidad')
                    )
                    .join(Producto, Importacion.producto_id == Producto.id)
                    .where(and_(
                        Importacion.pais_origen_id == pais.pais_id,
                        Producto.nombre_generico.ilike(f"%{producto_nombre}%"),
                        Importacion.fecha >= fecha_inicio_evolucion
                    ))
                    .group_by(extract('year', Importacion.fecha), extract('quarter', Importacion.fecha))
                    .order_by(extract('year', Importacion.fecha), extract('quarter', Importacion.fecha))
                )
                
                result_evol = await db.execute(stmt_evolucion)
                evolucion_data = result_evol.all()
                
                evolucion_trimestral = [
                    {
                        "periodo": f"{int(row.year)}-Q{int(row.quarter)}",
                        "cantidad": float(row.cantidad)
                    }
                    for row in evolucion_data
                ]
                
                # Calcular tendencia simple (primera vs última mitad)
                if len(evolucion_trimestral) >= 2:
                    mid = len(evolucion_trimestral) // 2
                    cantidad_inicial = sum(e["cantidad"] for e in evolucion_trimestral[:mid])
                    cantidad_reciente = sum(e["cantidad"] for e in evolucion_trimestral[mid:])
                    
                    if cantidad_inicial > 0:
                        cambio = ((cantidad_reciente - cantidad_inicial) / cantidad_inicial) * 100
                        tendencia = "Ganando share" if cambio > 10 else "Estable" if cambio > -10 else "Perdiendo share"
                    else:
                        tendencia = "Nuevo proveedor"
                    
                    pais_info["evolucion"] = {
                        "trimestral": evolucion_trimestral,
                        "tendencia": tendencia
                    }
            
            paises_list.append(pais_info)
        
        return {
            "producto": producto_nombre,
            "mercado_total_cantidad": float(mercado_total),
            "total_paises": len(paises_list),
            "paises": paises_list
        }
                        
    #------------MERCADO ANALYTICS ----------------#                
    @staticmethod
    async def tendencias_producto(
        db: AsyncSession,
        producto_nombre: str,
        granularidad: str = "month",
        fecha_start: Optional[str] = None,
        fecha_end: Optional[str] = None
    ):
        """Evolución temporal de importaciones"""
        
        filters = [Producto.nombre_generico.ilike(f"%{producto_nombre}%")]
        
        if fecha_start:
            filters.append(Importacion.fecha >= datetime.strptime(fecha_start, "%Y-%m-%d").date())
        if fecha_end:
            filters.append(Importacion.fecha <= datetime.strptime(fecha_end, "%Y-%m-%d").date())
        
        # Determinar agrupación temporal
        if granularidad == "month":
            year_col = extract('year', Importacion.fecha)
            month_col = extract('month', Importacion.fecha)
            group_cols = [year_col, month_col]
            select_cols = [
                year_col.label('year'),
                month_col.label('month')
            ]
        elif granularidad == "quarter":
            year_col = extract('year', Importacion.fecha)
            quarter_col = extract('quarter', Importacion.fecha)
            group_cols = [year_col, quarter_col]
            select_cols = [
                year_col.label('year'),
                quarter_col.label('quarter')
            ]
        else:  # year
            year_col = extract('year', Importacion.fecha)
            group_cols = [year_col]
            select_cols = [year_col.label('year')]
        
        stmt = (
            select(
                *select_cols,
                func.sum(Importacion.cantidad).label('cantidad_total'),
                func.sum(Importacion.fob_total).label('fob_total'),
                func.count(func.distinct(Importacion.importador_id)).label('num_importadores'),
                func.count(Importacion.id).label('num_transacciones')
            )
            .join(Producto, Importacion.producto_id == Producto.id)
            .where(and_(*filters))
            .group_by(*group_cols)
            .order_by(*group_cols)
        )
        
        result = await db.execute(stmt)
        rows = result.all()
        
        # Formatear respuesta
        serie_temporal = []
        for row in rows:
            if granularidad == "month":
                periodo = f"{int(row.year)}-{int(row.month):02d}"
            elif granularidad == "quarter":
                periodo = f"{int(row.year)}-Q{int(row.quarter)}"
            else:
                periodo = str(int(row.year))
            
            serie_temporal.append({
                "periodo": periodo,
                "cantidad_total": float(row.cantidad_total or 0),
                "fob_total": float(row.fob_total or 0),
                "num_importadores": int(row.num_importadores or 0),
                "num_transacciones": int(row.num_transacciones or 0)
            })
        
        return {
            "producto": producto_nombre,
            "granularidad": granularidad,
            "serie_temporal": serie_temporal
        }
    
        
    
    @staticmethod
    async def share_importadores(
        db: AsyncSession,
        producto_nombre: str,
        top_n: int = 10,
        fecha_start: Optional[str] = None,
        fecha_end: Optional[str] = None,
        incluir_crecimiento: bool = True
    ):
        """Market share de importadores por producto"""
        
        filters = [Producto.nombre_generico.ilike(f"%{producto_nombre}%")]
        
        if fecha_start:
            filters.append(Importacion.fecha >= datetime.strptime(fecha_start, "%Y-%m-%d").date())
        if fecha_end:
            filters.append(Importacion.fecha <= datetime.strptime(fecha_end, "%Y-%m-%d").date())
        
        # Obtener total del mercado
        stmt_total = (
            select(func.sum(Importacion.cantidad).label('mercado_total'))
            .join(Producto, Importacion.producto_id == Producto.id)
            .where(and_(*filters))
        )
        
        result_total = await db.execute(stmt_total)
        mercado_total = result_total.scalar() or 0
        
        # Obtener top importadores
        stmt_importadores = (
            select(
                Importador.id,
                Importador.rut,
                Importador.nombre,
                Importador.industria,
                func.sum(Importacion.cantidad).label('cantidad_total'),
                func.sum(Importacion.fob_total).label('fob_total')
            )
            .join(Importacion, Importacion.importador_id == Importador.id)
            .join(Producto, Importacion.producto_id == Producto.id)
            .where(and_(*filters))
            .group_by(Importador.id, Importador.rut, Importador.nombre, Importador.industria)
            .order_by(func.sum(Importacion.cantidad).desc())
            .limit(top_n)
        )
        
        result_imp = await db.execute(stmt_importadores)
        importadores = result_imp.all()
        
        # Calcular crecimiento si se solicita
        crecimiento_data = {}
        if incluir_crecimiento and fecha_end:
            fecha_end_dt = datetime.strptime(fecha_end, "%Y-%m-%d").date()
            
            # Calcular punto medio del rango
            if fecha_start:
                fecha_start_dt = datetime.strptime(fecha_start, "%Y-%m-%d").date()
            else:
                # Si no hay fecha_start, usar 1 año antes de fecha_end
                fecha_start_dt = fecha_end_dt - relativedelta(years=1)
            
            dias_total = (fecha_end_dt - fecha_start_dt).days
            fecha_mid = fecha_start_dt + timedelta(days=dias_total // 2)
            
            # Primera mitad vs segunda mitad
            for imp in importadores:
                # Primera mitad
                stmt_primera = (
                    select(func.sum(Importacion.cantidad).label('cantidad'))
                    .join(Producto, Importacion.producto_id == Producto.id)
                    .where(and_(
                        Importacion.importador_id == imp.id,
                        Producto.nombre_generico.ilike(f"%{producto_nombre}%"),
                        Importacion.fecha >= fecha_start_dt,
                        Importacion.fecha < fecha_mid
                    ))
                )
                
                result_primera = await db.execute(stmt_primera)
                cantidad_primera = result_primera.scalar() or 0
                
                # Segunda mitad
                stmt_segunda = (
                    select(func.sum(Importacion.cantidad).label('cantidad'))
                    .join(Producto, Importacion.producto_id == Producto.id)
                    .where(and_(
                        Importacion.importador_id == imp.id,
                        Producto.nombre_generico.ilike(f"%{producto_nombre}%"),
                        Importacion.fecha >= fecha_mid,
                        Importacion.fecha <= fecha_end_dt
                    ))
                )
                
                result_segunda = await db.execute(stmt_segunda)
                cantidad_segunda = result_segunda.scalar() or 0
                
                # Calcular % crecimiento
                if cantidad_primera > 0:
                    crecimiento_pct = ((cantidad_segunda - cantidad_primera) / cantidad_primera) * 100
                else:
                    crecimiento_pct = None
                
                crecimiento_data[imp.id] = {
                    "cantidad_periodo_1": float(cantidad_primera),
                    "cantidad_periodo_2": float(cantidad_segunda),
                    "crecimiento_porcentaje": round(crecimiento_pct, 2) if crecimiento_pct is not None else None
                }
        
        # Construir respuesta
        top_importadores = []
        otros_cantidad = mercado_total
        
        for imp in importadores:
            share = (imp.cantidad_total / mercado_total * 100) if mercado_total > 0 else 0
            otros_cantidad -= imp.cantidad_total
            
            imp_data = {
                "rut": imp.rut,
                "nombre": imp.nombre,
                "industria": imp.industria,
                "cantidad_total": float(imp.cantidad_total or 0),
                "fob_total": float(imp.fob_total or 0),
                "market_share_porcentaje": round(share, 2)
            }
            
            if incluir_crecimiento and imp.id in crecimiento_data:
                imp_data["crecimiento"] = crecimiento_data[imp.id]
            
            top_importadores.append(imp_data)
        
        # Calcular HHI (Herfindahl-Hirschman Index)
        hhi = sum((imp.cantidad_total / mercado_total * 100) ** 2 for imp in importadores if mercado_total > 0)
        
        return {
            "producto": producto_nombre,
            "mercado_total_cantidad": float(mercado_total),
            "concentracion_hhi": round(hhi, 2),
            "interpretacion_hhi": (
                "Mercado altamente concentrado" if hhi > 2500 else
                "Mercado moderadamente concentrado" if hhi > 1500 else
                "Mercado competitivo"
            ),
            "top_importadores": top_importadores,
            "otros_market_share_porcentaje": round((otros_cantidad / mercado_total * 100) if mercado_total > 0 else 0, 2)
        }
    
    @staticmethod
    async def nuevos_importadores(
        db: AsyncSession,
        producto_nombre: str,
        meses_recientes: int = 6,
        min_cantidad: float = 0
    ):
        """Detecta importadores que empezaron a importar recientemente"""
        
        fecha_corte = datetime.now().date() - relativedelta(months=meses_recientes)
        
        # Obtener primera fecha de importación por importador para este producto
        stmt_primera = (
            select(
                Importador.id,
                Importador.rut,
                Importador.nombre,
                Importador.industria,
                func.min(Importacion.fecha).label('primera_importacion'),
                func.sum(Importacion.cantidad).label('cantidad_total'),
                func.sum(Importacion.fob_total).label('fob_total'),
                func.count(Importacion.id).label('num_transacciones')
            )
            .join(Importacion, Importacion.importador_id == Importador.id)
            .join(Producto, Importacion.producto_id == Producto.id)
            .where(Producto.nombre_generico.ilike(f"%{producto_nombre}%"))
            .group_by(Importador.id, Importador.rut, Importador.nombre, Importador.industria)
            .having(func.min(Importacion.fecha) >= fecha_corte)
        )
        
        if min_cantidad > 0:
            stmt_primera = stmt_primera.having(func.sum(Importacion.cantidad) >= min_cantidad)
        
        stmt_primera = stmt_primera.order_by(func.min(Importacion.fecha).desc())
        
        result = await db.execute(stmt_primera)
        nuevos = result.all()
        
        # Para cada nuevo importador, calcular tendencia (primeras 3 importaciones vs últimas 3)
        importadores_list = []
        
        for imp in nuevos:
            # Obtener detalle de importaciones
            stmt_detalle = (
                select(
                    Importacion.fecha,
                    Importacion.cantidad,
                    Importacion.fob_total
                )
                .join(Producto, Importacion.producto_id == Producto.id)
                .where(and_(
                    Importacion.importador_id == imp.id,
                    Producto.nombre_generico.ilike(f"%{producto_nombre}%")
                ))
                .order_by(Importacion.fecha)
            )
            
            result_detalle = await db.execute(stmt_detalle)
            transacciones = result_detalle.all()
            
            # Calcular tendencia si hay suficientes transacciones
            tendencia = None
            if len(transacciones) >= 4:
                mid_point = len(transacciones) // 2
                cantidad_inicial = sum(t.cantidad or 0 for t in transacciones[:mid_point])
                cantidad_reciente = sum(t.cantidad or 0 for t in transacciones[mid_point:])
                
                if cantidad_inicial > 0:
                    tendencia = ((cantidad_reciente - cantidad_inicial) / cantidad_inicial) * 100
            
            importadores_list.append({
                "rut": imp.rut,
                "nombre": imp.nombre,
                "industria": imp.industria,
                "primera_importacion": imp.primera_importacion.isoformat(),
                "cantidad_total": float(imp.cantidad_total or 0),
                "fob_total": float(imp.fob_total or 0),
                "num_transacciones": int(imp.num_transacciones),
                "tendencia_crecimiento_porcentaje": round(tendencia, 2) if tendencia is not None else None,
                "interpretacion_tendencia": (
                    "Creciendo rápidamente" if tendencia and tendencia > 50 else
                    "Creciendo" if tendencia and tendencia > 0 else
                    "Estable o decreciendo" if tendencia is not None else
                    "Datos insuficientes"
                )
            })
        
        return {
            "producto": producto_nombre,
            "periodo_analizado_meses": meses_recientes,
            "fecha_corte": fecha_corte.isoformat(),
            "total_nuevos_importadores": len(importadores_list),
            "nuevos_importadores": importadores_list
        }
    #------------PROSPECCION ANALYTICS ----------------#
    @staticmethod
    async def cambios_proveedores(
        db: AsyncSession,
        producto_nombre: str,
        meses_periodo_1: int = 6,
        meses_periodo_2: int = 6,
        umbral_cambio: float = 30.0
    ):
        """Detecta importadores que cambiaron de país proveedor"""
        
        fecha_actual = datetime.now().date()
        fecha_inicio_periodo_2 = fecha_actual - relativedelta(months=meses_periodo_2)
        fecha_inicio_periodo_1 = fecha_inicio_periodo_2 - relativedelta(months=meses_periodo_1)
        
        # Obtener importadores activos en ambos periodos
        stmt_importadores = (
            select(func.distinct(Importacion.importador_id))
            .join(Producto, Importacion.producto_id == Producto.id)
            .where(and_(
                Producto.nombre_generico.ilike(f"%{producto_nombre}%"),
                Importacion.fecha >= fecha_inicio_periodo_1
            ))
        )
        
        result_imp = await db.execute(stmt_importadores)
        importador_ids = [row[0] for row in result_imp.all()]
        
        cambios_detectados = []
        
        for importador_id in importador_ids:
            # Periodo 1 - análisis por país
            stmt_p1 = (
                select(
                    Pais.nombre.label('pais'),
                    func.sum(Importacion.cantidad).label('cantidad')
                )
                .join(Producto, Importacion.producto_id == Producto.id)
                .join(Pais, Importacion.pais_origen_id == Pais.id)
                .where(and_(
                    Importacion.importador_id == importador_id,
                    Producto.nombre_generico.ilike(f"%{producto_nombre}%"),
                    Importacion.fecha >= fecha_inicio_periodo_1,
                    Importacion.fecha < fecha_inicio_periodo_2
                ))
                .group_by(Pais.nombre)
            )
            
            result_p1 = await db.execute(stmt_p1)
            paises_p1 = {row.pais: float(row.cantidad) for row in result_p1.all()}
            
            # Periodo 2 - análisis por país
            stmt_p2 = (
                select(
                    Pais.nombre.label('pais'),
                    func.sum(Importacion.cantidad).label('cantidad')
                )
                .join(Producto, Importacion.producto_id == Producto.id)
                .join(Pais, Importacion.pais_origen_id == Pais.id)
                .where(and_(
                    Importacion.importador_id == importador_id,
                    Producto.nombre_generico.ilike(f"%{producto_nombre}%"),
                    Importacion.fecha >= fecha_inicio_periodo_2
                ))
                .group_by(Pais.nombre)
            )
            
            result_p2 = await db.execute(stmt_p2)
            paises_p2 = {row.pais: float(row.cantidad) for row in result_p2.all()}
            
            # Verificar si hubo actividad en ambos periodos
            if not paises_p1 or not paises_p2:
                continue
            
            total_p1 = sum(paises_p1.values())
            total_p2 = sum(paises_p2.values())
            
            # Calcular cambios en distribución
            todos_paises = set(paises_p1.keys()) | set(paises_p2.keys())
            cambios_significativos = []
            
            for pais in todos_paises:
                share_p1 = (paises_p1.get(pais, 0) / total_p1 * 100) if total_p1 > 0 else 0
                share_p2 = (paises_p2.get(pais, 0) / total_p2 * 100) if total_p2 > 0 else 0
                cambio = share_p2 - share_p1
                
                if abs(cambio) >= umbral_cambio:
                    cambios_significativos.append({
                        "pais": pais,
                        "share_periodo_1": round(share_p1, 2),
                        "share_periodo_2": round(share_p2, 2),
                        "cambio_puntos_porcentuales": round(cambio, 2),
                        "tipo_cambio": "aumento" if cambio > 0 else "disminucion"
                    })
            
            if cambios_significativos:
                # Obtener datos del importador
                stmt_imp_data = select(Importador).where(Importador.id == importador_id)
                result_imp_data = await db.execute(stmt_imp_data)
                importador = result_imp_data.scalar_one_or_none()
                
                if importador:
                    cambios_detectados.append({
                        "importador": {
                            "rut": importador.rut,
                            "nombre": importador.nombre,
                            "industria": importador.industria
                        },
                        "cantidad_periodo_1": total_p1,
                        "cantidad_periodo_2": total_p2,
                        "cambios_distribucion": cambios_significativos
                    })
        
        return {
            "producto": producto_nombre,
            "periodo_1": {
                "desde": fecha_inicio_periodo_1.isoformat(),
                "hasta": fecha_inicio_periodo_2.isoformat(),
                "meses": meses_periodo_1
            },
            "periodo_2": {
                "desde": fecha_inicio_periodo_2.isoformat(),
                "hasta": fecha_actual.isoformat(),
                "meses": meses_periodo_2
            },
            "umbral_cambio_porcentaje": umbral_cambio,
            "total_importadores_con_cambios": len(cambios_detectados),
            "importadores": cambios_detectados
        }
     
    @staticmethod
    async def lealtad_proveedor(
        db: AsyncSession,
        producto_nombre: str,
        fecha_start: Optional[str] = None,
        fecha_end: Optional[str] = None,
        min_transacciones: int = 3
    ):
        """Analiza diversificación y lealtad a países proveedores"""
        
        filters = [Producto.nombre_generico.ilike(f"%{producto_nombre}%")]
        
        if fecha_start:
            filters.append(Importacion.fecha >= datetime.strptime(fecha_start, "%Y-%m-%d").date())
        if fecha_end:
            filters.append(Importacion.fecha <= datetime.strptime(fecha_end, "%Y-%m-%d").date())
        
        # Obtener importadores con suficientes transacciones
        stmt_importadores = (
            select(
                Importador.id,
                Importador.rut,
                Importador.nombre,
                Importador.industria,
                func.count(Importacion.id).label('num_transacciones')
            )
            .join(Importacion, Importacion.importador_id == Importador.id)
            .join(Producto, Importacion.producto_id == Producto.id)
            .where(and_(*filters))
            .group_by(Importador.id, Importador.rut, Importador.nombre, Importador.industria)
            .having(func.count(Importacion.id) >= min_transacciones)
        )
        
        result_imp = await db.execute(stmt_importadores)
        importadores = result_imp.all()
        
        analisis_importadores = []
        
        for imp in importadores:
            # Obtener distribución por país
            stmt_paises = (
                select(
                    Pais.nombre,
                    func.sum(Importacion.cantidad).label('cantidad'),
                    func.count(Importacion.id).label('num_transacciones')
                )
                .join(Producto, Importacion.producto_id == Producto.id)
                .join(Pais, Importacion.pais_origen_id == Pais.id)
                .where(and_(
                    Importacion.importador_id == imp.id,
                    *filters
                ))
                .group_by(Pais.nombre)
            )
            
            result_paises = await db.execute(stmt_paises)
            paises_data = result_paises.all()
            
            if not paises_data:
                continue
            
            total_cantidad = sum(p.cantidad for p in paises_data)
            num_paises = len(paises_data)
            
            # Calcular índice de concentración (Herfindahl)
            concentracion = sum(
                (p.cantidad / total_cantidad * 100) ** 2 
                for p in paises_data
            ) if total_cantidad > 0 else 0
            
            # Identificar país principal
            pais_principal = max(paises_data, key=lambda x: x.cantidad)
            share_pais_principal = (pais_principal.cantidad / total_cantidad * 100) if total_cantidad > 0 else 0
            
            # Calcular frecuencia de cambio (analizar orden temporal)
            stmt_timeline = (
                select(
                    Importacion.fecha,
                    Pais.nombre
                )
                .join(Producto, Importacion.producto_id == Producto.id)
                .join(Pais, Importacion.pais_origen_id == Pais.id)
                .where(and_(
                    Importacion.importador_id == imp.id,
                    *filters
                ))
                .order_by(Importacion.fecha)
            )
            
            result_timeline = await db.execute(stmt_timeline)
            timeline = result_timeline.all()
            
            # Contar cambios de país consecutivos
            cambios = 0
            for i in range(1, len(timeline)):
                if timeline[i].nombre != timeline[i-1].nombre:
                    cambios += 1
            
            frecuencia_cambio = (cambios / len(timeline) * 100) if len(timeline) > 1 else 0
            
            # Clasificación de lealtad
            if concentracion > 7000:  # ~84% en un solo país
                tipo_lealtad = "Muy leal"
            elif concentracion > 5000:  # ~70% en un solo país
                tipo_lealtad = "Leal"
            elif concentracion > 3000:
                tipo_lealtad = "Moderadamente diversificado"
            else:
                tipo_lealtad = "Altamente diversificado"
            
            # Distribución por país
            distribucion_paises = [
                {
                    "pais": p.nombre,
                    "cantidad": float(p.cantidad),
                    "share_porcentaje": round((p.cantidad / total_cantidad * 100) if total_cantidad > 0 else 0, 2),
                    "num_transacciones": int(p.num_transacciones)
                }
                for p in sorted(paises_data, key=lambda x: x.cantidad, reverse=True)
            ]
            
            analisis_importadores.append({
                "importador": {
                    "rut": imp.rut,
                    "nombre": imp.nombre,
                    "industria": imp.industria
                },
                "metricas_lealtad": {
                    "num_paises": num_paises,
                    "indice_concentracion": round(concentracion, 2),
                    "tipo_lealtad": tipo_lealtad,
                    "pais_principal": pais_principal.nombre,
                    "share_pais_principal_porcentaje": round(share_pais_principal, 2),
                    "frecuencia_cambio_porcentaje": round(frecuencia_cambio, 2),
                    "num_cambios": cambios
                },
                "distribucion_paises": distribucion_paises,
                "num_transacciones_total": int(imp.num_transacciones)
            })
        
        # Ordenar por cantidad total (usar primer país como proxy)
        analisis_importadores.sort(
            key=lambda x: x["distribucion_paises"][0]["cantidad"] if x["distribucion_paises"] else 0,
            reverse=True
        )
        
        return {
            "producto": producto_nombre,
            "total_importadores_analizados": len(analisis_importadores),
            "importadores": analisis_importadores
        }
    #------------SEGMENTACION ANALYTICS ----------------#
    @staticmethod
    async def clasificar_importadores(
        db: AsyncSession,
        producto_nombre: str,
        fecha_start: Optional[str] = None,
        fecha_end: Optional[str] = None,
        min_transacciones: int = 2
    ):
        """Clasifica importadores por perfil de compra"""
        
        filters = [Producto.nombre_generico.ilike(f"%{producto_nombre}%")]
        
        if fecha_start:
            filters.append(Importacion.fecha >= datetime.strptime(fecha_start, "%Y-%m-%d").date())
        if fecha_end:
            fecha_end_dt = datetime.strptime(fecha_end, "%Y-%m-%d").date()
            filters.append(Importacion.fecha <= fecha_end_dt)
        else:
            fecha_end_dt = datetime.now().date()
        
        if fecha_start:
            fecha_start_dt = datetime.strptime(fecha_start, "%Y-%m-%d").date()
        else:
            fecha_start_dt = fecha_end_dt - relativedelta(years=1)
        
        dias_periodo = (fecha_end_dt - fecha_start_dt).days
        
        # Obtener datos de importadores
        stmt_importadores = (
            select(
                Importador.id,
                Importador.rut,
                Importador.nombre,
                Importador.industria,
                func.sum(Importacion.cantidad).label('cantidad_total'),
                func.sum(Importacion.fob_total).label('fob_total'),
                func.count(Importacion.id).label('num_transacciones'),
                func.count(func.distinct(Importacion.pais_origen_id)).label('num_paises'),
                func.count(func.distinct(Producto.marca)).label('num_marcas'),
                # Para calcular precio promedio ponderado
                (func.sum(Importacion.fob_total) / func.sum(Importacion.cantidad)).label('fob_unit_promedio')
            )
            .join(Importacion, Importacion.importador_id == Importador.id)
            .join(Producto, Importacion.producto_id == Producto.id)
            .where(and_(*filters))
            .group_by(Importador.id, Importador.rut, Importador.nombre, Importador.industria)
            .having(func.count(Importacion.id) >= min_transacciones)
        )
        
        result_imp = await db.execute(stmt_importadores)
        importadores_data = result_imp.all()
        
        if not importadores_data:
            return {
                "producto": producto_nombre,
                "total_importadores": 0,
                "segmentos": {},
                "importadores": []
            }
        
        # Calcular percentiles para segmentación
        cantidades = [imp.cantidad_total for imp in importadores_data]
        precios = [imp.fob_unit_promedio for imp in importadores_data if imp.fob_unit_promedio]
        
        # Calcular cuartiles
        cantidades_sorted = sorted(cantidades)
        precios_sorted = sorted(precios) if precios else []
        
        def percentil(data, p):
            if not data:
                return 0
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = k - f
            if f + 1 < len(data):
                return data[f] + c * (data[f + 1] - data[f])
            return data[f]
        
        q1_cantidad = percentil(cantidades_sorted, 25)
        q2_cantidad = percentil(cantidades_sorted, 50)
        q3_cantidad = percentil(cantidades_sorted, 75)
        
        q1_precio = percentil(precios_sorted, 25) if precios_sorted else 0
        q2_precio = percentil(precios_sorted, 50) if precios_sorted else 0
        q3_precio = percentil(precios_sorted, 75) if precios_sorted else 0
        
        # Clasificar cada importador
        importadores_clasificados = []
        
        for imp in importadores_data:
            # Clasificación por volumen
            if imp.cantidad_total >= q3_cantidad:
                segmento_volumen = "Alto volumen"
            elif imp.cantidad_total >= q2_cantidad:
                segmento_volumen = "Volumen medio"
            else:
                segmento_volumen = "Bajo volumen"
            
            # Clasificación por precio
            if imp.fob_unit_promedio and precios_sorted:
                if imp.fob_unit_promedio >= q3_precio:
                    segmento_precio = "Premium"
                elif imp.fob_unit_promedio >= q2_precio:
                    segmento_precio = "Precio medio"
                else:
                    segmento_precio = "Precio bajo"
            else:
                segmento_precio = "Sin datos"
            
            # Calcular frecuencia de importación (transacciones por mes)
            meses_periodo = max(dias_periodo / 30, 1)
            frecuencia = imp.num_transacciones / meses_periodo
            
            if frecuencia >= 1:
                segmento_frecuencia = "Alta frecuencia"
            elif frecuencia >= 0.3:
                segmento_frecuencia = "Frecuencia media"
            else:
                segmento_frecuencia = "Baja frecuencia"
            
            # Clasificación por diversificación
            if imp.num_paises >= 3 or imp.num_marcas >= 3:
                segmento_diversificacion = "Muy diversificado"
            elif imp.num_paises >= 2 or imp.num_marcas >= 2:
                segmento_diversificacion = "Moderadamente diversificado"
            else:
                segmento_diversificacion = "Concentrado"
            
            # Perfil combinado (simplificado)
            if segmento_volumen == "Alto volumen" and segmento_precio == "Precio bajo":
                perfil_principal = "Comprador masivo"
            elif segmento_volumen == "Alto volumen" and segmento_precio == "Premium":
                perfil_principal = "Comprador premium alto volumen"
            elif segmento_volumen in ["Volumen medio", "Bajo volumen"] and segmento_precio == "Premium":
                perfil_principal = "Comprador premium especializado"
            elif segmento_frecuencia == "Alta frecuencia":
                perfil_principal = "Comprador frecuente"
            elif segmento_frecuencia == "Baja frecuencia" and segmento_volumen == "Bajo volumen":
                perfil_principal = "Comprador ocasional"
            else:
                perfil_principal = "Comprador estándar"
            
            importadores_clasificados.append({
                "importador": {
                    "rut": imp.rut,
                    "nombre": imp.nombre,
                    "industria": imp.industria
                },
                "metricas": {
                    "cantidad_total": float(imp.cantidad_total or 0),
                    "fob_total": float(imp.fob_total or 0),
                    "fob_unit_promedio": round(float(imp.fob_unit_promedio), 4) if imp.fob_unit_promedio else None,
                    "num_transacciones": int(imp.num_transacciones),
                    "frecuencia_mensual": round(frecuencia, 2),
                    "num_paises": int(imp.num_paises),
                    "num_marcas": int(imp.num_marcas)
                },
                "segmentacion": {
                    "perfil_principal": perfil_principal,
                    "segmento_volumen": segmento_volumen,
                    "segmento_precio": segmento_precio,
                    "segmento_frecuencia": segmento_frecuencia,
                    "segmento_diversificacion": segmento_diversificacion
                }
            })
        
        # Ordenar por cantidad total
        importadores_clasificados.sort(
            key=lambda x: x["metricas"]["cantidad_total"],
            reverse=True
        )
        
        # Contar importadores por segmento
        conteo_perfiles = {}
        for imp in importadores_clasificados:
            perfil = imp["segmentacion"]["perfil_principal"]
            conteo_perfiles[perfil] = conteo_perfiles.get(perfil, 0) + 1
        
        # Calcular distribución de segmentos
        total_importadores = len(importadores_clasificados)
        distribucion_perfiles = [
            {
                "perfil": perfil,
                "cantidad": count,
                "porcentaje": round((count / total_importadores * 100), 2)
            }
            for perfil, count in sorted(conteo_perfiles.items(), key=lambda x: x[1], reverse=True)
        ]

