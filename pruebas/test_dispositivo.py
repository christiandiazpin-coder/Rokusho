"""Pruebas de la pieza «dispositivo».

Esta pieza habla con hardware ajeno. Lo que se protege aquí no es que funcione:
es que **no invente** cuando el aparato no responde. Un agente que afirma «el
arranque está desbloqueado» sin haberlo leído puede llevar a alguien a borrar un
equipo que no era apto.

Las pruebas no necesitan un aparato conectado: simulan las respuestas de adb. Una
prueba que exige hardware real no corre en integración continua y termina
desactivándose, que es peor que no tenerla.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from chasis.pieza import _importar  # noqa: E402

MODULO = _importar(RAIZ / "piezas" / "dispositivo" / "implementacion.py", "disp_test")


@pytest.fixture()
def sin_adb(monkeypatch):
    """Simula que adb no está instalado."""
    monkeypatch.setattr(MODULO.shutil, "which", lambda nombre: None)
    return MODULO


@pytest.fixture()
def con_adb(monkeypatch, tmp_path):
    """Simula adb presente, con respuestas controladas."""
    monkeypatch.setattr(MODULO.shutil, "which",
                        lambda nombre: "/usr/bin/adb" if nombre == "adb" else None)
    return MODULO


def _fake_run(respuestas: dict[str, tuple[int, str, str]]):
    """Devuelve una función que imita subprocess.run para argumentos dados."""
    def run(argumentos, **kwargs):
        clave = " ".join(argumentos)
        for patron, (codigo, salida, error) in respuestas.items():
            if patron in clave:
                return subprocess.CompletedProcess(argumentos, codigo, salida, error)
        return subprocess.CompletedProcess(argumentos, 0, "", "")
    return run


# ── cuando falta la herramienta ─────────────────────────────────────────────

def test_sin_adb_listar_avisa_en_vez_de_inventar(sin_adb):
    r = sin_adb.listar_dispositivos()
    assert "ERROR" in r
    assert "adb no está instalado" in r


def test_sin_adb_herramientas_lo_dice(sin_adb, monkeypatch):
    # modo_mtk usa lsusb, que puede existir; aquí solo se comprueba el informe.
    monkeypatch.setattr(sin_adb.shutil, "which", lambda nombre: None)
    r = sin_adb.herramientas()
    assert "NO instalado" in r


# ── listar dispositivos ─────────────────────────────────────────────────────

def test_sin_dispositivos_lo_dice(con_adb, monkeypatch):
    monkeypatch.setattr(con_adb.subprocess, "run",
                        _fake_run({"devices": (0, "List of devices attached\n\n", "")}))
    r = con_adb.listar_dispositivos()
    assert "No hay ningún aparato conectado" in r


def test_dispositivo_no_autorizado_se_senala(con_adb, monkeypatch):
    salida = "List of devices attached\nABC123\tunauthorized\n"
    monkeypatch.setattr(con_adb.subprocess, "run",
                        _fake_run({"devices": (0, salida, "")}))
    r = con_adb.listar_dispositivos()
    assert "ABC123" in r
    assert "unauthorized" in r or "no autorizó" in r


def test_dispositivo_conectado_muestra_serie(con_adb, monkeypatch):
    salida = "List of devices attached\nXYZ789\tdevice\n"
    monkeypatch.setattr(con_adb.subprocess, "run",
                        _fake_run({"devices": (0, salida, "")}))
    assert "XYZ789" in con_adb.listar_dispositivos()


# ── identificar: el caso peligroso ──────────────────────────────────────────

def test_identificar_sin_serie_falla(con_adb):
    assert "ERROR" in con_adb.identificar("")


def test_identificar_aparato_que_no_responde_no_inventa(con_adb, monkeypatch):
    """Lo más importante de la pieza: sin respuesta, no hay datos."""
    monkeypatch.setattr(con_adb.subprocess, "run",
                        _fake_run({"get-state": (1, "", "error: device 'NADA' not found")}))
    r = con_adb.identificar("NADA")
    assert "ERROR" in r
    assert "no responde" in r
    assert "No inventes" in r


def test_identificar_lee_las_propiedades_reales(con_adb, monkeypatch):
    respuestas = {
        "get-state": (0, "device\n", ""),
        "getprop ro.product.model": (0, "TB-X306F\n", ""),
        "getprop ro.product.manufacturer": (0, "Lenovo\n", ""),
        "getprop ro.build.version.release": (0, "10\n", ""),
    }
    monkeypatch.setattr(con_adb.subprocess, "run", _fake_run(respuestas))
    r = con_adb.identificar("SERIE1")
    assert "TB-X306F" in r
    assert "Lenovo" in r
    assert "10" in r


def test_identificar_sin_propiedades_avisa(con_adb, monkeypatch):
    monkeypatch.setattr(con_adb.subprocess, "run",
                        _fake_run({"get-state": (0, "device\n", "")}))
    r = con_adb.identificar("SERIE1")
    assert "ERROR" in r
    assert "no devolvió ninguna propiedad" in r


def test_identificar_sugiere_la_ficha_si_existe(con_adb, monkeypatch):
    respuestas = {
        "get-state": (0, "device\n", ""),
        "getprop ro.product.model": (0, "TB-X306F\n", ""),
    }
    monkeypatch.setattr(con_adb.subprocess, "run", _fake_run(respuestas))
    r = con_adb.identificar("S1")
    assert "ficha" in r.lower()


# ── estado de arranque ─────────────────────────────────────────────────────

def test_estado_arranque_bloqueado(con_adb, monkeypatch):
    respuestas = {
        "get-state": (0, "device\n", ""),
        "ro.boot.flash.locked": (0, "1\n", ""),
    }
    monkeypatch.setattr(con_adb.subprocess, "run", _fake_run(respuestas))
    r = con_adb.estado_arranque("S1")
    assert "BLOQUEADO" in r


def test_estado_arranque_desbloqueado(con_adb, monkeypatch):
    respuestas = {
        "get-state": (0, "device\n", ""),
        "ro.boot.flash.locked": (0, "0\n", ""),
    }
    monkeypatch.setattr(con_adb.subprocess, "run", _fake_run(respuestas))
    assert "DESBLOQUEADO" in con_adb.estado_arranque("S1")


def test_estado_arranque_sin_datos_no_concluye(con_adb, monkeypatch):
    """Si el aparato no expone el estado, no se puede afirmar nada."""
    monkeypatch.setattr(con_adb.subprocess, "run",
                        _fake_run({"get-state": (0, "device\n", "")}))
    r = con_adb.estado_arranque("S1")
    assert "no expone" in r or "No se puede concluir" in r


def test_estado_arranque_sin_serie_falla(con_adb):
    assert "ERROR" in con_adb.estado_arranque("")


# ── ficha del modelo ───────────────────────────────────────────────────────

def test_ficha_de_modelo_conocido():
    r = MODULO.ficha("TB-X306F")
    assert "MediaTek" in r
    assert "P22T" in r


def test_ficha_de_modelo_desconocido_no_inventa():
    """Sin ficha, no debe afirmar procesador ni método de desbloqueo."""
    r = MODULO.ficha("SAMSUNG-XYZ")
    assert "No hay ficha" in r
    assert "MediaTek" not in r or "no se puede afirmar" in r.lower()


def test_ficha_sin_modelo_falla():
    assert "ERROR" in MODULO.ficha("")


def test_ficha_acepta_el_modelo_con_prefijo():
    """El agente puede pasar «Lenovo TB-X306F» y debe encontrarla igual."""
    r = MODULO.ficha("Lenovo TB-X306F")
    assert "P22T" in r


def test_la_ficha_admite_que_no_hay_metodo_oficial():
    """Honestidad: Lenovo no publica desbloqueo oficial para este modelo."""
    r = MODULO.ficha("TB-X306F")
    assert "no publica" in r or "no oficial" in r


# ── modo MTK (USB) ─────────────────────────────────────────────────────────

def test_modo_mtk_sin_aparatos(monkeypatch):
    monkeypatch.setattr(
        MODULO.subprocess, "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, "Bus 001 Device 001: ID 1d6b:0002 hub\n", ""))
    r = MODULO.modo_mtk()
    assert "No hay ningún aparato MediaTek" in r


def test_modo_mtk_con_aparato_en_brom(monkeypatch):
    salida = "Bus 001 Device 005: ID 0e8d:2000 MediaTek Inc. MT65xx Preloader\n"
    monkeypatch.setattr(
        MODULO.subprocess, "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, salida, ""))
    r = MODULO.modo_mtk()
    assert "BROM" in r
    assert "mtkclient" in r


def test_modo_mtk_si_lsusb_falla_no_revienta(monkeypatch):
    def explota(*a, **k):
        raise OSError("lsusb no está")
    monkeypatch.setattr(MODULO.subprocess, "run", explota)
    r = MODULO.modo_mtk()
    assert "ERROR" in r
