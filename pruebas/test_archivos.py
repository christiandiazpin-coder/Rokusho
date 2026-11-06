"""Pruebas de la pieza «archivos».

Es la pieza más usada del sistema: es la puerta entre el material del cliente y
el agente. Y tiene la única restricción de seguridad del proyecto: el agente no
puede leer fuera de la carpeta de trabajo.

Lo que se protege aquí no es que lea bien —eso es fácil— sino que **no se
escape**, ni por `..`, ni por ruta absoluta, ni por enlace simbólico.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from chasis.pieza import _importar  # noqa: E402

MODULO = _importar(RAIZ / "piezas" / "archivos" / "implementacion.py", "arch_test")


@pytest.fixture()
def espacio(tmp_path):
    """Carpeta de trabajo con contenido variado."""
    trabajo = tmp_path / "trabajo"
    trabajo.mkdir()
    (trabajo / "contrato.txt").write_text(
        "CONTRATO\nPRIMERO: partes\nTERCERO: monto 850.000 pesos\n", encoding="utf-8")
    (trabajo / "notas.md").write_text("# Notas\nSin IVA indicado.\n", encoding="utf-8")
    sub = trabajo / "documentos"
    sub.mkdir()
    (sub / "anexo.txt").write_text("Anexo uno.\n", encoding="utf-8")
    # Un secreto FUERA de la carpeta de trabajo: nunca debe poder leerse.
    (tmp_path / "secreto.txt").write_text("NO DEBE LEERSE\n", encoding="utf-8")
    MODULO.configurar(trabajo)
    return trabajo


# ── seguridad: no salir del espacio de trabajo ──────────────────────────────

@pytest.mark.parametrize("ruta", [
    "../secreto.txt",
    "../../etc/passwd",
    "/etc/passwd",
    "../",
    "documentos/../../secreto.txt",
    "/",
])
def test_no_lee_fuera_del_espacio(espacio, ruta):
    r = MODULO.leer(ruta)
    assert r.startswith(("RECHAZADO", "ERROR")), f"«{ruta}» debió rechazarse, dio: {r[:60]}"
    assert "NO DEBE LEERSE" not in r
    assert "root:" not in r


@pytest.mark.parametrize("ruta", ["..", "../", "/etc"])
def test_no_lista_fuera_del_espacio(espacio, ruta):
    r = MODULO.listar(ruta)
    assert r.startswith("RECHAZADO")


def test_no_escapa_por_enlace_simbolico(espacio, tmp_path):
    """El caso sutil: un enlace dentro de la carpeta apunta fuera.

    `resolve()` sigue el enlace, así que se detecta el escape. Sin eso, un
    enlace sería una puerta abierta al resto del disco.
    """
    (espacio / "enlace.txt").symlink_to(tmp_path / "secreto.txt")
    r = MODULO.leer("enlace.txt")
    assert r.startswith("RECHAZADO")
    assert "NO DEBE LEERSE" not in r


def test_el_rechazo_no_se_reporta_como_fallo_de_herramienta(espacio):
    """Un rechazo deliberado no es una herramienta rota.

    Antes lanzaba ValueError y el chasis lo mostraba como «la herramienta falló»,
    mezclando las dos cosas. Ahora es un mensaje explícito.
    """
    r = MODULO.leer("../../../etc/passwd")
    assert r.startswith("RECHAZADO")
    assert "falló" not in r.lower()


def test_ruta_vacia_se_rechaza(espacio):
    assert MODULO.leer("").startswith(("RECHAZADO", "ERROR"))


# ── listar ─────────────────────────────────────────────────────────────────

def test_lista_el_contenido(espacio):
    r = MODULO.listar(".")
    assert "contrato.txt" in r
    assert "notas.md" in r
    assert "[carpeta] documentos/" in r


def test_lista_una_subcarpeta(espacio):
    assert "anexo.txt" in MODULO.listar("documentos")


def test_lista_carpeta_vacia(espacio):
    vacia = espacio / "vacia"
    vacia.mkdir()
    assert "vacía" in MODULO.listar("vacia")


def test_listar_un_archivo_avisa(espacio):
    r = MODULO.listar("contrato.txt")
    assert "ERROR" in r
    assert "es un archivo" in r


def test_listar_inexistente(espacio):
    assert "ERROR" in MODULO.listar("no-existe")


def test_listar_muestra_el_tamano(espacio):
    assert "bytes" in MODULO.listar(".")


# ── leer ───────────────────────────────────────────────────────────────────

def test_lee_el_contenido_con_numeros_de_linea(espacio):
    r = MODULO.leer("contrato.txt")
    assert "TERCERO" in r
    assert "850.000" in r
    assert "1|" in r or "1 |" in r


def test_indica_las_lineas_leidas(espacio):
    r = MODULO.leer("contrato.txt")
    assert "líneas" in r
    assert "de 3" in r


def test_rango_de_lineas(espacio):
    r = MODULO.leer("contrato.txt", desde=2, hasta=2)
    assert "PRIMERO" in r
    assert "TERCERO" not in r


def test_avisa_de_las_lineas_que_quedan(espacio):
    r = MODULO.leer("contrato.txt", desde=1, hasta=1)
    assert "quedan" in r


def test_leer_una_carpeta_avisa(espacio):
    r = MODULO.leer("documentos")
    assert "ERROR" in r
    assert "es una carpeta" in r


def test_leer_inexistente(espacio):
    assert "ERROR" in MODULO.leer("no-existe.txt")


def test_archivo_binario_no_revienta(espacio):
    (espacio / "imagen.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    r = MODULO.leer("imagen.png")
    assert "ERROR" in r
    assert "binario" in r.lower() or "utf-8" in r.lower()


def test_archivo_demasiado_grande_avisa(espacio, monkeypatch):
    monkeypatch.setattr(MODULO, "MAX_BYTES", 10)
    r = MODULO.leer("contrato.txt")
    assert "ERROR" in r
    assert "límite" in r


def test_desde_mas_alla_del_final_avisa(espacio):
    r = MODULO.leer("contrato.txt", desde=999)
    assert "ERROR" in r
    assert "tiene 3 líneas" in r


# ── buscar ─────────────────────────────────────────────────────────────────

def test_busca_en_todos_los_archivos(espacio):
    r = MODULO.buscar("850.000")
    assert "contrato.txt" in r
    assert "850.000" in r


def test_la_busqueda_indica_archivo_y_linea(espacio):
    r = MODULO.buscar("TERCERO")
    assert "contrato.txt:" in r


def test_busca_en_subcarpetas(espacio):
    assert "anexo.txt" in MODULO.buscar("Anexo")


def test_busqueda_sin_resultados_lo_dice(espacio):
    r = MODULO.buscar("palabra-que-no-existe-xyz")
    assert "No se encontró" in r


def test_busqueda_ignora_mayusculas(espacio):
    assert "TERCERO" in MODULO.buscar("tercero")


def test_busqueda_no_lee_fuera_del_espacio(espacio):
    """El secreto de fuera no debe aparecer ni en una búsqueda global."""
    assert "NO DEBE LEERSE" not in MODULO.buscar("NO DEBE")


def test_busqueda_vacia_avisa(espacio):
    assert "ERROR" in MODULO.buscar("")


def test_busqueda_omite_archivos_ocultos(espacio):
    (espacio / ".oculto.txt").write_text("palabra-clave-oculta\n", encoding="utf-8")
    r = MODULO.buscar("palabra-clave-oculta")
    assert "No se encontró" in r


# ── sin espacio de trabajo ─────────────────────────────────────────────────

def test_buscar_sin_carpeta_avisa(tmp_path):
    MODULO.configurar(tmp_path / "no-existe")
    r = MODULO.buscar("algo")
    assert "ERROR" in r
    assert "no existe" in r
