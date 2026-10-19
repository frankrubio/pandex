# Seguridad

## Reportar una vulnerabilidad

Si encuentras algo que podría exponer datos de quien usa Pandex (su sesión de Canvas, sus
rutas, sus archivos) o permitir que alguien ejecute código en su PC:

1. **No abras un issue público.**
2. Usa **Security → Report a vulnerability** en este repositorio (aviso privado de GitHub).
3. Cuenta qué encontraste, cómo reproducirlo y qué versión de Pandex usas (Configuración →
   Acerca de).

Se responde en cuanto sea posible. Pandex es un proyecto estudiantil sin equipo dedicado, así
que no hay un plazo garantizado; los arreglos de seguridad tienen prioridad sobre todo lo demás.

## Qué cuenta como vulnerabilidad

- Que Pandex guarde, registre o envíe contraseñas, cookies o tokens.
- Que hable con un servidor que no figura en [docs/privacidad.md](docs/privacidad.md).
- Que escriba o borre fuera de los lugares de [specs/principios.md](specs/principios.md#p3-sin-residuos).
- Que una actualización pueda instalar código que no viene de este repositorio.
- Que un archivo descargado de Canvas pueda ejecutarse solo o escribir fuera de la carpeta de
  cursos (p. ej. nombres con `..`).

## Para quien contribuye

- Nunca subas `config.json`, `logs/`, perfiles de navegador ni capturas con datos reales. La
  CI lo revisa (`tests/test_principios.py`), pero la primera barrera eres tú.
- Si subiste algo personal por error, **no basta con borrarlo en otro commit**: queda en el
  historial. Avisa por el canal privado para limpiarlo.
- Revisa con cuidado el código generado por IA antes de proponerlo: puede verse bien y aun así
  registrar datos sensibles o abrir rutas fuera de lo permitido. El checklist del PR lo pide.
