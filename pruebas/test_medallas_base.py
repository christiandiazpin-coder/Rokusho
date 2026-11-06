"""Pruebas de las tres medallas base: documentos, agenda y comunicación.

Por qué existen: una medalla es texto, y el texto se diluye al editarlo. El valor
de Rokusho está en que esas reglas signifiquen algo, no en que el archivo exista.
Estas pruebas fijan las reglas que sostienen la promesa comercial —citar,
declarar ausencias, no inventar— para que un cambio descuidado las rompa de
forma visible.

Se prueba la estructura de cada medalla, no el criterio del modelo: eso se mide
con el modelo real, y está documentado en `docs/mediciones.md`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from chasis.medalla import cargar  # noqa: E402


def _texto(valores) -> str:
    return " ".join(valores).lower()


# ── documentos ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def documentos():
    return cargar("documentos", raiz=RAIZ / "medallas")


def test_documentos_carga(documentos):
    assert documentos.nombre
    assert documentos.persona.strip()


def test_documentos_exige_cita(documentos):
    """Sin cita verificable, el producto pierde su único diferenciador."""
    assert "cita" in _texto(documentos.reglas)


def test_documentos_separa_dicho_de_deducido(documentos):
    texto = _texto(documentos.reglas) + _texto(documentos.vocabulario)
    assert "deducido" in texto or "deduce" in texto
    assert "verificado" in texto


def test_documentos_declara_la_ausencia(documentos):
    """La regla más importante: lo que no está, se dice que no está."""
    texto = _texto(documentos.reglas) + _texto(documentos.prohibido)
    assert "no lo indica" in texto or "no está en el documento" in texto


def test_documentos_prohibe_afirmar_sin_respaldo(documentos):
    assert "no está en el documento" in _texto(documentos.prohibido)


def test_documentos_prohibe_ocultar_contradicciones(documentos):
    assert "contradicci" in _texto(documentos.prohibido)


def test_documentos_prohibe_decir_que_leyo_todo_si_no(documentos):
    """El fallo medido en Umbra: «revisado completo» con lectura parcial."""
    texto = _texto(documentos.prohibido)
    assert "completo" in texto


def test_documentos_no_redondea_cifras(documentos):
    texto = _texto(documentos.reglas) + _texto(documentos.prohibido)
    assert "redonde" in texto


# ── agenda ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def agenda():
    return cargar("agenda", raiz=RAIZ / "medallas")


def test_agenda_carga(agenda):
    assert agenda.nombre
    assert agenda.persona.strip()


def test_agenda_exige_inicio_fin_y_responsable(agenda):
    texto = _texto(agenda.reglas)
    assert "inicio" in texto and "fin" in texto and "responsable" in texto


def test_agenda_exige_revisar_choques(agenda):
    texto = _texto(agenda.reglas) + _texto(agenda.prohibido)
    assert "choque" in texto


def test_agenda_respeta_dependencias(agenda):
    assert "dependencia" in _texto(agenda.reglas)


def test_agenda_dice_cuando_no_cabe(agenda):
    """Comprimir todo para que quepa es mentir sobre la capacidad."""
    texto = _texto(agenda.reglas) + _texto(agenda.prohibido)
    assert "no cabe" in texto or "no alcanza" in texto or "qué se cae" in texto


def test_agenda_prohibe_ocultar_que_no_alcanza(agenda):
    texto = _texto(agenda.prohibido)
    assert "ocultar" in texto


def test_agenda_no_asume_duraciones(agenda):
    assert "dur" in _texto(agenda.prohibido)


# ── comunicación ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def comunicacion():
    return cargar("comunicacion", raiz=RAIZ / "medallas")


def test_comunicacion_carga(comunicacion):
    assert comunicacion.nombre
    assert comunicacion.persona.strip()


def test_comunicacion_exige_asunto(comunicacion):
    assert "asunto" in _texto(comunicacion.reglas)


def test_comunicacion_prohibe_inventar_datos(comunicacion):
    texto = _texto(comunicacion.prohibido)
    assert "inventar" in texto
    assert "montos" in texto or "fechas" in texto


def test_comunicacion_marca_los_datos_que_faltan(comunicacion):
    """La alternativa a inventar: marcar el hueco, no rellenarlo."""
    texto = _texto(comunicacion.reglas)
    assert "falta" in texto


def test_comunicacion_prohibe_prometer_sin_autorizacion(comunicacion):
    texto = _texto(comunicacion.prohibido)
    assert "autoriz" in texto


def test_comunicacion_ajusta_el_largo_al_canal(comunicacion):
    assert "canal" in _texto(comunicacion.reglas)


# ── coherencia entre las tres ─────────────────────────────────────────────

@pytest.mark.parametrize("nombre", ["documentos", "agenda", "comunicacion"])
def test_toda_medalla_base_prohibe_inventar(nombre):
    """El principio del proyecto: ninguna medalla base permite inventar datos.

    Si una medalla dejara de prohibirlo, el sistema perdería la característica
    que lo distingue, y no habría ninguna prueba que lo notara.
    """
    medalla = cargar(nombre, raiz=RAIZ / "medallas")
    texto = _texto(medalla.prohibido)
    assert any(p in texto for p in
               ("inventar", "invent", "afirmar algo que no", "asumir")), (
        f"la medalla «{nombre}» no prohíbe inventar datos")


@pytest.mark.parametrize("nombre", ["documentos", "agenda", "comunicacion"])
def test_toda_medalla_base_tiene_vocabulario_propio(nombre):
    """El vocabulario es lo que hace que hable del rubro y no en genérico."""
    medalla = cargar(nombre, raiz=RAIZ / "medallas")
    assert len(medalla.vocabulario) >= 3


@pytest.mark.parametrize("nombre", ["documentos", "agenda", "comunicacion"])
def test_toda_medalla_base_tiene_reglas_y_prohibiciones(nombre):
    medalla = cargar(nombre, raiz=RAIZ / "medallas")
    assert len(medalla.reglas) >= 4
    assert len(medalla.prohibido) >= 3


@pytest.mark.parametrize("nombre", ["documentos", "agenda", "comunicacion"])
def test_el_prompt_resultante_lleva_las_reglas(nombre):
    medalla = cargar(nombre, raiz=RAIZ / "medallas")
    sistema = medalla.a_sistema()
    assert "Reglas del rubro" in sistema
    assert "Prohibido en este rubro" in sistema
    for regla in medalla.reglas:
        assert regla in sistema


@pytest.mark.parametrize("nombre", ["documentos", "agenda", "comunicacion"])
def test_ninguna_medalla_permite_entregar_sin_aprobacion(nombre):
    """Coherente con el principio del proyecto, no con el rubro.

    Se busca la INTENCIÓN, no una palabra concreta: una medalla puede decir
    «aprobación», «revisión» o «visto bueno», y las tres exigen lo mismo. La
    primera versión de esta prueba falló con «documentos» porque su regla usa
    «revisión explícita» y «visto bueno». El fallo era del test, no de la medalla.
    """
    medalla = cargar(nombre, raiz=RAIZ / "medallas")
    sistema = medalla.a_sistema().lower()
    assert any(p in sistema for p in
               ("aprob", "aprueb", "revisión explícita", "revision explicita",
                "visto bueno")), (
        f"la medalla «{nombre}» no exige aprobación antes de entregar")
