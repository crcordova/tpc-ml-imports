from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.tables.importador import Importador
from app.tables.producto import Producto
from app.tables.importacion import Importacion
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
    async def get_by_product(db: AsyncSession, product: str):
        stmt = (
            select(Importador)
            .join(Importacion, Importador.id == Importacion.importador_id)
            .join(Producto, Importacion.producto_id == Producto.id)
            .where(
                Producto.nombre_generico.ilike(f"%{product}%") 
            )
            .distinct()  # Para evitar duplicados
            .order_by(Importador.nombre)
        ) 
        result = await db.execute(stmt)
        importadores = result.scalars().all()
        return importadores


    @staticmethod
    async def get_or_create(db: AsyncSession, rut: str, dv: str, nombre: str) -> Importador:
        result = await db.execute(
            select(Importador).where(Importador.rut == rut)
        )
        db_importador = result.scalars().first()
        if db_importador:
            return db_importador
        new_importador = Importador(rut=rut, nombre=nombre, dv=dv)
        db.add(new_importador)
        await db.flush()
        await db.refresh(new_importador)
        return new_importador

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
