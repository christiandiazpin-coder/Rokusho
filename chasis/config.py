"""Rutas y configuración del chasis.

Regla: nada de esto depende del rubro. Si algo cambia según el cliente,
va en la medalla, no aquí.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MEDALLAS = RAIZ / "medallas"
PIEZAS = RAIZ / "piezas"


def _leer_env(ruta: Path, clave: str) -> str:
    """Lee una clave de un archivo .env sin cargarlo entero en el proceso."""
    try:
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            nombre, valor = linea.split("=", 1)
            if nombre.strip() == clave:
                return valor.strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def clave_openrouter() -> str:
    """La clave nunca se escribe en un log ni se muestra en pantalla."""
    valor = os.getenv("OPENROUTER_API_KEY", "").strip()
    if valor:
        return valor
    return _leer_env(Path.home() / ".config" / "umbral" / "openrouter.env",
                     "OPENROUTER_API_KEY")


def clave_para(proveedor: str) -> str:
    """Cada proveedor lee su clave del entorno. Ninguna se escribe en disco."""
    mapa = {
        "openrouter": "OPENROUTER_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "deploy": "DEPLOY_API_KEY",
        "openai": "OPENAI_API_KEY",
    }
    variable = mapa.get(proveedor, f"{proveedor.upper()}_API_KEY")
    valor = os.getenv(variable, "").strip()
    if valor:
        return valor
    if proveedor == "openrouter":
        return _leer_env(Path.home() / ".config" / "umbral" / "openrouter.env",
                         "OPENROUTER_API_KEY")
    return ""


@dataclass(frozen=True)
class Ajustes:
    """Lo que el usuario puede cambiar sin tocar código."""

    proveedor: str = "deploy"
    base_url: str = "https://api-sf1.deploy.com/api/v1"
    modelo: str = "deepseek-ai/deepseek-v4.1-flash-1017"
    temperatura: float = 0.2
    max_pasos: int = 8
    idioma: str = "es"
    max_tokens_turno: int | None = None

    def __post_init__(self) -> None:
        if self.max_tokens_turno is not None and (
            type(self.max_tokens_turno) is not int or self.max_tokens_turno <= 0
        ):
            raise ValueError("ROKUSHO_MAX_TOKENS_TURNO debe ser un entero positivo")

    @classmethod
    def desde_entorno(cls) -> "Ajustes":
        base = cls()
        proveedor = os.getenv("ROKUSHO_PROVEEDOR", base.proveedor)
        # Si se cambia de proveedor sin dar base_url ni modelo, se usan los
        # de fábrica de ese proveedor en vez de apuntar al anterior.
        otros = {
            "openrouter": ("https://openrouter.ai/api/v1", "google/gemma-4-31b-it:free"),
        }
        base_url, modelo = otros.get(proveedor, (base.base_url, base.modelo))
        limite_tokens = os.getenv("ROKUSHO_MAX_TOKENS_TURNO")
        try:
            max_tokens_turno = int(limite_tokens) if limite_tokens is not None else None
        except ValueError as e:
            raise ValueError("ROKUSHO_MAX_TOKENS_TURNO debe ser un entero positivo") from e
        return cls(
            proveedor=proveedor,
            base_url=os.getenv("ROKUSHO_BASE_URL", base_url),
            modelo=os.getenv("ROKUSHO_MODELO", modelo),
            temperatura=float(os.getenv("ROKUSHO_TEMPERATURA", base.temperatura)),
            max_pasos=int(os.getenv("ROKUSHO_MAX_PASOS", base.max_pasos)),
            max_tokens_turno=max_tokens_turno,
        )
