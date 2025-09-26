from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.tables.pais import Pais
from app.schemas.pais import PaisCreate

class PaisService:

    @staticmethod
    async def create(db: AsyncSession, pais: PaisCreate) -> Pais:
        db_pais = Pais(**pais.dict())
        db.add(db_pais)
        await db.commit()
        await db.refresh(db_pais)
        return db_pais

    @staticmethod
    async def get_all(db: AsyncSession) -> list[Pais]:
        result = await db.execute(select(Pais))
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, pais_id: int) -> Pais | None:
        result = await db.execute(select(Pais).where(Pais.id == pais_id))
        return result.scalars().first()

    @staticmethod
    async def update(db: AsyncSession, pais_id: int, pais_data: dict) -> Pais | None:
        result = await db.execute(select(Pais).where(Pais.id == pais_id))
        db_pais = result.scalars().first()
        if not db_pais:
            return None
        for key, value in pais_data.items():
            setattr(db_pais, key, value)
        await db.commit()
        await db.refresh(db_pais)
        return db_pais

    @staticmethod
    async def delete(db: AsyncSession, pais_id: int) -> bool:
        result = await db.execute(select(Pais).where(Pais.id == pais_id))
        db_pais = result.scalars().first()
        if not db_pais:
            return False
        await db.delete(db_pais)
        await db.commit()
        return True
