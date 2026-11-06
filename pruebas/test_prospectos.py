"""Pruebas del recolector de prospectos.

Lo que se protege: que la lista no contenga datos inventados ni basura de la
página. Una lista de contactos con fichas falsas hace perder tiempo y credibilidad.

Los cuatro defectos que estas pruebas fijan se encontraron midiendo la
recolección real, no leyendo el código.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from herramientas import prospectos as P  # noqa: E402


# ── formato de teléfono: cuatro variantes reales de Chile ──────────────────

@pytest.mark.parametrize("texto,esperado", [
    ("(41) 2738946", "(41) 2738946"),      # Concepción, área 2 dígitos
    ("(2)232073038", "(2)232073038"),      # Santiago, área 1 dígito, 9 dígitos
    ("(71) 212415", "(71) 212415"),        # Talca, fijo de 6
    ("9 77756416", "9 77756416"),          # celular
])
def test_reconoce_los_formatos_de_telefono_chilenos(texto, esperado):
    """Cada variante falló en una versión anterior del regex.

    Talca perdía 13 de 15 teléfonos y Viña bajaba de 19 a 11 al arreglar otra.
    """
    m = P._RE_TELEFONO.search(texto)
    assert m is not None, f"no reconoció «{texto}»"
    assert m.group(0) == esperado


@pytest.mark.parametrize("texto", [
    "Calle 3 Poniente, 0110 - 16 1/2 Sur",
    "Calle 4 Norte, 1656 - Of 101",
    "Calle Freire, 740 - Of.42",
    "VIII Región, Talca, Chile",
])
def test_no_confunde_una_direccion_con_un_telefono(texto):
    assert P._RE_TELEFONO.search(texto) is None


# ── extracción de fichas ───────────────────────────────────────────────────

FICHAS = """01
Aemprolog
Calle Prieto, 775 - Depto 1204, VIII Región
(41) 2738946
Mapa
02
Lexeduca ltda.
Calle Lincoyán, 445
(41) 2737718
"""


def test_extrae_nombre_direccion_y_telefono():
    fichas = P.extraer(FICHAS, "concepcion", "https://ejemplo.cl")
    assert len(fichas) == 2
    assert fichas[0].nombre == "Aemprolog"
    assert "2738946" in fichas[0].telefono
    assert "Prieto" in fichas[0].direccion


def test_cada_ficha_lleva_su_url_de_origen():
    """Sin origen no se puede verificar: la lista sería inauditable."""
    fichas = P.extraer(FICHAS, "concepcion", "https://yelu.cl/city:concepcion")
    assert all(f.fuente == "https://yelu.cl/city:concepcion" for f in fichas)


def test_descarta_el_contador_de_companias():
    """Regresión: «1,692 compañías» entró como si fuera una empresa."""
    texto = "01\nAemprolog\n(41) 2738946\n02\n1,692 compañías\n03\nReal SpA\n"
    nombres = [f.nombre for f in P.extraer(texto, "x", "u")]
    assert not any("compañ" in n.lower() for n in nombres)


def test_descarta_controles_de_paginacion():
    texto = "01\nMap\n02\nSiguiente\n03\nEmpresa Real\n"
    nombres = [f.nombre for f in P.extraer(texto, "x", "u")]
    assert nombres == ["Empresa Real"]


def test_descarta_una_frase_larga_como_nombre():
    frase = "La Lista de Consultores en Chile y algo mas que no es una empresa"
    texto = f"01\n{frase}\n"
    assert P.extraer(texto, "x", "u") == []


def test_salta_lineas_vacias_entre_numero_y_nombre():
    """Regresión: el directorio real trae una línea en blanco, y sin saltarla
    el parser tomaba cadena vacía como nombre y no extraía nada."""
    texto = "01\n\nAemprolog\n\n(41) 2738946\n"
    fichas = P.extraer(texto, "x", "u")
    assert len(fichas) == 1
    assert fichas[0].nombre == "Aemprolog"


def test_no_inventa_correos():
    """El directorio oculta el correo; el recolector no debe adivinarlo."""
    fichas = P.extraer(FICHAS, "concepcion", "u")
    assert all(f.correo == "" for f in fichas)


# ── codificación ───────────────────────────────────────────────────────────

def test_repara_el_doble_decodificado():
    """«ConcepciÃ³n» es UTF-8 leído como latin-1."""
    assert P._arreglar_codificacion("ConcepciÃ³n") == "Concepción"


def test_no_toca_el_texto_ya_correcto():
    assert P._arreglar_codificacion("Concepción") == "Concepción"


# ── CSV ────────────────────────────────────────────────────────────────────

def test_escribe_csv_con_todas_las_columnas(tmp_path):
    fichas = P.extraer(FICHAS, "concepcion", "u")
    destino = tmp_path / "salida.csv"
    P.escribir_csv(fichas, destino)
    lineas = destino.read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 3  # cabecera + 2 fichas
    assert "fuente" in lineas[0]
    assert "Aemprolog" in lineas[1]
