from pydantic import BaseModel
from typing import Optional

class ImportadorBase(BaseModel):
    rut: str
    dv: Optional[str] = None
    nombre: Optional[str] = None
    industria: Optional[str] = None
    industria2: Optional[str] = None
    clave_economica: Optional[str] = None

class ImportadorCreate(ImportadorBase):
    pass

class ImportadorResponse(ImportadorBase):
    id: int

    class Config:
        from_attributes = True
