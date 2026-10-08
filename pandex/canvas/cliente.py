"""La API REST de Canvas, usada con las cookies de tu sesión (sin tokens).

Hechos de Canvas que explican el diseño:

- A muchos alumnos ``/courses/{id}/files`` les responde 403 (pasa en UTEC): el
  nombre real y el tamaño de cada archivo hay que pedirlos uno por uno.
- Las respuestas largas vienen paginadas (cabecera ``Link: rel="next"``).
- Si se pregunta muy rápido, Canvas responde 429 o 403 "rate limit": se espera
  un poco y se reintenta.
"""

import threading
import time


class CanvasError(RuntimeError):
    def __init__(self, mensaje, estado=None):
        super().__init__(mensaje)
        self.estado = estado


class SinConexion(CanvasError):
    """La red se cayó o Canvas no respondió a tiempo."""


def _meta(info):
    return {"nombre": info.get("display_name") or info.get("filename") or "",
            "tamano": info.get("size")}


class Canvas:
    """Cliente mínimo. Cada hilo tiene su propia conexión: varias peticiones van a la vez."""

    def __init__(self, base_url, cookies, user_agent):
        self.base = base_url.rstrip("/")
        self._cookies = cookies
        self._ua = user_agent
        self._local = threading.local()

    def _sesion(self):
        s = getattr(self._local, "s", None)
        if s is None:
            import requests  # al sincronizar, no al abrir Pandex (~17 MB menos en reposo)

            s = requests.Session()
            s.headers["User-Agent"] = self._ua
            for c in self._cookies:
                s.cookies.set(c["name"], c["value"], domain=c.get("domain"), path=c.get("path", "/"))
            self._local.s = s
        return s

    def _get(self, url, params=None, stream=False, timeout=(10, 60)):
        """GET con reintentos si Canvas pide calma (límite de peticiones)."""
        import requests  # se carga al sincronizar, no al abrir Pandex
        for intento in range(4):
            try:
                resp = self._sesion().get(url, params=params, stream=stream, timeout=timeout)
            except requests.RequestException as exc:
                raise SinConexion("Se cortó la conexión con Canvas") from exc
            limitado = resp.status_code == 429 or (
                resp.status_code == 403 and "rate limit" in resp.text[:300].lower()
            )
            if not limitado:
                return resp
            time.sleep(1.5 * (intento + 1))
        return resp

    def api(self, ruta_o_url, params=None):
        """GET a ``/api/v1…``; junta todas las páginas si la respuesta es una lista."""
        url = ruta_o_url if ruta_o_url.startswith("http") else f"{self.base}/api/v1{ruta_o_url}"
        salida = []
        while url:
            resp = self._get(url, params=params)
            params = None  # la página "next" ya trae sus parámetros
            if resp.status_code != 200:
                raise CanvasError(f"Canvas respondió {resp.status_code}", resp.status_code)
            try:
                datos = resp.json()
            except ValueError as exc:
                raise CanvasError("Canvas respondió algo que no es JSON") from exc
            if not isinstance(datos, list):
                return datos
            salida.extend(datos)
            url = resp.links.get("next", {}).get("url")
        return salida

    def cursos(self):
        """Tus cursos activos."""
        return self.api("/courses", {"enrollment_state": "active", "per_page": 100})

    def modulos(self, curso_id):
        """Los módulos del curso con sus ítems (solo lo que el docente publicó).

        ``content_details`` trae si un ítem está bloqueado para ti y desde cuándo se
        abre: así no se intenta bajar lo que el docente programó para más adelante.
        """
        modulos = self.api(f"/courses/{curso_id}/modules",
                           {"include[]": ["items", "content_details"], "per_page": 100})
        for modulo in modulos:
            # con muchos ítems Canvas no los incluye: hay que pedirlos aparte
            if "items" not in modulo and modulo.get("items_url"):
                modulo["items"] = self.api(modulo["items_url"],
                                           {"include[]": "content_details", "per_page": 100})
        return modulos

    def archivos_del_curso(self, curso_id):
        """``{file_id: meta}`` en una llamada, o None si Canvas no deja ver el listado."""
        try:
            crudos = self.api(f"/courses/{curso_id}/files", {"per_page": 100})
        except SinConexion:
            raise
        except CanvasError as exc:
            if exc.estado in (401, 403, 404):
                return None
            raise
        return {f["id"]: _meta(f) for f in crudos if isinstance(f, dict) and "id" in f}

    def archivo(self, curso_id, file_id):
        """``{"nombre", "tamano"}`` de un archivo; ``{}`` si está bloqueado u oculto."""
        try:
            return _meta(self.api(f"/courses/{curso_id}/files/{file_id}"))
        except SinConexion:
            raise
        except CanvasError:
            return {}

    def descargar(self, curso_id, file_id, destino_tmp, espera_html=False):
        """Baja el archivo a ``destino_tmp`` y devuelve cuántos bytes escribió."""
        import requests
        url = f"{self.base}/courses/{curso_id}/files/{file_id}/download?download_frd=1"
        resp = self._get(url, stream=True, timeout=(10, 180))
        with resp:
            if resp.status_code != 200:
                raise CanvasError(f"Canvas devolvió {resp.status_code}", resp.status_code)
            tipo = (resp.headers.get("content-type") or "").lower()
            if tipo.startswith("text/html") and not espera_html:
                raise CanvasError("Canvas devolvió una página, no el archivo")
            escritos = 0
            try:
                with open(destino_tmp, "wb") as fh:
                    for trozo in resp.iter_content(1 << 16):
                        fh.write(trozo)
                        escritos += len(trozo)
            except requests.RequestException as exc:
                raise SinConexion("Se cortó la conexión con Canvas") from exc
        if not escritos:
            raise CanvasError("archivo vacío")
        return escritos
