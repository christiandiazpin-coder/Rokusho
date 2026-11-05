"""Pieza «informe»: convierte lo que el agente escribió en un entregable.

Decisión de diseño: el agente escribe Markdown y la pieza se encarga de la
presentación. Si se le pidiera HTML directamente, la mitad de las veces
inventaría etiquetas o estilos rotos. Separar contenido y forma hace que el
resultado sea consistente y que el agente pueda concentrarse en lo que sabe
hacer: escribir.

El HTML es imprimible: se abre en el navegador y se guarda como PDF sin
instalar nada. El Markdown sirve para pegar en correo o en Word.
"""

from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path

# Se configura al arrancar; por defecto, una subcarpeta del espacio de trabajo.
INFORMES = Path.cwd() / "trabajo" / "informes"

MAX_CONTENIDO = 120_000
FORMATOS = ("html", "markdown", "md")


def configurar(carpeta: Path) -> None:
    """Fija dónde se guardan los informes. La llama el CLI, no el modelo."""
    global INFORMES
    INFORMES = Path(carpeta).resolve() / "informes"


def _nombre_seguro(titulo: str) -> str:
    """Convierte un título en un nombre de archivo ASCII sin sorpresas.

    Se quitan los acentos a propósito: un archivo llamado «análisis.html» se
    rompe al compartirlo por correo, al subirlo a un servidor o al abrirlo
    desde una URL. El título visible conserva sus tildes; el nombre del
    archivo no.
    """
    import unicodedata

    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", titulo)
        if not unicodedata.combining(c))
    limpio = re.sub(r"[^a-zA-Z0-9\s-]", "", sin_acentos).strip().lower()
    limpio = re.sub(r"[\s_-]+", "-", limpio).strip("-")
    return (limpio or "informe")[:80]


def _fecha() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ─── Markdown → HTML ─────────────────────────────────────────────────────────
# Se implementa a mano, sin dependencias. Cubre lo que un informe necesita:
# títulos, párrafos, listas, tablas, negrita, código y citas.


def _en_linea(texto: str) -> str:
    """Aplica el formato en línea a un fragmento ya escapado."""
    texto = re.sub(r"`([^`]+)`", r"<code>\1</code>", texto)
    texto = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", texto)
    texto = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", texto)
    return texto


def _es_separador_tabla(linea: str) -> bool:
    return bool(re.fullmatch(r"\s*\|?[\s:|-]+\|?\s*", linea)) and "-" in linea


def _celdas(linea: str) -> list[str]:
    partes = linea.strip().strip("|").split("|")
    return [p.strip() for p in partes]


def _tabla(filas: list[str]) -> str:
    cabecera = _celdas(filas[0])
    cuerpo = [_celdas(f) for f in filas[2:]]
    salida = ["<table><thead><tr>"]
    salida.extend(f"<th>{_en_linea(html.escape(c))}</th>" for c in cabecera)
    salida.append("</tr></thead><tbody>")
    for fila in cuerpo:
        salida.append("<tr>")
        # Se rellena o recorta para que todas las filas tengan las mismas celdas.
        fila = (fila + [""] * len(cabecera))[: len(cabecera)]
        salida.extend(f"<td>{_en_linea(html.escape(c))}</td>" for c in fila)
        salida.append("</tr>")
    salida.append("</tbody></table>")
    return "".join(salida)


