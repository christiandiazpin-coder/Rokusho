"""Etiquetas de procedencia: marca cada dato como verificado o supuesto.

Idea de fondo, tomada de la neurociencia (monitoreo de fuente): el cerebro no
solo recuerda un dato, recuerda de dónde salió. Cuando ese mecanismo falla, una
invención se siente igual que un recuerdo.

Un modelo de lenguaje tiene exactamente ese problema: no distingue lo que leyó
de lo que supuso. Este módulo le pone la etiqueta por él, comprobando si el dato
aparece literalmente en algo que una herramienta devolvió.

Diferencia con `auditoria.py`: allí se juzga si una **afirmación** estaba
respaldada. Aquí se juzga cada **dato concreto** (una cifra, una ruta, un
nombre de archivo) y se etiqueta.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

VERIFICADO = "VERIFICADO"
HIPOTESIS = "HIPOTESIS"

# Qué se considera un «dato duro»: cifras con unidad, rutas y nombres de archivo.
_RE_CIFRA_CON_UNIDAD = re.compile(
    r"\b\d[\d.,]*\s*(%|pesos|uf|clp|usd|dólares|dolares|euros|"
    r"días|dias|meses|años|anios|horas|minutos|segundos|"
    r"líneas|lineas|páginas|paginas|bytes|mb|gb|kb)\b",
    re.IGNORECASE)
_RE_RUTA = re.compile(r"[\w./-]+/[\w./-]+\.\w{1,5}\b")
_RE_ARCHIVO = re.compile(r"\b[\w-]+\.(txt|md|html|json|log|py|pdf|csv|xlsx|docx)\b")
# Cifras con separador interno y dígito verificador: RUT 76.543.210-8,
# teléfonos, códigos. Sin este patrón, el RUT se escapaba del etiquetado y
# quedaba sin marcar, que es justo el dato que más se inventa en un informe.
_RE_CIFRA_LARGA = re.compile(r"\b\d[\d.,]*-?[\dKk]\b")


def _normalizar(texto: str) -> str:
    sin = "".join(c for c in unicodedata.normalize("NFKD", texto)
                  if not unicodedata.combining(c))
    return sin.lower()


def _sin_formato(texto: str) -> str:
    """Quita separadores de miles para comparar cifras escritas distinto."""
    return re.sub(r"(?<=\d)[.,](?=\d{3}\b)", "", texto)


@dataclass
class Dato:
    texto: str
    tipo: str
    etiqueta: str
    ubicacion: str = ""  # en qué salida apareció, si apareció

    def __str__(self) -> str:
        marca = "✓" if self.etiqueta == VERIFICADO else "?"
        extra = f" ({self.ubicacion})" if self.ubicacion else ""
        return f"{marca} {self.texto} — {self.etiqueta}{extra}"


@dataclass
class Resultado:
    datos: list[Dato] = field(default_factory=list)

    @property
    def verificados(self) -> list[Dato]:
        return [d for d in self.datos if d.etiqueta == VERIFICADO]

    @property
    def hipotesis(self) -> list[Dato]:
        return [d for d in self.datos if d.etiqueta == HIPOTESIS]

    @property
    def proporcion_verificada(self) -> float:
        return len(self.verificados) / len(self.datos) if self.datos else 0.0


def _buscar_en(dato: str, salidas: list[str]) -> str:
    """Devuelve el fragmento de salida donde aparece el dato, o vacío."""
    objetivo = _normalizar(_sin_formato(dato))
    for salida in salidas:
        normal = _normalizar(_sin_formato(salida))
        if objetivo in normal:
            # Se devuelve la línea para que se pueda citar.
            for linea in salida.splitlines():
                if objetivo in _normalizar(_sin_formato(linea)):
                    return linea.strip()[:120]
    return ""


def etiquetar(texto: str, salidas: list[str]) -> Resultado:
    """Recorre el texto y etiqueta cada dato duro según aparezca o no en las salidas."""
    resultado = Resultado()
    vistos: set[str] = set()

    def anadir(coincidencia: str, tipo: str) -> None:
        limpio = coincidencia.strip()
        clave = _normalizar(_sin_formato(limpio))
        # Se deduplica por el VALOR numérico, no por el texto: «850.000 pesos»
        # y «850.000» son el mismo dato y contarlo dos veces infla los totales
        # del resumen, que es justo lo que el usuario mira.
        numerico = re.sub(r"[.,]", "", re.sub(r"[^\d]", "", limpio))
        if numerico and len(numerico) >= 3:
            clave = f"num:{numerico}"
        if clave in vistos:
            return
        vistos.add(clave)
        ubicacion = _buscar_en(limpio, salidas)
        resultado.datos.append(Dato(
            texto=limpio, tipo=tipo,
            etiqueta=VERIFICADO if ubicacion else HIPOTESIS,
            ubicacion=ubicacion))

    for m in _RE_CIFRA_CON_UNIDAD.finditer(texto):
        anadir(m.group(0), "cifra con unidad")
    for m in _RE_CIFRA_LARGA.finditer(texto):
        anadir(m.group(0), "cifra")
    for m in _RE_RUTA.finditer(texto):
        anadir(m.group(0), "ruta")
    for m in _RE_ARCHIVO.finditer(texto):
        anadir(m.group(0), "archivo")

    return resultado


def anotar(texto: str, resultado: Resultado) -> str:
    """Añade al final del texto una tabla con la procedencia de cada dato."""
    if not resultado.datos:
        return texto
    lineas = ["", "---", "PROCEDENCIA DE LOS DATOS", ""]
    lineas.append(f"De {len(resultado.datos)} datos con formato verificable, "
                  f"{len(resultado.verificados)} aparecen en la salida de una "
                  f"herramienta y {len(resultado.hipotesis)} no.")
    lineas.append("")
    for d in resultado.datos:
        lineas.append(f"  {d}")
    if resultado.hipotesis:
        lineas.append("")
        lineas.append("Los marcados con ? no se encontraron en ninguna salida: "
                      "pueden venir del conocimiento del modelo. Trátalos como "
                      "hipótesis hasta confirmarlos.")
    return texto + "\n".join(lineas)


def resumen(resultado: Resultado) -> dict:
    return {
        "datos": len(resultado.datos),
        "verificados": len(resultado.verificados),
        "hipotesis": len(resultado.hipotesis),
        "proporcion_verificada": round(resultado.proporcion_verificada, 3),
    }
