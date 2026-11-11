"""Cliente de IA: cualquier proveedor compatible con OpenRouter.

El chasis no asume un modelo. Si un proveedor falla, pasa al siguiente sin
romper el turno. La clave nunca se registra en el log ni en la traza.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

import requests

from .config import Ajustes, clave_para


class ErrorProveedor(RuntimeError):
    """El proveedor respondió con error después de reintentar."""


@dataclass
class Respuesta:
    contenido: str
    llamadas: list[dict]
    modelo: str
    tokens_entrada: int = 0
    tokens_salida: int = 0
    uso_disponible: bool = False


class ClienteIA:
    def __init__(self, ajustes: Ajustes, *, reintentos: int = 3, espera: float = 4.0) -> None:
        self.ajustes = ajustes
        self.reintentos = reintentos
        self.espera = espera
        self.clave = clave_para(ajustes.proveedor)
        if not self.clave:
            raise ErrorProveedor(
                f"falta la clave de {ajustes.proveedor}. "
                "Define OPENROUTER_API_KEY o escríbela en ~/.config/umbral/openrouter.env"
            )

    def _cabeceras(self) -> dict:
        cabeceras = {
            "Authorization": f"Bearer {self.clave}",
            "Content-Type": "application/json",
        }
        if self.ajustes.proveedor == "openrouter":
            cabeceras["HTTP-Referer"] = "https://rokusho.local"
            cabeceras["X-Title"] = "Rokusho"
        return cabeceras

    def conversar(self, mensajes: list[dict], herramientas: list[dict] | None = None,
                  *, modelo: str | None = None) -> Respuesta:
        """Un turno de conversación. Reintenta ante fallas transitorias."""
        cuerpo: dict = {
            "model": modelo or self.ajustes.modelo,
            "messages": mensajes,
            "temperature": self.ajustes.temperatura,
        }
        if herramientas:
            cuerpo["tools"] = herramientas
            cuerpo["tool_choice"] = "auto"

        url = f"{self.ajustes.base_url.rstrip('/')}/chat/completions"
        ultimo = ""
        for intento in range(self.reintentos):
            try:
                r = requests.post(url, headers=self._cabeceras(), json=cuerpo, timeout=120)
            except requests.RequestException as e:
                ultimo = f"fallo de red: {e}"
            else:
                if r.status_code == 200:
                    return self._leer(r.json())
                ultimo = f"HTTP {r.status_code}: {r.text[:300]}"
                # 429 y 5xx son transitorios; 4xx no.
                if r.status_code not in (429, 500, 502, 503, 504):
                    raise ErrorProveedor(ultimo)
            if intento < self.reintentos - 1:
                time.sleep(self.espera * (intento + 1))

        raise ErrorProveedor(f"{self.ajustes.proveedor} no respondió: {ultimo}")

    def _leer(self, datos: dict) -> Respuesta:
        opciones = datos.get("choices") or []
        if not opciones:
            raise ErrorProveedor(f"respuesta sin «choices»: {str(datos)[:300]}")
        mensaje = opciones[0].get("message") or {}

        # El texto puede venir en «content», «reasoning_content» (DeepSeek y
        # otros modelos que razonan) o «reasoning» (OpenRouter). Si se corta
        # por límite de tokens, «content» queda vacío y el texto está en el
        # razonamiento: sin este respaldo el turno se pierde entero.
        contenido = mensaje.get("content") or ""
        if not contenido:
            contenido = (mensaje.get("reasoning_content")
                         or mensaje.get("reasoning") or "")

        uso = datos.get("usage") or {}
        def contar(valor) -> int | None:
            # Algunos proveedores devuelven los enteros como cadenas.
            if type(valor) is int and valor >= 0:
                return valor
            if isinstance(valor, str) and valor.isascii() and valor.isdecimal():
                return int(valor)
            return None

        entrada = contar(uso.get("prompt_tokens"))
        salida = contar(uso.get("completion_tokens"))
        uso_disponible = entrada is not None and salida is not None
        return Respuesta(
            contenido=contenido,
            llamadas=mensaje.get("tool_calls") or [],
            modelo=datos.get("model", self.ajustes.modelo),
            tokens_entrada=entrada if entrada is not None else 0,
            tokens_salida=salida if salida is not None else 0,
            uso_disponible=uso_disponible,
        )
