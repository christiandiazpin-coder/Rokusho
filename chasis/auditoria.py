"""Auditoría de afirmaciones: contrasta lo que el agente dice con lo que hizo.

Por qué existe: un modelo puede escribir «lo verifiqué» sin haber llamado a la
herramienta que verifica. No es mentira deliberada — es dar por hecho un
resultado que no se midió. En un informe que un cliente va a usar para decidir,
eso es el fallo más caro posible.

Qué hace: recorre el texto del reporte, identifica las frases que **afirman un
resultado**, y busca en el turno la evidencia que las respalde. Si una frase
afirma algo y ninguna herramienta lo comprobó, se marca.

Qué NO hace: no juzga si el texto es bueno, ni si la conclusión es correcta.
Solo juzga la relación entre lo afirmado y lo ocurrido.

Esto viene del proyecto Umbra, donde se midió sobre episodios reales: el agente
escribió «formato corregido» dos veces y las dos el comando seguía fallando.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# Verbos y fórmulas que convierten una frase en una afirmación de resultado.
# En minúsculas y sin tildes: se comparan sobre texto normalizado.
AFIRMACIONES = (
    "corregido", "corregida", "arreglado", "arreglada", "solucionado",
    "verificado", "verificada", "comprobado", "comprobada", "confirmado",
    "funciona", "funcionando", "esta listo", "terminado", "terminada",
    "sin errores", "sin problemas", "sin defectos", "limpio", "limpia",
    "correcto", "correcta", "perfecto", "perfecta", "impecable",
    "aprobado", "cumple", "garantizado", "asegurado", "resuelto", "resuelta",
    "se aplico", "aplicado", "aplicada", "se genero", "generado", "generada",
    "corri", "ejecute", "comprobe", "revise", "verifique", "calcule",
    "encontre", "detecte", "identifique", "lei", "conclui",
)

# Palabras que anuncian una medición real y no una impresión.
EVIDENCIA = (
    "medido", "medicion", "promedio", "luminancia", "contraste",
    "ffprobe", "ffmpeg", "pytest", "ruff", "passed", "failed",
    "checks passed", "sha256", "bytes", "duracion", "lufs", "bitrate",
    "linea", "lineas", "columna", "pagina", "clausula", "articulo",
    "->", ":/", ".txt", ".md", ".html", ".json", ".log", ".py", ".pdf",
)

# Una herramienta falló si su salida EMPIEZA así. Un fallo invalida cualquier
# afirmación de éxito hecha sobre esa misma herramienta.
#
# Antes incluía «no hay», «no existe» y «no encontr» sin anclar al inicio, y eso
# marcaba como fallido cualquier informe informativo: «No hay ningún informe: la
# carpeta no existe» es una respuesta VÁLIDA de la herramienta, no un fallo. Un
# resultado negativo no es una herramienta rota.
#
# Se distingue ahora entre:
#   - el prefijo de error que ponen las herramientas («ERROR:», «BLOQUEADO:»)
#   - un mensaje de ausencia, que es información legítima
_FRACASO = re.compile(
    r"^\s*(ERROR:|BLOQUEADO:|DENEGADO:|FAILED\b|Traceback\b|AssertionError\b|"
    r"KeyError\b|no se pudo\b|exit code: [1-9])",
    re.IGNORECASE | re.MULTILINE)

# Un bloque de código no se audita: es una cita, no una afirmación propia.
_CODIGO = re.compile(r"```.*?```", re.DOTALL)

# Frases que reconocen un límite o un fallo. Si la frase los contiene, es honesta
# aunque use una palabra de afirmación: «no pude verificar» no es una mentira.
_RECONOCE = (
    "no pude", "no lo pude", "no se pudo", "no fue posible", "no tengo",
    "no hay", "no esta", "no esta en", "no aparece", "no lo indica",
    "no encontre", "no encontro", "falta", "faltan", "pendiente",
    "no verifique", "sin verificar", "no comprobe", "no medi",
    "no es posible", "no puedo afirmar", "no puedo confirmar", "supongo",
    "supuse", "asumo", "asumi", "deduje", "deducido", "estimado",
    "no alcance", "no alcance a", "queda fuera", "no cubre",
)


def _normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para comparar palabras sin pelearse con acentos."""
    sin = "".join(c for c in unicodedata.normalize("NFKD", texto)
                  if not unicodedata.combining(c))
    return sin.lower()


