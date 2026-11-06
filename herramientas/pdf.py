#!/usr/bin/env python3
"""Genera un PDF con la documentación de Rokusho, para revisar en papel.

Sin pandoc ni librerías de Markdown: se convierte a HTML con un conversor propio
y se imprime con Chrome. La razón es que el equipo donde corre esto no tiene las
herramientas habituales, y añadir dependencias por un PDF de revisión no se
justifica.

Lo que convierte: títulos, párrafos, listas, tablas, citas, negrita, cursiva y
código. Lo que no: enlaces (se imprimen como texto) e imágenes.

Uso:
    python -m herramientas.pdf --salida ~/Documentos/Rokusho-documentacion.pdf
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Orden de lectura: primero qué es el proyecto, al final cómo se publicó.
DOCUMENTOS = [
    ("README.md", "Qué es Rokusho"),
    ("docs/plan-de-negocios.md", "Plan de negocios"),
    ("docs/precio-y-venta.md", "Precio y forma de venta"),
    ("docs/prospectos.md", "Prospectos y recolección de contactos"),
    ("docs/mediciones.md", "Registro de mediciones y defectos"),
    ("docs/rokusho-001.md", "Rokusho-001: la tablet"),
    ("docs/rokusho-001-objetivo.md", "Rokusho-001: el objetivo real"),
    ("docs/GUIA-CONTINUIDAD.md", "Guía para continuar el proyecto"),
    ("docs/publicar-github-pages.md", "Cómo se publicó la web"),
    ("docs/publicar.md", "Opciones de alojamiento evaluadas"),
]


def _en_linea(texto: str) -> str:
    texto = re.sub(r"`([^`]+)`", r"<code>\1</code>", texto)
    texto = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", texto)
    texto = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", texto)
    return texto


def _celdas(linea: str) -> list[str]:
    return [c.strip() for c in linea.strip().strip("|").split("|")]


def _tabla(filas: list[str]) -> str:
    cab = _celdas(filas[0])
    cuerpo = [_celdas(f) for f in filas[2:]]
    out = ["<table><thead><tr>"]
    out.extend(f"<th>{_en_linea(html.escape(c))}</th>" for c in cab)
    out.append("</tr></thead><tbody>")
    for fila in cuerpo:
        fila = (fila + [""] * len(cab))[: len(cab)]
        out.append("<tr>")
        out.extend(f"<td>{_en_linea(html.escape(c))}</td>" for c in fila)
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def md_a_html(texto: str) -> str:
    """Convierte Markdown a HTML. Mismo criterio que la pieza «informe»."""
    lineas = texto.splitlines()
    out: list[str] = []
    i = 0
    lista: str | None = None

    def cerrar() -> None:
        nonlocal lista
        if lista:
            out.append(f"</{lista}>")
            lista = None

    while i < len(lineas):
        linea = lineas[i]
        d = linea.strip()

        if not d:
            cerrar()
            i += 1
            continue

        # Bloque de código cercado
        if d.startswith("```"):
            cerrar()
            i += 1
            bloque = []
            while i < len(lineas) and not lineas[i].strip().startswith("```"):
                bloque.append(lineas[i])
                i += 1
            i += 1
            out.append("<pre>" + html.escape("\n".join(bloque)) + "</pre>")
            continue

        # Tabla
        if ("|" in d and i + 1 < len(lineas)
                and re.fullmatch(r"\s*\|?[\s:|-]+\|?\s*", lineas[i + 1])
                and "-" in lineas[i + 1]):
            cerrar()
            bloque = [linea, lineas[i + 1]]
            i += 2
            while i < len(lineas) and "|" in lineas[i] and lineas[i].strip():
                bloque.append(lineas[i])
                i += 1
            out.append(_tabla(bloque))
            continue

        # Separador
        if re.fullmatch(r"(-\s*){3,}", d):
            cerrar()
            out.append("<hr>")
            i += 1
            continue

        # Títulos
        t = re.match(r"^(#{1,4})\s+(.*)$", d)
        if t:
            cerrar()
            n = len(t.group(1))
            out.append(f"<h{n}>{_en_linea(html.escape(t.group(2)))}</h{n}>")
            i += 1
            continue

        # Cita
        if d.startswith("> "):
            cerrar()
            cita = [d[2:]]
            i += 1
            while i < len(lineas) and lineas[i].strip().startswith("> "):
                cita.append(lineas[i].strip()[2:])
                i += 1
            out.append("<blockquote>" +
                       _en_linea(html.escape(" ".join(cita))) + "</blockquote>")
            continue

        # Listas
        ord_ = re.match(r"^(\d+)[.)]\s+(.*)$", d)
        vin = re.match(r"^[-*+]\s+(.*)$", d)
        if ord_ or vin:
            tipo = "ol" if ord_ else "ul"
            if lista != tipo:
                cerrar()
                out.append(f"<{tipo}>")
                lista = tipo
            item = ord_.group(2) if ord_ else vin.group(1)
            out.append(f"<li>{_en_linea(html.escape(item))}</li>")
            i += 1
            continue

        # Párrafo
        cerrar()
        par = [d]
        i += 1
        while i < len(lineas):
            sig = lineas[i].strip()
            if (not sig or sig.startswith(("#", "> ", "```"))
                    or re.match(r"^[-*+]\s", sig) or re.match(r"^\d+[.)]\s", sig)
                    or re.fullmatch(r"(-\s*){3,}", sig)):
                break
            par.append(sig)
            i += 1
        out.append(f"<p>{_en_linea(html.escape(' '.join(par)))}</p>")

    cerrar()
    return "\n".join(out)


PLANTILLA = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<title>Rokusho — documentación</title>
<style>
  @page {{ size: A4; margin: 18mm 16mm; }}
  body {{
    font-family: Georgia, "Times New Roman", serif;
    font-size: 10.5pt; line-height: 1.55; color: #1a1a1a; margin: 0;
  }}
  .portada {{
    page-break-after: always; text-align: left;
    padding-top: 95mm;
  }}
  .portada .marca {{
    font-family: Helvetica, Arial, sans-serif; font-size: 9pt;
    letter-spacing: .3em; text-transform: uppercase; color: #1f4e79;
    margin-bottom: 14mm;
  }}
  .portada h1 {{
    font-size: 30pt; margin: 0 0 8mm; line-height: 1.1; color: #1a1a1a;
  }}
  .portada .sub {{ font-size: 12pt; color: #5b6472; margin-bottom: 30mm; }}
  .portada .indice {{ font-size: 10pt; color: #333; }}
  .portada .indice div {{ margin-bottom: 2.5mm; }}
  .portada .pie {{
    font-family: Helvetica, Arial, sans-serif; font-size: 8.5pt;
    color: #8a929c; margin-top: 40mm;
  }}
  .doc {{ page-break-before: always; }}
  .doc > h1:first-child {{
    font-family: Helvetica, Arial, sans-serif; font-size: 17pt;
    color: #1f4e79; border-bottom: 2px solid #1f4e79;
    padding-bottom: 3mm; margin: 0 0 6mm;
  }}
  h2 {{
    font-family: Helvetica, Arial, sans-serif; font-size: 12pt;
    color: #1f4e79; margin: 9mm 0 3mm; page-break-after: avoid;
    border-bottom: 1px solid #d8dce0; padding-bottom: 1.5mm;
  }}
  h3 {{ font-family: Helvetica, Arial, sans-serif; font-size: 10.5pt; margin: 6mm 0 2mm; }}
  h4 {{ font-family: Helvetica, Arial, sans-serif; font-size: 10pt; color: #5b6472; margin: 4mm 0 1.5mm; }}
  p {{ margin: 0 0 3mm; text-align: justify; }}
  ul, ol {{ margin: 0 0 3mm; padding-left: 6mm; }}
  li {{ margin-bottom: 1.2mm; }}
  table {{
    width: 100%; border-collapse: collapse; margin: 3mm 0 5mm;
    font-family: Helvetica, Arial, sans-serif; font-size: 8.5pt;
    page-break-inside: avoid;
  }}
  th, td {{ border: 1px solid #d8dce0; padding: 1.8mm 2.5mm; text-align: left; vertical-align: top; }}
  th {{ background: #f2f5f8; font-weight: 600; }}
  blockquote {{
    margin: 3mm 0; padding: 2mm 4mm; border-left: 2.5px solid #1f4e79;
    background: #f7f9fb; color: #444; font-style: italic;
  }}
  code {{
    font-family: "DejaVu Sans Mono", monospace; font-size: 8.5pt;
    background: #f1f3f5; padding: 0.3mm 1mm; border-radius: 1mm;
  }}
  pre {{
    background: #f6f8fa; border: 1px solid #e1e4e8; padding: 3mm;
    font-family: "DejaVu Sans Mono", monospace; font-size: 8pt;
    overflow-wrap: break-word; white-space: pre-wrap; page-break-inside: avoid;
  }}
  hr {{ border: 0; border-top: 1px solid #d8dce0; margin: 6mm 0; }}
</style></head><body>
{portada}
{cuerpo}
</body></html>
"""


