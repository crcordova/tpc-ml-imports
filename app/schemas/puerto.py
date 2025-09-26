from pydantic import BaseModel
from typing import Optional
from app.schemas.pais import PaisResponse

class PuertoBase(BaseModel):
    nombre: str
    pais_id: int

class PuertoCreate(PuertoBase):
    pass

class PuertoResponse(PuertoBase):
    id: int
    pais: Optional[PaisResponse] = None  # incluir info del país relacionado

    class Config:
        orm_mode = True
