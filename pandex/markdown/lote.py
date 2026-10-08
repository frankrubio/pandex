"""Una conversión completa: revisar, convertir, verificar e informar.

Reglas:

- el tipo se decide SOLO por la extensión (MarkItDown no ejecuta Magika);
- el .md va junto al original; si ya existe se salta, salvo que se pida forzar;
- forzar solo reescribe .md que generó Pandex (llevan una marca en la línea 1);
- audio y video no se tocan: MarkItDown solo los entiende transcribiendo por internet;
- si el texto sale muy corto, en PDFs e imágenes se intenta el OCR de Windows
  (local y gratis); lo que siga corto se reporta para revisar.
"""

import traceback
from collections import Counter
from pathlib import Path

from .archivos import (
    CON_OCR,
    MARCA,
    PUEDEN_SER_IMAGEN,
    SIN_IA,
    SOPORTADOS,
    escribir_atomico,
    generado_por_pandex,
    nombres_repetidos,
    recorrer,
    ruta_md,
)
from .clasificador import Clasificador
from .conversion import OcrLocal, crear_markitdown, limpiar_pdf, motivo_legible


def convertir(ctx):
    entrada = ctx.entrada or {}
    forzar = bool(entrada.get("forzar"))
    umbral = int(ctx.params.get("umbral_contenido_imagen", 200))

    # ---- 1. qué hay que revisar
    # archivos marcados a mano = decisión tuya explícita: no se filtran
    elegidos_a_mano = bool(entrada.get("archivos"))
    filtro = "todos" if elegidos_a_mano else entrada.get("filtro", "estudio")
    if elegidos_a_mano:
        candidatos = [Path(s) for s in entrada["archivos"]]
        origen = f"{len(candidatos)} archivo(s) elegidos en {entrada.get('carpeta', '')}"
    else:
        carpeta = Path(entrada["carpeta"])
        candidatos = list(recorrer(carpeta, bool(entrada.get("recursivo"))))
        origen = f"{carpeta}" + ("  (con subcarpetas)" if entrada.get("recursivo") else "")

    clasificador = Clasificador(ctx.params.get("clasificacion"))
    convertibles, omitidos, sin_ia, ignorados = [], [], [], Counter()
    todos_convertibles = []
    for p in candidatos:
        ext = p.suffix.lower()
        if ext in SOPORTADOS:
            todos_convertibles.append(p)
            if filtro == "estudio":
                es, motivo = clasificador.clasificar(p)
                if not es:
                    omitidos.append((p, motivo))
                    continue
            convertibles.append(p)
        elif ext in SIN_IA:
            sin_ia.append(p)
        elif ext != ".md":
            ignorados[ext or "(sin extensión)"] += 1

    # nombres repetidos (Clase 3.pptx + Clase 3.pdf) sacados del recorrido que ya
    # se hizo, sin volver a leer cada carpeta. Cuentan TODOS los convertibles, no
    # solo los filtrados: si no, el .md se llamaría distinto según el botón usado.
    repetidos_por_carpeta = {}
    if not elegidos_a_mano:
        por_carpeta = {}
        for p in todos_convertibles:
            por_carpeta.setdefault(p.parent, Counter())[p.stem.casefold()] += 1
        repetidos_por_carpeta = {
            c: {s for s, n in cuenta.items() if n > 1} for c, cuenta in por_carpeta.items()
        }

    ctx.log(f"convertir_md: {origen} -> {len(convertibles)} a convertir, "
            f"{len(omitidos)} omitidos (filtro={filtro}), {len(sin_ia)} audio/video, "
            f"forzar={forzar}")

    convertidos, ya, fallidos, cortos, con_ocr, protegidos = [], [], [], [], [], []
    ocr = None
    if convertibles:
        ctx.decir(f"Reviso {len(convertibles)} archivo(s)…")
        motor = crear_markitdown()
        if ctx.params.get("ocr_local", True):
            ocr = OcrLocal(int(ctx.params.get("ocr_max_paginas", 60)))
            if not ocr.disponible:
                ctx.log(ocr.motivo, "warning")

        try:
            for i, archivo in enumerate(convertibles, start=1):
                ctx.progreso(i, len(convertibles))
                carpeta = archivo.parent
                if carpeta not in repetidos_por_carpeta:  # solo al elegir a mano
                    repetidos_por_carpeta[carpeta] = nombres_repetidos(carpeta)
                destino = ruta_md(archivo, repetidos_por_carpeta[carpeta])

                if destino.exists():
                    if not forzar:
                        ya.append(archivo)
                        continue
                    if not generado_por_pandex(destino):
                        protegidos.append(destino)
                        continue

                try:
                    texto = motor.convert_local(str(archivo)).markdown or ""
                except Exception as exc:
                    motivo = motivo_legible(exc)
                    fallidos.append((archivo, motivo))
                    ctx.log(f"falló {archivo}: {motivo}\n{traceback.format_exc()}", "warning")
                    continue

                via = "MarkItDown"
                if archivo.suffix.lower() == ".pdf":
                    texto = limpiar_pdf(texto)
                if (len(texto.strip()) < umbral and ocr is not None and ocr.disponible
                        and archivo.suffix.lower() in CON_OCR):
                    # el OCR es un respaldo: si falla, vale lo que sacó MarkItDown
                    try:
                        texto_ocr, nota = ocr.leer(archivo)
                    except Exception as exc:
                        ctx.log(f"OCR falló en {archivo.name}: {exc}", "warning")
                    else:
                        if len(texto_ocr.strip()) > len(texto.strip()):
                            texto, via = texto_ocr, f"OCR de Windows ({ocr.idioma})"
                            con_ocr.append((archivo, len(texto.strip()), nota))

                try:
                    cabecera = f"{MARCA} convertido desde «{archivo.name}» con {via} -->\n\n"
                    escribir_atomico(destino, cabecera + texto.strip() + "\n")
                except OSError as exc:
                    fallidos.append((archivo, f"no pude escribir el .md ({motivo_legible(exc)})"))
                    continue

                largo = len(texto.strip())
                convertidos.append((archivo, destino, largo))
                if largo < umbral and archivo.suffix.lower() in PUEDEN_SER_IMAGEN:
                    cortos.append((archivo, largo))
                ctx.log(f"convertido {archivo.name} -> {destino.name} ({largo} car., {via})")
        finally:
            if ocr is not None:
                ocr.cerrar()

    # ---- 2. verificar en disco lo que de verdad quedó
    reales = [c for c in convertidos if c[1].exists()]
    perdidos = [c for c in convertidos if not c[1].exists()]
    for archivo, destino, _ in perdidos:
        fallidos.append((archivo, "se convirtió pero el .md no aparece en disco"))

    if elegidos_a_mano:
        modo = "archivos elegidos a mano (sin filtrar)"
    elif filtro == "estudio":
        modo = "solo material de estudio"
    else:
        modo = "todos los archivos"
    modo += " · " + ("forzar reconversión" if forzar else "saltar los ya convertidos")

    informe = _informe(
        origen=origen, modo=modo, umbral=umbral,
        revisados=len(todos_convertibles) + len(sin_ia),
        reales=reales, ya=ya, fallidos=fallidos, sin_ia=sin_ia, omitidos=omitidos,
        cortos=cortos, con_ocr=con_ocr, protegidos=protegidos, ignorados=ignorados,
        ocr_motivo=ocr.motivo if ocr is not None and not ocr.disponible else None,
    )

    partes = []
    if reales:
        partes.append(f"convertí {len(reales)}")
    if ya:
        partes.append(f"{len(ya)} ya estaban")
    if omitidos:
        partes.append(f"{len(omitidos)} no eran material")
    if fallidos:
        partes.append(f"{len(fallidos)} fallaron")
    if cortos:
        partes.append(f"{len(cortos)} para revisar")
    if sin_ia:
        partes.append(f"{len(sin_ia)} sin soporte sin IA")
    resumen = ", ".join(partes) or "no había nada convertible"
    resumen = resumen[0].upper() + resumen[1:] + "."

    return {
        "ok": not fallidos,
        "resumen": resumen,
        "detalle": informe.splitlines(),
        "informe": informe,
        "carpeta": entrada.get("carpeta"),
    }



