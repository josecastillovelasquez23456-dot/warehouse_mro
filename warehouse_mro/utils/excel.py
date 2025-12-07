import io
import pandas as pd
import unicodedata
import re

# =====================================================================================
#                                   NORMALIZACIÓN
# =====================================================================================

EQUIVALENCIAS = {
    # Código del Material
    "codigo del material": "Código del Material",
    "codigo_material": "Código del Material",
    "codigodelmaterial": "Código del Material",
    "cod material": "Código del Material",
    "codigo": "Código del Material",
    "material": "Código del Material",

    # Descripción
    "texto breve de material": "Texto breve de material",
    "descripcion": "Texto breve de material",
    "texto_breve_material": "Texto breve de material",

    # Unidad
    "unidad de medida base": "Unidad de medida base",
    "unidad de medida": "Unidad de medida base",
    "umb": "Unidad de medida base",
    "unidad": "Unidad de medida base",

    # Ubicación
    "ubicacion": "Ubicación",
    "ubicación": "Ubicación",
    "location": "Ubicación",
    "ubi": "Ubicación",

    # Libre utilización
    "libre utilizacion": "Libre utilización",
    "libre utilización": "Libre utilización",
    "stock": "Libre utilización",
    "conteo": "Libre utilización",

    "stock de seguridad": "Stock de seguridad",
    "stock seguridad": "Stock de seguridad",

    "stock maximo": "Stock máximo",
    "stock máximo": "Stock máximo",
}


def limpiar(texto: str) -> str:
    """Limpia y normaliza encabezados para comparaciones flexibles."""
    if texto is None:
        return ""

    texto = str(texto).strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = texto.lower()

    for r in ["-", "_", ".", ",", ";", "﻿", "\u200b"]:
        texto = texto.replace(r, " ")

    return " ".join(texto.split())


def mapear_columnas(df, requeridas):
    columnas_originales = list(df.columns)
    columnas_mapeadas = {}

    for col in columnas_originales:
        clean = limpiar(col)

        if clean in EQUIVALENCIAS:
            columnas_mapeadas[col] = EQUIVALENCIAS[clean]

    faltantes = [v for v in requeridas.values() if v not in columnas_mapeadas.values()]

    return columnas_mapeadas, faltantes


# =====================================================================================
#                           COLUMNAS REQUERIDAS INVENTARIO
# =====================================================================================

INV_REQUIRED = {
    "mat": "Código del Material",
    "desc": "Texto breve de material",
    "umb": "Unidad de medida base",
    "ubi": "Ubicación",
    "libre": "Libre utilización",
}

def load_inventory_excel(file_storage):
    """Carga Excel de inventario con validación compatible con Render/Koyeb."""

    try:
        # Leer DIRECTAMENTE desde el stream → evita Forbidden 403 en cloud
        df = pd.read_excel(file_storage.stream)
    except Exception:
        raise ValueError("No se pudo leer el archivo Excel. Verifique el formato.")

    columnas_mapeadas, faltantes = mapear_columnas(df, INV_REQUIRED)

    if faltantes:
        raise ValueError(
            "El archivo no contiene todas las columnas requeridas.\n"
            "Faltan: " + ", ".join(faltantes)
        )

    # Construir DataFrame limpio con nombres oficiales
    clean = {official: df[original] for original, official in columnas_mapeadas.items()}

    return pd.DataFrame(clean)

# =====================================================================================
#                           COLUMNAS REQUERIDAS ALMACÉN 2D
# =====================================================================================

W2D_REQUIRED = {
    "mat": "Código del Material",
    "desc": "Texto breve de material",
    "umb": "Unidad de medida base",
    "seg": "Stock de seguridad",
    "max": "Stock máximo",
    "ubi": "Ubicación",
    "libre": "Libre utilización",
}


