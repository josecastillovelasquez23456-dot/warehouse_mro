import io
import pandas as pd
import unicodedata
import re
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

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


# =====================================================
# INVENTARIO BASE
# =====================================================

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


# =====================================================
# LAYOUT 2D
# =====================================================

WAREHOUSE_2D_REQUIRED = {
    "mat": "Código del Material",
    "desc": "Texto breve de material",
    "umb": "Unidad de medida base",
    "ubi": "Ubicación",
    "seg": "Stock de seguridad",
    "max": "Stock máximo",
    "libre": "Libre utilización",
}


def load_warehouse2d_excel(file_storage):
    content = file_storage.read()
    df = pd.read_excel(io.BytesIO(content))
    file_storage.seek(0)

    columnas_mapeadas, faltantes = mapear_columnas(df, WAREHOUSE_2D_REQUIRED)
    if faltantes:
        raise ValueError("Faltan columnas requeridas: " + ", ".join(faltantes))

    final = {oficial: df[original] for original, oficial in columnas_mapeadas.items()}
    return pd.DataFrame(final)


# =====================================================
# ORDEN DE UBICACIONES
# =====================================================

def sort_location_advanced(loc):
    if not loc:
        return (999999, "Z", 999999)

    loc = str(loc).upper()
    nums = re.findall(r"(\d+)", loc)
    main = int(nums[0]) if nums else 999999
    last = int(nums[-1]) if nums else 999999
    letters = "".join([c for c in loc if c.isalpha()][1:]) or "Z"

    return (main, letters, last)


# =====================================================
# GENERAR EXCEL DE DISCREPANCIAS
# =====================================================

def generate_discrepancies_excel(df):
    wb = Workbook()
    ws = wb.active
    ws.title = "Discrepancias"

    headers = df.columns.tolist()

    # Encabezados
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")
        cell.fill = PatternFill(start_color="DDDDDD", fill_type="solid")

    # Datos
    for row_idx, row in df.iterrows():
        for col_idx, value in enumerate(row.tolist(), 1):
            ws.cell(row=row_idx + 2, column=col_idx, value=value)

    # Ajuste de ancho de columnas
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                max_len = max(max_len, len(str(cell.value)))
            except:
                pass
        ws.column_dimensions[col_letter].width = max_len + 2

    # Guardar archivo en memoria
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return output
