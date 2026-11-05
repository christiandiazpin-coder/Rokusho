"""Piezas: lo que el chasis puede hacer, no lo que sabe.

Una pieza declara sus herramientas y las implementa. El chasis las expone
al modelo; si el modelo intenta usar una que no está declarada, no existe.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import config


class PiezaInvalida(ValueError):
    """La pieza existe pero no se puede usar."""


@dataclass
class Herramienta:
    nombre: str
    descripcion: str
    parametros: dict[str, str]
    funcion: Callable[..., str]

    def a_schema(self) -> dict:
        """Formato de herramientas que entiende OpenRouter (estilo OpenAI)."""
        propiedades = {
            nombre: {"type": tipo, "description": f"Parámetro {nombre}"}
            for nombre, tipo in self.parametros.items()
        }
        return {
            "type": "function",
            "function": {
                "name": self.nombre,
                "description": self.descripcion,
                "parameters": {
                    "type": "object",
                    "properties": propiedades,
                    "required": list(self.parametros),
                },
            },
        }


@dataclass
class Pieza:
    nombre: str
    version: str
    descripcion: str
    herramientas: list[Herramienta] = field(default_factory=list)
    ruta: Path = field(default=Path("."), compare=False)
    configurar: Callable[..., None] | None = field(default=None, compare=False)

    def a_schemas(self) -> list[dict]:
        return [h.a_schema() for h in self.herramientas]

    def buscar(self, nombre: str) -> Herramienta | None:
        return next((h for h in self.herramientas if h.nombre == nombre), None)


def _gancho_configuracion(modulo) -> Callable[..., None] | None:
    """Busca la función con la que una pieza recibe su contexto de ejecución.

    Se llama por referencia al módulo ya importado: reimportar el archivo
    crearía una segunda copia del módulo con sus propias variables globales,
    y la configuración se aplicaría a la copia equivocada.
    """
    for nombre in ("configurar", "configurar_contexto"):
        fn = getattr(modulo, nombre, None)
        if callable(fn):
            return fn
    return None


def cargar(nombre: str, raiz: Path | None = None) -> Pieza:
    """Carga una pieza: lee su pieza.toml e importa su implementación."""
    raiz = raiz or config.PIEZAS
    carpeta = raiz / nombre
    archivo = carpeta / "pieza.toml"
    implementacion = carpeta / "implementacion.py"

    if not carpeta.is_dir():
        disponibles = sorted(p.name for p in raiz.iterdir() if p.is_dir()) if raiz.is_dir() else []
        raise PiezaInvalida(
            f"no existe la pieza «{nombre}». "
            f"Disponibles: {', '.join(disponibles) or '(ninguna)'}"
        )
    if not archivo.is_file():
        raise PiezaInvalida(f"la pieza «{nombre}» no tiene pieza.toml")
    if not implementacion.is_file():
        raise PiezaInvalida(f"la pieza «{nombre}» no tiene implementacion.py")

    try:
        datos = tomllib.loads(archivo.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise PiezaInvalida(f"no se pudo leer {archivo}: {e}") from e

    try:
        modulo = _importar(implementacion, f"rokusho_pieza_{nombre}")
    except Exception as e:  # noqa: BLE001 - se reporta con contexto
        raise PiezaInvalida(f"la pieza «{nombre}» no se pudo importar: {e}") from e

    declaradas = datos.get("herramientas", [])
    if not isinstance(declaradas, list) or not declaradas:
        raise PiezaInvalida(f"la pieza «{nombre}» no declara herramientas")

    herramientas: list[Herramienta] = []
    for decl in declaradas:
        if not isinstance(decl, dict) or "nombre" not in decl:
            raise PiezaInvalida(f"herramienta mal declarada en «{nombre}»: {decl!r}")
        fn_nombre = decl.get("funcion", decl["nombre"])
        funcion = getattr(modulo, fn_nombre, None)
        if not callable(funcion):
            raise PiezaInvalida(
                f"la pieza «{nombre}» declara «{decl['nombre']}» pero "
                f"implementacion.py no tiene la función «{fn_nombre}»"
            )
        parametros = decl.get("parametros", {})
        if not isinstance(parametros, dict):
            raise PiezaInvalida(f"«parametros» de {decl['nombre']} debe ser una tabla")
        herramientas.append(Herramienta(
            nombre=decl["nombre"],
            descripcion=decl.get("descripcion", ""),
            parametros={k: str(v) for k, v in parametros.items()},
            funcion=funcion,
        ))

    pieza = Pieza(
        nombre=datos.get("nombre", nombre),
        version=datos.get("version", "0"),
        descripcion=datos.get("descripcion", ""),
        herramientas=herramientas,
        ruta=carpeta,
        configurar=_gancho_configuracion(modulo),
    )
    pieza.a_schemas()  # valida que los esquemas se puedan construir
    return pieza


def _importar(ruta: Path, nombre_modulo: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location(nombre_modulo, ruta)
    if spec is None or spec.loader is None:
        raise PiezaInvalida(f"no se pudo preparar {ruta}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def disponibles(raiz: Path | None = None) -> list[str]:
    raiz = raiz or config.PIEZAS
    if not raiz.is_dir():
        return []
    return sorted(p.name for p in raiz.iterdir()
                  if p.is_dir() and (p / "pieza.toml").is_file())


def cargar_varias(nombres: list[str], raiz: Path | None = None) -> list[Pieza]:
    """Carga varias piezas y avisa si dos declaran la misma herramienta."""
    piezas = [cargar(n, raiz) for n in nombres]
    vistos: dict[str, str] = {}
    for p in piezas:
        for h in p.herramientas:
            if h.nombre in vistos:
                raise PiezaInvalida(
                    f"la herramienta «{h.nombre}» está en dos piezas "
                    f"({vistos[h.nombre]} y {p.nombre}); el agente no sabría cuál usar"
                )
            vistos[h.nombre] = p.nombre
    return piezas
