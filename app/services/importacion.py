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
