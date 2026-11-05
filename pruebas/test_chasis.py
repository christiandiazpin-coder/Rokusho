"""Pruebas del chasis.

Se prueba lo que puede fallar en silencio: una medalla a medio cargar, una
pieza que declara algo que no implementa, y una herramienta que se escapa del
espacio de trabajo. Un error visible es aceptable; una respuesta del rubro
equivocado no.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from chasis import pieza as pieza_mod
from chasis.agente import Agente
from chasis.medalla import MedallaInvalida, cargar as cargar_medalla
from chasis.pieza import PiezaInvalida, cargar as cargar_pieza


class ClienteFalso:
    """Reemplaza al proveedor: se prueba el chasis, no la red."""

    def __init__(self, respuestas: list) -> None:
        self.respuestas = list(respuestas)
        self.recibido: list[dict] = []

    def conversar(self, mensajes, herramientas=None, *, modelo=None):
        from chasis.ia import Respuesta
        self.recibido.append({"mensajes": list(mensajes), "herramientas": herramientas})
        if not self.respuestas:
            raise AssertionError("el agente pidió más turnos de los previstos")
        r = self.respuestas.pop(0)
        if isinstance(r, str):
            return Respuesta(contenido=r, llamadas=[], modelo="falso")
        return Respuesta(contenido=r.get("contenido", ""),
                         llamadas=r.get("llamadas", []), modelo="falso")


def _medalla_dir(base: Path, nombre: str, **campos) -> Path:
    """Escribe una medalla de prueba.

    Los valores de tipo lista se escriben como arreglo; los de texto se citan
    una sola vez. El helper anterior producía `""texto""`, que TOML rechaza.
    """
    carpeta = base / nombre
    carpeta.mkdir(parents=True)
    partes = ['nombre = "X"', 'version = "1"', 'descripcion = "d"']
    for clave, valor in campos.items():
        if isinstance(valor, list):
            partes.append(f"{clave} = [" + ", ".join(f'"{v}"' for v in valor) + "]")
        else:
            texto = str(valor).replace("\\", "\\\\").replace('"', '\\"')
            partes.append(f'{clave} = "{texto}"')
    (carpeta / "medalla.toml").write_text("\n".join(partes) + "\n", encoding="utf-8")
    return carpeta


# ── medallas ─────────────────────────────────────────────────────────────────

def test_medalla_valida_se_carga(tmp_path):
    _medalla_dir(tmp_path, "prueba", persona="Eres de prueba", reglas=["r1", "r2"])
    m = cargar_medalla("prueba", raiz=tmp_path)
    assert m.nombre == "X"
    assert m.reglas == ("r1", "r2")


def test_medalla_inexistente_dice_cuales_hay(tmp_path):
    _medalla_dir(tmp_path, "salud", persona="p")
    with pytest.raises(MedallaInvalida) as e:
        cargar_medalla("finanzas", raiz=tmp_path)
    assert "salud" in str(e.value)


def test_medalla_sin_persona_falla(tmp_path):
    carpeta = tmp_path / "mala"
    carpeta.mkdir()
    (carpeta / "medalla.toml").write_text(
        'nombre = "x"\nversion = "1"\ndescripcion = "d"\npersona = "   "\n', encoding="utf-8")
    with pytest.raises(MedallaInvalida, match="persona"):
        cargar_medalla("mala", raiz=tmp_path)


def test_medalla_toml_roto_falla_con_ruta(tmp_path):
    carpeta = tmp_path / "rota"
    carpeta.mkdir()
    (carpeta / "medalla.toml").write_text('nombre = "x"\npersona = sin comillas\n',
                                          encoding="utf-8")
    with pytest.raises(MedallaInvalida, match="medalla.toml"):
        cargar_medalla("rota", raiz=tmp_path)


def test_medalla_reglas_deben_ser_lista(tmp_path):
    _medalla_dir(tmp_path, "rara", persona="p", reglas='"no soy lista"')
    with pytest.raises(MedallaInvalida, match="lista"):
        cargar_medalla("rara", raiz=tmp_path)


def test_prompt_incluye_vocabulario_reglas_y_prohibiciones(tmp_path):
    _medalla_dir(tmp_path, "m", persona="Persona X",
                 vocabulario=["turno"], reglas=["regla uno"], prohibido=["inventar"])
    texto = cargar_medalla("m", raiz=tmp_path).a_sistema()
    assert "Persona X" in texto
    assert "turno" in texto and "regla uno" in texto and "inventar" in texto


# ── piezas ───────────────────────────────────────────────────────────────────

def _pieza_dir(base: Path, nombre: str, toml: str, codigo: str) -> Path:
    carpeta = base / nombre
    carpeta.mkdir(parents=True)
    (carpeta / "pieza.toml").write_text(textwrap.dedent(toml), encoding="utf-8")
    (carpeta / "implementacion.py").write_text(textwrap.dedent(codigo), encoding="utf-8")
    return carpeta


def test_pieza_valida_carga_herramientas(tmp_path):
    _pieza_dir(tmp_path, "eco", """
        nombre = "eco"
        version = "1"
        descripcion = "repite"
        herramientas = [
          { nombre = "repetir", funcion = "repetir", descripcion = "repite", parametros = { texto = "string" } },
        ]
    """, """
        def repetir(texto: str) -> str:
            return texto
    """)
    p = cargar_pieza("eco", raiz=tmp_path)
    assert [h.nombre for h in p.herramientas] == ["repetir"]
    # «required» va dentro de «parameters», como exige el formato OpenAI/OpenRouter.
    esquema = p.herramientas[0].a_schema()
    assert esquema["function"]["parameters"]["required"] == ["texto"]


def test_pieza_declara_funcion_inexistente(tmp_path):
    _pieza_dir(tmp_path, "mentirosa", """
        nombre = "m"
        version = "1"
        descripcion = "d"
        herramientas = [
          { nombre = "hacer", funcion = "no_existe", descripcion = "d", parametros = {} },
        ]
    """, "def otra(): return 'x'")
    with pytest.raises(PiezaInvalida, match="no_existe"):
        cargar_pieza("mentirosa", raiz=tmp_path)


def test_pieza_sin_implementacion_falla(tmp_path):
    carpeta = tmp_path / "vacia"
    carpeta.mkdir()
    (carpeta / "pieza.toml").write_text('nombre="v"\nversion="1"\ndescripcion="d"\nherramientas=[{nombre="h"}]\n',
                                        encoding="utf-8")
    with pytest.raises(PiezaInvalida, match="implementacion.py"):
        cargar_pieza("vacia", raiz=tmp_path)


def test_dos_piezas_con_misma_herramienta_chocan(tmp_path):
    toml = """
        nombre = "p"
        version = "1"
        descripcion = "d"
        herramientas = [
          { nombre = "igual", funcion = "f", descripcion = "d", parametros = {} },
        ]
    """
    _pieza_dir(tmp_path, "a", toml, "def f(): return 'a'")
    _pieza_dir(tmp_path, "b", toml, "def f(): return 'b'")
    with pytest.raises(PiezaInvalida, match="igual"):
        pieza_mod.cargar_varias(["a", "b"], raiz=tmp_path)


def test_gancho_configurar_se_llama_sobre_el_modulo_de_la_pieza(tmp_path):
    """Regresión: reimportar el archivo configuraba otra copia del módulo."""
    _pieza_dir(tmp_path, "conf", """
        nombre = "c"
        version = "1"
        descripcion = "d"
        herramientas = [
          { nombre = "ver", funcion = "ver", descripcion = "d", parametros = {} },
        ]
    """, """
        RUTA = "sin-configurar"

        def configurar(carpeta):
            global RUTA
            RUTA = str(carpeta)

        def ver() -> str:
            return RUTA
    """)
    p = cargar_pieza("conf", raiz=tmp_path)
    assert p.configurar is not None
    p.configurar("/tmp/destino")
    # La herramienta debe ver el cambio: mismo módulo, mismas globales.
    assert p.herramientas[0].funcion() == "/tmp/destino"


# ── agente ───────────────────────────────────────────────────────────────────

def _agente(tmp_path, piezas=None):
    _medalla_dir(tmp_path / "medallas", "m", persona="Eres de prueba")
    m = cargar_medalla("m", raiz=tmp_path / "medallas")
    return Agente(m, piezas or [], cliente=ClienteFalso([]))


def test_agente_sin_herramientas_responde_directo(tmp_path):
    ag = _agente(tmp_path)
    ag._cliente = ClienteFalso(["respuesta final"])
    turno = ag.ejecutar("hola")
    assert turno.respuesta == "respuesta final"
    assert turno.pasos == []


def test_agente_usa_herramienta_y_devuelve_el_resultado_al_modelo(tmp_path):
    _pieza_dir(tmp_path / "piezas", "eco", """
        nombre = "eco"
        version = "1"
        descripcion = "d"
        herramientas = [
          { nombre = "repetir", funcion = "repetir", descripcion = "d", parametros = { texto = "string" } },
        ]
    """, """
        def repetir(texto: str) -> str:
            return "eco:" + texto
    """)
    p = cargar_pieza("eco", raiz=tmp_path / "piezas")
    ag = _agente(tmp_path, [p])
    ag._cliente = ClienteFalso([
        {"llamadas": [{"id": "1", "function": {"name": "repetir",
                                               "arguments": '{"texto": "hola"}'}}]},
        "listo",
    ])
    turno = ag.ejecutar("repite hola")
    assert turno.respuesta == "listo"
    assert turno.uso_herramientas == ["repetir"]
    assert turno.pasos[0].resultado == "eco:hola"
    # El resultado tiene que volver al modelo, con su tool_call_id.
    mensajes = ag._cliente.recibido[1]["mensajes"]
    assert any(m.get("role") == "tool" and m["content"] == "eco:hola" for m in mensajes)


def test_herramienta_inexistente_devuelve_error_al_modelo(tmp_path):
    ag = _agente(tmp_path)
    ag._cliente = ClienteFalso([
        {"llamadas": [{"id": "1", "function": {"name": "volar", "arguments": "{}"}}]},
        "no pude",
    ])
    turno = ag.ejecutar("vuela")
    assert "no existe la herramienta" in turno.pasos[0].resultado


def test_json_de_argumentos_roto_no_tumba_el_turno(tmp_path):
    ag = _agente(tmp_path)
    ag._cliente = ClienteFalso([
        {"llamadas": [{"id": "1", "function": {"name": "x", "arguments": "{roto"}}]},
        "sigo",
    ])
    turno = ag.ejecutar("x")
    assert turno.respuesta == "sigo"


def test_herramienta_que_explota_devuelve_error_y_el_turno_sigue(tmp_path):
    _pieza_dir(tmp_path / "piezas", "boom", """
        nombre = "b"
        version = "1"
        descripcion = "d"
        herramientas = [
          { nombre = "explotar", funcion = "explotar", descripcion = "d", parametros = {} },
        ]
    """, """
        def explotar() -> str:
            raise RuntimeError("se rompio")
    """)
    p = cargar_pieza("boom", raiz=tmp_path / "piezas")
    ag = _agente(tmp_path, [p])
    ag._cliente = ClienteFalso([
        {"llamadas": [{"id": "1", "function": {"name": "explotar", "arguments": "{}"}}]},
        "recuperado",
    ])
    turno = ag.ejecutar("explota")
    assert turno.respuesta == "recuperado"
    assert "se rompio" in turno.pasos[0].resultado


def test_al_agotar_pasos_pide_cierre_sin_herramientas(tmp_path):
    _pieza_dir(tmp_path / "piezas", "loop", """
        nombre = "l"
        version = "1"
        descripcion = "d"
        herramientas = [
          { nombre = "girar", funcion = "girar", descripcion = "d", parametros = {} },
        ]
    """, "def girar(): return 'otra vez'")
    p = cargar_pieza("loop", raiz=tmp_path / "piezas")
    ag = _agente(tmp_path, [p])
    eterno = {"llamadas": [{"id": "1", "function": {"name": "girar", "arguments": "{}"}}]}
    ag._cliente = ClienteFalso([eterno, eterno, "cierre forzado"])
    turno = ag.ejecutar("gira", max_pasos=2)
    assert turno.respuesta == "cierre forzado"
    assert ag._cliente.recibido[-1]["herramientas"] is None


def test_el_sistema_del_agente_incluye_medalla_y_piezas(tmp_path):
    _pieza_dir(tmp_path / "piezas", "p1", """
        nombre = "p1"
        version = "1"
        descripcion = "pieza de prueba"
        herramientas = [
          { nombre = "hacer_algo", funcion = "f", descripcion = "hace algo", parametros = {} },
        ]
    """, "def f(): return 'ok'")
    p = cargar_pieza("p1", raiz=tmp_path / "piezas")
    ag = _agente(tmp_path, [p])
    sistema = ag.sistema()
    assert "RUBRO" in sistema
    assert "hacer_algo" in sistema
    assert "No inventes" in sistema