def _sin_codigo(texto: str) -> str:
    return _CODIGO.sub(" ", texto)


def _frases(texto: str) -> list[str]:
    """Divide en frases sin romper por abreviaturas ni por cifras con punto."""
    partes = re.split(r"(?<=[.!?])\s+|\n{1,}", texto)
    return [p.strip() for p in partes if p and p.strip()]


# Verbos que presentan un dato como establecido, aunque no sean de "resultado".
# «El total es de X» no dice «verifiqué», pero afirma un dato igual de fuerte.
_AFIRMA_DATO = re.compile(
    r"\b(es de|son de|asciende|totaliza|equivale|corresponde|"
    r"queda en|quedo en|suma|alcanza|representa)\b")


def _afirma(frase: str) -> str | None:
    """Devuelve la palabra de afirmación si la frase afirma un resultado o un dato."""
    normal = _normalizar(frase)
    for palabra in AFIRMACIONES:
        if re.search(rf"\b{re.escape(palabra)}\b", normal):
            return palabra
    # Una frase con cifras que las presenta como establecidas también afirma.
    # Sin esto, «el total es de 10.200.000 pesos» pasaba sin auditar: no tenía
    # ninguna palabra de la lista, pero afirmaba una cifra igual de fuerte.
    if re.search(r"\d", frase) and _AFIRMA_DATO.search(normal):
        return "afirma un dato"
    return None


def _reconoce_el_fallo(frase: str) -> bool:
    normal = _normalizar(frase)
    return any(p in normal for p in _RECONOCE)


def _la_cifra_esta_en_la_salida(frase: str, salidas: list[str]) -> bool:
    """Comprueba si las cifras de la frase aparecen en lo que devolvieron las herramientas.

    Un número sin respaldo es el dato inventado más frecuente: se copia mal, se
    redondea de memoria o se supone.
    """
    cifras = re.findall(r"\d[\d.,]*\d|\d", frase)
    if not cifras:
        return True  # la frase no afirma cifras
    juntas = _normalizar(" ".join(salidas))
    sin_formato = re.sub(r"[.,]", "", juntas)
    for cifra in cifras:
        limpia = re.sub(r"[.,]", "", cifra)
        if len(limpia) < 2:
            continue  # un dígito suelto aparece en cualquier parte
        if limpia not in sin_formato:
            return False
    return True


def _midio_cero(pasos) -> bool:
    """Verdadero si NINGUNA herramienta exitosa devolvió contenido sustantivo.

    Antes bastaba con que UNA herramienta informara cero resultados para marcar
    todo el turno, y eso produjo un falso positivo real: el agente leyó el
    contrato completo (11 de 11 líneas) y además buscó «IVA» sin resultados. La
    búsqueda vacía disparaba el aviso aunque la lectura hubiera ido bien.

    La condición correcta es más estricta: el turno no midió nada si *todas* sus
    herramientas exitosas devolvieron vacío o solo un mensaje de «no encontré».
    """
    if not pasos:
        return False
    for paso in pasos:
        salida = (paso.resultado or "").strip()
        normal = _normalizar(salida)
        # Una salida con contenido real tiene más de un mensaje de vacío.
        vacia = (len(salida) < 80 or
                 bool(re.match(r"^(no se encontr|no hay|no existe|vacio|vacia|"
                               r"la carpeta .* esta vacia)", normal)))
        if not vacia:
            return False  # esta herramienta sí midió algo
    return True


@dataclass
class Aviso:
    """Una afirmación que no encontró respaldo."""
    frase: str
    motivo: str
    palabra: str = ""

    def __str__(self) -> str:
        recorte = self.frase if len(self.frase) <= 160 else self.frase[:157] + "..."
        return f"«{recorte}»\n    → {self.motivo}"