def _informe(origen, modo, umbral, revisados, reales, ya, fallidos, sin_ia, omitidos,
             cortos, con_ocr, protegidos, ignorados, ocr_motivo=None):
    def fila(etiqueta, n, extra=""):
        return f"  {etiqueta:.<42} {n:>5}{extra}"

    l = [
        "CONVERTIR A MARKDOWN — RESUMEN",
        f"Origen: {origen}",
        f"Modo: {modo}",
        "",
        fila("Archivos revisados ", revisados),
        fila("Convertidos ", len(reales)),
        fila("Ya convertidos (saltados) ", len(ya)),
        fila("No son material de estudio (omitidos) ", len(omitidos)),
        fila("Fallidos ", len(fallidos)),
        fila("Tipo no soportado sin IA ", len(sin_ia)),
        fila("Posible contenido-imagen ", len(cortos), "   (revisar)"),
    ]
    if con_ocr:
        l.append(fila("Leídos con OCR de Windows ", len(con_ocr)))
    if protegidos:
        l.append(fila(".md tuyos que no se pisaron ", len(protegidos)))
    if ocr_motivo and cortos:
        l.extend(["", f"Nota: {ocr_motivo}; los textos cortos quedaron sin OCR."])

    def seccion(titulo, filas):
        if filas:
            l.extend(["", titulo])
            l.extend(f"  · {f}" for f in filas)

    seccion("FALLIDOS", [f"{a.name} — {m}" for a, m in fallidos])
    seccion(
        f"POSIBLE CONTENIDO-IMAGEN, REVISAR  (menos de {umbral} caracteres)",
        [f"{a.name} — {n} caracteres  [{a.parent}]" for a, n in cortos],
    )
    seccion(
        "LEÍDOS CON OCR DE WINDOWS  (revisa: el OCR puede confundir letras)",
        [f"{a.name} — {n} caracteres" + (f"  ({nota})" if nota else "")
         for a, n, nota in con_ocr],
    )
    if omitidos:
        por_motivo = {}
        for a, motivo in omitidos:
            por_motivo.setdefault(motivo, []).append(a.name)
        filas = []
        for motivo, nombres in sorted(por_motivo.items(), key=lambda kv: -len(kv[1])):
            muestra = ", ".join(nombres[:6])
            resto = f" …y {len(nombres) - 6} más" if len(nombres) > 6 else ""
            filas.append(f"{motivo} ({len(nombres)}): {muestra}{resto}")
        seccion("NO SON MATERIAL DE ESTUDIO  (usa «Todos» si igual los quieres)", filas)
    seccion(
        "TIPO NO SOPORTADO SIN IA  (audio/video: MarkItDown los transcribe por internet)",
        [f"{a.name}  [{a.parent}]" for a in sin_ia],
    )
    seccion(
        ".md QUE YA EXISTÍAN Y NO SON DE PANDEX  (no se reescribieron)",
        [str(p) for p in protegidos],
    )
    if ignorados:
        top = ", ".join(f"{ext} ×{n}" for ext, n in ignorados.most_common(6))
        l.extend(["", f"Otros archivos ignorados (formato no pedido): {sum(ignorados.values())}"
                  f"  —  {top}"])
    if reales:
        l.extend(["", "CONVERTIDOS"])
        l.extend(f"  · {a.name}  →  {d.name}  ({n} car.)" for a, d, n in reales)
    return "\n".join(l)