def load_warehouse2d_excel(file_storage):
    """Carga Excel para el mapa 2D. Maneja columnas faltantes automáticamente."""

    content = file_storage.read()
    df = pd.read_excel(io.BytesIO(content))
    file_storage.seek(0)

    columnas_mapeadas, faltantes = mapear_columnas(df, W2D_REQUIRED)

    # Manejo de columnas faltantes
    for falt in faltantes:
        if falt == "Stock de seguridad":
            df["Stock de seguridad"] = 0
            columnas_mapeadas["Stock de seguridad"] = "Stock de seguridad"

        elif falt == "Stock máximo":
            df["Stock máximo"] = 0
            columnas_mapeadas["Stock máximo"] = "Stock máximo"

    clean = {}
    for original, oficial in columnas_mapeadas.items():
        if original in df.columns:
            clean[oficial] = df[original]
        else:
            clean[oficial] = df[oficial]

    return pd.DataFrame(clean)


# =====================================================================================
#                       ORDENAMIENTO AVANZADO DE UBICACIONES
# =====================================================================================

def sort_location_advanced(loc):
    """Ordenamiento industrial de ubicaciones tipo E026A07, E005B01, PLANTA, etc."""
    
    if loc is None:
        return (999999, "Z", 999999)

    loc = str(loc).strip().upper()

    if not any(c.isdigit() for c in loc):
        return (999999, loc, 999999)

    nums = re.findall(r"(\d+)", loc)
    main = int(nums[0]) if nums else 999999
    last = int(nums[-1]) if nums else 999999

    letters = "".join([c for c in loc if c.isalpha()][1:]) or "Z"

    return (main, letters, last)


# =====================================================================================
#                       GENERADOR DE EXCEL PROFESIONAL
# =====================================================================================

def generate_discrepancies_excel(df: pd.DataFrame) -> io.BytesIO:
    """Genera un Excel profesional con bordes, colores y formato corporativo."""

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Discrepancias", index=False)
        book = writer.book
        ws = writer.sheets["Discrepancias"]

        # ---------------- Estilos ----------------
        header = book.add_format({
            "bold": True,
            "bg_color": "#1F4E78",
            "font_color": "white",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        })

        normal_left = book.add_format({
            "align": "left",
            "border": 1,
            "valign": "vcenter",
        })

        normal_right = book.add_format({
            "align": "right",
            "border": 1,
            "valign": "vcenter",
            "num_format": "#,##0.00",
        })

        red_text = book.add_format({
            "font_color": "red",
            "border": 1,
            "align": "right",
            "num_format": "#,##0.00",
        })

        estado_ok = book.add_format({"bg_color": "#D9EAF7", "border": 1, "align": "center"})
        estado_falta = book.add_format({"bg_color": "#FCE4D6", "border": 1, "align": "center"})
        estado_critico = book.add_format({"bg_color": "#F4CCCC", "border": 1, "align": "center"})
        estado_sobra = book.add_format({"bg_color": "#D9EAD3", "border": 1, "align": "center"})

        # ---------------- Encabezados
        for col, name in enumerate(df.columns):
            ws.write(0, col, name, header)

        # ---------------- Autoajuste columnas
        for i, colname in enumerate(df.columns):
            max_len = max(df[colname].astype(str).map(len).max(), len(colname)) + 2
            ws.set_column(i, i, max_len)

        ws.freeze_panes(1, 0)

        diff_col = df.columns.get_loc("Diferencia")
        est_col = df.columns.get_loc("Estado")

        # ---------------- Filas
        for row in range(1, len(df) + 1):
            diferencia = df.iloc[row - 1]["Diferencia"]
            estado = str(df.iloc[row - 1]["Estado"]).upper()

            if diferencia < 0:
                ws.write(row, diff_col, diferencia, red_text)
            else:
                ws.write(row, diff_col, diferencia, normal_right)

            if estado == "CRÍTICO":
                ws.write(row, est_col, estado, estado_critico)
            elif estado == "FALTA":
                ws.write(row, est_col, estado, estado_falta)
            elif estado == "SOBRA":
                ws.write(row, est_col, estado, estado_sobra)
            else:
                ws.write(row, est_col, estado, estado_ok)

            for col in range(len(df.columns)):
                if col in (diff_col, est_col):
                    continue

                value = df.iloc[row - 1, col]

                if isinstance(value, (int, float)):
                    ws.write(row, col, value, normal_right)
                else:
                    ws.write(row, col, value, normal_left)

    output.seek(0)
    return output

