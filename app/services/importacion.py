from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from datetime import datetime, date
from app.tables.importacion import Importacion
from app.tables.producto import Producto
from app.tables.importador import Importador
from app.tables.pais import Pais
from app.tables.puerto import Puerto
from app.schemas.importacion import ImportacionCreate

class ImportacionService:

    @staticmethod
    async def create(db: AsyncSession, importacion: ImportacionCreate) -> Importacion:
        db_importacion = Importacion(**importacion.model_dump())
        db.add(db_importacion)
        await db.commit()
        await db.refresh(db_importacion)
        return db_importacion

    @staticmethod
    async def get_all(db: AsyncSession) -> list[Importacion]:
        result = await db.execute(select(Importacion).options(
                joinedload(Importacion.importador),
                joinedload(Importacion.producto),
                joinedload(Importacion.pais_origen),
                joinedload(Importacion.pais_adquisicion),
                joinedload(Importacion.puerto_embarque).joinedload(Puerto.pais),
                joinedload(Importacion.puerto_desembarque).joinedload(Puerto.pais),
            ))
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, importacion_id: int):
        result = await db.execute(
            select(Importacion)
            .options(
                joinedload(Importacion.importador),
                joinedload(Importacion.producto),
                joinedload(Importacion.pais_origen),
                joinedload(Importacion.pais_adquisicion),
                joinedload(Importacion.puerto_embarque).joinedload(Puerto.pais),
                joinedload(Importacion.puerto_desembarque).joinedload(Puerto.pais),
            )
            .where(Importacion.id == importacion_id)
        )
        return result.scalars().first()
    
    @staticmethod
    async def create_from_row(
        db:AsyncSession, 
        row, 
        producto_id: int, 
        importador_id: int,
        pais_origen_id: int,
        pais_adquisicion_id: int,
        puerto_embarque_id: int,
        puerto_desembarque_id: int
        ) -> Importacion:
        
        importacion_data = {
            "importador_id": importador_id,
            "producto_id": producto_id,
            "pais_origen_id": pais_origen_id,
            "pais_adquisicion_id": pais_adquisicion_id,
            "puerto_embarque_id": puerto_embarque_id,
            "puerto_desembarque_id": puerto_desembarque_id,
            "fecha": row["fecha"],
            "descripcion": row["descripcion"],
            "descripcion_arancelaria": row["descripcion_arancelaria"],
            "via_transporte": row["via_transporte"],
            "compania_transporte": row["compania_transporte"],
            "forma_pago": row["forma_pago"],
            "clausula": row["clausula"],
            "acuerdo_comercial": row["acuerdo_comercial"],
            "cantidad": row["cantidad"],
            "unidad": row["unidad"],
            "fob_total": row["fob_total"],
            "fob_unit": row["fob_unit"],
            "flete_total": row["flete_total"],
            "seguro_total": row["seguro_total"],
            "cif_total": row["cif_total"],
            "cif_unit": row["cif_unit"],
            "impuesto": row["impuesto"],
            "iva_total": row["iva_total"]
        }
        new_importacion = Importacion(**importacion_data)
        db.add(new_importacion)
        await db.flush()
        await db.refresh(new_importacion)
        return new_importacion

    @staticmethod
    async def update(db: AsyncSession, importacion_id: int, importacion_data: dict) -> Importacion | None:
        result = await db.execute(select(Importacion).where(Importacion.id == importacion_id))
        db_importacion = result.scalars().first()
        if not db_importacion:
            return None
        for key, value in importacion_data.items():
            setattr(db_importacion, key, value)
        await db.commit()
        await db.refresh(db_importacion)
        return db_importacion

    @staticmethod
    async def delete(db: AsyncSession, importacion_id: int) -> bool:
        result = await db.execute(select(Importacion).where(Importacion.id == importacion_id))
        db_importacion = result.scalars().first()
        if not db_importacion:
            return False
        await db.delete(db_importacion)
        await db.commit()
        return True

    @staticmethod
    async def get_importaciones(
        db: AsyncSession,
        fecha_start: date | None = None,
        fecha_end: date | None = None,
        nombre_importador: str | None = None,
        rut_importador: str | None = None,
        producto: str | None = None,
        pais_origen: str | None = None
    ):
        query = (
            select(Importacion)
            .options(
                joinedload(Importacion.producto),
                joinedload(Importacion.importador),
                joinedload(Importacion.pais_origen),
                joinedload(Importacion.pais_adquisicion),
            )
        )

        # Filtros dinámicos
        filters = []

        if fecha_start:
            filters.append(Importacion.fecha >= fecha_start)
        if fecha_end:
            filters.append(Importacion.fecha <= fecha_end)
        if nombre_importador:
            filters.append(Importador.nombre.ilike(f"%{nombre_importador}%"))
        if rut_importador:
            filters.append(Importador.rut.ilike(f"%{rut_importador}%"))
        if producto:
            filters.append(Producto.nombre_generico.ilike(f"%{producto}%"))
        if pais_origen:
            filters.append(Pais.nombre.ilike(f"%{pais_origen}%"))

        if filters:
            query = query.join(Importacion.importador).join(Importacion.producto).join(Importacion.pais_origen).filter(and_(*filters))

        result = await db.execute(query)
        importaciones = result.scalars().all()

        # Formatear resultado
        response = []
        for imp in importaciones:
            response.append({
                "id": imp.id,
                "fecha": imp.fecha,
                "pais_origen": imp.pais_origen.nombre if imp.pais_origen else None,
                "pais_adquisicion": imp.pais_adquisicion.nombre if imp.pais_adquisicion else None,
                "producto_nombre": imp.producto.nombre_generico if imp.producto else None,
                "marca": imp.producto.marca if imp.producto else None,
                "variedad": imp.producto.variedad if imp.producto else None,
                "descripcion": imp.descripcion,
                "via_transporte": imp.via_transporte,
                "compania_transporte": imp.compania_transporte,
                "forma_pago": imp.forma_pago,
                "clausula": imp.clausula,
                "cantidad": imp.cantidad,
                "unidad": imp.unidad,
                "fob_total": imp.fob_total,
                "fob_unit": imp.fob_unit,
                "flete_total": imp.flete_total,
                "seguro_total": imp.seguro_total,
                "cif_total": imp.cif_total,
                "cif_unit": imp.cif_unit,
                "impuesto": imp.impuesto,
                "iva_total": imp.iva_total,
            })
        return response