"""Sincronizar Canvas de punta a punta, con un Canvas falso y carpetas temporales."""

from datetime import date, timedelta

from tests.apoyo import CanvasFalso, ConCarpetaTemporal, modulo

HOY = date.today()
CALENDARIO = [{"semana": 6, "inicio": str(HOY - timedelta(days=1)), "fin": str(HOY + timedelta(days=1))}]
SECCIONES = {"material de clase": "Material de clase", "actividades": "Actividades"}


class ConfiguracionClasica(ConCarpetaTemporal):
    """Cursos escritos a mano con ``codigo``/``tipo`` (como los usa quien creó Pandex)."""

    def setUp(self):
        super().setUp()
        self.ciclo = self.tmp / "Ciclo"
        clase = self.ciclo / "Calculo" / "Sem 6" / "Material de clase"
        clase.mkdir(parents=True)
        (clase / "Clase 6.pdf").write_bytes(b"c" * 9000)
        (self.ciclo / "Programacion_I" / "Sem 6" / "Laboratorio").mkdir(parents=True)
        (self.ciclo / "Programacion_I" / "Sem 6" / "Teoría").mkdir(parents=True)
        CanvasFalso.reiniciar(
            cursos=[
                {"id": 3, "name": "Cálculo (CC6101) - Teoría 4"},
                {"id": 1, "name": "Programación I (CS6002) - Teoría 1"},
                {"id": 2, "name": "Programación I (CS6002) - Laboratorio 14"},
            ],
            modulos={
                3: [modulo("Semana 6", ("sub", "Material de clase"), ("file", "Clase 6.pdf", 101),
                           ("file", "Guia 6", 102), ("file", "Roto.pdf", 103), ("file", "Cortado.pdf", 104),
                           ("sub", "Sección rarísima"), ("file", "Perdido.pdf", 105))],
                1: [modulo("Semana 6", ("file", "S6 Teoria.pdf", 201))],
                2: [modulo("Semana 6", ("file", "S6 Teoria.pdf", 202))],
            },
            archivos={101: ("x.pdf", 9000), 102: ("Guia 6.pdf", 5000), 103: ("x.pdf", 6000),
                      104: ("x.pdf", 8000), 105: ("x.pdf", 4500), 201: ("x.pdf", 7000),
                      202: ("x.pdf", 7000)},
        )
        CanvasFalso.fallar, CanvasFalso.incompletos = {103}, {104}
        self.params = {
            "canvas_url": "https://canvas.ejemplo.edu", "destino": str(self.ciclo),
            "calendario": CALENDARIO, "secciones": SECCIONES,
            "cursos": [
                {"codigo": "CC6101", "carpeta": "Calculo", "alias": "Cálculo"},
                {"codigo": "CS6002", "tipo": "teoria", "carpeta": "Programacion_I",
                 "subcarpeta_fija": "Teoría", "alias": "Programación"},
                {"codigo": "CS6002", "tipo": "laboratorio", "carpeta": "Programacion_I",
                 "subcarpeta_fija": "Lab", "alias_subcarpeta": ["Laboratorio"], "alias": "Programación (lab)"},
            ],
        }

    def test_corridas_sucesivas(self):
        guia = self.ciclo / "Calculo" / "Sem 6" / "Material de clase" / "Guia 6.pdf"
        r, _ = self.sincronizar(self.params)
        self.assertEqual(guia.stat().st_size, 5000, "la guía baja con su extensión real")
        self.assertTrue((self.ciclo / "Programacion_I" / "Sem 6" / "Teoría" / "S6 Teoria.pdf").exists())
        self.assertFalse((self.ciclo / "Programacion_I" / "Sem 6" / "Laboratorio" / "S6 Teoria.pdf").exists(),
                         "el mismo archivo publicado en teoría y lab se baja una vez")
        self.assertEqual((guia.parent / "Clase 6.pdf").read_bytes(), b"c" * 9000, "no pisa lo que tenías")
        self.assertFalse((guia.parent / "Cortado.pdf").exists(), "un archivo incompleto no llega")
        self.assertFalse((guia.parent / "Roto.pdf").exists())
        self.assertFalse((guia.parent.parent / "Sección rarísima").exists(), "sección desconocida: nada")
        self.assertFalse(r["ok"])
        self.assertIn("Cálculo 1", r["resumen"])
        self.assertIn("Programación 1", r["resumen"])
        self.assertIn("no se pudieron bajar", r["resumen"])
        self.assertTrue(r["informe"])
        self.assertEqual(CanvasFalso.llamadas["archivo"], 7)

        r, _ = self.sincronizar(self.params)
        self.assertEqual(CanvasFalso.llamadas["archivo"], 4, "con historial no pregunta lo conocido")
        self.assertEqual(CanvasFalso.llamadas["listado"], 0, "recuerda que el listado está prohibido")
        self.assertEqual(CanvasFalso.llamadas["descargar"], 2, "reintenta solo lo que falló")

        CanvasFalso.fallar, CanvasFalso.incompletos = set(), set()
        r, _ = self.sincronizar(self.params)
        self.assertIn("2 nuevo(s): Cálculo 2", r["resumen"])

        guia.unlink()
        self.sincronizar(self.params)
        self.assertTrue(guia.exists(), "si borras algo que bajó Pandex, se revisa y vuelve")

    def test_sin_novedades_no_abre_ventana(self):
        self.params["cursos"] = self.params["cursos"][1:]
        self.sincronizar(self.params)
        r, _ = self.sincronizar(self.params)
        self.assertTrue(r["resumen"].startswith("✓ Todo al día · 2 cursos"), r["resumen"])
        self.assertIsNone(r["informe"])

    def test_corte_de_conexion(self):
        from pandex.canvas.cliente import SinConexion

        def sin_red(_self, _cid):
            raise SinConexion("Se cortó la conexión con Canvas")

        original = CanvasFalso.modulos
        CanvasFalso.modulos = sin_red
        try:
            r, _ = self.sincronizar(self.params)
        finally:
            CanvasFalso.modulos = original
        self.assertFalse(r["ok"])
        self.assertIn("conexión", r["resumen"])

    def test_fuera_del_ciclo_no_toca_nada(self):
        self.params["calendario"] = [{"semana": 1, "inicio": "2000-01-01", "fin": "2000-01-07"}]
        r, _ = self.sincronizar(self.params)
        self.assertIn("ninguna semana del ciclo", r["resumen"])

    def test_sin_configurar(self):
        r, _ = self.sincronizar({})
        self.assertFalse(r["ok"])
        self.assertIn("Configurar Canvas", r["resumen"])


