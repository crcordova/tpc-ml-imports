from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.tables.importacion import Importacion
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
        result = await db.execute(select(Importacion))
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, importacion_id: int) -> Importacion | None:
        result = await db.execute(select(Importacion).where(Importacion.id == importacion_id))
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
