"""El motor: MarkItDown local (sin plugins ni IA) y el OCR local (Windows o Tesseract)."""

import io
import shutil
import subprocess
import sys

from .archivos import TEXTO_PLANO


def detectar_codificacion(muestra):
    """Reglas fijas en vez de adivinar.

    La detección estadística falla con archivos cortos: a un CSV de Excel en
    español le decía «cp1250» (centroeuropeo) y la Ñ salía rota. Orden:
    marca BOM → UTF-8 si decodifica limpio → cp1252, que es lo que usa Windows
    en español (Excel, Bloc de notas antiguo). Solo si ni eso encaja, se adivina.
    """
    if muestra.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if muestra.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16"
    try:
        muestra.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError as exc:
        # una letra de varios bytes cortada justo al final de la muestra no cuenta
        if exc.start >= len(muestra) - 3 and exc.reason == "unexpected end of data":
            return "utf-8"
    try:
        muestra.decode("cp1252")
        return "cp1252"
    except UnicodeDecodeError:
        import charset_normalizer

        mejor = charset_normalizer.from_bytes(muestra).best()
        return mejor.encoding if mejor else None


def crear_markitdown():
    """MarkItDown sin plugins, sin LLM y decidiendo el tipo solo por la extensión.

    Por defecto MarkItDown corre Magika (una red neuronal) sobre cada archivo para
    adivinar su tipo. Aquí se reemplaza ese paso: la extensión manda, y la
    codificación de los formatos de texto sale de detectar_codificacion().
    Se importa aquí dentro para no alargar el arranque de Pandex.
    """
    import mimetypes

    from markitdown import MarkItDown

    class MarkItDownPorExtension(MarkItDown):
        def _get_stream_info_guesses(self, file_stream, base_guess):
            ext = (base_guess.extension or "").lower()
            mimetype = mimetypes.guess_type("x" + ext, strict=False)[0]
            charset = None
            if ext in TEXTO_PLANO:
                pos = file_stream.tell()
                try:
                    charset = detectar_codificacion(file_stream.read(65536))
                finally:
                    file_stream.seek(pos)
            return [base_guess.copy_and_update(mimetype=mimetype, charset=charset)]

    return MarkItDownPorExtension(enable_plugins=False)


class _OcrBase:
    """Lo común: recorrer un PDF página por página o leer una imagen."""

    nombre = "OCR"
    motivo = None
    idioma = None

    def _reconocer(self, imagen):
        raise NotImplementedError

    def cerrar(self):
        pass

    def leer(self, archivo):
        """Devuelve (texto, nota). Nota explica si se cortó por tamaño."""
        if archivo.suffix.lower() == ".pdf":
            import pypdfium2 as pdfium

            doc = pdfium.PdfDocument(str(archivo))
            try:
                total = len(doc)
                paginas = []
                for i in range(min(total, self.max_paginas)):
                    texto = self._reconocer(doc[i].render(scale=2).to_pil())
                    if texto.strip():
                        paginas.append(f"## Página {i + 1}\n\n{texto.strip()}")
            finally:
                doc.close()
            nota = None
            if total > self.max_paginas:
                nota = f"OCR solo de las primeras {self.max_paginas} de {total} páginas"
            return "\n\n".join(paginas), nota

        from PIL import Image

        with Image.open(archivo) as imagen:
            return self._reconocer(imagen).strip(), None


class OcrTesseract(_OcrBase):
    """El OCR de Linux/macOS: el programa ``tesseract``, si está instalado. Local y gratis.

    Instalarlo (Debian/Ubuntu): ``sudo apt install tesseract-ocr tesseract-ocr-spa``.
    """

    nombre = "Tesseract"
    PREFERIDOS = ("spa", "eng")

    def __init__(self, max_paginas=60):
        self.max_paginas = max_paginas
        self.exe = shutil.which("tesseract")
        if self.exe is None:
            self.motivo = ("Tesseract no está instalado "
                           "(sudo apt install tesseract-ocr tesseract-ocr-spa)")
            return
        try:
            salida = subprocess.run([self.exe, "--list-langs"], capture_output=True, text=True,
                                    timeout=20).stdout.split()
        except (OSError, subprocess.SubprocessError):
            salida = []
        idiomas = [i for i in self.PREFERIDOS if i in salida]
        if not idiomas:
            self.exe = None
            self.motivo = ("Tesseract no tiene el idioma español ni inglés "
                           "(sudo apt install tesseract-ocr-spa)")
        else:
            self.idioma = "+".join(idiomas)

    @property
    def disponible(self):
        return self.exe is not None

    def _reconocer(self, imagen):
        buffer = io.BytesIO()
        imagen.convert("RGB").save(buffer, "PNG")
        r = subprocess.run([self.exe, "stdin", "stdout", "-l", self.idioma],
                           input=buffer.getvalue(), capture_output=True, timeout=180)
        return r.stdout.decode("utf-8", errors="replace")