@dataclass
class Auditoria:
    avisos: list[Aviso] = field(default_factory=list)
    frases_auditadas: int = 0
    frases_afirmativas: int = 0
    herramientas_exitosas: int = 0
    herramientas_fallidas: int = 0

    @property
    def limpia(self) -> bool:
        return not self.avisos

    def __bool__(self) -> bool:
        """Verdadero si hay avisos: permite `if auditoria:`."""
        return bool(self.avisos)


def auditar(turno) -> Auditoria:
    """Audita un `Turno` del chasis contra la evidencia que produjo."""
    texto = _sin_codigo(turno.respuesta or "")
    pasos = list(turno.pasos)

    exitosas = [p for p in pasos if not _FRACASO.search(p.resultado or "")]
    fallidas = [p for p in pasos if _FRACASO.search(p.resultado or "")]
    salidas = [p.resultado or "" for p in exitosas]

    auditoria = Auditoria(
        herramientas_exitosas=len(exitosas),
        herramientas_fallidas=len(fallidas),
    )

    # Solo se considera que el turno no midió nada si ninguna herramienta
    # exitosa devolvió contenido.
    mido_cero = _midio_cero(exitosas)

    for frase in _frases(texto):
        auditoria.frases_auditadas += 1
        palabra = _afirma(frase)
        if not palabra:
            continue
        auditoria.frases_afirmativas += 1

        if _reconoce_el_fallo(frase):
            continue  # la frase ya admite el límite: es honesta

        # 1. Una herramienta falló y la frase no lo menciona.
        if fallidas:
            nombres = _normalizar(" ".join(p.herramienta for p in fallidas))
            if not any(n in _normalizar(frase) for n in nombres.split()):
                auditoria.avisos.append(Aviso(
                    frase,
                    f"usa «{palabra}» pero en el turno hubo "
                    f"{len(fallidas)} herramienta(s) que fallaron y la frase no lo dice",
                    palabra))
                continue

        # 2. Afirma un resultado sin haber usado ninguna herramienta.
        if not exitosas and not fallidas:
            auditoria.avisos.append(Aviso(
                frase,
                f"usa «{palabra}» pero el turno no ejecutó ninguna herramienta: "
                "no hay con qué respaldarlo",
                palabra))
            continue

        # 3. Una cifra que no aparece en la salida.
        if salidas and not _la_cifra_esta_en_la_salida(frase, salidas):
            auditoria.avisos.append(Aviso(
                frase,
                "menciona una cifra que no aparece en la salida de ninguna herramienta",
                palabra))
            continue

        # 4. Una herramienta que revisó cero elementos no verifica nada.
        if mido_cero and any(p in _normalizar(frase) for p in ("verific", "revis", "comprob")):
            auditoria.avisos.append(Aviso(
                frase,
                "afirma haber verificado, pero una herramienta del turno informó "
                "haber revisado cero elementos",
                palabra))

    return auditoria


def formatear(auditoria: Auditoria) -> str:
    """Texto para añadir al final del reporte, visible para quien lo lea."""
    if auditoria.limpia:
        return ""
    lineas = ["", "---", "AVISOS DE AUDITORÍA",
              "Las siguientes frases afirman un resultado sin respaldo en lo que "
              "realmente ocurrió en este turno:", ""]
    for i, aviso in enumerate(auditoria.avisos, 1):
        lineas.append(f"{i}. {aviso}")
        lineas.append("")
    lineas.append("Esto no significa que el trabajo esté mal; significa que el "
                  "reporte afirma más de lo que se comprobó. Revisar antes de entregar.")
    return "\n".join(lineas)


def resumen(auditoria: Auditoria) -> dict:
    """Cifras para medir el auditor, no para leerlas en el informe."""
    return {
        "avisos": len(auditoria.avisos),
        "frases_auditadas": auditoria.frases_auditadas,
        "frases_afirmativas": auditoria.frases_afirmativas,
        "herramientas_exitosas": auditoria.herramientas_exitosas,
        "herramientas_fallidas": auditoria.herramientas_fallidas,
        "limpia": auditoria.limpia,
    }
