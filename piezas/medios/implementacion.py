"""Pieza «medios»: mide archivos reales en vez de opinar sobre ellos.

Todo lo que devuelve sale de ffprobe o de un fotograma decodificado. La regla
del proyecto es que un render no está listo porque el archivo exista, sino
porque la medición lo confirma.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

# Se configura al arrancar; si no, se usa la carpeta actual.
TRABAJO = Path.cwd() / "trabajo"
TIEMPO_LIMITE = 120


def configurar(carpeta: Path) -> None:
    global TRABAJO
    TRABAJO = carpeta.resolve()


def _dentro(ruta_texto: str) -> Path:
    if not ruta_texto or not ruta_texto.strip():
        raise ValueError("la ruta viene vacía")
    candidata = (TRABAJO / ruta_texto).resolve()
    try:
        candidata.relative_to(TRABAJO)
    except ValueError:
        raise ValueError(
            f"«{ruta_texto}» queda fuera del espacio de trabajo."
        ) from None
    return candidata


def _ffprobe() -> str | None:
    return shutil.which("ffprobe")


def _ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


def medir(ruta: str) -> str:
    binario = _ffprobe()
    if not binario:
        return ("ERROR: ffprobe no está instalado en este equipo. "
                "No se puede medir el archivo; no lo afirmes como verificado.")
    archivo = _dentro(ruta)
    if not archivo.is_file():
        return f"ERROR: no existe el archivo «{ruta}»."

    proceso = subprocess.run(
        [binario, "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", str(archivo)],
        capture_output=True, text=True, timeout=TIEMPO_LIMITE)
    if proceso.returncode != 0:
        return f"ERROR: ffprobe falló con «{ruta}»: {proceso.stderr[:300]}"

    try:
        datos = json.loads(proceso.stdout)
    except json.JSONDecodeError:
        return f"ERROR: ffprobe devolvió algo que no es JSON para «{ruta}»."

    formato = datos.get("format") or {}
    pistas = datos.get("streams") or []
    lineas = [f"Medición real de «{ruta}» (ffprobe):"]

    duracion = formato.get("duration")
    if duracion:
        lineas.append(f"  duración: {float(duracion):.3f} s")
    tamano = formato.get("size")
    if tamano:
        lineas.append(f"  tamaño: {int(tamano) / 1_048_576:.1f} MB")

    for p in pistas:
        if p.get("codec_type") == "video":
            lineas.append(
                f"  video: {p.get('codec_name', '?')} "
                f"{p.get('width', '?')}x{p.get('height', '?')} "
                f"{p.get('r_frame_rate', '?')} fps "
                f"{p.get('pix_fmt', '?')}")
        elif p.get("codec_type") == "audio":
            lineas.append(
                f"  audio: {p.get('codec_name', '?')} "
                f"{p.get('sample_rate', '?')} Hz "
                f"{p.get('channels', '?')} canal(es)")

    if len(lineas) == 1:
        lineas.append("  (el archivo no declara pistas de audio ni de video)")
    return "\n".join(lineas)


def medir_nivel_audio(ruta: str) -> str:
    binario = _ffmpeg()
    if not binario:
        return "ERROR: ffmpeg no está instalado; no se puede medir el audio."
    archivo = _dentro(ruta)
    if not archivo.is_file():
        return f"ERROR: no existe el archivo «{ruta}»."

    proceso = subprocess.run(
        [binario, "-v", "info", "-i", str(archivo), "-af", "loudnorm=print_format=json",
         "-f", "null", "-"],
        capture_output=True, text=True, timeout=TIEMPO_LIMITE * 3)
    salida = proceso.stderr
    inicio = salida.rfind("{")
    fin = salida.rfind("}")
    if inicio < 0 or fin < inicio:
        return (f"ERROR: no se pudo medir el nivel de «{ruta}». "
                "No afirmes que el audio está bien sin este dato.")

    try:
        datos = json.loads(salida[inicio:fin + 1])
    except json.JSONDecodeError:
        return f"ERROR: la medición de «{ruta}» no devolvió cifras legibles."

    return (
        f"Nivel de audio medido de «{ruta}» (EBU R128):\n"
        f"  integrado: {datos.get('input_i', '?')} LUFS\n"
        f"  pico real: {datos.get('input_tp', '?')} dBTP\n"
        f"  rango: {datos.get('input_lra', '?')} LU\n"
        f"  referencia: para publicación en línea se apunta a −14 LUFS "
        f"(redes) o −16 a −18 LUFS (video); un pico sobre 0 dBTP satura."
    )


def fotograma(ruta: str, segundo: float = 0) -> str:
    binario = _ffmpeg()
    if not binario:
        return "ERROR: ffmpeg no está instalado; no se puede inspeccionar el fotograma."
    archivo = _dentro(ruta)
    if not archivo.is_file():
        return f"ERROR: no existe el archivo «{ruta}»."

    try:
        from PIL import Image  # importación local: la pieza no arranca sin PIL
        import numpy as np
    except ImportError as e:
        return (f"ERROR: falta una dependencia para leer el fotograma ({e}). "
                "No inventes la luminancia.")

    proceso = subprocess.run(
        [binario, "-v", "error", "-ss", str(segundo), "-i", str(archivo),
         "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True, timeout=TIEMPO_LIMITE)
    if not proceso.stdout:
        return (f"ERROR: no hay fotograma en el segundo {segundo} de «{ruta}». "
                "Puede estar más allá del final del archivo.")

    import io
    imagen = Image.open(io.BytesIO(proceso.stdout)).convert("L")
    matriz = np.asarray(imagen)
    media = float(matriz.mean())
    desviacion = float(matriz.std())
    claros = float((matriz > 150).mean() * 100)

    # Veredicto basado en el CONTRASTE, no en la luminancia media. Una lámina
    # antigua oscura tiene media baja (18) pero desviación alta (19) y está
    # perfectamente visible; un negro de verdad tiene desviación ~0. La media
    # sola etiquetaba de «negro» material que se ve bien, y el error contrario
    # (media 27, 0 % de claros, una sola línea) lo etiquetaba de «imagen».
    if desviacion < 6:
        veredicto = "negro pleno o un solo tono: sin imagen"
    elif desviacion < 12:
        veredicto = "casi sin contraste: apenas un trazo, no se lee como imagen"
    elif media < 30 and claros < 2:
        veredicto = "imagen muy oscura pero con detalle (lámina o rótulo sobre negro)"
    else:
        veredicto = "plano con imagen"

    return (
        f"Fotograma en {segundo} s de «{ruta}»:\n"
        f"  luminancia media: {media:.1f} (escala 0-255)\n"
        f"  desviación (contraste): {desviacion:.1f}\n"
        f"  píxeles claros: {claros:.2f} %\n"
        f"  veredicto: {veredicto}"
    )
