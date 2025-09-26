from pydantic import BaseModel

class ProductoBase(BaseModel):
    partida_arancelaria: str | None = None
    nombre_generico: str
    marca: str | None = None
    variedad: str | None = None
    descripcion: str | None = None

class ProductoCreate(ProductoBase):
    pass

class ProductoResponse(ProductoBase):
    id: int

    class Config:
        orm_mode = True