def construir(destino: Path) -> int:
    fuentes: list[tuple[str, str]] = []
    indice: list[str] = []
    for ruta_rel, titulo in DOCUMENTOS:
        ruta = RAIZ / ruta_rel
        if not ruta.is_file():
            print(f"  aviso: no existe {ruta_rel}; se omite")
            continue
        texto = ruta.read_text(encoding="utf-8")
        # El título propio del documento se reemplaza por el del índice, para
        # que el PDF tenga una jerarquía coherente y no diez H1 distintos.
        texto = re.sub(r"^#\s+.*\n", "", texto, count=1)
        fuentes.append((titulo, md_a_html(texto)))
        indice.append(titulo)

    if not fuentes:
        print("No hay documentos que convertir.")
        return 1

    # strftime con %B depende del locale del sistema y devolvía «November»
    # dentro de un documento en español.
    meses = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre")
    ahora = datetime.now()
    fecha = f"{ahora.day} de {meses[ahora.month - 1]} de {ahora.year}"
    portada = (
        '<div class="portada">'
        '<div class="marca">Rokusho</div>'
        '<h1>Documentación del proyecto</h1>'
        f'<div class="sub">Para revisión · {fecha}</div>'
        '<div class="indice">'
        + "".join(f"<div>{i}. {html.escape(t)}</div>"
                  for i, t in enumerate(indice, 1))
        + '</div>'
        '<div class="pie">Rokusho · informes con fuente verificable · '
        'Villa Alemana, Chile</div></div>'
    )

    cuerpo = "\n".join(
        f'<section class="doc"><h1>{html.escape(t)}</h1>{h}</section>'
        for t, h in fuentes)

    pagina = PLANTILLA.format(portada=portada, cuerpo=cuerpo)
    temporal = Path(tempfile.mkdtemp()) / "rokusho.html"
    temporal.write_text(pagina, encoding="utf-8")

    chrome = (shutil.which("google-chrome") or shutil.which("chromium")
              or shutil.which("chromium-browser"))
    if not chrome:
        print("ERROR: no se encontró Chrome ni Chromium para imprimir el PDF.")
        print(f"El HTML quedó en {temporal}; se puede imprimir desde el navegador.")
        return 1

    destino.parent.mkdir(parents=True, exist_ok=True)
    orden = [chrome, "--headless", "--disable-gpu", "--no-sandbox",
             "--no-pdf-header-footer", f"--print-to-pdf={destino}",
             f"file://{temporal}"]
    proceso = subprocess.run(orden, capture_output=True, text=True, timeout=180)
    if not destino.is_file():
        print(f"ERROR: Chrome no generó el PDF.\n{proceso.stderr[:400]}")
        return 1

    print(f"PDF generado: {destino}")
    print(f"  {destino.stat().st_size / 1024:.0f} KB · {len(fuentes)} documentos")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Genera un PDF con la documentación.")
    p.add_argument("--salida", default=str(Path.home() / "Documentos" /
                                           "Rokusho-documentacion.pdf"))
    args = p.parse_args(argv)
    return construir(Path(args.salida).expanduser())


if __name__ == "__main__":
    raise SystemExit(main())
