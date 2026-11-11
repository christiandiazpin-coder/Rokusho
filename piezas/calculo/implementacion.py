"""Pieza «calculo»: aritmética exacta, sin preguntársela al modelo.

Por qué existe: un modelo de lenguaje se equivoca en cuentas y lo afirma con la
misma seguridad que cuando acierta. No hay forma de saber, mirando el texto, si
un resultado es correcto. Esta pieza no le pide cuentas al modelo: las ejecuta.

Seguridad: la expresión la escribe un modelo, que a su vez lee documentos de un
cliente. Por eso NO se usa `eval`. Se recorre el árbol sintáctico con una lista
blanca de nodos: si aparece algo que no está permitido (una llamada, un atributo,
una variable, un import), se rechaza. Un `eval` aquí sería una puerta abierta
para ejecutar código arbitrario desde un documento manipulado.

Decimales: se usa `Decimal` y no `float` para el dinero. Con float, 0.1 + 0.2 no
da 0.3, y un informe con centavos mal sumados destruye la confianza más rápido
que cualquier otra cosa.
"""

from __future__ import annotations

import ast
import math
import operator
import re
from datetime import date, timedelta
from decimal import Decimal, DivisionByZero, InvalidOperation, getcontext

# Precisión alta: 28 dígitos por defecto se queda corto con montos grandes.
getcontext().prec = 40

MAX_EXPRESION = 500
MAX_POTENCIA = 1000  # evita 9**9**9 y similares

# Lista blanca de operadores binarios.
_BINARIOS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

# Lista blanca de operadores unarios.
_UNARIOS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Funciones permitidas, con su aridad.
_FUNCIONES = {
    "sqrt": (math.sqrt, 1, 1),
    "abs": (abs, 1, 1),
    "round": (round, 1, 2),
    "min": (min, 1, 20),
    "max": (max, 1, 20),
    "floor": (math.floor, 1, 1),
    "ceil": (math.ceil, 1, 1),
}

CONSTANTES = {
    "pi": Decimal(str(math.pi)),
    "e": Decimal(str(math.e)),
}


class ExpresionInvalida(ValueError):
    """La expresión no es aritmética válida o no está permitida."""


def configurar(carpeta=None) -> None:
    """La pieza no necesita espacio de trabajo; existe por simetría."""
    return None


def _decimal(valor) -> Decimal:
    """Convierte a Decimal cuidando el caso del float (que ya trae su error)."""
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, bool):
        raise ExpresionInvalida("no se admiten valores booleanos")
    if isinstance(valor, int):
        return Decimal(valor)
    if isinstance(valor, float):
        # str() antes que Decimal() para no arrastrar el error binario.
        return Decimal(str(valor))
    raise ExpresionInvalida(f"valor no numérico: {type(valor).__name__}")


