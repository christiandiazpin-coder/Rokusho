"""Banco de pruebas: ¿el modelo elige bien la herramienta cuando hay muchas?

Qué mide, y qué NO: el banco anterior mezclaba dos preguntas distintas —
«¿elige bien entre N opciones?» y «¿decide usar una herramienta?». Se descubrió
porque los fallos eran del tipo «no llamó a ninguna» en tareas que el modelo
podía resolver de memoria (redondear 3.14159, generar un color).

Este banco elimina esa contaminación con un truco simple: **los datos se generan
al azar en cada ejecución** y no existen en ningún otro lugar. El modelo no puede
saberlos. Si acierta, fue porque llamó a la herramienta correcta; si responde de
memoria, falla. Solo hay una forma de acertar.

Diseño:

1. Se crea un archivo de datos con claves y valores aleatorios.
2. Cada herramienta `consultar_N` lee **una clave concreta** de ese archivo y
   devuelve un valor. Ninguna puede responder nada sin leer.
3. Se le pide al modelo el valor de una clave. Solo una herramienta la tiene.
4. Se comprueba a cuál llamó. Además se verifica que el valor que reporta sea el
   real, para detectar el caso de «llamó bien pero inventó el número».

Uso:
    python -m benchmarks.piezas --niveles 4,8,12,16,20 --repeticiones 2
"""

from __future__ import annotations

import argparse
import json
import random
import string
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chasis.agente import Agente  # noqa: E402
from chasis.config import Ajustes  # noqa: E402
from chasis.medalla import Medalla  # noqa: E402
from chasis.pieza import Herramienta, Pieza  # noqa: E402

MAX_NIVEL = 20


def _valor_aleatorio(rng: random.Random) -> str:
    """Un valor que no existe en el conocimiento del modelo ni en el prompt."""
    letras = "".join(rng.choices(string.ascii_uppercase, k=3))
    digitos = "".join(rng.choices(string.digits, k=5))
    return f"{letras}-{digitos}"


def _fabricar_entorno(rng: random.Random) -> dict[str, str]:
    """Crea los datos. Solo viven en esta ejecución y en el archivo en disco."""
    return {f"clave_{i}": _valor_aleatorio(rng) for i in range(MAX_NIVEL)}


def _fabricar_herramienta(nombre: str, clave: str, datos: dict[str, str],
                          ruta: Path) -> Herramienta:
    """Una herramienta que solo sabe leer SU clave del archivo."""

    def consultar(**_) -> str:
        # Se relee el archivo en cada llamada: así la herramienta no puede
        # responder nada que no esté en disco.
        try:
            contenido = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            return f"ERROR: no se pudo leer el registro de datos: {e}"
        if clave not in contenido:
            return f"ERROR: la clave «{clave}» no está en el registro."
        return f"El valor de {clave} es {contenido[clave]}"

    return Herramienta(
        nombre=nombre,
        descripcion=(f"Consulta el valor registrado de la clave «{clave}» "
                     f"en el registro interno. Devuelve el valor exacto."),
        parametros={},
        funcion=consultar,
    )


def _medalla() -> Medalla:
    return Medalla(
        nombre="benchmark de selección",
        version="0",
        descripcion="Mide la elección de herramienta.",
        persona=(
            "Tu única fuente de verdad son las herramientas. Los valores que se "
            "te piden solo existen dentro de ellas: no los conoces de antemano y "
            "no puedes deducirlos. Debes llamar a la herramienta que corresponde "
            "a la clave pedida. Si respondes sin llamar, estarás inventando el "
            "valor."
        ),
    )


@dataclass
class Resultado:
    herramientas: int
    aciertos: int = 0
    llamo_bien: int = 0
    intentos: int = 0
    tokens_entrada: int = 0
    tokens_salida: int = 0
    segundos: float = 0.0
    fallos: list[str] = field(default_factory=list)

    @property
    def precision(self) -> float:
        return self.aciertos / self.intentos if self.intentos else 0.0

    @property
    def seleccion(self) -> float:
        """Solo mide si eligió la herramienta correcta, sin juzgar el valor."""
        return self.llamo_bien / self.intentos if self.intentos else 0.0

    @property
    def tokens_por_intento(self) -> float:
        return self.tokens_entrada / self.intentos if self.intentos else 0.0


