"""Medallas: el saber de un rubro, enchufable al chasis.

Una medalla no ejecuta nada. Solo define qué sabe el agente y cómo habla.
Si una medalla está mal escrita, el chasis falla en voz alta: una medalla
a medio cargar produciría respuestas del rubro equivocado y eso es peor
que un error visible.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import config


class MedallaInvalida(ValueError):
    """La medalla existe pero no se puede usar."""


@dataclass(frozen=True)
class Medalla:
    nombre: str
    version: str
    descripcion: str
    persona: str
    vocabulario: tuple[str, ...] = ()
    reglas: tuple[str, ...] = ()
    prohibido: tuple[str, ...] = ()
    ruta: Path = field(default=Path("."), compare=False)

    def a_sistema(self) -> str:
        """El texto que el modelo recibe como identidad de rubro."""
        partes = [f"# RUBRO: {self.nombre}", self.persona.strip()]

        if self.vocabulario:
            partes.append("\n## Vocabulario que DEBES usar")
            partes.extend(f"- {t}" for t in self.vocabulario)

        if self.reglas:
            partes.append("\n## Reglas del rubro (obligatorias)")
            partes.extend(f"{i}. {r}" for i, r in enumerate(self.reglas, 1))

        if self.prohibido:
            partes.append("\n## Prohibido en este rubro")
            partes.extend(f"- {p}" for p in self.prohibido)

        return "\n".join(partes)


def _texto(datos: dict, clave: str, *, obligatorio: bool = True) -> str:
    valor = datos.get(clave)
    if valor is None:
        if obligatorio:
            raise MedallaInvalida(f"falta el campo obligatorio «{clave}»")
        return ""
    if not isinstance(valor, str):
        raise MedallaInvalida(f"«{clave}» debe ser texto, no {type(valor).__name__}")
    return valor.strip()


def _lista(datos: dict, clave: str) -> tuple[str, ...]:
    valor = datos.get(clave, [])
    if not isinstance(valor, list) or any(not isinstance(x, str) for x in valor):
        raise MedallaInvalida(f"«{clave}» debe ser una lista de textos")
    return tuple(x.strip() for x in valor if x.strip())


def cargar(nombre: str, raiz: Path | None = None) -> Medalla:
    """Carga una medalla por nombre. Falla en voz alta si no sirve."""
    raiz = raiz or config.MEDALLAS
    carpeta = raiz / nombre
    archivo = carpeta / "medalla.toml"

    if not carpeta.is_dir():
        disponibles = sorted(p.name for p in raiz.iterdir() if p.is_dir()) if raiz.is_dir() else []
        raise MedallaInvalida(
            f"no existe la medalla «{nombre}». "
            f"Disponibles: {', '.join(disponibles) or '(ninguna)'}"
        )
    if not archivo.is_file():
        raise MedallaInvalida(f"la medalla «{nombre}» no tiene medalla.toml")

    try:
        datos = tomllib.loads(archivo.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise MedallaInvalida(f"no se pudo leer {archivo}: {e}") from e

    medalla = Medalla(
        nombre=_texto(datos, "nombre"),
        version=_texto(datos, "version"),
        descripcion=_texto(datos, "descripcion"),
        persona=_texto(datos, "persona"),
        vocabulario=_lista(datos, "vocabulario"),
        reglas=_lista(datos, "reglas"),
        prohibido=_lista(datos, "prohibido"),
        ruta=carpeta,
    )

    if not medalla.persona:
        raise MedallaInvalida(f"la medalla «{nombre}» tiene la persona vacía")
    return medalla


def disponibles(raiz: Path | None = None) -> list[str]:
    raiz = raiz or config.MEDALLAS
    if not raiz.is_dir():
        return []
    return sorted(p.name for p in raiz.iterdir()
                  if p.is_dir() and (p / "medalla.toml").is_file())
