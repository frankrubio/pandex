"""Todo lo de Canvas, separado por responsabilidad.

===================  ==========================================================
``nombres``          normalizar texto, nombres válidos en Windows, nº de semana
``cliente``          la API REST de Canvas con las cookies de tu sesión
``sesion``           iniciar sesión con un navegador (Playwright) y cerrarlo
``historial``        qué archivo de Canvas ya está en tu disco y dónde
``estructura``       leer cursos y módulos: semanas, secciones, teoría/lab
``destinos``         a qué carpeta va cada archivo y si ya lo tienes
``sincronizar``      la tarea completa, por fases
``adoptar``          usar una carpeta que ya tenías y reordenarla
``asistente``        la ventana de configuración inicial
===================  ==========================================================
"""
