from sqlalchemy import Column, Integer, String
from app.database import Base

class Pais(Base):
    __tablename__ = "paises"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False)
    codigo_iso = Column(String, unique=True, nullable=True)  # ej: CL, US, CN