class TeoriaYLaboratorio(ConCarpetaTemporal):
    """Teoría y lab son materiales distintos aunque compartan carpeta."""

    def setUp(self):
        super().setUp()
        self.pi = self.tmp / "Ciclo" / "Proyectos"
        (self.pi / "Sem 6" / "Teoría").mkdir(parents=True)
        (self.pi / "Sem 6" / "Laboratorio").mkdir(parents=True)
        (self.pi / "Sem 6" / "Teoría" / "semana 6.pptx").write_bytes(b"t" * 9000)
        (self.pi / "Glosario.pdf").write_bytes(b"g" * 5000)
        self.com = self.tmp / "Ciclo" / "Comunicacion"
        (self.com / "Sem 6" / "Material de clase").mkdir(parents=True)
        (self.com / "Sem 6" / "Material de clase" / "Clase.pptx").write_bytes(b"c" * 6000)
        (self.com / "Material de Laboratorio" / "Trabajos de laboratorio").mkdir(parents=True)

        def mod(sem, *ids):
            return modulo(f"Semana {sem}", ("sub", "Material de clases"),
                          *[("file", CanvasFalso.archivos[i][0], i) for i in ids])

        CanvasFalso.reiniciar(
            cursos=[
                {"id": 4, "name": "Proyectos I (PI6001) - Teoría 1"},
                {"id": 5, "name": "Proyectos I (PI6001) - Laboratorio 14"},
                {"id": 6, "name": "Comunicación (HH6001) - Teoría 1"},
                {"id": 7, "name": "Comunicación (HH6001) - Laboratorio 14"},
                {"id": 8, "name": "Taller colaborativo (PI6001) - Teoría 2"},  # «lab» dentro de una palabra
            ],
            modulos={}, archivos={
                401: ("semana 6.pptx", 9000), 402: ("Guia comun.pdf", 7777), 403: ("semana 7.pptx", 4000),
                501: ("semana 6.pptx", 12000), 502: ("Guia comun.pdf", 7777), 503: ("Glosario.pdf", 5000),
                504: ("semana 7.pptx", 4100), 601: ("Clase.pptx", 6000), 701: ("Clase.pptx", 8000),
            },
        )
        CanvasFalso.modulos_ = {
            4: [mod(6, 401, 402), mod(7, 403)],
            5: [mod(6, 501, 502, 503), mod(7, 504)],
            6: [modulo("Semana 6", ("sub", "Material de clase"), ("file", "Clase.pptx", 601))],
            7: [modulo("Laboratorio", ("sub", "Material de laboratorio"), ("file", "Clase.pptx", 701))],
        }
        self.params = {
            "canvas_url": "https://canvas.ejemplo.edu", "destino": str(self.tmp / "Ciclo"),
            "calendario": CALENDARIO,
            "secciones": {"material de clase": "Material de clase"},
            "cursos": [
                {"codigo": "HH6001", "tipo": "teoria", "carpeta": "Comunicacion", "alias": "Comunicación"},
                {"codigo": "HH6001", "tipo": "laboratorio", "carpeta": "Comunicacion", "modo": "lista",
                 "subcarpeta_raiz": "Material de Laboratorio", "seccion_unica": "material de laboratorio",
                 "nunca_escribir": ["Trabajos de laboratorio"], "alias": "Comunicación (lab)"},
                {"codigo": "PI6001", "tipo": "teoria", "carpeta": "Proyectos",
                 "subcarpeta_fija": "Teoría", "alias": "Proyectos"},
                {"codigo": "PI6001", "tipo": "laboratorio", "carpeta": "Proyectos",
                 "subcarpeta_fija": "Lab", "alias_subcarpeta": ["Laboratorio"], "alias": "Proyectos (lab)"},
            ],
        }

    def test_cada_mitad_recibe_lo_suyo(self):
        r, _ = self.sincronizar(self.params)
        lab6 = self.pi / "Sem 6" / "Laboratorio"
        self.assertEqual((lab6 / "semana 6.pptx").stat().st_size, 12000,
                         "el del lab se baja aunque teoría tenga uno con el mismo nombre")
        self.assertEqual((self.pi / "Sem 6" / "Teoría" / "semana 6.pptx").read_bytes(), b"t" * 9000)
        self.assertTrue((self.pi / "Sem 6" / "Teoría" / "Guia comun.pdf").exists())
        self.assertFalse((lab6 / "Guia comun.pdf").exists(), "el MISMO archivo en los dos se baja una vez")
        self.assertFalse((lab6 / "Glosario.pdf").exists(), "lo suelto en la raíz cuenta para los dos")
        self.assertEqual((self.pi / "Sem 7" / "Teoría" / "semana 7.pptx").stat().st_size, 4000)
        self.assertEqual((self.pi / "Sem 7" / "Lab" / "semana 7.pptx").stat().st_size, 4100)
        lab_com = self.com / "Material de Laboratorio" / "Sem 6" / "Clase.pptx"
        self.assertEqual(lab_com.stat().st_size, 8000, "modo lista: va a la semana del calendario")
        self.assertFalse(any((self.com / "Material de Laboratorio" / "Trabajos de laboratorio").iterdir()))
        self.assertTrue(r["resumen"].startswith("✓ 5 nuevo(s)"), r["resumen"])

        r, _ = self.sincronizar(self.params)
        self.assertTrue(r["resumen"].startswith("✓ Todo al día"), r["resumen"])


