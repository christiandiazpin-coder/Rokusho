"""El agente: medalla puesta sobre el chasis, con piezas enchufadas.

Un agente es la combinación de:
  - una medalla (qué sabe)
  - cero o más piezas (qué puede hacer)
  - un modelo (quién piensa)

Nada de eso está cableado: se pasa al construirlo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from . import auditoria as _auditoria
from . import procedencia as _procedencia
from .config import Ajustes
from .ia import ClienteIA, ErrorProveedor, Respuesta
from .medalla import Medalla
from .pieza import Pieza


REGLAS_DEL_CHASIS = """\
# CÓMO TRABAJAS

Eres un agente de Rokusho. Trabajas para una empresa real y tu salida la lee una persona.

1. No inventes. Si un dato no está en lo que leíste ni lo devolvió una herramienta, dilo:
   «no lo tengo» es una respuesta válida y útil. Un dato inventado cuesta más que un dato faltante.
2. Distingue lo que verificaste de lo que supones. Cuando afirmes algo, que se pueda rastrear
   a la herramienta o al archivo de donde salió.
3. Si una herramienta falla, lee el error y prueba otra vía. No repitas la misma llamada
   esperando otro resultado, y no afirmes que hiciste algo que la herramienta rechazó.
4. Antes de cerrar, di qué hiciste, qué quedó pendiente y qué necesitas de la persona.
4b. Cada cifra, ruta o dato concreto que escribas debe venir de la salida de una
   herramienta. Si lo deduces, dilo con la palabra «deducido» o «estimo»: el
   sistema marca como HIPOTESIS todo dato que no pueda rastrear.
