"""Credenciales fuera de config.json y del repositorio."""

try:
    import keyring as _keyring
except ImportError:
    _keyring = None

class ErrorCredencial(RuntimeError):
    pass


def _clave(nombre):
    if not isinstance(nombre, str) or not nombre or any(c.isspace() for c in nombre):
        raise ErrorCredencial("Nombre de credencial no válido")
    return nombre


def guardar(nombre, valor):
    nombre = _clave(nombre)
    if not isinstance(valor, str) or not valor:
        raise ErrorCredencial("La credencial está vacía")
    modulo = _keyring
    if modulo is None:
        raise ErrorCredencial("Instala el soporte de credenciales seguro y vuelve a conectar.")
    try:
        modulo.set_password("Pandex", nombre, valor)
    except Exception as exc:
        raise ErrorCredencial("No pude guardar la credencial en el almacén seguro.") from exc


def leer(nombre):
    nombre = _clave(nombre)
    modulo = _keyring
    if modulo is None:
        return None
    try:
        return modulo.get_password("Pandex", nombre)
    except Exception:
        return None


def borrar(nombre):
    nombre = _clave(nombre)
    modulo = _keyring
    if modulo is None:
        return
    try:
        modulo.delete_password("Pandex", nombre)
    except Exception:
        return
