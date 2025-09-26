from sqlalchemy import Column, Integer, String, Text
from app.database import Base

class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    partida_arancelaria = Column(String, index=True, nullable=True)
    nombre_generico = Column(String, index=True, nullable=False)
    marca = Column(String, nullable=True)
    variedad = Column(String, nullable=True)