def markdown_a_html(texto: str) -> str:
    """Convierte un subconjunto de Markdown a HTML. Escapa todo lo demás."""
    lineas = texto.splitlines()
    salida: list[str] = []
    i = 0
    en_lista: str | None = None

    def cerrar_lista() -> None:
        nonlocal en_lista
        if en_lista:
            salida.append(f"</{en_lista}>")
            en_lista = None

    while i < len(lineas):
        linea = lineas[i]
        desnuda = linea.strip()

        if not desnuda:
            cerrar_lista()
            i += 1
            continue

        # Tabla: una línea con | seguida de un separador.
        if ("|" in desnuda and i + 1 < len(lineas)
                and _es_separador_tabla(lineas[i + 1])):
            cerrar_lista()
            bloque = [linea, lineas[i + 1]]
            i += 2
            # Las filas de datos empiezan justo después del separador. Antes se
            # avanzaba una línea de más y se perdía la primera fila.
            while i < len(lineas) and "|" in lineas[i] and lineas[i].strip():
                bloque.append(lineas[i])
                i += 1
            salida.append(_tabla(bloque))
            continue

        # Títulos.
        titulo = re.match(r"^(#{1,4})\s+(.*)$", desnuda)
        if titulo:
            cerrar_lista()
            nivel = len(titulo.group(1))
            salida.append(f"<h{nivel}>{_en_linea(html.escape(titulo.group(2)))}</h{nivel}>")
            i += 1
            continue

        # Separador horizontal. Sin este caso, «---» se imprimía como texto
        # literal en medio del informe.
        if re.fullmatch(r"(-\s*){3,}|(\*\s*){3,}|(_\s*){3,}", desnuda):
            cerrar_lista()
            salida.append("<hr>")
            i += 1
            continue

        # Cita.
        if desnuda.startswith("> "):
            cerrar_lista()
            salida.append(f"<blockquote>{_en_linea(html.escape(desnuda[2:]))}</blockquote>")
            i += 1
            continue

        # Listas ordenadas y sin ordenar.
        ordenada = re.match(r"^(\d+)[.)]\s+(.*)$", desnuda)
        vineta = re.match(r"^[-*+]\s+(.*)$", desnuda)

        if ordenada or vineta:
            tipo = "ol" if ordenada else "ul"
            if en_lista != tipo:
                cerrar_lista()
                salida.append(f"<{tipo}>")
                en_lista = tipo
            item = ordenada.group(2) if ordenada else vineta.group(1)
            salida.append(f"<li>{_en_linea(html.escape(item))}</li>")
            i += 1
            continue

        # Párrafo: se acumulan líneas hasta encontrar una vacía o un bloque.
        cerrar_lista()
        parrafo = [desnuda]
        i += 1
        while i < len(lineas):
            siguiente = lineas[i].strip()
            if (not siguiente or siguiente.startswith(("#", ">", "- ", "* ", "+ "))
                    or re.match(r"^\d+[.)]\s+", siguiente)
                    or ("|" in siguiente and i + 1 < len(lineas)
                        and _es_separador_tabla(lineas[i + 1]))):
                break
            parrafo.append(siguiente)
            i += 1
        salida.append(f"<p>{_en_linea(html.escape(' '.join(parrafo)))}</p>")

    cerrar_lista()
    return "\n".join(salida)


