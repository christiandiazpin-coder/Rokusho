"""Pruebas de la pieza «medios».

El caso central es el veredicto de un fotograma: la luminancia media sola
etiquetaba como «imagen» un plano casi negro y como «negro» una lámina antigua
oscura pero visible. Las pruebas fijan el criterio por contraste.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from chasis.pieza import cargar

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def pieza():
    return cargar("medios", raiz=RAIZ / "piezas")


@pytest.fixture()
def video_sintetico(tmp_path, pieza):
    """Genera videos de control con ffmpeg: negro, gris uniforme y con detalle."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg no está instalado")

    def generar(nombre: str, filtro: str) -> Path:
        destino = tmp_path / nombre
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
             "-i", "color=c=black:s=320x180:d=3", "-vf", filtro,
             "-c:v", "libx264", "-pix_fmt", "yuv420p", str(destino)],
            check=True, capture_output=True, timeout=120)
        return destino

    pieza.configurar(tmp_path)
    return {nombre: generar(nombre, filtro) for nombre, filtro in {
        "negro.mp4": "null",
        "plano.mp4": "drawbox=x=0:y=0:w=iw:h=ih:color=gray@1:t=fill",
        "detalle.mp4": ("drawbox=x=0:y=0:w=iw:h=ih:color=black@1:t=fill,"
                        "drawbox=x=40:y=40:w=200:h=90:color=white@1:t=fill"),
    }.items()}


def _medida(salida: str, etiqueta: str) -> float:
    for linea in salida.splitlines():
        if etiqueta in linea:
            return float(linea.split(":")[1].strip().split()[0])
    raise AssertionError(f"la salida no trae «{etiqueta}»:\n{salida}")


def test_negro_pleno_se_detecta(video_sintetico, pieza):
    salida = pieza.herramientas[2].funcion("negro.mp4", 1.0)
    assert "sin imagen" in salida
    assert _medida(salida, "desviaci") < 6


def test_gris_uniforme_no_es_imagen(video_sintetico, pieza):
    """Sin contraste no hay imagen, aunque la media sea alta."""
    salida = pieza.herramientas[2].funcion("plano.mp4", 1.0)
    assert _medida(salida, "luminancia media") > 60
    assert "sin imagen" in salida or "casi sin contraste" in salida


def test_imagen_con_detalle_pasa(video_sintetico, pieza):
    salida = pieza.herramientas[2].funcion("detalle.mp4", 1.0)
    assert "plano con imagen" in salida


def test_fotograma_fuera_de_rango_avisa(tmp_path, pieza, video_sintetico):
    salida = pieza.herramientas[2].funcion("negro.mp4", 999)
    assert "no hay fotograma" in salida


def test_ruta_fuera_del_espacio_de_trabajo_se_rechaza(video_sintetico, pieza):
    with pytest.raises(ValueError):
        pieza.herramientas[2].funcion("../../../etc/passwd", 0)


def test_medir_inexistente_no_inventa(video_sintetico, pieza):
    salida = pieza.herramientas[0].funcion("no-existe.mp4")
    assert "ERROR" in salida and "no existe" in salida


def test_medir_devuelve_duracion_real(video_sintetico, pieza):
    salida = pieza.herramientas[0].funcion("negro.mp4")
    assert "duración" in salida
    assert "video: h264 320x180" in salida


def test_nivel_de_audio_sobre_un_video_sin_audio(video_sintetico, pieza):
    """Sin pista de audio no hay nivel: se avisa, no se inventa una cifra."""
    salida = pieza.herramientas[1].funcion("negro.mp4")
    assert "ERROR" in salida or "LUFS" in salida
