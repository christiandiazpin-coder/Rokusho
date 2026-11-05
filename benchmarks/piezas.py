"""Banco de pruebas: ¿cuántas herramientas tolera el modelo antes de confundirse?

El problema que mide: cada vez que se añade una pieza al chasis, sus herramientas
entran en el prompt. Con muchas, dos cosas pueden pasar — el modelo elige mal, o
el prompt crece hasta que el costo y el ruido se vuelven inaceptables. Ninguna de
las dos se nota mirando el código.

Diseño: se generan N herramientas sintéticas con nombres y descripciones
inequívocas. Después se le pide al modelo una tarea que **solo una** de ellas
puede resolver. Se comprueba si llamó a esa y no a otra.

Cada herramienta devuelve su propio nombre, así el acierto se verifica sin
ambigüedad: si la respuesta es «T7», acertó; cualquier otra cosa, no.

Uso:
    python -m benchmarks.piezas --niveles 4,8,12,16 --repeticiones 1
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chasis.agente import Agente  # noqa: E402
from chasis.config import Ajustes  # noqa: E402
from chasis.medalla import Medalla  # noqa: E402
from chasis.pieza import Herramienta, Pieza  # noqa: E402


# Cada tarea apunta a una herramienta por su nombre. El encargo está escrito
# para que la elección sea inequívoca: si el modelo falla, es por saturación,
# no porque el enunciado fuera ambiguo.
TAREAS: list[dict] = [
    {"herramienta": "T0", "encargo": "Convierte 1500 pesos chilenos a dólares."},
    {"herramienta": "T1", "encargo": "Cuenta cuántas palabras tiene el texto «hola mundo»."},
    {"herramienta": "T2", "encargo": "Dime qué día de la semana fue el 3 de marzo de 2020."},
    {"herramienta": "T3", "encargo": "Genera un código de color hexadecimal a partir de un nombre."},
    {"herramienta": "T4", "encargo": "Calcula la raíz cuadrada de 2 con seis decimales."},
    {"herramienta": "T5", "encargo": "Ordena alfabéticamente la lista: pera, manzana, kiwi."},
    {"herramienta": "T6", "encargo": "Comprime la frase «aaaabbbcc» indicando cuántas veces se repite cada letra."},
    {"herramienta": "T7", "encargo": "Invierte el orden de las palabras de «uno dos tres»."},
    {"herramienta": "T8", "encargo": "Cuenta cuántas vocales hay en «murciélago»."},
    {"herramienta": "T9", "encargo": "Redondea 3.14159 a tres decimales."},
    {"herramienta": "T10", "encargo": "Dime cuántos días tiene el mes de febrero de 2028."},
    {"herramienta": "T11", "encargo": "Pasa 45 grados a radianes."},
    {"herramienta": "T12", "encargo": "Cuenta cuántas palabras empiezan con la letra «c» en «casa perro cama gato cielo»."},
    {"herramienta": "T13", "encargo": "Convierte a mayúsculas la frase «hola mundo»."},
    {"herramienta": "T14", "encargo": "Suma los números 3, 8 y 14."},
    {"herramienta": "T15", "encargo": "Dime el resto de dividir 17 entre 5."},
    {"herramienta": "T16", "encargo": "Genera el doble de 21 y luego súmale 7."},
    {"herramienta": "T17", "encargo": "Separa en líneas la frase «uno dos tres»."},
    {"herramienta": "T18", "encargo": "Calcula el 15 por ciento de 240."},
    {"herramienta": "T19", "encargo": "Dime cuál es el número mayor entre 4, 19 y 7."},
]

# Descripciones escritas para ser inequívocas: cada una dice exactamente lo que
# hace y nada más. Si fueran ambiguas, el experimento mediría la ambigüedad del
# enunciado en vez de la saturación del modelo.
DESCRIPCIONES = {
    "T0": "Convierte una cantidad de pesos chilenos a dólares estadounidenses.",
    "T1": "Cuenta el número de palabras de un texto.",
    "T2": "Devuelve el día de la semana de una fecha concreta.",
    "T3": "Genera un código de color hexadecimal a partir de un nombre.",
    "T4": "Calcula la raíz cuadrada de un número con decimales.",
    "T5": "Ordena alfabéticamente una lista de palabras.",
    "T6": "Comprime un texto indicando cuántas veces se repite cada letra.",
    "T7": "Invierte el orden de las palabras de una frase.",
    "T8": "Cuenta cuántas vocales hay en una palabra.",
    "T9": "Redondea un número decimal a menos decimales.",
    "T10": "Dice cuántos días tiene un mes de un año concreto.",
    "T11": "Convierte grados a radianes.",
    "T12": "Cuenta cuántas palabras de una frase empiezan con una letra dada.",
    "T13": "Convierte un texto a mayúsculas.",
    "T14": "Suma una lista de números.",
    "T15": "Calcula el resto de una división entera.",
    "T16": "Duplica un número y le suma otro valor.",
    "T17": "Separa una frase en líneas distintas.",
    "T18": "Calcula un porcentaje de una cantidad.",
    "T19": "Devuelve el número mayor de una lista.",
}


def _fabricar(nombre: str) -> Herramienta:
    """Crea una herramienta que devuelve su propio nombre al ser llamada."""

    def ejecutar(**_) -> str:
        return f"RESULTADO_DE_{nombre}"

    return Herramienta(
        nombre=nombre,
        descripcion=DESCRIPCIONES[nombre],
        parametros={"entrada": "string"},
        funcion=ejecutar,
    )


def _medalla() -> Medalla:
    return Medalla(
        nombre="benchmark de piezas",
        version="0",
        descripcion="Mide la elección de herramientas.",
        persona=(
            "Tienes herramientas y debes usar exactamente la que corresponda al "
            "encargo. Llama a una sola herramienta, la correcta. No respondas de "
            "memoria si existe una herramienta que hace ese trabajo."
        ),
    )


@dataclass
class Resultado:
    herramientas: int
    aciertos: int = 0
    intentos: int = 0
    tokens_entrada: int = 0
    tokens_salida: int = 0
    segundos: float = 0.0
    fallos: list[str] = field(default_factory=list)

    @property
    def precision(self) -> float:
        return self.aciertos / self.intentos if self.intentos else 0.0

    @property
    def tokens_por_intento(self) -> float:
        return self.tokens_entrada / self.intentos if self.intentos else 0.0


def ejecutar(niveles: list[int], repeticiones: int, pausa: float = 0.0) -> list[Resultado]:
    ajustes = Ajustes.desde_entorno()
    resultados: list[Resultado] = []

    for n in niveles:
        pieza = Pieza(
            nombre=f"sintetica_{n}",
            version="0",
            descripcion=f"{n} herramientas de prueba.",
            herramientas=[_fabricar(f"T{i}") for i in range(n)],
        )
        resultado = Resultado(herramientas=n)
        tareas = [t for t in TAREAS if int(t["herramienta"][1:]) < n]

        for _ in range(repeticiones):
            for tarea in tareas:
                agente = Agente(_medalla(), [pieza], ajustes)
                inicio = time.monotonic()
                try:
                    turno = agente.ejecutar(tarea["encargo"], max_pasos=2)
                except Exception as e:  # noqa: BLE001 - un fallo del proveedor no invalida el resto
                    resultado.intentos += 1
                    resultado.fallos.append(f"{tarea['herramienta']}: ERROR {type(e).__name__}")
                    continue
                resultado.segundos += time.monotonic() - inicio
                resultado.intentos += 1
                resultado.tokens_entrada += turno.tokens_entrada
                resultado.tokens_salida += turno.tokens_salida

                usadas = turno.uso_herramientas
                if usadas and usadas[0] == tarea["herramienta"]:
                    resultado.aciertos += 1
                else:
                    elegida = usadas[0] if usadas else "(ninguna)"
                    resultado.fallos.append(
                        f"{tarea['herramienta']} -> {elegida}")
                if pausa:
                    time.sleep(pausa)

        resultados.append(resultado)
        print(f"  {n:>2} herramientas: {resultado.aciertos}/{resultado.intentos} "
              f"({resultado.precision:.0%}), "
              f"{resultado.tokens_por_intento:,.0f} tokens/intento", flush=True)

    return resultados


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Mide la elección de herramientas según cuántas haya.")
    p.add_argument("--niveles", default="4,8,12,16",
                   help="Cantidades de herramientas a probar, separadas por coma.")
    p.add_argument("--repeticiones", type=int, default=1)
    p.add_argument("--pausa", type=float, default=0.0)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    niveles = [int(x) for x in args.niveles.split(",") if x.strip()]
    ajustes = Ajustes.desde_entorno()
    print(f"Modelo: {ajustes.modelo}")
    print(f"Niveles: {niveles} · repeticiones: {args.repeticiones}\n")

    resultados = ejecutar(niveles, args.repeticiones, args.pausa)

    print("\n" + "=" * 62)
    print(f"{'herramientas':>13} {'aciertos':>10} {'precisión':>11} {'tokens/int':>12}")
    for r in resultados:
        print(f"{r.herramientas:>13} {r.aciertos:>4}/{r.intentos:<5} "
              f"{r.precision:>10.0%} {r.tokens_por_intento:>12,.0f}")

    if args.json:
        print("\n" + json.dumps([r.__dict__ for r in resultados], ensure_ascii=False, indent=2))

    fallos = [f for r in resultados for f in r.fallos]
    if fallos:
        print(f"\nErrores de elección ({len(fallos)}):")
        for f in fallos[:20]:
            print(f"  {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