5. Responde en español, en el registro del rubro de tu medalla.
"""


class ErrorAgente(RuntimeError):
    """El agente no pudo completar el turno."""


@dataclass
class Paso:
    numero: int
    herramienta: str
    argumentos: dict
    resultado: str


@dataclass
class Turno:
    respuesta: str
    pasos: list[Paso] = field(default_factory=list)
    modelo: str = ""
    tokens_entrada: int = 0
    tokens_salida: int = 0
    # Auditoría del propio turno: se calcula al cerrarlo, no se pide.
    avisos: list = field(default_factory=list)
    procedencia: dict = field(default_factory=dict)

    @property
    def uso_herramientas(self) -> list[str]:
        return [p.herramienta for p in self.pasos]

    @property
    def limpio(self) -> bool:
        """Verdadero si el reporte no tiene afirmaciones sin respaldo."""
        return not self.avisos


class Agente:
    def __init__(self, medalla: Medalla, piezas: list[Pieza] | None = None,
                 ajustes: Ajustes | None = None, cliente: ClienteIA | None = None) -> None:
        self.medalla = medalla
        self.piezas = piezas or []
        self.ajustes = ajustes or Ajustes.desde_entorno()
        self._cliente = cliente
        self._herramientas = {
            h.nombre: h for p in self.piezas for h in p.herramientas
        }

    @property
    def cliente(self) -> ClienteIA:
        if self._cliente is None:
            self._cliente = ClienteIA(self.ajustes)
        return self._cliente

    def sistema(self) -> str:
        partes = [REGLAS_DEL_CHASIS, self.medalla.a_sistema()]
        if self.piezas:
            partes.append("\n# HERRAMIENTAS DISPONIBLES")
            for pieza in self.piezas:
                partes.append(f"\n## Pieza: {pieza.nombre} — {pieza.descripcion}")
                for h in pieza.herramientas:
                    partes.append(f"- `{h.nombre}`: {h.descripcion}")
        partes.append(
            "\nCuando termines el trabajo, responde en texto normal (sin llamar herramientas) "
            "con el entregable completo."
        )
        return "\n".join(partes)

    def ejecutar(self, encargo: str, *, max_pasos: int | None = None) -> Turno:
        """Resuelve un encargo, permitiendo que el modelo use herramientas."""
        limite = max_pasos if max_pasos is not None else self.ajustes.max_pasos
        mensajes: list[dict] = [
            {"role": "system", "content": self.sistema()},
            {"role": "user", "content": encargo},
        ]
        esquemas = [h.a_schema() for p in self.piezas for h in p.herramientas] or None

        pasos: list[Paso] = []
        entrada = salida = 0
        modelo_usado = ""

        for numero in range(1, limite + 1):
            respuesta: Respuesta = self.cliente.conversar(mensajes, esquemas)
            entrada += respuesta.tokens_entrada
            salida += respuesta.tokens_salida
            modelo_usado = respuesta.modelo

            if not respuesta.llamadas:
                return self._cerrar(
                    respuesta.contenido.strip(), pasos, modelo_usado,
                    entrada, salida)

            mensajes.append({
                "role": "assistant",
                "content": respuesta.contenido or "",
                "tool_calls": respuesta.llamadas,
            })

            for llamada in respuesta.llamadas:
                nombre, argumentos, ident = self._desglosar(llamada)
                resultado = self._ejecutar_herramienta(nombre, argumentos)
                pasos.append(Paso(numero, nombre, argumentos, resultado))
                mensajes.append({
                    "role": "tool",
                    "tool_call_id": ident,
                    "name": nombre,
                    "content": resultado,
                })

        # Se agotaron los pasos: se pide el cierre sin herramientas.
        mensajes.append({
            "role": "user",
            "content": "Se agotaron los pasos disponibles. Entrega ahora tu mejor resultado "
                       "con lo que ya obtuviste, y di qué quedó pendiente.",
        })
        cierre = self.cliente.conversar(mensajes, None)
        entrada += cierre.tokens_entrada
        salida += cierre.tokens_salida
        return self._cerrar(cierre.contenido.strip(), pasos,
                            cierre.modelo or modelo_usado, entrada, salida)

    def _cerrar(self, respuesta: str, pasos: list[Paso], modelo: str,
                entrada: int, salida: int) -> Turno:
        """Cierra el turno auditando lo que el reporte afirma.

        La auditoría no se pide: ocurre siempre. Un agente que puede entregar sin
        ser auditado acaba entregando afirmaciones sin respaldo, y eso es
        exactamente lo que este proyecto existe para evitar.
        """
        turno = Turno(respuesta=respuesta, pasos=pasos, modelo=modelo,
                      tokens_entrada=entrada, tokens_salida=salida)
        try:
            auditoria = _auditoria.auditar(turno)
            turno.avisos = auditoria.avisos
            if not auditoria.limpia:
                turno.respuesta = respuesta + "\n" + _auditoria.formatear(auditoria)
            salidas = [p.resultado or "" for p in pasos]
            proc = _procedencia.etiquetar(respuesta, salidas)
            turno.procedencia = _procedencia.resumen(proc)
        except Exception:  # noqa: BLE001 - auditar no debe tumbar la entrega
            # Si la auditoría falla, el turno se entrega sin ella, pero se dice.
            turno.procedencia = {"error": "la auditoría no pudo ejecutarse"}
        return turno

    def _desglosar(self, llamada: dict) -> tuple[str, dict[str, Any], str]:
        funcion = llamada.get("function") or {}
        nombre = funcion.get("name", "")
        ident = llamada.get("id", "")
        crudo = funcion.get("arguments") or "{}"
        try:
            argumentos = json.loads(crudo) if isinstance(crudo, str) else dict(crudo)
        except json.JSONDecodeError:
            argumentos = {"_error_parseo": crudo[:200]}
        return nombre, argumentos, ident

    def _ejecutar_herramienta(self, nombre: str, argumentos: dict) -> str:
        herramienta = self._herramientas.get(nombre)
        if herramienta is None:
            disponibles = ", ".join(sorted(self._herramientas)) or "(ninguna)"
            return (f"ERROR: no existe la herramienta «{nombre}». "
                    f"Disponibles: {disponibles}")
        if "_error_parseo" in argumentos:
            return ("ERROR: los argumentos no eran JSON válido. "
                    "Reenvía la llamada con JSON correcto.")
        try:
            return str(herramienta.funcion(**argumentos))
        except TypeError as e:
            return f"ERROR: argumentos incorrectos para «{nombre}»: {e}"
        except Exception as e:  # noqa: BLE001 - la herramienta no debe tumbar el turno
            return f"ERROR: «{nombre}» falló: {type(e).__name__}: {e}"