def _evaluar(nodo: ast.AST):
    """Recorre el árbol permitiendo solo aritmética. Nada de llamadas arbitrarias."""
    if isinstance(nodo, ast.Expression):
        return _evaluar(nodo.body)

    if isinstance(nodo, ast.Constant):
        if isinstance(nodo.value, bool) or not isinstance(nodo.value, (int, float)):
            raise ExpresionInvalida(
                f"solo se admiten números; se encontró {type(nodo.value).__name__}")
        return _decimal(nodo.value)

    if isinstance(nodo, ast.BinOp):
        tipo = type(nodo.op)
        if tipo not in _BINARIOS:
            raise ExpresionInvalida(f"operador no permitido: {tipo.__name__}")
        izquierda = _evaluar(nodo.left)
        derecha = _evaluar(nodo.right)
        if tipo is ast.Pow:
            # Un exponente enorme cuelga el proceso.
            if derecha > MAX_POTENCIA:
                raise ExpresionInvalida(
                    f"exponente demasiado grande ({derecha}); el máximo es {MAX_POTENCIA}")
        if tipo in (ast.Div, ast.FloorDiv, ast.Mod) and derecha == 0:
            raise ExpresionInvalida("división por cero")
        return _decimal(_BINARIOS[tipo](izquierda, derecha))

    if isinstance(nodo, ast.UnaryOp):
        tipo = type(nodo.op)
        if tipo not in _UNARIOS:
            raise ExpresionInvalida(f"operador unario no permitido: {tipo.__name__}")
        return _decimal(_UNARIOS[tipo](_evaluar(nodo.operand)))

    if isinstance(nodo, ast.Name):
        if nodo.id in CONSTANTES:
            return CONSTANTES[nodo.id]
        raise ExpresionInvalida(
            f"«{nodo.id}» no es una constante conocida. Solo se admite: "
            f"{', '.join(sorted(CONSTANTES))}")

    if isinstance(nodo, ast.Call):
        if not isinstance(nodo.func, ast.Name):
            raise ExpresionInvalida("solo se pueden llamar funciones por su nombre")
        nombre = nodo.func.id
        if nombre not in _FUNCIONES:
            raise ExpresionInvalida(
                f"función no permitida: «{nombre}». Disponibles: "
                f"{', '.join(sorted(_FUNCIONES))}")
        if nodo.keywords:
            raise ExpresionInvalida("no se admiten argumentos con nombre")
        # Los nombres son «aridad_min»/«aridad_max» y no «minimo»/«maximo» a
        # propósito: con el nombre «maximo» se sombreaba la función max() de
        # Python dentro de esta misma función, y min(5,2,8) fallaba.
        funcion, aridad_min, aridad_max = _FUNCIONES[nombre]
        if not aridad_min <= len(nodo.args) <= aridad_max:
            raise ExpresionInvalida(
                f"«{nombre}» espera entre {aridad_min} y {aridad_max} argumentos")
        argumentos = [_evaluar(a) for a in nodo.args]
        if nombre in ("min", "max"):
            # Se desempaqueta la lista: min([5,2,8]) daría un solo argumento
            # y devolvería la lista entera en vez del mínimo.
            return _decimal(funcion(*argumentos))
        if nombre == "round":
            # round() de Python no acepta Decimal como número de decimales.
            if len(argumentos) > 1:
                return _decimal(round(argumentos[0], int(argumentos[1])))
            return _decimal(round(argumentos[0]))
        return _decimal(funcion(*argumentos))

    if isinstance(nodo, (ast.Attribute, ast.Subscript, ast.Lambda, ast.Dict,
                         ast.List, ast.Set, ast.Tuple, ast.Compare, ast.BoolOp,
                         ast.IfExp, ast.JoinedStr, ast.Starred, ast.Await,
                         ast.NamedExpr)):
        raise ExpresionInvalida(
            f"no se permite «{type(nodo).__name__}»: la expresión debe ser "
            "aritmética pura")

    raise ExpresionInvalida(f"no se permite «{type(nodo).__name__}»")


def _formatear(valor: Decimal) -> str:
    """Presenta el número sin notación científica y sin ceros de relleno."""
    if valor == valor.to_integral_value():
        return f"{int(valor):,}"
    texto = format(valor.normalize(), "f")
    entero, _, decimales = texto.partition(".")
    signo = ""
    if entero.startswith("-"):
        signo, entero = "-", entero[1:]
    entero = f"{int(entero):,}" if entero else "0"
    decimales = decimales.rstrip("0")
    return f"{signo}{entero}.{decimales}" if decimales else f"{signo}{entero}"


