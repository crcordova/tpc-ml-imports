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

@router.post("/excel")
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
        # Leer Excel
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))

        # Limpiar y filtrar la data
        df = clean_and_filter_excel(df)

        df.to_csv("debug_cleaned.csv", index=False)  # Guardar para debug

        # Instanciar services
        producto_service = ProductoService(db)
        importador_service = ImportadorService(db)
        pais_service = PaisService(db)
        puerto_service = PuertoService(db)
        importacion_service = ImportacionService(db)

        # Iterar sobre cada fila y guardar en la DB
        for _, row in df.iterrows():
            # 1️⃣ Pais origen y adquisicion
            pais_origen = await pais_service.get_or_create(row["PAIS DE ORIGEN"])
            pais_adquisicion = await pais_service.get_or_create(row["PAIS DE ADQUISICION"])

            # 2️⃣ Puertos
            puerto_embarque = await puerto_service.get_or_create(row["PUERTO DE EMBARQUE"], pais_origen.id)
            puerto_desembarque = await puerto_service.get_or_create(row["PUERTO DE DESEMBARQUE"], pais_adquisicion.id)

            # 3️⃣ Producto
            producto = await producto_service.get_or_create(
                nombre_generico=row["PRODUCTO"],
                marca=row.get("MARCA"),
                variedad=row.get("VARIEDAD"),
                descripcion=row.get("DESCRIPCION"),
                partida_arancelaria=row.get("PARTIDA ARANCELARIA")
            )

            # 4️⃣ Importador
            importador = await importador_service.get_or_create(
                rut=row["RUT PROBABLE IMPORTADOR"],
                nombre=row["PROBABLE IMPORTADOR"]
            )

            # 5️⃣ Importacion
            await importacion_service.create_from_row(
                row=row,
                producto_id=producto.id,
                importador_id=importador.id,
                pais_origen_id=pais_origen.id,
                pais_adquisicion_id=pais_adquisicion.id,
                puerto_embarque_id=puerto_embarque.id,
                puerto_desembarque_id=puerto_desembarque.id
            )

        return {"status": "success", "rows_processed": len(df)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
