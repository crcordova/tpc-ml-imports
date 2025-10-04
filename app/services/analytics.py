from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date as dt_date
from app.tables.importacion import Importacion 
from app.tables.importador import Importador
from app.tables.producto import Producto

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
        stmt = (
            select(
                Importador.nombre,
                Importador.rut,
                func.sum(Importacion.cantidad).label("total_cantidad")
            )
            .join(Importacion, Importacion.importador_id == Importador.id)
            .join(Producto, Producto.id == Importacion.producto_id)
            .where(
                Producto.nombre_generico == producto_nombre,
                Importacion.fecha >= fecha_inicio,
                Importacion.fecha <= fecha_fin
            )
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
        rut: str = None,
        nombre: str = None,
        fecha_inicio: dt_date = None,
        fecha_fin: dt_date = None
    ):
        if not rut and not nombre:
            raise ValueError("Se requiere al menos rut o nombre del importador")

        # Si solo hay fecha inicio, fecha_fin = hoy
        if fecha_inicio and not fecha_fin:
            fecha_fin = dt_date.today()

        stmt = (
            select(
                Producto.nombre_generico,
                Producto.marca,
                Producto.variedad,
                func.sum(Importacion.cantidad).label("cantidad_total"),
                func.sum(Importacion.fob_total).label("fob_total"),
                (func.sum(Importacion.fob_unit * Importacion.cantidad) / func.sum(Importacion.cantidad)).label("fob_unit_ponderado"),
                func.max(Importacion.fob_unit).label("fob_unit_max"),
                func.min(Importacion.fob_unit).label("fob_unit_min")
            )
            .join(Importacion, Importacion.producto_id == Producto.id)
            .join(Importador, Importacion.importador_id == Importador.id)
        )

        # Filtros
        if rut:
            stmt = stmt.where(Importador.rut == rut)
        if nombre:
            stmt = stmt.where(Importador.nombre.ilike(f"%{nombre}%"))
        if fecha_inicio:
            stmt = stmt.where(Importacion.fecha >= fecha_inicio)
        if fecha_fin:
            stmt = stmt.where(Importacion.fecha <= fecha_fin)

        stmt = stmt.group_by(Producto.id).order_by(func.sum(Importacion.cantidad).desc())

        result = await db.execute(stmt)
        rows = result.fetchall()

        return [
            {
                "producto": r[0],
                "marca": r[1],
                "variedad": r[2],
                "cantidad_total": r[3],
                "fob_total": r[4],
                "fob_unit_ponderado": r[5],
                "fob_unit_max": r[6],
                "fob_unit_min": r[7]
            }
            for r in rows
        ]