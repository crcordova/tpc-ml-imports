from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.tables.puerto import Puerto
from app.schemas.puerto import PuertoCreate

class PuertoService:

    @staticmethod
    async def create(db: AsyncSession, puerto: PuertoCreate) -> Puerto:
        db_puerto = Puerto(**puerto.dict())
        db.add(db_puerto)
        await db.commit()
        await db.refresh(db_puerto)
        return db_puerto

    @staticmethod
    async def get_all(db: AsyncSession) -> list[Puerto]:
        result = await db.execute(select(Puerto))
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, puerto_id: int) -> Puerto | None:
        result = await db.execute(select(Puerto).where(Puerto.id == puerto_id))
        return result.scalars().first()
    
    @staticmethod
    async def get_or_create(db: AsyncSession, nombre: str, pais_id: int) -> Puerto:
        result = await db.execute(select(Puerto).where(Puerto.nombre == nombre, Puerto.pais_id == pais_id))
        db_puerto = result.scalars().first()
        if db_puerto:
            return db_puerto
        new_puerto = Puerto(nombre=nombre, pais_id=pais_id)
        db.add(new_puerto)
        await db.flush()
        await db.refresh(new_puerto)
        return new_puerto

    @staticmethod
    async def update(db: AsyncSession, puerto_id: int, puerto_data: dict) -> Puerto | None:
        result = await db.execute(select(Puerto).where(Puerto.id == puerto_id))
        db_puerto = result.scalars().first()
        if not db_puerto:
            return None
        for key, value in puerto_data.items():
            setattr(db_puerto, key, value)
        await db.commit()
        await db.refresh(db_puerto)
        return db_puerto

    @staticmethod
    async def delete(db: AsyncSession, puerto_id: int) -> bool:
        result = await db.execute(select(Puerto).where(Puerto.id == puerto_id))
        db_puerto = result.scalars().first()
        if not db_puerto:
            return False
        await db.delete(db_puerto)
        await db.commit()
        return True
