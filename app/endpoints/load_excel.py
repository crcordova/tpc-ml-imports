from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
from io import BytesIO
from app.database import get_db_public
from app.services.importacion import ImportacionService
from app.services.importador import ImportadorService
from app.services.producto import ProductoService
from app.services.pais import PaisService
from app.services.puerto import PuertoService
from app.utils.cleaning import clean_and_filter_excel  # aquí iría tu lógica de limpieza

router = APIRouter(
    prefix="/load",
    tags=["Load Excel"]
)

@router.post("/")
async def load_excel(file: UploadFile = File(...), db: AsyncSession = Depends(get_db_public)):
    """
    Endpoint para cargar un Excel de importaciones por producto.
    - Limpia y filtra los datos
    - Crea registros nuevos si no existen
    - Carga los datos en la base
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx o .xls)")

    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))

        df = clean_and_filter_excel(df)

        for _, row in df.iterrows():

            pais_origen = await PaisService.get_or_create(db,row["pais_origen"])
            pais_adquisicion = await PaisService.get_or_create(db,row["pais_adquisicion"])

            puerto_embarque = await PuertoService.get_or_create(db,row["puerto_embarque"], pais_adquisicion.id)
            puerto_desembarque = await PuertoService.get_or_create(db,row["puerto_desembarque"], 1)

            producto = await ProductoService.get_or_create(db=db,
                nombre_generico=row["producto"],
                marca=row.get("marca"),
                variedad=row.get("variedad"),
                partida_arancelaria=row.get("partida_arancelaria")
            )

            importador = await ImportadorService.get_or_create(
                db=db,
                rut=row["rut"],
                dv=row["dv"],
                nombre=row["nombre"]
            )

            await ImportacionService.create_from_row(
                db=db,
                row=row,
                producto_id=producto.id,
                importador_id=importador.id,
                pais_origen_id=pais_origen.id,
                pais_adquisicion_id=pais_adquisicion.id,
                puerto_embarque_id=puerto_embarque.id,
                puerto_desembarque_id=puerto_desembarque.id
            )
        await db.commit()

        return {"status": "success", "rows_processed": len(df)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
