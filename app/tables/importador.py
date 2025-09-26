from sqlalchemy import Column, Integer, String
from app.database import Base

class Importador(Base):
    __tablename__ = "importadores"

    id = Column(Integer, primary_key=True, index=True)
    rut = Column(String, unique=True, index=True, nullable=False)
    dv = Column(String, nullable=True)
    nombre = Column(String, nullable=True)
    industria = Column(String, nullable=True)
    industria2 = Column(String, nullable=True)
    clave_economica = Column(String, nullable=True)
