"""Banco de pruebas: ¿se degrada la elección cuando las herramientas se parecen?

El banco anterior demostró que con 20 herramientas bien distintas el modelo acierta
el 100%. Pero no podía detectar degradación: el 100% en todos los niveles no
distingue «muy bueno» de «perfecto».

Este banco aísla la variable. **El número de herramientas es siempre el mismo**;
lo único que cambia es cuánto se parecen entre sí. Si la precisión cae al pasar de
distintas a parecidas, la causa es la confusibilidad y no el tamaño.

Tres condiciones, con el mismo N y las mismas tareas:

1. **distintas** — nombres y descripciones que no comparten nada.
2. **parecidas** — nombres que difieren en un sufijo; descripciones casi iguales.
   Es el caso real: `leer_archivo_local` frente a `leer_archivo_remoto`.
3. **distractores** — la herramienta correcta está, pero la mitad de las demás
   son plausibles y no sirven para la tarea.

Los datos siguen siendo aleatorios, así que un fallo no puede ser «respondió de
memoria».

Uso:
    python -m benchmarks.piezas_confusables --n 8 --repeticiones 2
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

# Raíces temáticas para la condición «distintas»: ningún parecido entre sí.
TEMAS_DISTINTOS = [
    ("clima", "Consulta la temperatura registrada en una ciudad."),
    ("distancia", "Calcula la distancia entre dos puntos geográficos."),
    ("peso", "Devuelve el peso registrado de un paquete."),
    ("volumen", "Calcula el volumen de un contenedor."),
    ("color", "Devuelve el código de color de una marca."),
    ("idioma", "Detecta el idioma de un texto."),
    ("moneda", "Convierte un monto entre dos divisas."),
    ("hora", "Devuelve la hora local de una zona horaria."),
    ("sabor", "Consulta el perfil de sabor de un ingrediente."),
    ("textura", "Devuelve la textura asignada a un material."),
    ("sonido", "Consulta el nivel de ruido de un entorno."),
    ("olor", "Devuelve la descripción olfativa de una muestra."),
    ("dureza", "Consulta la dureza de un mineral."),
    ("brillo", "Devuelve el brillo medido de una superficie."),
    ("tacto", "Consulta la sensación táctil de un tejido."),
    ("sabor2", "Devuelve el regusto de una bebida."),
]

# Familia de nombres que solo difieren en el sufijo. Es la condición realista:
# en un Rokusho con varias piezas, dos herramientas pueden llamarse casi igual.
SUFIJOS_PARECIDOS = [
    ("local", "Lee el registro guardado en el equipo local."),
    ("remoto", "Lee el registro guardado en el servidor remoto."),
    ("temporal", "Lee el registro guardado en el almacenamiento temporal."),
    ("historico", "Lee el registro guardado en el archivo histórico."),
    ("respaldo", "Lee el registro guardado en la copia de respaldo."),
    ("cache", "Lee el registro guardado en la caché."),
    ("externo", "Lee el registro guardado en un medio externo."),
    ("interno", "Lee el registro guardado en el almacenamiento interno."),
    ("compartido", "Lee el registro guardado en la carpeta compartida."),
    ("privado", "Lee el registro guardado en la carpeta privada."),
    ("publico", "Lee el registro guardado en la carpeta pública."),
    ("archivado", "Lee el registro guardado en la carpeta archivada."),
    ("sincronizado", "Lee el registro guardado en la carpeta sincronizada."),
    ("protegido", "Lee el registro guardado en la carpeta protegida."),
    ("migrado", "Lee el registro guardado en la carpeta migrada."),
    ("importado", "Lee el registro guardado en la carpeta importada."),
]

# Nombres plausibles que no sirven para la tarea pedida: los distractores.
DISTRACTORES = [
    ("calcular_media", "Calcula el promedio de una lista de números."),
    ("formatear_fecha", "Convierte una fecha a otro formato."),
    ("contar_palabras", "Cuenta las palabras de un texto."),
    ("ordenar_lista", "Ordena alfabéticamente una lista."),
    ("convertir_mayusculas", "Convierte un texto a mayúsculas."),
    ("validar_correo", "Comprueba si un correo tiene formato válido."),
    ("generar_hash", "Calcula el hash de un texto."),
    ("redondear", "Redondea un número a menos decimales."),
    ("sumar_total", "Suma los valores de una columna."),
    ("buscar_duplicados", "Encuentra elementos repetidos en una lista."),
]


def _valor(rng: random.Random) -> str:
    return ("".join(rng.choices(string.ascii_uppercase, k=3)) + "-"
            + "".join(rng.choices(string.digits, k=5)))


@dataclass
class Conjunto:
    """Un juego de herramientas para una condición."""

    condicion: str
    nombre_clave: str          # la clave pedida
    herramienta_correcta: str  # el nombre que debe elegir
    herramientas: list[Herramienta]
    valor_esperado: str


def _crear_herramienta(nombre: str, descripcion: str, clave: str,
                       ruta: Path) -> Herramienta:
    """La descripción DEBE decir qué clave lee.

    Sin eso, el modelo no tiene forma de saber cuál herramienta corresponde a la
    clave pedida: elegiría al azar. Un banco así mide suerte, no confusibilidad.
    En la primera versión de este archivo faltaba, y el resultado (0 % en dos
    condiciones) no medía nada del modelo.
    """
    def consultar(**_) -> str:
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            return f"ERROR: no se pudo leer el registro: {e}"
        if clave not in datos:
            return f"ERROR: la clave «{clave}» no está en el registro."
        return f"El valor de {clave} es {datos[clave]}"

    return Herramienta(nombre=nombre,
                       descripcion=f"{descripcion} Devuelve el valor de la clave «{clave}».",
                       parametros={}, funcion=consultar)


def _conjunto_distintas(n: int, rng: random.Random, carpeta: Path) -> Conjunto:
    """Nombres y descripciones sin ningún parecido entre sí."""
    datos = {f"clave_{i}": _valor(rng) for i in range(n)}
    ruta = carpeta / f"distintas_{n}.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")

    herramientas = []
    for i, (tema, desc) in enumerate(TEMAS_DISTINTOS[:n]):
        herramientas.append(_crear_herramienta(
            f"consultar_{tema}", desc, f"clave_{i}", ruta))

    # Si el objetivo siempre fuera el primero, se podría acertar por posición
    # en vez de por significado. Se elige una posición central al azar.
    indice = rng.randrange(len(herramientas) // 2, len(herramientas))
    return Conjunto("distintas", f"clave_{indice}", herramientas[indice].nombre,
                    herramientas, datos[f"clave_{indice}"])


def _conjunto_parecidas(n: int, rng: random.Random, carpeta: Path) -> Conjunto:
    """Mismo prefijo, sufijo distinto. Descripciones casi idénticas."""
    datos = {f"clave_{i}": _valor(rng) for i in range(n)}
    ruta = carpeta / f"parecidas_{n}.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")

    herramientas = []
    for i, (sufijo, desc) in enumerate(SUFIJOS_PARECIDOS[:n]):
        herramientas.append(_crear_herramienta(
            f"leer_registro_{sufijo}", desc, f"clave_{i}", ruta))

    # La clave pedida es la del sufijo «historico», no la primera: pedir siempre
    # la primera permitiría acertar por posición en vez de por significado.
    objetivo = next(i for i, (s, _) in enumerate(SUFIJOS_PARECIDOS[:n])
                    if s == "historico")
    return Conjunto("parecidas", f"clave_{objetivo}", herramientas[objetivo].nombre,
                    herramientas, datos[f"clave_{objetivo}"])


def _conjunto_distractores(n: int, rng: random.Random, carpeta: Path) -> Conjunto:
    """La correcta está, pero el resto suena plausible y no sirve."""
    datos = {f"clave_{i}": _valor(rng) for i in range(n)}
    ruta = carpeta / f"distractores_{n}.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")

    # La herramienta correcta se llama de forma neutra, para que no destaque
    # ni por nombre ni por posición.
    correcta = _crear_herramienta(
        "leer_registro_maestro", "Lee el registro maestro de valores guardados.",
        "clave_0", ruta)

    otras = []
    for i, (nombre, desc) in enumerate(DISTRACTORES[:n - 1], start=1):
        if i >= n:
            break
        otras.append(_crear_herramienta(nombre, desc, f"clave_{i}", ruta))

    # La correcta se inserta en una posición central al azar: si fuera siempre
    # la primera, la posición sería una pista.
    herramientas = list(otras)
    indice = rng.randrange(len(herramientas) // 2, len(herramientas) + 1)
    herramientas.insert(indice, correcta)
    return Conjunto("distractores", "clave_0", "leer_registro_maestro",
                    herramientas, datos["clave_0"])


GENERADORES = {
    "distintas": _conjunto_distintas,
    "parecidas": _conjunto_parecidas,
    "distractores": _conjunto_distractores,
}


def _medalla() -> Medalla:
    return Medalla(
        nombre="benchmark de confusibilidad",
        version="0",
        descripcion="Mide la elección con herramientas parecidas.",
        persona=(
            "Tu única fuente de verdad son las herramientas. Los valores que se "
            "te piden solo existen dentro de una de ellas: no los conoces de "
            "antemano. Lee con cuidado la descripción de cada herramienta y elige "
            "exactamente la que corresponde a la clave pedida. Varias pueden "
            "parecerse; solo una tiene esa clave."
        ),
    )


@dataclass
class Resultado:
    condicion: str
    herramientas: int
    aciertos: int = 0
    intentos: int = 0
    tokens_entrada: int = 0
    segundos: float = 0.0
    fallos: list[str] = field(default_factory=list)

    @property
    def precision(self) -> float:
        return self.aciertos / self.intentos if self.intentos else 0.0


def ejecutar(n: int, repeticiones: int, pausa: float = 0.0) -> list[Resultado]:
    ajustes = Ajustes.desde_entorno()
    carpeta = Path("/tmp/rokusho-bench-confusables")
    carpeta.mkdir(parents=True, exist_ok=True)
    resultados: list[Resultado] = []

    for condicion, generador in GENERADORES.items():
        resultado = Resultado(condicion, n)
        for rep in range(repeticiones):
            # Semilla determinista: hash() de texto cambia en cada proceso
            # (PYTHONHASHSEED), y un benchmark que no se puede repetir no vale.
            semilla = sum(ord(c) for c in condicion) * 1000 + n * 10 + rep
            rng = random.Random(semilla)
            conjunto = generador(n, rng, carpeta)
            pieza = Pieza(nombre=f"{condicion}_{n}", version="0",
                          descripcion=f"Registro ({condicion}).",
                          herramientas=conjunto.herramientas)

            agente = Agente(_medalla(), [pieza], ajustes)
            inicio = time.monotonic()
            try:
                turno = agente.ejecutar(
                    f"¿Cuál es el valor registrado de «{conjunto.nombre_clave}»? "
                    "Dame el valor exacto.", max_pasos=2)
            except Exception as e:  # noqa: BLE001
                resultado.intentos += 1
                resultado.fallos.append(f"rep{rep}: ERROR {type(e).__name__}")
                continue

            resultado.segundos += time.monotonic() - inicio
            resultado.intentos += 1
            resultado.tokens_entrada += turno.tokens_entrada

            usadas = turno.uso_herramientas
            eligio = bool(usadas) and usadas[0] == conjunto.herramienta_correcta
            reporto = conjunto.valor_esperado in turno.respuesta
            if eligio and reporto:
                resultado.aciertos += 1
            else:
                motivo = ("no llamó" if not usadas
                          else f"llamó a {usadas[0]}" if not eligio
                          else "llamó bien pero no reportó el valor")
                resultado.fallos.append(
                    f"rep{rep}: esperaba {conjunto.herramienta_correcta} -> {motivo}")
            if pausa:
                time.sleep(pausa)

        resultados.append(resultado)
        print(f"  {condicion:<14} {resultado.aciertos}/{resultado.intentos} "
              f"({resultado.precision:.0%}) · "
              f"{resultado.tokens_entrada / max(1, resultado.intentos):,.0f} tok/intento",
              flush=True)

    return resultados


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Mide la elección con herramientas parecidas, con N fijo.")
    p.add_argument("--n", type=int, default=8,
                   help="Número de herramientas (igual en las tres condiciones).")
    p.add_argument("--repeticiones", type=int, default=2)
    p.add_argument("--pausa", type=float, default=0.0)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    print(f"Modelo: {Ajustes.desde_entorno().modelo}")
    print(f"N herramientas: {args.n} (igual en las tres condiciones)")
    print("Solo cambia cuánto se parecen entre sí. Los valores son aleatorios.\n")

    resultados = ejecutar(args.n, args.repeticiones, args.pausa)

    print("\n" + "=" * 60)
    print(f"{'condición':<16} {'aciertos':>10} {'precisión':>12}")
    for r in resultados:
        print(f"{r.condicion:<16} {r.aciertos:>4}/{r.intentos:<5} {r.precision:>11.0%}")

    if args.json:
        print("\n" + json.dumps([r.__dict__ for r in resultados], ensure_ascii=False, indent=2))

    fallos = [f for r in resultados for f in r.fallos]
    if fallos:
        print(f"\nFallos ({len(fallos)}):")
        for f in fallos[:20]:
            print(f"  {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
