from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.tables.importador import Importador
from app.schemas.importador import ImportadorCreate, ImportadorResponse


class ImportadorService:


    @staticmethod
    async def create(db: AsyncSession, importador: ImportadorCreate) -> Importador:
        
        db_importador = Importador(**importador.model_dump())
        db.add(db_importador)
        await db.commit()
        await db.refresh(db_importador)
        return db_importador

    @staticmethod
    async def get_all(db: AsyncSession) -> list[Importador]:
        result = await db.execute(select(Importador))
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, importador_id: int) -> Importador | None:
        result = await db.execute(
            select(Importador).where(Importador.id == importador_id)
        )
        return result.scalars().first()

    @staticmethod
    async def update(db: AsyncSession, importador_id: int, importador_data: dict) -> Importador | None:
        result = await db.execute(
            select(Importador).where(Importador.id == importador_id)
        )
        db_importador = result.scalars().first()
        if not db_importador:
            return None
        for key, value in importador_data.items():
            setattr(db_importador, key, value)
        await db.commit()
        await db.refresh(db_importador)
        return db_importador

    @staticmethod
    async def delete(db: AsyncSession, importador_id: int) -> bool:
        result = await db.execute(
            select(Importador).where(Importador.id == importador_id)
        )
        db_importador = result.scalars().first()
        if not db_importador:
            return False
        await db.delete(db_importador)
        await db.commit()
        return True
