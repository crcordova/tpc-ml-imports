import pandas as pd

def clean_and_filter_excel(df):
    """
    Limpieza inicial de los datos de importaciones desde Excel.
    """
    columns_of_interest = [
        "DIA",
        "MES",
        "AÑO",
        "RUT PROBABLE IMPORTADOR",
        "DIGITO VERIFICADOR RUT",
        "PROBABLE IMPORTADOR",
        "PARTIDA ARANCELARIA",
        "PRODUCTO",
        "MARCA",
        "VARIEDAD",
        "DESCRIPCION",
        "DESCRIPCION ARANCELARIA",
        "PAIS DE ORIGEN",
        "PAIS DE ADQUISICION",
        "VIA DE TRANSPORTE",
        "COMPAÑIA DE TRANSPORTE",
        "FORMA PAGO",
        "CLAUSULA",
        "PUERTO DE EMBARQUE",
        "PUERTO DE DESEMBARQUE",
        "ACUERDO COMERCIAL",
        "CANTIDAD",
        "UNIDAD",
        "FOB TOTAL",
        "US$ FOB UNIT",
        "FLETE TOTAL",
        "SEGURO TOTAL",
        "CIF TOTAL",
        "US$ CIF UNIT",
        "IMPUESTO",
        "TOTAL IVA"

    ]
    df = df[columns_of_interest]

    rename_map = {
        "RUT PROBABLE IMPORTADOR": "rut",
        "DIGITO VERIFICADOR RUT": "dv",
        "PROBABLE IMPORTADOR": "nombre",
        "PARTIDA ARANCELARIA": "partida_arancelaria",
        "PRODUCTO": "producto",
        "MARCA": "marca",
        "VARIEDAD": "variedad",
        "DESCRIPCION": "descripcion",
        "DESCRIPCION ARANCELARIA": "descripcion_arancelaria",
        "PAIS DE ORIGEN": "pais_origen",
        "PAIS DE ADQUISICION": "pais_adquisicion",
        "VIA DE TRANSPORTE": "via_transporte",
        "COMPAÑIA DE TRANSPORTE": "compania_transporte",
        "FORMA PAGO": "forma_pago",
        "CLAUSULA": "clausula",
        "PUERTO DE EMBARQUE": "puerto_embarque",
        "PUERTO DE DESEMBARQUE": "puerto_desembarque",
        "ACUERDO COMERCIAL": "acuerdo_comercial",
        "CANTIDAD": "cantidad",
        "UNIDAD": "unidad",
        "FOB TOTAL": "fob_total",
        "US$ FOB UNIT": "fob_unit",
        "FLETE TOTAL": "flete_total",
        "SEGURO TOTAL": "seguro_total",
        "CIF TOTAL": "cif_total",
        "US$ CIF UNIT": "cif_unit",
        "IMPUESTO": "impuesto",
        "TOTAL IVA": "iva_total"
    }

    df = df.rename(columns=rename_map)

    df["fecha"] = pd.to_datetime(
        df[["DIA", "MES", "AÑO"]].astype(str).agg("-".join, axis=1),
        format="%d-%m-%Y",
        errors="coerce"
    )
    
    df = df.drop(columns=["DIA", "MES", "AÑO"])

    df["rut"] = df["rut"].astype(str).str.replace("^'", "", regex=True).str.strip()

    # Normalizar nombre de producto
    df["producto"] = df["producto"].astype(str).str.upper().str.strip()

    for col in ["marca", "variedad", "descripcion", "descripcion_arancelaria",
                "pais_origen", "pais_adquisicion", "via_transporte", "compania_transporte",
                "forma_pago", "clausula", "puerto_embarque", "puerto_desembarque", "acuerdo_comercial"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    numeric_cols = [
        "cantidad", "fob_total", "fob_unit", "flete_total",
        "seguro_total", "cif_total", "cif_unit", "impuesto", "iva_total"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            
    return df