PLANTILLA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{titulo}</title>
<style>
  :root {{
    --tinta: #1a1a1a;
    --tenue: #5f6368;
    --linea: #d8dce0;
    --acento: #1f4e79;
    --fondo: #ffffff;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 48px 56px;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 15px; line-height: 1.62; color: var(--tinta);
    background: var(--fondo);
    max-width: 860px; margin-inline: auto;
  }}
  header {{ border-bottom: 2px solid var(--acento); padding-bottom: 18px; margin-bottom: 32px; }}
  header .marca {{
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    font-size: 10.5px; letter-spacing: .22em; text-transform: uppercase;
    color: var(--tenue); margin-bottom: 10px;
  }}
  header h1 {{ font-size: 26px; margin: 0 0 8px; line-height: 1.25; color: var(--acento); }}
  header .meta {{
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    font-size: 11.5px; color: var(--tenue); display: flex; gap: 18px; flex-wrap: wrap;
  }}
  h2 {{
    font-size: 18px; margin: 32px 0 12px; color: var(--acento);
    border-bottom: 1px solid var(--linea); padding-bottom: 6px;
  }}
  h3 {{ font-size: 15.5px; margin: 24px 0 8px; }}
  h4 {{ font-size: 14px; margin: 20px 0 6px; color: var(--tenue); }}
  p {{ margin: 0 0 12px; }}
  ul, ol {{ margin: 0 0 14px; padding-left: 24px; }}
  li {{ margin-bottom: 5px; }}
  table {{
    width: 100%; border-collapse: collapse; margin: 14px 0 20px;
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif; font-size: 13px;
  }}
  th, td {{ border: 1px solid var(--linea); padding: 8px 11px; text-align: left; vertical-align: top; }}
  th {{ background: #f3f5f7; font-weight: 600; }}
  hr {{ border: 0; border-top: 1px solid var(--linea); margin: 26px 0; }}
  blockquote {{
    margin: 14px 0; padding: 10px 16px; border-left: 3px solid var(--acento);
    background: #f7f9fb; color: var(--tenue); font-style: italic;
  }}
  code {{
    font-family: "SF Mono", Consolas, monospace; font-size: 12.5px;
    background: #f1f3f5; padding: 1px 5px; border-radius: 3px;
  }}
  footer {{
    margin-top: 48px; padding-top: 14px; border-top: 1px solid var(--linea);
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    font-size: 10.5px; color: var(--tenue); line-height: 1.6;
  }}
  @page {{ margin: 18mm; }}
  @media print {{
    body {{ padding: 0; max-width: none; font-size: 11pt; }}
    h2 {{ page-break-after: avoid; }}
    table, blockquote {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body>
<header>
  <div class="marca">{marca}</div>
  <h1>{titulo}</h1>
  <div class="meta"><span>{fecha}</span>{cliente}</div>
</header>
<main>
{cuerpo}
</main>
<footer>
  Documento generado por {marca}.<br>
  Para guardarlo como PDF: abrir en el navegador y elegir «Imprimir → Guardar como PDF».
</footer>
</body>
</html>
"""


def crear_informe(titulo: str, contenido: str, formato: str = "html",
                  cliente: str = "") -> str:
    titulo = (titulo or "").strip()
    if not titulo:
        return "ERROR: falta el título del informe."
    if not contenido or not contenido.strip():
        return ("ERROR: el contenido está vacío. Un informe sin contenido no es un "
                "entregable; escribe primero el texto.")
    if len(contenido) > MAX_CONTENIDO:
        return (f"ERROR: el contenido tiene {len(contenido):,} caracteres y el límite "
                f"es {MAX_CONTENIDO:,}. Divídelo en secciones o recórtalo.")

    formato = (formato or "html").strip().lower()
    if formato not in FORMATOS:
        return (f"ERROR: formato «{formato}» no reconocido. "
                f"Usa uno de: {', '.join(FORMATOS)}.")

    INFORMES.mkdir(parents=True, exist_ok=True)
    base = _nombre_seguro(titulo)
    fecha = _fecha()
    marca = "Rokusho"

    if formato in ("markdown", "md"):
        destino = INFORMES / f"{base}.md"
        texto = f"# {titulo}\n\n_{fecha}_"
        if cliente:
            texto += f" · {cliente}"
        texto += f"\n\n{contenido.strip()}\n\n---\n_Documento generado por {marca}._\n"
        try:
            destino.write_text(texto, encoding="utf-8")
        except OSError as e:
            return f"ERROR: no se pudo escribir el informe: {e}"
    else:
        destino = INFORMES / f"{base}.html"
        cuerpo = markdown_a_html(contenido)
        if not cuerpo.strip():
            return ("ERROR: el contenido no produjo ningún bloque de texto. "
                    "Revisa que no sea solo espacios en blanco.")
        bloque_cliente = f"<span>{html.escape(cliente)}</span>" if cliente else ""
        pagina = PLANTILLA.format(
            titulo=html.escape(titulo), cuerpo=cuerpo, fecha=fecha,
            cliente=bloque_cliente, marca=marca)
        try:
            destino.write_text(pagina, encoding="utf-8")
        except OSError as e:
            return f"ERROR: no se pudo escribir el informe: {e}"

    # Se mide el archivo resultante: no se afirma que quedó escrito sin verlo.
    try:
        tamano = destino.stat().st_size
    except OSError:
        return f"ERROR: se intentó escribir «{destino.name}» pero no se puede leer."
    if tamano == 0:
        return f"ERROR: «{destino.name}» quedó vacío ({tamano} bytes). No es un entregable."

    lineas = contenido.count("\n") + 1
    extra = ""
    if destino.suffix == ".html":
        extra = ("\n  Para PDF: abrir en el navegador → Imprimir → Guardar como PDF."
                 "\n  Para Word: abrir en el navegador y copiar, o crear también en markdown.")
    return (
        f"Informe creado y verificado:\n"
        f"  archivo: {destino}\n"
        f"  formato: {destino.suffix.lstrip('.')}\n"
        f"  tamaño: {tamano:,} bytes\n"
        f"  contenido de origen: {lineas} líneas, {len(contenido):,} caracteres\n"
        f"  fecha: {fecha}{extra}"
    )


def listar_informes() -> str:
    if not INFORMES.is_dir():
        return (f"Todavía no hay informes: la carpeta «{INFORMES}» no existe. "
                "Se crea al generar el primero.")

    archivos = sorted((p for p in INFORMES.iterdir()
                       if p.is_file() and p.suffix in (".html", ".md")),
                      key=lambda p: p.stat().st_mtime, reverse=True)
    if not archivos:
        return f"La carpeta de informes «{INFORMES}» está vacía."

    lineas = [f"Informes creados ({len(archivos)}):"]
    for a in archivos:
        info = a.stat()
        cuando = datetime.fromtimestamp(info.st_mtime).strftime("%Y-%m-%d %H:%M")
        lineas.append(f"  {a.name}  ({info.st_size:,} bytes, {cuando})")
    return "\n".join(lineas)


def leer_informe(nombre: str) -> str:
    if not nombre or not nombre.strip():
        return "ERROR: falta el nombre del informe."

    nombre = nombre.strip()
    candidato = (INFORMES / nombre).resolve()
    try:
        candidato.relative_to(INFORMES)
    except ValueError:
        return ("ERROR: esa ruta queda fuera de la carpeta de informes. "
                "Solo se pueden leer informes de ahí.")

    if not candidato.is_file():
        # Se intenta con las extensiones habituales.
        for sufijo in (".html", ".md"):
            alternativa = INFORMES / f"{nombre}{sufijo}"
            if alternativa.is_file():
                candidato = alternativa
                break
        else:
            return f"ERROR: no existe el informe «{nombre}». Usa listar_informes."

    try:
        texto = candidato.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return f"ERROR: no se pudo leer «{candidato.name}»: {e}"

    if candidato.suffix == ".md":
        return f"[{candidato.name}]\n{texto}"
    return (f"[{candidato.name} — vista de texto del HTML]\n"
            f"({len(texto):,} caracteres de HTML; se muestra sin etiquetas)\n\n"
            + re.sub(r"<[^>]+>", "", texto)[:15000])
