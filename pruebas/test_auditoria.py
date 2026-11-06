"""Pruebas del auditor de afirmaciones y de las etiquetas de procedencia.

El auditor existe para un caso concreto: el agente reporta «verificado» sin haber
verificado. Un auditor con falsos positivos es igual de inútil que uno que no
detecta nada, porque el usuario aprende a ignorar los avisos. Por eso se prueban
los dos lados: los casos que debe atrapar y los que debe dejar pasar.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from chasis import auditoria as A  # noqa: E402
from chasis import procedencia as P  # noqa: E402
from chasis.agente import Paso, Turno  # noqa: E402

LECTURA_OK = (
    "[contrato.txt — líneas 1-11 de 11]\n"
    "    1| CONTRATO DE PRESTACIÓN DE SERVICIOS\n"
    "    2| Entre Servicios Andinos SpA (en adelante \"el Prestador\")\n"
    "    7| TERCERO: El monto mensual es de 850.000 pesos, pagaderos a 30 días.\n"
)
BUSQUEDA_VACIA = "No se encontró «IVA» en el espacio de trabajo."
ERROR_LECTURA = "ERROR: no existe «contrato.txt»."


def _turno(texto: str, pasos: list[tuple[str, str]]) -> Turno:
    return Turno(respuesta=texto,
                 pasos=[Paso(i + 1, n, {}, s) for i, (n, s) in enumerate(pasos)])


# ── lo que debe atrapar ─────────────────────────────────────────────────────

def test_detecta_exito_afirmado_con_herramienta_fallida():
    t = _turno("He verificado el contrato y queda correcto.", [("leer", ERROR_LECTURA)])
    a = A.auditar(t)
    assert len(a.avisos) >= 1
    assert any("fallaron" in av.motivo for av in a.avisos)


def test_detecta_cifra_que_no_esta_en_la_salida():
    """El dato inventado más frecuente: una cifra que se copió mal o se supuso."""
    t = _turno("El total del contrato es de 10.200.000 pesos.", [("leer", LECTURA_OK)])
    a = A.auditar(t)
    assert len(a.avisos) >= 1
    assert any("cifra" in av.motivo for av in a.avisos)


def test_detecta_afirmacion_sin_ninguna_herramienta():
    t = _turno("He revisado el documento y está todo correcto.", [])
    a = A.auditar(t)
    assert len(a.avisos) >= 1
    assert any("no ejecutó ninguna herramienta" in av.motivo for av in a.avisos)


def test_detecta_turno_que_no_midio_nada():
    """Una sola búsqueda vacía no acredita haber verificado."""
    t = _turno("He verificado todo y está correcto.", [("buscar", BUSQUEDA_VACIA)])
    a = A.auditar(t)
    assert len(a.avisos) >= 1


# ── lo que NO debe marcar (falsos positivos) ────────────────────────────────

def test_reporte_honesto_que_reconoce_el_fallo_no_se_marca():
    t = _turno("No pude verificar el monto: el archivo no existe. Queda pendiente.",
               [("leer", ERROR_LECTURA)])
    assert A.auditar(t).avisos == []


def test_cifra_que_si_esta_en_la_salida_no_se_marca():
    t = _turno("El monto mensual es de 850.000 pesos.", [("leer", LECTURA_OK)])
    assert A.auditar(t).avisos == []


def test_lectura_completa_mas_busqueda_vacia_no_marca():
    """Regresión: un falso positivo real.

    El agente leyó el contrato completo y además buscó «IVA» sin resultados. La
    regla anterior marcaba todo el turno por esa búsqueda vacía, aunque la lectura
    hubiera ido bien. El aviso era falso y enseñaba al usuario a ignorarlos.
    """
    t = _turno("**Monto mensual: 850.000 pesos** — dato verificado.",
               [("leer", LECTURA_OK), ("buscar", BUSQUEDA_VACIA)])
    assert A.auditar(t).avisos == [], (
        "la lectura completa debió contar como medición real")


def test_texto_sin_afirmaciones_no_se_marca():
    t = _turno("Aquí está el documento que pediste.", [("leer", LECTURA_OK)])
    assert A.auditar(t).avisos == []


def test_el_codigo_no_se_audita():
    """Un bloque de código es una cita, no una afirmación propia."""
    t = _turno("Mira:\n```\nverificado correcto limpio\n```\n", [("leer", LECTURA_OK)])
    assert A.auditar(t).avisos == []


# ── formato y resumen ───────────────────────────────────────────────────────

def test_formatear_vacio_cuando_esta_limpia():
    assert A.formatear(A.Auditoria()) == ""


def test_formatear_incluye_los_avisos():
    av = A.Aviso("He verificado todo.", "no hay herramientas", "verificado")
    texto = A.formatear(A.Auditoria(avisos=[av]))
    assert "AVISOS DE AUDITORÍA" in texto
    assert "He verificado todo." in texto


def test_resumen_da_cifras():
    t = _turno("He verificado.", [("leer", ERROR_LECTURA)])
    r = A.resumen(A.auditar(t))
    assert r["herramientas_fallidas"] == 1
    assert r["avisos"] >= 1
    assert r["limpia"] is False


def test_auditoria_es_verdadera_si_hay_avisos():
    """Permite `if auditoria:` de forma natural."""
    t = _turno("He verificado.", [("leer", ERROR_LECTURA)])
    assert bool(A.auditar(t)) is True
    assert bool(A.auditar(_turno("Nada que decir.", []))) is False


# ── procedencia ─────────────────────────────────────────────────────────────

def test_etiqueta_verificado_lo_que_esta_en_la_salida():
    r = P.etiquetar("El monto es de 850.000 pesos.", [LECTURA_OK])
    assert r.verificados, "850.000 pesos está en la salida y debió marcarse VERIFICADO"


def test_etiqueta_hipotesis_lo_que_no_esta():
    r = P.etiquetar("El contrato fue firmado el 3 de enero de 2020.", [LECTURA_OK])
    assert r.hipotesis, "esa fecha no está en la salida y debió marcarse HIPOTESIS"


def test_mezcla_verificado_e_hipotesis():
    r = P.etiquetar(
        "El monto es de 850.000 pesos y el RUT es 76.543.210-8.",
        [LECTURA_OK])
    assert r.verificados and r.hipotesis


def test_sin_datos_no_hay_nada_que_etiquetar():
    r = P.etiquetar("Texto sin cifras ni rutas.", [])
    assert r.datos == []
    assert P.anotar("Texto sin cifras ni rutas.", r) == "Texto sin cifras ni rutas."


def test_proporcion_verificada_es_un_numero_entre_cero_y_uno():
    r = P.etiquetar("850.000 pesos y 99.999 dólares.", [LECTURA_OK])
    assert 0.0 <= r.proporcion_verificada <= 1.0


def test_anotar_avisa_de_las_hipotesis():
    r = P.etiquetar("El monto es de 850.000 pesos y además 77.777 dólares.", [LECTURA_OK])
    texto = P.anotar("original", r)
    assert "PROCEDENCIA DE LOS DATOS" in texto
    assert "original" in texto


def test_resumen_procedencia():
    r = P.etiquetar("850.000 pesos y 99.999 dólares.", [LECTURA_OK])
    s = P.resumen(r)
    assert s["datos"] == len(r.datos)
    assert s["verificados"] + s["hipotesis"] == s["datos"]


# ── regresión: un resultado negativo no es una herramienta rota ─────────────

@pytest.mark.parametrize("salida", [
    "No hay ningún informe: la carpeta no existe. Se crea al generar el primero.",
    "No se encontró «IVA» en el espacio de trabajo.",
    "No se encontró «RUT» en el espacio de trabajo.",
    "La carpeta «.» está vacía.",
])
def test_resultado_negativo_no_cuenta_como_fallo(salida):
    """Regresión con seis falsos positivos medidos en un turno real.

    `listar_informes` respondió «No hay ningún informe: la carpeta no existe»,
    que es una respuesta VÁLIDA, y el auditor la contó como herramienta fallida.
    A partir de ahí marcó las seis afirmaciones del turno. El aviso era falso.
    """
    assert A._FRACASO.search(salida) is None


@pytest.mark.parametrize("salida", [
    "ERROR: no existe «contrato.txt».",
    "ERROR: la expresión no es válida",
    "BLOQUEADO: la ruta queda fuera del espacio de trabajo.",
    "DENEGADO: sin permiso.",
    "Traceback (most recent call last):",
    "exit code: 1",
])
def test_error_real_si_cuenta_como_fallo(salida):
    assert A._FRACASO.search(salida) is not None


def test_turno_con_resultado_negativo_no_se_marca_si_leyo_bien():
    """El caso completo del falso positivo: lectura buena + lista vacía."""
    t = _turno(
        "**Monto mensual: 850.000 pesos** — dato verificado, línea 7.",
        [("leer", LECTURA_OK),
         ("listar_informes", "No hay ningún informe: la carpeta no existe.")])
    assert A.auditar(t).avisos == []
