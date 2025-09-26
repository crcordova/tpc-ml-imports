from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Puerto(Base):
    __tablename__ = "puertos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    pais_id = Column(Integer, ForeignKey("paises.id"))

    pais = relationship("Pais")