class ConfiguracionDelAsistente(ConCarpetaTemporal):
    """Lo que escribe el asistente: copia la organización de Canvas tal cual."""

    def setUp(self):
        super().setUp()
        self.raiz = self.tmp / "Cursos"
        self.raiz.mkdir()
        CanvasFalso.reiniciar(
            cursos=[{"id": 10, "name": "Física I (FI101) - Sección 2"}],
            modulos={10: [
                modulo("Sílabo y anexo", ("file", "Sílabo.pdf", 900)),
                modulo("Semana 1", ("file", "Bienvenida.pdf", 901), ("sub", "Material de clase"),
                       ("file", "Clase 1.pdf", 902), ("sub", "Lecturas"), ("file", "Lectura 1.pdf", 903)),
                modulo("Semana 2", ("sub", "Material de clase"), ("file", "Clase 2.pdf", 904)),
            ]},
            archivos={900: ("Sílabo.pdf", 5000), 901: ("Bienvenida.pdf", 5100), 902: ("Clase 1.pdf", 5200),
                      903: ("Lectura 1.pdf", 5300), 904: ("Clase 2.pdf", 5400)},
        )
        self.params = {
            "canvas_url": "https://canvas.ejemplo.edu", "destino": str(self.raiz),
            "formato_semana": "Semana {n:02d}", "secciones": {"Material de clase": "Material de clase"},
            "cursos": [{"canvas_id": 10, "carpeta": "Física I", "alias": "Física I",
                        "crear_secciones": True, "otros_modulos": True}],
        }

    def test_copia_la_organizacion_de_canvas(self):
        r, _ = self.sincronizar(self.params)
        fisica = self.raiz / "Física I"
        self.assertTrue((fisica / "Sílabo y anexo" / "Sílabo.pdf").exists(), "módulos sin semana: su carpeta")
        self.assertTrue((fisica / "Semana 01" / "Bienvenida.pdf").exists(), "sin subencabezado: en la semana")
        self.assertTrue((fisica / "Semana 01" / "Material de clase" / "Clase 1.pdf").exists())
        self.assertTrue((fisica / "Semana 01" / "Lecturas" / "Lectura 1.pdf").exists(),
                        "un subencabezado nuevo crea su carpeta")
        self.assertTrue((fisica / "Semana 02" / "Material de clase" / "Clase 2.pdf").exists())
        self.assertTrue(r["resumen"].startswith("✓ 5 nuevo(s)"), r["resumen"])

    def test_descarga_inicial_desde_una_semana(self):
        r, _ = self.sincronizar(self.params, {"inicial": "desde", "desde_semana": 2})
        fisica = self.raiz / "Física I"
        self.assertFalse((fisica / "Semana 01").exists(), "lo anterior a la semana elegida no baja")
        self.assertTrue((fisica / "Semana 02" / "Material de clase" / "Clase 2.pdf").exists())
        self.assertTrue((fisica / "Sílabo y anexo" / "Sílabo.pdf").exists(), "lo general sí baja")

        r, _ = self.sincronizar(self.params)
        self.assertFalse((fisica / "Semana 01").exists(), "y no baja después: quedó como omitido")
        self.assertTrue(r["resumen"].startswith("✓ Todo al día"), r["resumen"])

    def test_descarga_inicial_nada(self):
        self.sincronizar(self.params, {"inicial": "nada"})
        self.assertEqual(list(self.raiz.rglob("*.pdf")), [])
        CanvasFalso.modulos_[10].append(modulo("Semana 3", ("file", "Clase 3.pdf", 905)))
        CanvasFalso.archivos[905] = ("Clase 3.pdf", 5500)
        r, _ = self.sincronizar(self.params)
        self.assertEqual([p.name for p in self.raiz.rglob("*.pdf")], ["Clase 3.pdf"],
                         "después solo baja lo que se publique")
