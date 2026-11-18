"""A qué hosts se conecta Pandex (spec 004, PRI-04). Cualquier host nuevo cambia esa spec.

- El host de tu Canvas (la dirección que escribiste). Las descargas siguen la redirección que
  Canvas mismo manda a su almacenamiento de archivos; Pandex no pide nada fuera de Canvas.
- GitHub, solo al buscar o instalar actualizaciones.

Los programas que Pandex abre (tu navegador, rclone, pip) están en ``docs/privacidad.md``.
"""

from urllib.parse import urlsplit

GITHUB = frozenset({"raw.githubusercontent.com", "codeload.github.com", "github.com", "api.github.com"})


class ErrorRed(RuntimeError):
    """Un pedido a un host que no está en la lista."""


def host(url):
    try:
        partes = urlsplit(str(url))
        return (partes.hostname or "").lower() if partes.scheme in ("http", "https") and not partes.username \
            else ""
    except ValueError:
        return ""


def exigir(url, permitidos, solo_https=True):
    """Lanza ``ErrorRed`` si ``url`` no va a uno de ``permitidos`` (o no es https)."""
    destino = host(url)
    if not destino or destino not in permitidos or (solo_https and not str(url).lower().startswith("https://")):
        raise ErrorRed(f"Pandex no se conecta a «{destino or url}»: no está en su lista (docs/privacidad.md).")
    return url
