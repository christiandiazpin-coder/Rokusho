"""Pieza «memoria»: lo que el agente aprendió del negocio, entre sesiones.

Diseño: una entrada es un bloque con clave, contenido, fuente y fecha, guardado
en un único archivo de texto. Se eligió texto y no una base de datos porque el
cliente tiene que poder abrirlo, leerlo y corregirlo sin herramientas.

Regla del proyecto: cada entrada guarda **de dónde salió** (la fuente). Una
memoria sin fuente es una creencia, y una creencia guardada se vuelve un dato
falso que el agente repetirá con seguridad.

Regla de vida útil: si un dato deja de ser cierto, se borra. Un dato viejo es
peor que no tener el dato, porque el agente lo usará en lugar de preguntar.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

MEMORIA = Path.cwd() / "trabajo" / "memoria.md"

MAX_CLAVE = 120
MAX_CONTENIDO = 4_000
MAX_ENTRADAS = 500

INICIO = "<!-- entrada -->"
FIN = "<!-- fin-entrada -->"

PLANTILLA = """# Memoria del negocio

Lo que Rokusho aprendió de este negocio. Cada entrada dice de dónde salió.
Si un dato de aquí deja de ser cierto, bórralo: un dato viejo es peor que
ninguno, porque el agente lo usará en vez de preguntar.

