"""Pruebas de la medalla «marketing».

Una medalla de marketing es el lugar más fácil para que un sistema de IA empiece
a inventar: testimonios, cifras de clientes, superlativos. Esta medalla existe
con una restricción explícita —no puede inventar pruebas— y estas pruebas fijan
esa restricción para que no se diluya al editarla.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from chasis.medalla import cargar  # noqa: E402


@pytest.fixture(scope="module")
def medalla():
    return cargar("marketing", raiz=RAIZ / "medallas")


def test_la_medalla_carga(medalla):
    assert medalla.nombre
    assert medalla.persona.strip()


def test_prohibe_inventar_testimonios(medalla):
    texto = " ".join(medalla.prohibido).lower()
    assert "testimonio" in texto
    assert "inventar" in texto or "invent" in texto


def test_prohibe_cifras_de_resultados_sin_medir(medalla):
    texto = " ".join(medalla.prohibido).lower()
    assert "cifras de resultados" in texto or "porcentajes" in texto


def test_prohibe_superlativos_sin_respaldo(medalla):
    texto = " ".join(medalla.prohibido).lower()
    assert "líder" in texto or "lider" in texto
    assert "superlativo" in texto


def test_prohibe_urgencia_falsa(medalla):
    texto = " ".join(medalla.prohibido).lower()
    assert "urgencia" in texto


def test_prohibe_publicar_sin_aprobacion(medalla):
    texto = " ".join(medalla.prohibido).lower()
    assert "apruebe" in texto or "aprobación" in texto or "aprobacion" in texto


def test_exige_fuente_para_cada_afirmacion(medalla):
    """La regla central: sin algo que exista, no se afirma."""
    texto = " ".join(medalla.reglas).lower()
    assert "sostenerse" in texto or "respaldo" in texto or "exista" in texto


def test_contempla_el_caso_sin_casos_de_exito(medalla):
    """El caso real del primer cliente: no hay nada que mostrar todavía."""
    texto = " ".join(medalla.reglas).lower()
    assert "no tenga casos" in texto or "no tenga" in texto


def test_el_prompt_incluye_las_prohibiciones(medalla):
    sistema = medalla.a_sistema()
    assert "Prohibido" in sistema
    assert "testimonio" in sistema.lower()


def test_la_persona_no_promete_lo_que_no_se_puede(medalla):
    """La persona debe reconocer que no puede inventar pruebas."""
    texto = medalla.persona.lower()
    assert "inventar" in texto


def test_prohibe_publicar_sin_aprobacion_explicita(medalla):
    """Coherente con el principio del proyecto: nada sale sin revisión."""
    texto = " ".join(medalla.prohibido).lower()
    assert "apruebe" in texto or "aprob" in texto
