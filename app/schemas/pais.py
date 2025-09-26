from pydantic import BaseModel

class PaisBase(BaseModel):
    nombre: str
    codigo_iso: str | None = None

class PaisCreate(PaisBase):
    pass

class PaisResponse(PaisBase):
    id: int

    class Config:
        orm_mode = True
