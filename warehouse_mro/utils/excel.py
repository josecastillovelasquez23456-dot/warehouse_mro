import io
import pandas as pd
import unicodedata
import re

# =====================================================
# NORMALIZACIÓN
# =====================================================

EQUIVALENCIAS = {
    "codigo del material": "Código del Material",
    "codigo_material": "Código del Material",
    "codigodelmaterial": "Código del Material",
    "cod material": "Código del Material",
    "codigo": "Código del Material",
    "material": "Código del Material",

    "texto breve de material": "Texto breve de material",
    "descripcion": "Texto breve de material",

    "unidad de medida base": "Unidad de medida base",
    "unidad de medida": "Unidad de medida base",
    "umb": "Unidad de medida base",

    "ubicacion": "Ubicación",
    "ubicación": "Ubicación",
    "location": "Ubicación",

    "libre utilizacion": "Libre utilización",
    "libre utilización": "Libre utilización",
    "stock": "Libre utilización",
}

def limpiar(texto: str) -> str:
    if texto is None:
        return ""
    texto = str(texto).strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = texto.lower().replace("_", " ").replace("-", " ")
    return " ".join(texto.split())


def mapear_columnas(df, requeridas):
    columnas_originales = list(df.columns)
    columns_map = {}

    for col in columnas_originales:
        clean = limpiar(col)
        if clean in EQUIVALENCIAS:
            columns_map[col] = EQUIVALENCIAS[clean]

    faltantes = [v for v in requeridas.values() if v not in columns_map.values()]
    return columns_map, faltantes


INV_REQUIRED = {
    "mat": "Código del Material",
    "desc": "Texto breve de material",
    "umb": "Unidad de medida base",
    "ubi": "Ubicación",
    "libre": "Libre utilización",
}

def load_inventory_excel(file_storage):
    content = file_storage.read()
    df = pd.read_excel(io.BytesIO(content))
    file_storage.seek(0)

    columnas_mapeadas, faltantes = mapear_columnas(df, INV_REQUIRED)
    if faltantes:
        raise ValueError("Faltan columnas requeridas: " + ", ".join(faltantes))

    final = {oficial: df[original] for original, oficial in columnas_mapeadas.items()}
    return pd.DataFrame(final)


def sort_location_advanced(loc):
    if not loc:
        return (999999, "Z", 999999)

    loc = str(loc).upper()
    nums = re.findall(r"(\d+)", loc)
    main = int(nums[0]) if nums else 999999
    last = int(nums[-1]) if nums else 999999
    letters = "".join([c for c in loc if c.isalpha()][1:]) or "Z"

    return (main, letters, last)