def calcular(expresion: str) -> str:
    if not expresion or not expresion.strip():
        return "ERROR: no diste ninguna expresión."
    if len(expresion) > MAX_EXPRESION:
        return (f"ERROR: la expresión tiene {len(expresion)} caracteres y el límite "
                f"es {MAX_EXPRESION}.")

    limpia = expresion.strip()
    # Se quitan las comas de miles SOLO cuando separan grupos de tres dígitos
    # dentro de un mismo número: 1,500,000 → 1500000.
    #
    # Antes se quitaban todas las comas de la expresión, y eso rompía cualquier
    # llamada con varios argumentos: «min(5,2,8)» se convertía en «min(528)» y
    # devolvía 528 en vez de 2. Un separador de argumentos no es un separador
    # de miles.
    limpia = re.sub(r"(?<=\d),(?=\d{3}\b)", "", limpia)

    try:
        arbol = ast.parse(limpia, mode="eval")
    except SyntaxError as e:
        return (f"ERROR: la expresión «{expresion}» no es válida como aritmética "
                f"({e.msg}). Usa solo números y operadores.")

    try:
        resultado = _evaluar(arbol)
    except ExpresionInvalida as e:
        return f"ERROR: {e}"
    except (ZeroDivisionError, DivisionByZero):
        return "ERROR: división por cero."
    except (InvalidOperation, OverflowError, ValueError) as e:
        return f"ERROR: no se pudo calcular ({type(e).__name__}: {e})"

    if resultado.is_nan() or resultado.is_infinite():
        return f"ERROR: el resultado no es un número finito ({resultado})."

    return (
        f"{expresion.strip()} = {_formatear(resultado)}\n"
        f"  exacto: {resultado}\n"
        f"  (calculado con aritmética decimal, no por el modelo)"
    )


def porcentaje(operacion: str, a: float, b: float) -> str:
    op = (operacion or "").strip().lower()
    try:
        da, db = _decimal(a), _decimal(b)
    except ExpresionInvalida as e:
        return f"ERROR: {e}"

    if op in ("de", "porcentaje_de", "cuanto_es"):
        if db == 0:
            return "ERROR: el porcentaje sobre cero no está definido."
        r = da * db / Decimal(100)
        return f"{_formatear(da)}% de {_formatear(db)} = {_formatear(r)}"

    if op in ("que_porcentaje", "representa", "sobre"):
        if db == 0:
            return "ERROR: no se puede calcular el porcentaje sobre un total de cero."
        r = da * Decimal(100) / db
        return (f"{_formatear(da)} sobre {_formatear(db)} = {_formatear(r)}%\n"
                f"  exacto: {r}")

    if op in ("variacion", "cambio"):
        if db == 0:
            return "ERROR: no hay variación posible desde un valor inicial de cero."
        r = (da - db) * Decimal(100) / db
        signo = "aumento" if r > 0 else "disminución" if r < 0 else "sin cambio"
        return (f"De {_formatear(db)} a {_formatear(da)}: {signo} de "
                f"{_formatear(abs(r))}%\n  exacto: {r}")

    return (f"ERROR: operación «{operacion}» no reconocida. Usa: "
            "«de» (a% de b), «que_porcentaje» (qué % es a de b) "
            "o «variacion» (cambio de b a a).")


