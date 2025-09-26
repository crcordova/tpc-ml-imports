from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.tables.producto import Producto
from app.schemas.producto import ProductoCreate

class ProductoService:

    @staticmethod
    async def create(db: AsyncSession, producto: ProductoCreate) -> Producto:
        db_producto = Producto(**producto.dict())
        db.add(db_producto)
        await db.commit()
        await db.refresh(db_producto)
        return db_producto

    @staticmethod
    async def get_all(db: AsyncSession) -> list[Producto]:
        result = await db.execute(select(Producto))
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, producto_id: int) -> Producto | None:
        result = await db.execute(select(Producto).where(Producto.id == producto_id))
        return result.scalars().first()

    @staticmethod
    async def update(db: AsyncSession, producto_id: int, producto_data: dict) -> Producto | None:
        result = await db.execute(select(Producto).where(Producto.id == producto_id))
        db_producto = result.scalars().first()
        if not db_producto:
            return None
        for key, value in producto_data.items():
            setattr(db_producto, key, value)
        await db.commit()
        await db.refresh(db_producto)
        return db_producto

    @staticmethod
    async def delete(db: AsyncSession, producto_id: int) -> bool:
        result = await db.execute(select(Producto).where(Producto.id == producto_id))
        db_producto = result.scalars().first()
        if not db_producto:
            return False
        await db.delete(db_producto)
        await db.commit()
        return True
