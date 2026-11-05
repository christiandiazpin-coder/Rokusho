"""Pruebas del banco de selección de herramientas.

No llaman al modelo: prueban que el banco **mide lo que dice medir**. Un banco
mal construido da números que parecen una medición y no lo son; ya pasó una vez
con la versión anterior, que mezclaba «elegir» con «decidir usar».

Lo que se verifica aquí: que los datos sean imposibles de adivinar, que cada
herramienta solo pueda leer su propia clave, y que la detección de acierto
distinga los tres casos (no llamó / llamó mal / llamó bien pero no reportó).
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from benchmarks import piezas as banco  # noqa: E402


# ── los datos no se pueden adivinar ──────────────────────────────────────────

def test_los_valores_son_aleatorios_y_distintos():
    rng = random.Random(1)
    datos = banco._fabricar_entorno(rng)
    valores = list(datos.values())
    assert len(set(valores)) == len(valores), "hay valores repetidos"
    for v in valores:
        assert len(v) == 9  # AAA-00000


def test_dos_ejecuciones_no_dan_los_mismos_datos():
    a = banco._fabricar_entorno(random.Random(1))
    b = banco._fabricar_entorno(random.Random(2))
    assert a != b


def test_los_valores_no_son_predecibles_por_el_indice():
    """Un valor no puede deducirse del nombre de su clave."""
    rng = random.Random(7)
    datos = banco._fabricar_entorno(rng)
    assert datos["clave_0"] != "clave_0"
    assert not datos["clave_3"].startswith("clave")


# ── cada herramienta solo lee su clave ──────────────────────────────────────

def test_herramienta_devuelve_su_propio_valor(tmp_path):
    datos = {"clave_0": "AAA-11111", "clave_1": "BBB-22222"}
    ruta = tmp_path / "datos.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")

    h0 = banco._fabricar_herramienta("consultar_0", "clave_0", datos, ruta)
    h1 = banco._fabricar_herramienta("consultar_1", "clave_1", datos, ruta)

    assert "AAA-11111" in h0.funcion()
    assert "BBB-22222" in h1.funcion()


def test_herramienta_no_filtra_otros_valores(tmp_path):
    datos = {"clave_0": "AAA-11111", "clave_1": "BBB-22222"}
    ruta = tmp_path / "datos.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")

    h0 = banco._fabricar_herramienta("consultar_0", "clave_0", datos, ruta)
    salida = h0.funcion()
    assert "BBB-22222" not in salida


def test_herramienta_lee_del_disco_no_de_memoria(tmp_path):
    """Si el archivo cambia, la herramienta debe reflejarlo."""
    ruta = tmp_path / "datos.json"
    ruta.write_text(json.dumps({"clave_0": "VIEJO-00000"}), encoding="utf-8")
    h = banco._fabricar_herramienta("consultar_0", "clave_0", {}, ruta)
    assert "VIEJO-00000" in h.funcion()

    ruta.write_text(json.dumps({"clave_0": "NUEVO-99999"}), encoding="utf-8")
    assert "NUEVO-99999" in h.funcion()


def test_herramienta_sin_archivo_avisa(tmp_path):
    h = banco._fabricar_herramienta("consultar_0", "clave_0", {},
                                    tmp_path / "no-existe.json")
    assert "ERROR" in h.funcion()


def test_herramienta_con_clave_ausente_avisa(tmp_path):
    ruta = tmp_path / "datos.json"
    ruta.write_text(json.dumps({"otra": "x"}), encoding="utf-8")
    h = banco._fabricar_herramienta("consultar_0", "clave_0", {}, ruta)
    assert "ERROR" in h.funcion()


# ── la medalla obliga a usar la herramienta ─────────────────────────────────

def test_la_medalla_dice_que_los_datos_solo_estan_en_las_herramientas():
    """El prompt debe dejar claro que no puede responder de memoria."""
    texto = banco._medalla().a_sistema()
    assert "solo existen dentro de ellas" in texto
    assert "inventando" in texto


def test_las_herramientas_tienen_nombres_y_descripciones_unicas():
    datos = banco._fabricar_entorno(random.Random(3))
    ruta = Path("/tmp/no-se-usa.json")
    herramientas = [banco._fabricar_herramienta(f"consultar_{i}", f"clave_{i}", datos, ruta)
                    for i in range(6)]
    nombres = [h.nombre for h in herramientas]
    descripciones = [h.descripcion for h in herramientas]
    assert len(set(nombres)) == len(nombres)
    assert len(set(descripciones)) == len(descripciones), "hay descripciones repetidas"


# ── detección de acierto ────────────────────────────────────────────────────

def test_resultado_distingue_eleccion_de_acierto():
    r = banco.Resultado(herramientas=8, intentos=10, llamo_bien=9, aciertos=7)
    assert r.seleccion == pytest.approx(0.9)
    assert r.precision == pytest.approx(0.7)


def test_resultado_sin_intentos_no_divide_por_cero():
    r = banco.Resultado(herramientas=4)
    assert r.seleccion == 0.0
    assert r.precision == 0.0
    assert r.tokens_por_intento == 0.0