def ejecutar(niveles: list[int], repeticiones: int, pausa: float = 0.0,
             semilla: int | None = None) -> list[Resultado]:
    ajustes = Ajustes.desde_entorno()
    resultados: list[Resultado] = []
    carpeta = Path("/tmp/rokusho-bench-piezas")
    carpeta.mkdir(parents=True, exist_ok=True)

    for n in niveles:
        n = min(n, MAX_NIVEL)
        resultado = Resultado(herramientas=n)

        for rep in range(repeticiones):
            # Datos nuevos en cada repetición: si se repitieran, el modelo
            # podría recordar el valor de la vez anterior.
            rng = random.Random((semilla or 0) * 1000 + n * 10 + rep)
            datos = _fabricar_entorno(rng)
            ruta = carpeta / f"datos_{n}_{rep}.json"
            ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")

            herramientas = [
                _fabricar_herramienta(f"consultar_{i}", f"clave_{i}", datos, ruta)
                for i in range(n)
            ]
            pieza = Pieza(nombre=f"registro_{n}", version="0",
                          descripcion=f"Registro interno con {n} claves.",
                          herramientas=herramientas)

            for indice in range(n):
                clave = f"clave_{indice}"
                esperado = datos[clave]
                agente = Agente(_medalla(), [pieza], ajustes)
                inicio = time.monotonic()
                try:
                    turno = agente.ejecutar(
                        f"¿Cuál es el valor registrado de «{clave}»? Dame el valor exacto.",
                        max_pasos=2)
                except Exception as e:  # noqa: BLE001 - un fallo del proveedor no invalida el resto
                    resultado.intentos += 1
                    resultado.fallos.append(f"{clave}: ERROR {type(e).__name__}")
                    continue

                resultado.segundos += time.monotonic() - inicio
                resultado.intentos += 1
                resultado.tokens_entrada += turno.tokens_entrada
                resultado.tokens_salida += turno.tokens_salida

                usadas = turno.uso_herramientas
                correcta = f"consultar_{indice}"
                eligio_bien = bool(usadas) and usadas[0] == correcta
                if eligio_bien:
                    resultado.llamo_bien += 1

                # Acierto completo: eligió bien Y el valor que reporta es el real.
                reporto_bien = esperado in turno.respuesta
                if eligio_bien and reporto_bien:
                    resultado.aciertos += 1
                else:
                    motivo = ("no llamó" if not usadas
                              else f"llamó a {usadas[0]}" if not eligio_bien
                              else "llamó bien pero no reportó el valor")
                    resultado.fallos.append(
                        f"{clave} (esperaba {esperado}) -> {motivo}")

                if pausa:
                    time.sleep(pausa)

        resultados.append(resultado)
        print(f"  {n:>2} herramientas: elección {resultado.llamo_bien}/{resultado.intentos} "
              f"({resultado.seleccion:.0%}) · acierto total {resultado.aciertos}/{resultado.intentos} "
              f"({resultado.precision:.0%}) · {resultado.tokens_por_intento:,.0f} tok/intento",
              flush=True)

    return resultados


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Mide la selección de herramientas con datos imposibles de saber.")
    p.add_argument("--niveles", default="4,8,12,16,20")
    p.add_argument("--repeticiones", type=int, default=1)
    p.add_argument("--pausa", type=float, default=0.0)
    p.add_argument("--semilla", type=int, default=None)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    niveles = [int(x) for x in args.niveles.split(",") if x.strip()]
    print(f"Modelo: {Ajustes.desde_entorno().modelo}")
    print("Los valores de las claves son aleatorios: el modelo no puede saberlos")
    print("sin llamar a la herramienta, así que un fallo no puede ser de memoria.")
    print(f"Niveles: {niveles} · repeticiones: {args.repeticiones}\n")

    resultados = ejecutar(niveles, args.repeticiones, args.pausa, args.semilla)

    print("\n" + "=" * 74)
    print(f"{'herramientas':>13} {'elección':>12} {'acierto total':>16} {'tok/int':>10}")
    for r in resultados:
        print(f"{r.herramientas:>13} {r.seleccion:>11.0%} "
              f"{r.precision:>16.0%} {r.tokens_por_intento:>10,.0f}")

    if args.json:
        print("\n" + json.dumps([r.__dict__ for r in resultados], ensure_ascii=False, indent=2))

    fallos = [f for r in resultados for f in r.fallos]
    if fallos:
        print(f"\nFallos ({len(fallos)}):")
        for f in fallos[:25]:
            print(f"  {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
