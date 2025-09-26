from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class Importacion(Base):
    __tablename__ = "importaciones"

    id = Column(Integer, primary_key=True, index=True)

    # Relaciones principales
    importador_id = Column(Integer, ForeignKey("importadores.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    pais_origen_id = Column(Integer, ForeignKey("paises.id"), nullable=True, index=True)
    pais_adquisicion_id = Column(Integer, ForeignKey("paises.id"), nullable=True)
    puerto_embarque_id = Column(Integer, ForeignKey("puertos.id"), nullable=True)
    puerto_desembarque_id = Column(Integer, ForeignKey("puertos.id"), nullable=True)

    # Datos de la operación
    fecha = Column(Date, nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    descripcion_arancelaria = Column(Text, nullable=True)
    via_transporte = Column(String, nullable=True)
    compania_transporte = Column(String, nullable=True)
    forma_pago = Column(String, nullable=True)
    clausula = Column(String, nullable=True)
    acuerdo_comercial = Column(String, nullable=True)


    # Valores económicos
    cantidad = Column(Float, nullable=True)
    unidad = Column(String, nullable=True)
    fob_total = Column(Float, nullable=True)
    fob_unit = Column(Float, nullable=True)
    flete_total = Column(Float, nullable=True)
    seguro_total = Column(Float, nullable=True)
    cif_total = Column(Float, nullable=True)
    cif_unit = Column(Float, nullable=True)
    impuesto = Column(Float, nullable=True)
    iva_total = Column(Float, nullable=True)

    # Relaciones ORM
    importador = relationship("Importador")
    producto = relationship("Producto")
    pais_origen = relationship("Pais", foreign_keys=[pais_origen_id])
    pais_adquisicion = relationship("Pais", foreign_keys=[pais_adquisicion_id])
    puerto_embarque = relationship("Puerto", foreign_keys=[puerto_embarque_id])
    puerto_desembarque = relationship("Puerto", foreign_keys=[puerto_desembarque_id])
