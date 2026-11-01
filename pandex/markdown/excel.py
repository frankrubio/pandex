"""Excel (.xlsx y .xls) a tablas Markdown sin pandas.

MarkItDown lee Excel con pandas, que pesa 81 MB solo para esto. Aquí se lee con
openpyxl (.xlsx) y xlrd (.xls), que pesan 4 MB entre los dos, y el resultado es el mismo:
una sección ``## Hoja`` por hoja, con su tabla (la primera fila es el encabezado).
"""

import datetime as _dt
import io

EXTENSIONES = {".xlsx", ".xls"}


def _celda(valor):
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "TRUE" if valor else "FALSE"
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    if isinstance(valor, _dt.datetime):
        return valor.date().isoformat() if valor.time() == _dt.time() else valor.isoformat(sep=" ")
    if isinstance(valor, (_dt.date, _dt.time)):
        return valor.isoformat()
    return " ".join(str(valor).split()).replace("|", "\\|")


def tabla(filas):
    """Filas (listas de valores) → tabla Markdown. Quita filas y columnas vacías del borde."""
    filas = [[_celda(v) for v in fila] for fila in filas]
    filas = [f for f in filas if any(f)]
    if not filas:
        return ""
    ancho = max(max((i + 1 for i, v in enumerate(f) if v), default=0) for f in filas)
    filas = [(f + [""] * ancho)[:ancho] for f in filas]
    lineas = ["| " + " | ".join(filas[0]) + " |", "|" + " --- |" * ancho]
    lineas += ["| " + " | ".join(f) + " |" for f in filas[1:]]
    return "\n".join(lineas)


def hojas_xlsx(datos):
    """``[(nombre, filas)]`` de un .xlsx (bytes)."""
    import openpyxl

    try:
        libro = openpyxl.load_workbook(io.BytesIO(datos), read_only=True, data_only=True)
    except TypeError as exc:  # algunos programas escriben «showZeroes»; openpyxl lo rechaza
        if "showZeroes" not in str(exc):
            raise
        libro = openpyxl.load_workbook(io.BytesIO(_reparar_show_zeroes(datos)), read_only=True, data_only=True)
    try:
        return [(hoja.title, [list(f) for f in hoja.iter_rows(values_only=True)]) for hoja in libro.worksheets]
    finally:
        libro.close()


def _reparar_show_zeroes(datos):
    import re
    import zipfile

    etiqueta = re.compile(rb"<sheetView(?=[\s/>])[^>]*>")
    salida = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(datos)) as origen, zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as destino:
        for item in origen.infolist():
            contenido = origen.read(item.filename)
            if item.filename.startswith("xl/worksheets/") and b"showZeroes" in contenido:
                contenido = etiqueta.sub(lambda m: m.group(0).replace(b"showZeroes", b"showZeros"), contenido)
            destino.writestr(item, contenido)
    return salida.getvalue()


def hojas_xls(datos):
    """``[(nombre, filas)]`` de un .xls (Excel 97-2003, bytes)."""
    import xlrd

    libro = xlrd.open_workbook(file_contents=datos)
    hojas = []
    for hoja in libro.sheets():
        filas = []
        for r in range(hoja.nrows):
            fila = []
            for c in range(hoja.ncols):
                celda = hoja.cell(r, c)
                if celda.ctype == xlrd.XL_CELL_DATE:
                    fila.append(xlrd.xldate.xldate_as_datetime(celda.value, libro.datemode))
                elif celda.ctype == xlrd.XL_CELL_BOOLEAN:
                    fila.append(bool(celda.value))
                else:
                    fila.append(celda.value if celda.value != "" else None)
            filas.append(fila)
        hojas.append((hoja.name, filas))
    return hojas


def a_markdown(datos, extension):
    hojas = hojas_xls(datos) if extension == ".xls" else hojas_xlsx(datos)
    partes = []
    for nombre, filas in hojas:
        cuerpo = tabla(filas)
        partes.append(f"## {nombre}\n" + (cuerpo or "_(hoja vacía)_"))
    return "\n\n".join(partes)


def convertidor():
    """Un conversor para registrar en MarkItDown (se importa aquí: solo al convertir)."""
    from markitdown import DocumentConverter, DocumentConverterResult

    class ExcelSinPandas(DocumentConverter):
        def accepts(self, file_stream, stream_info, **kwargs):
            return (stream_info.extension or "").lower() in EXTENSIONES

        def convert(self, file_stream, stream_info, **kwargs):
            extension = (stream_info.extension or "").lower()
            return DocumentConverterResult(markdown=a_markdown(file_stream.read(), extension))

    return ExcelSinPandas()
