from pydantic import BaseModel
from datetime import date
from typing import Optional
from app.schemas.importador import ImportadorResponse
from app.schemas.producto import ProductoResponse
from app.schemas.pais import PaisResponse
from app.schemas.puerto import PuertoResponse

class ImportacionBase(BaseModel):
    importador_id: int
    producto_id: int
    pais_origen_id: Optional[int] = None
    pais_adquisicion_id: Optional[int] = None
    puerto_embarque_id: Optional[int] = None
    puerto_desembarque_id: Optional[int] = None

    fecha: date
    descripcion: Optional[str] = None
    via_transporte: Optional[str] = None
    forma_pago: Optional[str] = None
    tipo_carga: Optional[str] = None
    tipo_bulto: Optional[str] = None
    peso_bruto_total: Optional[float] = None

    cantidad: Optional[float] = None
    unidad: Optional[str] = None
    fob: Optional[float] = None
    fob_unit: Optional[float] = None
    flete: Optional[float] = None
    seguro: Optional[float] = None
    cif: Optional[float] = None
    cif_unit: Optional[float] = None
    impuesto: Optional[float] = None
    acuerdo_comercial: Optional[str] = None
    estado_mercancia: Optional[str] = None

class ImportacionCreate(ImportacionBase):
    pass

class ImportacionResponse(ImportacionBase):
    id: int
    importador: Optional[ImportadorResponse] = None
    producto: Optional[ProductoResponse] = None
    pais_origen: Optional[PaisResponse] = None
    pais_adquisicion: Optional[PaisResponse] = None
    puerto_embarque: Optional[PuertoResponse] = None
    puerto_desembarque: Optional[PuertoResponse] = None

    class Config:
        orm_mode = True
