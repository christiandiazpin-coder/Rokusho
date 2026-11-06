"""Pruebas de la pieza «calculo».

Dos objetivos: que las cuentas sean exactas, y que la expresión —que la escribe
un modelo que a su vez lee documentos de un cliente— no pueda ejecutar código.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chasis.pieza import cargar

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def pieza():
    return cargar("calculo", raiz=RAIZ / "piezas")


@pytest.fixture(scope="module")
def f(pieza):
    return {h.nombre: h.funcion for h in pieza.herramientas}


# ── exactitud ────────────────────────────────────────────────────────────────

def test_suma_decimal_exacta(f):
    """0.1 + 0.2 es el error clásico de coma flotante; en decimal da 0.3."""
    assert "0.3" in f["calcular"]("0.1 + 0.2").splitlines()[0]


def test_multiplicacion_de_montos(f):
    assert "10,200,000" in f["calcular"]("850000 * 12").splitlines()[0]


def test_iva_calculado_no_estimado(f):
    assert "285,000" in f["calcular"]("1500000 * 0.19").splitlines()[0]


def test_division_larga(f):
    r = f["calcular"]("100 / 3")
    assert "33.33" in r.splitlines()[0]


def test_expresion_con_parentesis(f):
    assert "14" in f["calcular"]("2 * (3 + 4)").splitlines()[0]


def test_potencia(f):
    # El resultado sale con separador de miles: 1,024.
    assert "1,024" in f["calcular"]("2 ** 10").splitlines()[0]


def test_operador_modulo(f):
    assert "1" in f["calcular"]("7 % 2").splitlines()[0]


# ── coma de miles (regresión) ────────────────────────────────────────────────

def test_coma_de_miles_en_expresion(f):
    assert "18,000,000" in f["calcular"]("1,500,000 * 12").splitlines()[0]


def test_coma_como_separador_de_argumentos_no_se_borra(f):
    """Regresión grave: quitar todas las comas convertía min(5,2,8) en min(528)."""
    assert "= 2" in f["calcular"]("min(5,2,8)").splitlines()[0]
    assert "= 8" in f["calcular"]("max(5,2,8)").splitlines()[0]


def test_round_con_coma_de_argumentos(f):
    assert "3.14" in f["calcular"]("round(3.14159, 2)").splitlines()[0]


# ── funciones permitidas ─────────────────────────────────────────────────────

@pytest.mark.parametrize("expresion,esperado", [
    ("sqrt(16)", "4"),
    ("abs(-42)", "42"),
    ("floor(3.8)", "3"),
    ("ceil(3.2)", "4"),
])
def test_funciones_permitidas(f, expresion, esperado):
    assert f"= {esperado}" in f["calcular"](expresion).splitlines()[0]


# ── seguridad: la expresión viene de un modelo ───────────────────────────────

@pytest.mark.parametrize("ataque", [
    "__import__('os').system('echo PWNED')",
    "open('/etc/passwd').read()",
    "().__class__.__bases__[0].__subclasses__()",
    "exec('import os')",
    "eval('1')",
    "[x for x in range(10)]",
    "lambda: 1",
    "import os",
    "{'a': 1}",
    "(1, 2)",
    "1 if 1 else 2",
    "x",
    "os.system('ls')",
])
def test_codigo_arbitrario_se_rechaza(f, ataque):
    r = f["calcular"](ataque)
    assert r.startswith("ERROR"), f"«{ataque}» debía rechazarse, devolvió: {r}"


def test_potencia_gigante_se_rechaza(f):
    """Sin límite, 9**9**9 cuelga el proceso. El exponente se acota."""
    assert "ERROR" in f["calcular"]("9**9999")
    # Una potencia razonable sí se calcula.
    assert "387,420,489" in f["calcular"]("9**9").splitlines()[0]


def test_division_por_cero_avisa_sin_caer(f):
    r = f["calcular"]("1/0")
    assert "ERROR" in r and "cero" in r


def test_expresion_vacia(f):
    assert "ERROR" in f["calcular"]("")


def test_expresion_muy_larga(f):
    assert "ERROR" in f["calcular"]("1+" * 400 + "1")


# ── porcentaje ───────────────────────────────────────────────────────────────

def test_porcentaje_de_una_cantidad(f):
    assert "285,000" in f["porcentaje"]("de", 19, 1_500_000)


def test_que_porcentaje_representa(f):
    r = f["porcentaje"]("que_porcentaje", 285_000, 1_500_000)
    assert "19" in r


def test_variacion_positiva(f):
    assert "aumento" in f["porcentaje"]("variacion", 120, 100)


def test_variacion_negativa(f):
    assert "disminución" in f["porcentaje"]("variacion", 80, 100)


def test_porcentaje_sobre_cero_no_se_inventa(f):
    assert "ERROR" in f["porcentaje"]("que_porcentaje", 10, 0)


def test_operacion_desconocida(f):
    assert "ERROR" in f["porcentaje"]("inventada", 1, 2)


# ── estadística ──────────────────────────────────────────────────────────────

def test_estadistica_basica(f):
    r = f["estadistica"]("850000, 850000, 900000, 780000")
    assert "3,380,000" in r        # suma
    assert "845,000" in r          # media
    assert "850,000" in r          # mediana
    assert "780,000" in r          # mínimo


def test_estadistica_mediana_par(f):
    r = f["estadistica"]("1, 2, 3, 4")
    assert "mediana: 2.5" in r


def test_estadistica_con_valor_invalido(f):
    assert "ERROR" in f["estadistica"]("1, dos, 3")


def test_estadistica_vacia(f):
    assert "ERROR" in f["estadistica"]("")


# ── fechas ───────────────────────────────────────────────────────────────────

def test_dias_entre_fechas(f):
    assert "364" in f["dias_entre"]("2026-03-01", "2027-02-28")


def test_dias_entre_en_orden_inverso(f):
    r = f["dias_entre"]("2027-02-28", "2026-03-01")
    assert "antes" in r


def test_fecha_invalida(f):
    assert "ERROR" in f["dias_entre"]("2026-13-45", "2027-01-01")


def test_sumar_meses(f):
    r = f["sumar_fechas"]("2026-03-01", meses=12)
    assert "2027-03-01" in r


def test_restar_dias(f):
    r = f["sumar_fechas"]("2026-03-01", dias=-60)
    assert "2025-12-31" in r


def test_sumar_sin_indicar_cuanto(f):
    assert "ERROR" in f["sumar_fechas"]("2026-03-01")


def test_fin_de_mes_al_sumar_meses(f):
    """31 de enero + 1 mes no debe fallar: se ajusta al último día de febrero."""
    r = f["sumar_fechas"]("2026-01-31", meses=1)
    assert "2026-02-28" in r


# ── medición de texto ───────────────────────────────────────────────────────
# Existe por un defecto medido: el agente escribió un mensaje de 136 palabras y
# reportó 133. Contó a mano y usó la calculadora solo para sumar sus conteos.

def test_contar_palabras_basico(f):
    r = f["contar_palabras"]("Hola mundo de prueba")
    assert "palabras: 4" in r


def test_contar_caracteres_con_y_sin_espacios(f):
    """Regresión: un escape mal escrito hacía que ambas cifras coincidieran."""
    r = f["contar_palabras"]("Hola mundo")
    assert "con espacios): 10" in r
    assert "sin espacios): 9" in r


def test_los_signos_sueltos_no_cuentan_como_palabra(f):
    """Regresión: el guion largo inflaba el conteo.

    Se detectó midiendo un mensaje real: la herramienta daba 138 palabras donde
    había 136. La causa era contar «—» como palabra.
    """
    r = f["contar_palabras"]("uno — dos")
    assert "palabras: 2" in r


def test_el_marcador_corchetes_cuenta_como_una_palabra(f):
    """«[nombre]» se reemplaza por un nombre: es una palabra en el envío."""
    r = f["contar_palabras"]("Hola [nombre]")
    assert "palabras: 2" in r


def test_informa_el_criterio_alternativo_si_difiere(f):
    r = f["contar_palabras"]("uno — dos")
    assert "NOTA" in r
    assert "signos sueltos" in r


def test_medir_texto_informa_si_cabe(f):
    r = f["medir_texto"]("Hola mundo", limite=100)
    assert "cabe por caracteres: sí" in r
    assert "VEREDICTO: cabe" in r


def test_medir_texto_detecta_que_se_pasa_en_ambas(f):
    """Un texto largo en palabras Y en caracteres debe dar veredicto claro."""
    r = f["medir_texto"]("palabra " * 100, limite=50)
    assert "NO" in r
    assert "recortar" in r


def test_medir_texto_avisa_si_solo_se_pasa_en_una(f):
    """Caso que confundió al primer test: 200 caracteres pero una sola palabra.

    Se pasa en caracteres y no en palabras. La herramienta debe avisar de la
    ambigüedad en vez de dar un veredicto rotundo: depende de qué mida el canal.
    """
    r = f["medir_texto"]("x" * 200, limite=50)
    assert "cabe por caracteres: NO" in r
    assert "cabe por palabras: sí" in r
    assert "AVISO" in r


def test_medir_texto_sin_limite_no_compara(f):
    r = f["medir_texto"]("Hola mundo")
    assert "límite indicado" not in r


def test_medir_texto_vacio_falla(f):
    assert "ERROR" in f["medir_texto"]("")
    assert "ERROR" in f["contar_palabras"]("")


def test_el_conteo_coincide_con_el_total_de_lineas(f):
    """La suma por línea debe dar el total: si no, hay un error de cuenta."""
    r = f["contar_palabras"]("una dos\ntres cuatro\ncinco")
    assert "palabras: 5" in r
    assert "suma de las líneas: 5" in r
