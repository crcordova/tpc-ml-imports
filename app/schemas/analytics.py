from pydantic import BaseModel
from datetime import date
from typing import Optional

class TopImportadoresRequest(BaseModel):
    producto: str
    n_importadores: int
    fecha_inicio: date
    fecha_fin: date


class ImportadorDetalleRequest(BaseModel):
    rut: Optional[str] = None
    nombre: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None