class OcrLocal(_OcrBase):
    """El OCR que trae Windows (Windows.Media.Ocr). Local, gratis, sin internet."""

    nombre = "OCR de Windows"

    def __init__(self, max_paginas=60):
        self.max_paginas = max_paginas
        self.motivo = None
        self.idioma = None
        self._loop = None
        try:
            from winrt.windows.globalization import Language
            from winrt.windows.media.ocr import OcrEngine

            motor = OcrEngine.try_create_from_user_profile_languages()
            if motor is None:
                for tag in ("es-MX", "es-ES", "en-US"):
                    if OcrEngine.is_language_supported(Language(tag)):
                        motor = OcrEngine.try_create_from_language(Language(tag))
                        break
            self.motor = motor
            self.maximo = OcrEngine.max_image_dimension
            if motor is None:
                self.motivo = "Windows no tiene ningún idioma de OCR instalado"
            else:
                self.idioma = motor.recognizer_language.language_tag
        except Exception as exc:
            self.motor = None
            self.motivo = f"OCR de Windows no disponible ({exc.__class__.__name__})"

    @property
    def disponible(self):
        return self.motor is not None

    def _esperar(self, corrutina):
        # un solo bucle para todo el lote: crear uno por página es lento y ruidoso
        if self._loop is None:
            import asyncio  # solo con OCR: no se carga al abrir Pandex

            self._loop = asyncio.new_event_loop()
        return self._loop.run_until_complete(corrutina)

    def cerrar(self):
        if self._loop is not None:
            self._loop.close()
            self._loop = None

    async def _leer_png(self, png):
        from winrt.windows.graphics.imaging import BitmapDecoder
        from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream

        stream = InMemoryRandomAccessStream()
        writer = DataWriter(stream)
        writer.write_bytes(png)
        await writer.store_async()
        writer.detach_stream()
        stream.seek(0)
        decoder = await BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()
        resultado = await self.motor.recognize_async(bitmap)
        return "\n".join(linea.text for linea in resultado.lines)

    def _png(self, imagen):
        # el motor rechaza lados de más de max_image_dimension
        lado = max(imagen.size)
        if lado > self.maximo:
            factor = self.maximo / lado
            imagen = imagen.resize(
                (int(imagen.width * factor), int(imagen.height * factor))
            )
        buffer = io.BytesIO()
        imagen.convert("RGB").save(buffer, "PNG")
        return buffer.getvalue()

    def _reconocer(self, imagen):
        return self._esperar(self._leer_png(self._png(imagen)))


def crear_ocr(max_paginas=60):
    """El OCR del sistema: el de Windows allí, Tesseract en los demás."""
    return OcrLocal(max_paginas) if sys.platform == "win32" else OcrTesseract(max_paginas)


def limpiar_pdf(texto):
    """El texto de un PDF suele traer cada palabra separada por tabulaciones
    (``Fundamentos\tde\tCálculo``) y muchas líneas en blanco: lo deja legible."""
    import re

    lineas = [re.sub(r"[ \t]+", " ", linea).strip() for linea in texto.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lineas)).strip()


def motivo_legible(exc):
    """Una frase útil en vez de un traceback."""
    if isinstance(exc, PermissionError):
        return "sin permiso de lectura (¿está abierto en otra app, o solo en la nube sin conexión?)"
    if isinstance(exc, FileNotFoundError):
        return "el archivo ya no está"
    texto = f"{exc.__class__.__name__}: {exc}"
    bajo = texto.casefold()
    if "password" in bajo or "encrypt" in bajo or "contraseña" in bajo:
        return "está protegido con contraseña"
    if "missingdependency" in bajo:
        return "falta una librería para este formato (revisa requirements.txt)"
    if "badzipfile" in bajo or "not a zip file" in bajo:
        return "el archivo está dañado o no es lo que dice su extensión"
    if "unsupportedformat" in bajo:
        return "MarkItDown no reconoce su contenido"
    primera = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
    return primera[:160]
