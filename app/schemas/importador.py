from pydantic import BaseModel

class ImportadorBase(BaseModel):
    rut: str
    dv: str
    nombre: str
    industria: str | None = None
    industria2: str | None = None
    clave_economica: str | None = None

class ImportadorCreate(ImportadorBase):
    pass

class ImportadorResponse(ImportadorBase):
    id: int

    class Config:
        orm_mode = True