<!-- entradas -->
<!-- fin-entradas -->
"""


class Entrada:
    __slots__ = ("clave", "contenido", "fuente", "fecha")

    def __init__(self, clave: str, contenido: str, fuente: str, fecha: str) -> None:
        self.clave = clave
        self.contenido = contenido
        self.fuente = fuente
        self.fecha = fecha

    def a_bloque(self) -> str:
        return (
            f"{INICIO}\n"
            f"## {self.clave}\n"
            f"- fecha: {self.fecha}\n"
            f"- fuente: {self.fuente}\n\n"
            f"{self.contenido}\n"
            f"{FIN}\n"
        )


def configurar(carpeta: Path) -> None:
    """Fija dónde vive la memoria. La llama el CLI, no el modelo."""
    global MEMORIA
    MEMORIA = Path(carpeta).resolve() / "memoria.md"


def _limpiar_clave(clave: str) -> str:
    # La clave va en un encabezado de Markdown: no puede llevar saltos ni ##.
    limpia = re.sub(r"[#\r\n\t]+", " ", clave or "").strip()
    return re.sub(r"\s+", " ", limpia)[:MAX_CLAVE]


def _leer() -> list[Entrada]:
    if not MEMORIA.is_file():
        return []
    try:
        texto = MEMORIA.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    entradas: list[Entrada] = []
    for bloque in texto.split(INICIO)[1:]:
        cuerpo = bloque.split(FIN)[0]
        lineas = cuerpo.strip().splitlines()
        if not lineas:
            continue
        clave = lineas[0].lstrip("# ").strip()
        fecha = ""
        fuente = ""
        resto: list[str] = []
        for linea in lineas[1:]:
            if linea.startswith("- fecha:"):
                fecha = linea.split(":", 1)[1].strip()
            elif linea.startswith("- fuente:"):
                fuente = linea.split(":", 1)[1].strip()
            else:
                resto.append(linea)
        entradas.append(Entrada(clave, "\n".join(resto).strip(), fuente, fecha))
    return entradas


def _escribir(entradas: list[Entrada]) -> None:
    MEMORIA.parent.mkdir(parents=True, exist_ok=True)
    partes = [PLANTILLA.split("<!-- entradas -->")[0], "<!-- entradas -->\n"]
    for e in entradas:
        partes.append(e.a_bloque())
    partes.append("<!-- fin-entradas -->\n")
    MEMORIA.write_text("".join(partes), encoding="utf-8")


def recordar(clave: str, contenido: str, fuente: str = "") -> str:
    clave_limpia = _limpiar_clave(clave)
    if not clave_limpia:
        return "ERROR: falta la clave. Es el nombre corto con el que recuperarás el dato."
    if not contenido or not contenido.strip():
        return ("ERROR: el contenido está vacío. Guardar una entrada vacía ocupa "
                "lugar y no dice nada.")
    if len(contenido) > MAX_CONTENIDO:
        return (f"ERROR: el contenido tiene {len(contenido):,} caracteres y el límite "
                f"es {MAX_CONTENIDO:,}. Guárdalo en un informe, no en la memoria.")

    entradas = _leer()
    existente = next((e for e in entradas if e.clave.casefold() == clave_limpia.casefold()), None)
    fecha = datetime.now().strftime("%Y-%m-%d")

    if existente is not None:
        anterior = existente.contenido
        existente.contenido = contenido.strip()
        # Si no dan fuente nueva, se conserva la que había: perder la procedencia
        # de un dato al actualizarlo sería un retroceso.
        if fuente and fuente.strip():
            existente.fuente = fuente.strip()
        existente.fecha = fecha
        _escribir(entradas)
        return (f"Entrada «{existente.clave}» actualizada.\n"
                f"  contenido anterior: {anterior[:200]}\n"
                f"  contenido nuevo: {existente.contenido[:200]}\n"
                f"  fuente: {existente.fuente or '(sin fuente)'}")

    if len(entradas) >= MAX_ENTRADAS:
        return (f"ERROR: la memoria ya tiene {len(entradas)} entradas y el límite es "
                f"{MAX_ENTRADAS}. Borra las que ya no sean ciertas con «olvidar».")

    nueva = Entrada(clave_limpia, contenido.strip(), (fuente or "").strip() or "(no indicada)", fecha)
    entradas.append(nueva)
    _escribir(entradas)

    aviso = ""
    if not fuente or not fuente.strip():
        aviso = ("\n  AVISO: guardado sin fuente. Un dato sin procedencia no se puede "
                 "verificar después; conviene indicar de dónde salió.")
    return (f"Guardado en la memoria:\n"
            f"  clave: {nueva.clave}\n"
            f"  fecha: {nueva.fecha}\n"
            f"  fuente: {nueva.fuente}\n"
            f"  archivo: {MEMORIA}{aviso}")


def recuperar(consulta: str) -> str:
    if not consulta or not consulta.strip():
        return "ERROR: no diste qué buscar."
    aguja = consulta.strip().casefold()

    entradas = _leer()
    if not entradas:
        return ("La memoria está vacía: todavía no hay nada guardado de este negocio. "
                "No supongas datos que no estén.")

    encontradas = [e for e in entradas
                   if aguja in e.clave.casefold() or aguja in e.contenido.casefold()
                   or aguja in e.fuente.casefold()]

    if not encontradas:
        claves = ", ".join(e.clave for e in entradas[:12])
        return (f"No hay nada en la memoria sobre «{consulta}».\n"
                f"Claves guardadas: {claves}\n"
                "Si el dato no está, hay que preguntarlo o buscarlo; no inventarlo.")

    lineas = [f"Memoria — {len(encontradas)} entrada(s) para «{consulta}»:"]
    for e in encontradas:
        lineas.append(f"\n## {e.clave}")
        lineas.append(f"  ({e.fecha} · fuente: {e.fuente})")
        for l in e.contenido.splitlines():
            lineas.append(f"  {l}")
    return "\n".join(lineas)


def listar_memoria() -> str:
    entradas = _leer()
    if not entradas:
        return "La memoria está vacía. Se llena con «recordar»."

    lineas = [f"Memoria del negocio — {len(entradas)} entrada(s):"]
    for e in entradas:
        fuente = "" if e.fuente == "(no indicada)" else f" · {e.fuente}"
        lineas.append(f"  {e.clave}  ({e.fecha}{fuente})")
    return "\n".join(lineas)


def olvidar(clave: str) -> str:
    clave_limpia = _limpiar_clave(clave)
    if not clave_limpia:
        return "ERROR: falta la clave que quieres borrar."

    entradas = _leer()
    if not entradas:
        return "La memoria está vacía: no hay nada que borrar."

    objetivo = next((e for e in entradas if e.clave.casefold() == clave_limpia.casefold()), None)
    if objetivo is None:
        parecidas = [e.clave for e in entradas if clave_limpia.casefold() in e.clave.casefold()]
        pista = f" Parecidas: {', '.join(parecidas)}." if parecidas else ""
        return f"ERROR: no hay ninguna entrada con la clave «{clave_limpia}».{pista}"

    entradas.remove(objetivo)
    _escribir(entradas)
    return (f"Borrada la entrada «{objetivo.clave}».\n"
            f"  quedan {len(entradas)} entrada(s) en la memoria.")