def estadistica(valores: str) -> str:
    if not valores or not valores.strip():
        return "ERROR: no diste ningún valor."
    crudos = [v.strip() for v in valores.replace(";", ",").split(",") if v.strip()]
    numeros: list[Decimal] = []
    for c in crudos:
        try:
            numeros.append(_decimal(float(c)))
        except (ValueError, ExpresionInvalida):
            return f"ERROR: «{c}» no es un número."

    if not numeros:
        return "ERROR: no hay números válidos en la lista."

    n = len(numeros)
    ordenados = sorted(numeros)
    total = sum(numeros)
    media = total / n
    if n % 2:
        mediana = ordenados[n // 2]
    else:
        mediana = (ordenados[n // 2 - 1] + ordenados[n // 2]) / 2
    varianza = sum((x - media) ** 2 for x in numeros) / n

    return (
        f"Estadística de {n} valores:\n"
        f"  suma: {_formatear(total)}\n"
        f"  media: {_formatear(media)}\n"
        f"  mediana: {_formatear(mediana)}\n"
        f"  mínimo: {_formatear(ordenados[0])}\n"
        f"  máximo: {_formatear(ordenados[-1])}\n"
        f"  desviación estándar (poblacional): {_formatear(varianza.sqrt())}\n"
        f"  (calculado, no estimado)"
    )


def _leer_fecha(texto: str) -> date | None:
    try:
        return date.fromisoformat((texto or "").strip())
    except ValueError:
        return None


_DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def dias_entre(desde: str, hasta: str) -> str:
    a, b = _leer_fecha(desde), _leer_fecha(hasta)
    if a is None:
        return f"ERROR: «{desde}» no es una fecha válida. Usa AAAA-MM-DD."
    if b is None:
        return f"ERROR: «{hasta}» no es una fecha válida. Usa AAAA-MM-DD."

    dias = (b - a).days
    signo = "después" if dias >= 0 else "antes"
    meses = dias / Decimal("30.436875")
    anios = dias / Decimal("365.2425")
    return (
        f"De {a.isoformat()} ({_DIAS[a.weekday()]}) a {b.isoformat()} "
        f"({_DIAS[b.weekday()]}):\n"
        f"  días: {dias:,}\n"
        f"  la segunda fecha es {abs(dias):,} días {signo} de la primera\n"
        f"  meses aproximados: {_formatear(meses)}\n"
        f"  años aproximados: {_formatear(anios)}\n"
        f"  (los meses y años son aproximados: se calculan sobre el promedio "
        f"del calendario, no sobre meses individuales)"
    )


def _sumar_meses(fecha: date, meses: int) -> date:
    total = fecha.month - 1 + meses
    anio = fecha.year + total // 12
    mes = total % 12 + 1
    # Si el día no existe en el mes destino, se usa el último día de ese mes.
    for dia in range(fecha.day, 0, -1):
        try:
            return date(anio, mes, dia)
        except ValueError:
            continue
    return fecha


def sumar_fechas(fecha: str, dias: int = 0, meses: int = 0, anios: int = 0) -> str:
    base = _leer_fecha(fecha)
    if base is None:
        return f"ERROR: «{fecha}» no es una fecha válida. Usa AAAA-MM-DD."
    if any(not isinstance(v, int) for v in (dias, meses, anios)):
        return "ERROR: los días, meses y años deben ser números enteros."

    resultado = base
    if anios:
        try:
            resultado = resultado.replace(year=resultado.year + anios)
        except ValueError:
            # 29 de febrero en año no bisiesto.
            resultado = resultado.replace(year=resultado.year + anios, day=28)
    if meses:
        resultado = _sumar_meses(resultado, meses)
    if dias:
        resultado = resultado + timedelta(days=dias)

    detalle = []
    if anios:
        detalle.append(f"{anios:+d} año(s)")
    if meses:
        detalle.append(f"{meses:+d} mes(es)")
    if dias:
        detalle.append(f"{dias:+d} día(s)")
    if not detalle:
        return "ERROR: no indicaste cuánto sumar o restar."

    return (
        f"{base.isoformat()} ({_DIAS[base.weekday()]}) "
        f"{' '.join(detalle)} → {resultado.isoformat()} "
        f"({_DIAS[resultado.weekday()]})\n"
        f"  días transcurridos: {(resultado - base).days:,}"
    )


# ─── Medición de texto ───────────────────────────────────────────────────────
# Existe por un defecto medido: el agente escribió un mensaje de 136 palabras y
# reportó 133. Contó a mano, y la calculadora solo sumó los conteos por línea
# que él había preparado. La herramienta era correcta; el dato que entraba no.
#
# Contar palabras parece trivial y por eso nadie lo verifica. Un mensaje que se
# pasa del límite de LinkedIn se corta sin aviso, y el error se descubre después
# de enviarlo.


def _palabras(texto: str) -> list[str]:
    """Separa en palabras con un criterio explícito, no con `split()`.

    Criterio (documentado porque no es el obvio):

    1. Un marcador entre corchetes (`[nombre]`, `[empresa]`) cuenta como UNA
       palabra, porque en el mensaje enviado se reemplaza por un nombre.
    2. Los signos sueltos (`—`, `-`, `·`, `•`) **no** cuentan: no son palabras.
    3. La puntuación pegada a una palabra no la divide: `sobran?` es una palabra.
    4. Se conservan los guiones internos (`dígame-le`) y apóstrofos (`don't`).

    Por qué no se usa `split()`: cuenta el guion largo como palabra y deja
    `[nombre]:` pegado. La primera versión de esta función sí usaba `split()` y
    daba 138 palabras donde había 136. Se detectó comparando contra el conteo
    manual de un mensaje real, y es la razón de que este criterio esté escrito.
    """
    # Los marcadores entre corchetes se preservan como una unidad.
    limpio = re.sub(r"\[([^\]]+)\]", r" \1 ", texto)
    limpio = re.sub(r"[«»\"“”()¿?¡!.,;:]", " ", limpio)
    return [p for p in limpio.split() if any(c.isalnum() for c in p)]


def contar_palabras(texto: str) -> str:
    if texto is None or not str(texto):
        return "ERROR: el texto está vacío."
    texto = str(texto)
    lineas = texto.splitlines() or [texto]
    conteo_lineas = [len(_palabras(l)) for l in lineas]
    total = sum(conteo_lineas)
    caracteres_sin_espacios = len(re.sub(r"\s", "", texto))

    # Se informan los dos criterios porque difieren en textos con signos sueltos
    # o marcadores. Ocultar la diferencia haría que el número pareciera un error
    # cuando en realidad depende de qué se cuenta como palabra.
    bruto = len(texto.split())
    nota = ""
    if bruto != total:
        nota = (f"\n  NOTA: con el criterio de separar por espacios salen {bruto} "
                f"(cuenta los signos sueltos como palabras). Se informa {total}, "
                f"que es el criterio de un texto enviado.")

    return (
        f"Conteo del texto:\n"
        f"  palabras: {total}\n"
        f"  caracteres (con espacios): {len(texto)}\n"
        f"  caracteres (sin espacios): {caracteres_sin_espacios}\n"
        f"  líneas: {len(lineas)}\n"
        f"  palabras por línea: {conteo_lineas}\n"
        f"  suma de las líneas: {total} (debe coincidir con el total)\n"
        f"  (contado por código, no a ojo){nota}"
    )


def medir_texto(texto: str, limite: int = 0) -> str:
    if texto is None or not str(texto):
        return "ERROR: el texto está vacío."
    texto = str(texto)
    palabras = len(_palabras(texto))
    caracteres = len(texto)

    lineas = [
        f"Medición del texto:",
        f"  palabras: {palabras}",
        f"  caracteres (con espacios): {caracteres}",
    ]

    if limite and int(limite) > 0:
        tope = int(limite)
        # Se informa de las dos medidas porque los canales usan una u otra:
        # LinkedIn corta por caracteres, un correo formal se mide en palabras.
        cabe_car = caracteres <= tope
        cabe_pal = palabras <= tope
        lineas.append(f"  límite indicado: {tope}")
        lineas.append(f"  cabe por caracteres: {'sí' if cabe_car else 'NO'} "
                      f"(margen {tope - caracteres:+d})")
        lineas.append(f"  cabe por palabras: {'sí' if cabe_pal else 'NO'} "
                      f"(margen {tope - palabras:+d})")
        if not cabe_car and not cabe_pal:
            lineas.append("  VEREDICTO: se pasa del límite en ambas medidas. "
                          "Hay que recortar antes de entregar.")
        elif not cabe_car or not cabe_pal:
            lineas.append("  AVISO: se pasa del límite en una de las dos medidas. "
                          "Confirma en qué unidad mide el canal.")
        else:
            lineas.append("  VEREDICTO: cabe dentro del límite.")

    lineas.append("  (medido por código, no estimado)")
    return "\n".join(lineas)
