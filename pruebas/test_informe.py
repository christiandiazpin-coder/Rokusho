"""Pruebas de la pieza «informe».

El caso central: la conversión de Markdown a HTML. Un conversor que se come una
fila de una tabla produce un informe que **parece** correcto y omite un dato.
Ese es el peor error posible en este proyecto, así que la tabla se prueba fila
por fila.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from chasis.pieza import cargar, _importar

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def pieza():
    return cargar("informe", raiz=RAIZ / "piezas")


@pytest.fixture()
def modulo():
    return _importar(RAIZ / "piezas" / "informe" / "implementacion.py", "informe_test")


@pytest.fixture()
def espacio(tmp_path, pieza):
    pieza.configurar(tmp_path)
    return tmp_path


MD_COMPLETO = """## Resumen ejecutivo

El contrato tiene **12 meses** de plazo desde el 1 de marzo de 2026.

### Datos verificados

| Dato | Valor | Fuente |
|---|---|---|
| Monto mensual | 850.000 pesos | cláusula TERCERO |
| Plazo | 12 meses | cláusula SEGUNDO |
| Renovación | 6 meses | cláusula CUARTO |

### Pendientes

1. No indica moneda expresa
2. No menciona IVA

- Sin causal de término
- Sin tribunal competente

> El contrato no consigna el valor total del período.
"""


# ── conversión de Markdown ───────────────────────────────────────────────────

def test_tabla_conserva_todas_las_filas(modulo):
    """Regresión: el conversor perdía la primera fila de datos."""
    md = ("| Dato | Valor |\n|---|---|\n"
          "| Uno | 1 |\n| Dos | 2 |\n| Tres | 3 |\n")
    salida = modulo.markdown_a_html(md)
    for esperado in ("Uno", "Dos", "Tres"):
        assert esperado in salida, f"falta la fila «{esperado}» en:\n{salida}"
    assert salida.count("<tr>") == 4  # 1 cabecera + 3 datos


def test_tabla_de_una_sola_fila(modulo):
    md = "| A | B |\n|---|---|\n| 1 | 2 |\n"
    salida = modulo.markdown_a_html(md)
    assert "<td>1</td>" in salida and "<td>2</td>" in salida


def test_titulos_por_nivel(modulo):
    salida = modulo.markdown_a_html("# Uno\n## Dos\n### Tres\n")
    assert "<h1>Uno</h1>" in salida
    assert "<h2>Dos</h2>" in salida
    assert "<h3>Tres</h3>" in salida


def test_listas_ordenadas_y_sin_ordenar(modulo):
    salida = modulo.markdown_a_html("1. uno\n2. dos\n\n- a\n- b\n")
    assert "<ol>" in salida and "<ul>" in salida
    assert salida.count("<li>") == 4


def test_lista_no_se_queda_abierta_entre_bloques(modulo):
    salida = modulo.markdown_a_html("- a\n\nTexto suelto.\n")
    assert "</ul>" in salida
    assert "<p>Texto suelto.</p>" in salida


def test_negrita_y_cursiva(modulo):
    salida = modulo.markdown_a_html("Tiene **12 meses** de plazo y *énfasis*.\n")
    assert "<strong>12 meses</strong>" in salida
    assert "<em>énfasis</em>" in salida


def test_cita(modulo):
    salida = modulo.markdown_a_html("> No consigna el total.\n")
    assert "<blockquote>" in salida


def test_caracteres_especiales_se_escapan(modulo):
    """Un informe con HTML escrito por el agente no debe inyectar etiquetas."""
    salida = modulo.markdown_a_html("Precio < 100 y script <script>alert(1)</script>\n")
    assert "<script>" not in salida
    assert "&lt;script&gt;" in salida


def test_parrafo_de_varias_lineas_se_une(modulo):
    salida = modulo.markdown_a_html("Primera línea\nsegunda línea\n")
    assert salida.count("<p>") == 1


def test_texto_vacio_no_produce_html(modulo):
    assert modulo.markdown_a_html("   \n\n  \n").strip() == ""


# ── creación de archivos ─────────────────────────────────────────────────────

def test_crear_informe_html(espacio, pieza):
    f = {h.nombre: h.funcion for h in pieza.herramientas}
    r = f["crear_informe"]("Análisis de contrato", MD_COMPLETO, "html", "Cliente SpA")
    assert "verificado" in r
    archivo = espacio / "informes" / "analisis-de-contrato.html"
    assert archivo.is_file()
    html = archivo.read_text(encoding="utf-8")
    assert "<table>" in html
    assert "850.000 pesos" in html
    assert "Cliente SpA" in html
    assert "<!DOCTYPE html>" in html


def test_crear_informe_markdown(espacio, pieza):
    f = {h.nombre: h.funcion for h in pieza.herramientas}
    f["crear_informe"]("Análisis", MD_COMPLETO, "markdown")
    archivo = espacio / "informes" / "analisis.md"
    assert archivo.is_file()
    texto = archivo.read_text(encoding="utf-8")
    assert texto.startswith("# Análisis")
    assert "850.000 pesos" in texto


def test_nombre_de_archivo_sin_acentos_ni_simbolos(espacio, pieza):
    """Un archivo «análisis.html» se rompe al compartirlo; debe ser ASCII."""
    f = {h.nombre: h.funcion for h in pieza.herramientas}
    f["crear_informe"]("Análisis de presión — Ñandú & Cía. (2026)", MD_COMPLETO, "html")
    archivos = list((espacio / "informes").iterdir())
    assert len(archivos) == 1
    nombre = archivos[0].name
    assert nombre.isascii(), f"el nombre «{nombre}» tiene caracteres no ASCII"
    assert not re.search(r"[—&()]", nombre)


def test_titulo_vacio_falla(espacio, pieza):
    f = {h.nombre: h.funcion for h in pieza.herramientas}
    assert "ERROR" in f["crear_informe"]("", MD_COMPLETO)


def test_contenido_vacio_falla(espacio, pieza):
    f = {h.nombre: h.funcion for h in pieza.herramientas}
    r = f["crear_informe"]("Título", "   ")
    assert "ERROR" in r and "vacío" in r


def test_formato_desconocido_falla(espacio, pieza):
    f = {h.nombre: h.funcion for h in pieza.herramientas}
    r = f["crear_informe"]("Título", MD_COMPLETO, "pdf")
    assert "ERROR" in r and "pdf" in r


def test_contenido_demasiado_largo_falla(espacio, pieza):
    f = {h.nombre: h.funcion for h in pieza.herramientas}
    r = f["crear_informe"]("Título", "x" * 200_000)
    assert "ERROR" in r and "límite" in r


def test_el_resultado_informa_el_tamano_real(espacio, pieza):
    """No se debe afirmar que el archivo quedó escrito sin medirlo."""
    f = {h.nombre: h.funcion for h in pieza.herramientas}
    r = f["crear_informe"]("X", MD_COMPLETO, "html")
    archivo = espacio / "informes" / "x.html"
    assert f"{archivo.stat().st_size:,} bytes" in r


# ── listado y lectura ────────────────────────────────────────────────────────

def test_listar_sin_informes(espacio, pieza):
    f = {h.nombre: h.funcion for h in pieza.herramientas}
    assert "no existe" in f["listar_informes"]()


def test_listar_con_informes(espacio, pieza):
    f = {h.nombre: h.funcion for h in pieza.herramientas}
    f["crear_informe"]("Uno", MD_COMPLETO, "html")
    f["crear_informe"]("Dos", MD_COMPLETO, "markdown")
    r = f["listar_informes"]()
    assert "uno.html" in r and "dos.md" in r


def test_leer_informe_por_nombre_sin_extension(espacio, pieza):
    f = {h.nombre: h.funcion for h in pieza.herramientas}
    f["crear_informe"]("Mi informe", MD_COMPLETO, "markdown")
    r = f["leer_informe"]("mi-informe")
    assert "850.000 pesos" in r


def test_leer_informe_inexistente(espacio, pieza):
    f = {h.nombre: h.funcion for h in pieza.herramientas}
    r = f["leer_informe"]("no-existe")
    assert "ERROR" in r


def test_leer_no_permite_salir_de_la_carpeta(espacio, pieza):
    f = {h.nombre: h.funcion for h in pieza.herramientas}
    r = f["leer_informe"]("../../../etc/passwd")
    assert "ERROR" in r


def test_separador_horizontal_no_se_imprime_como_texto(modulo):
    """Regresión: «---» aparecía literal en medio del informe."""
    salida = modulo.markdown_a_html("Texto antes.\n\n---\n\nTexto después.\n")
    assert "<hr>" in salida
    assert "---" not in salida


def test_separador_de_tabla_no_se_confunde_con_separador_horizontal(modulo):
    """La línea «|---|---|» es parte de una tabla, no un separador suelto."""
    salida = modulo.markdown_a_html("| A | B |\n|---|---|\n| 1 | 2 |\n")
    assert "<table>" in salida
    assert "<hr>" not in salida
