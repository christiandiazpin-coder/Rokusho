"""Pieza «archivos»: acceso de solo lectura al espacio de trabajo del cliente.

Regla de seguridad: el agente no puede salir de la carpeta de trabajo ni escribir
en ella. Esto no es una restricción de conveniencia; es lo que permite decirle a
un cliente que su material no se puede tocar por accidente.
"""

from __future__ import annotations

import os
from pathlib import Path

# Se configura al arrancar; si no, se usa la carpeta actual.
TRABAJO = Path.cwd() / "trabajo"

MAX_BYTES = 400_000
MAX_LINEAS = 2_000
MAX_RESULTADOS = 60


def configurar(carpeta: Path) -> None:
    """Fija la carpeta de trabajo. La llama el CLI, no el modelo."""
    global TRABAJO
    TRABAJO = carpeta.resolve()


class FueraDelEspacio(Exception):
    """La ruta pedida no está dentro del espacio de trabajo del cliente."""


def _dentro(ruta_texto: str) -> Path:
    """Resuelve una ruta y verifica que quede dentro del espacio de trabajo.

    Se usa `resolve()`, que sigue los enlaces simbólicos: así un enlace dentro de
    la carpeta que apunte fuera del sistema se rechaza igual que una ruta con
    `..`. Sin eso, un enlace sería una puerta abierta al resto del disco.

    Lanza `FueraDelEspacio`, que las herramientas convierten en mensaje. Antes
    lanzaba `ValueError` y el chasis lo reportaba como «la herramienta falló»,
    mezclando un rechazo deliberado con una herramienta rota.
    """
    if not ruta_texto or not ruta_texto.strip():
        raise FueraDelEspacio("la ruta viene vacía")
    candidata = (TRABAJO / ruta_texto).resolve()
    try:
        candidata.relative_to(TRABAJO)
    except ValueError:
        raise FueraDelEspacio(
            f"«{ruta_texto}» queda fuera del espacio de trabajo. "
            "Solo puedes leer lo que está dentro."
        ) from None
    return candidata


def _relativa(ruta: Path) -> str:
    try:
        return str(ruta.relative_to(TRABAJO))
    except ValueError:
        return str(ruta)


def listar(ruta: str = ".") -> str:
    try:
        carpeta = _dentro(ruta)
    except FueraDelEspacio as e:
        return f"RECHAZADO: {e}"
    if not carpeta.exists():
        return f"ERROR: no existe «{ruta}»."
    if not carpeta.is_dir():
        return f"ERROR: «{ruta}» es un archivo, no una carpeta."

    entradas = sorted(carpeta.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    if not entradas:
        return f"La carpeta «{_relativa(carpeta)}» está vacía."

    lineas = [f"Contenido de «{_relativa(carpeta)}» ({len(entradas)} entradas):"]
    for e in entradas[:MAX_RESULTADOS]:
        if e.is_dir():
            lineas.append(f"  [carpeta] {e.name}/")
        else:
            lineas.append(f"  {e.name}  ({e.stat().st_size:,} bytes)")
    if len(entradas) > MAX_RESULTADOS:
        lineas.append(f"  … y {len(entradas) - MAX_RESULTADOS} más.")
    return "\n".join(lineas)


def leer(ruta: str, desde: int = 1, hasta: int = 0) -> str:
    try:
        archivo = _dentro(ruta)
    except FueraDelEspacio as e:
        return f"RECHAZADO: {e}"
    if not archivo.exists():
        return f"ERROR: no existe «{ruta}»."
    if not archivo.is_file():
        return f"ERROR: «{ruta}» es una carpeta. Usa listar."

    tamano = archivo.stat().st_size
    if tamano > MAX_BYTES:
        return (f"ERROR: «{ruta}» pesa {tamano:,} bytes y el límite es {MAX_BYTES:,}. "
                "No se leyó: pedir un rango no serviría porque no se puede indexar sin leerlo.")

    try:
        texto = archivo.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return (f"ERROR: «{ruta}» no es texto legible en UTF-8. "
                "Probablemente es un binario (PDF, imagen, planilla).")

    lineas = texto.splitlines()
    total = len(lineas)
    desde = max(1, int(desde or 1))
    hasta = int(hasta or 0)
    if hasta <= 0:
        hasta = min(total, desde + MAX_LINEAS - 1)
    hasta = min(hasta, total)

    if desde > total:
        return f"ERROR: «{ruta}» tiene {total} líneas; pediste desde la {desde}."

    trozo = lineas[desde - 1:hasta]
    cuerpo = "\n".join(f"{i:>5}| {l}" for i, l in enumerate(trozo, desde))
    cabecera = f"[{_relativa(archivo)} — líneas {desde}-{hasta} de {total}]"
    if hasta < total:
        cabecera += f"\n(quedan {total - hasta} líneas; pide el siguiente rango con desde={hasta + 1})"
    return f"{cabecera}\n{cuerpo}"


def buscar(texto: str) -> str:
    aguja = (texto or "").strip()
    if not aguja:
        return "ERROR: no diste un texto que buscar."
    if not TRABAJO.is_dir():
        return f"ERROR: el espacio de trabajo «{TRABAJO}» no existe."

    encontrados: list[str] = []
    sin_leer: list[str] = []
    aguja_baja = aguja.casefold()

    for archivo in sorted(TRABAJO.rglob("*")):
        if not archivo.is_file():
            continue
        if any(parte.startswith(".") or parte == "__pycache__" for parte in archivo.parts):
            continue
        try:
            if archivo.stat().st_size > MAX_BYTES:
                sin_leer.append(_relativa(archivo))
                continue
            contenido = archivo.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            sin_leer.append(_relativa(archivo))
            continue

        for numero, linea in enumerate(contenido.splitlines(), 1):
            if aguja_baja in linea.casefold():
                encontrados.append(f"{_relativa(archivo)}:{numero}: {linea.strip()[:200]}")
                if len(encontrados) >= MAX_RESULTADOS:
                    break
        if len(encontrados) >= MAX_RESULTADOS:
            break

    if not encontrados:
        aviso = f"No se encontró «{aguja}» en el espacio de trabajo."
        if sin_leer:
            aviso += ("\nNo se pudieron leer (binarios o demasiado grandes): "
                      + ", ".join(sin_leer[:10]))
        return aviso

    salida = [f"{len(encontrados)} coincidencia(s) de «{aguja}»:"]
    salida.extend(encontrados)
    if len(encontrados) >= MAX_RESULTADOS:
        salida.append(f"(se cortó en {MAX_RESULTADOS}; afina la búsqueda)")
    return "\n".join(salida)
