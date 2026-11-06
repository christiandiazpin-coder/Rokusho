#!/usr/bin/env python3
"""Recolector de prospectos desde directorios públicos chilenos.

Regla que no se rompe: **cada ficha lleva la URL de donde salió.** Un dato de
contacto sin origen es un dato que no se puede verificar, y en un negocio que
vende "cada dato con su fuente" eso sería incoherente.

Lo que hace: lee un directorio, extrae nombre, dirección y teléfono, y escribe un
CSV. Lo que NO hace: adivinar correos, scrapear redes, ni completar campos.

Uso:
    python -m herramientas.prospectos --ciudad concepcion --salida /tmp/conce.csv
    python -m herramientas.prospectos --ciudad valparaiso --salida /tmp/valpo.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _arreglar_codificacion(texto: str) -> str:
    """Repara el doble decodificado típico de los directorios chilenos.

    «ConcepciÃ³n» es UTF-8 leído como latin-1. Se detecta porque aparece «Ã»
    seguido de otro byte alto.
    """
    if "Ã" not in texto and "Â" not in texto:
        return texto
    try:
        return texto.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return texto


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto)
                   if not unicodedata.combining(c))


@dataclass
class Prospecto:
    nombre: str
    ciudad: str
    direccion: str = ""
    telefono: str = ""
    sitio: str = ""
    correo: str = ""
    fuente: str = ""          # URL de donde salió
    nota: str = ""

    def a_fila(self) -> dict[str, str]:
        return {
            "nombre": self.nombre, "ciudad": self.ciudad,
            "direccion": self.direccion, "telefono": self.telefono,
            "sitio": self.sitio, "correo": self.correo,
            "fuente": self.fuente, "nota": self.nota,
        }


# En el texto del directorio, cada ficha empieza con un número de dos dígitos en
# su propia línea («01», «02»…), seguido del nombre en la línea siguiente.
_RE_NUMERO = re.compile(r"^\d{2}$")
# Teléfonos chilenos reales, en los formatos que usan los directorios:
#   (41) 2738946      Concepción, área de 2 dígitos
#   (2)232073038      Santiago, área de 1 dígito y 9 dígitos
#   (71) 212415       Talca, fijo de 6 dígitos
#   9 77756416        celular
#
# Versiones anteriores fallaron en cada uno de esos casos, y cada fallo se
# detectó midiendo cuántos teléfonos se perdían por ciudad. La condición que
# evita capturar direcciones es que el número lleve código de área entre
# paréntesis (o empiece con 9 en el caso del celular) y que la secuencia de
# dígitos resultante tenga largo de teléfono (7 a 9), no de numeración de calle.
_RE_TELEFONO = re.compile(
    r"\(\d{1,3}\)\s?\d{6,9}\b"
    r"|\b9\s?\d{4}[\s.-]?\d{4}\b")

_RE_WEB = re.compile(r"https?://(?!duckduckgo|yelu)[\w.-]+\.[a-z]{2,}", re.IGNORECASE)


def extraer(texto: str, ciudad: str, url: str) -> list[Prospecto]:
    """Extrae fichas del texto de un directorio. Todo lo que devuelve es literal."""
    texto = _arreglar_codificacion(texto)
    lineas = [l.strip() for l in texto.splitlines()]
    fichas: list[Prospecto] = []
    i = 0

    # Se descartan las líneas vacías: entre el número de ficha y el nombre hay
    # una línea en blanco en el directorio real. Sin saltarlas, el parser tomaba
    # cadena vacía como nombre y no extraía nada.
    lineas = [l for l in lineas if l]

    while i < len(lineas):
        if _RE_NUMERO.match(lineas[i]) and i + 1 < len(lineas):
            nombre = lineas[i + 1]
            # Filtros de ruido. El directorio intercala contadores y controles
            # de paginación entre las fichas («1,692 compañías», «Map»,
            # «Siguiente»), y sin filtrarlos entran como si fueran empresas.
            ruido = (
                not any(c.isalpha() for c in nombre)      # solo números/símbolos
                or re.match(r"^[\d.,]+\s*(compañ|compan|resultad|empresas)", nombre, re.I)
                or nombre.lower() in {"map", "mapa", "siguiente", "anterior",
                                      "ver más", "ver mas", "filtrar por ciudad"}
                or len(nombre) >= 120                      # un párrafo no es un nombre
                or nombre.count(" ") > 12                  # frase, no razón social
            )
            if not ruido:
                ficha = Prospecto(nombre=nombre, ciudad=ciudad, fuente=url)
                # Se miran las siguientes líneas buscando dirección y teléfono,
                # sin pasar de la siguiente ficha.
                j = i + 2
                while j < len(lineas) and not _RE_NUMERO.match(lineas[j]):
                    linea = lineas[j]
                    tel = _RE_TELEFONO.search(linea)
                    if tel and not ficha.telefono:
                        ficha.telefono = tel.group(0).strip()
                    elif (not ficha.direccion and len(linea) > 12
                          and any(p in linea.lower() for p in
                                  ("calle", "avenida", "pasaje", "av.", "of.",
                                   "depto", "piso", "regi"))):
                        ficha.direccion = linea
                    web = _RE_WEB.search(linea)
                    if web and not ficha.sitio:
                        ficha.sitio = web.group(0)
                    j += 1
                fichas.append(ficha)
                i = j
                continue
        i += 1

    return fichas


def recolectar(ciudad: str, pagina: int = 1) -> tuple[list[Prospecto], str]:
    """Lee el directorio para una ciudad. Devuelve (fichas, url_leida)."""
    from chasis.pieza import _importar

    modulo = _importar(Path(__file__).resolve().parent.parent
                       / "piezas" / "web" / "implementacion.py", "web_prospectos")

    ciudad_url = ciudad.lower().replace(" ", "")
    url = f"https://www.yelu.cl/category/Consultores/city:{ciudad_url}"
    if pagina > 1:
        url += f"?page={pagina}"

    salida = modulo.leer_pagina(url)
    if "CONTENIDO_EXTERNO" not in salida:
        return [], url

    # Se quitan las marcas y la cabecera antes de parsear.
    cuerpo = salida.split("<<<CONTENIDO_EXTERNO_NO_CONFIABLE>>>")[-1]
    cuerpo = cuerpo.split("<<<FIN_CONTENIDO_EXTERNO>>>")[0]
    return extraer(cuerpo, ciudad, url), url


def escribir_csv(fichas: list[Prospecto], destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    campos = ["nombre", "ciudad", "direccion", "telefono", "sitio",
              "correo", "fuente", "nota"]
    with destino.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        for ficha in fichas:
            escritor.writerow(ficha.a_fila())


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Recolecta prospectos desde directorios públicos. Cada ficha "
                    "lleva la URL de origen; no se adivina ningún dato.")
    p.add_argument("--ciudad", required=True, help="Ej.: concepcion, valparaiso")
    p.add_argument("--salida", required=True, help="Ruta del CSV")
    p.add_argument("--paginas", type=int, default=1,
                   help="Cuántas páginas del directorio recorrer.")
    args = p.parse_args(argv)

    todas: list[Prospecto] = []
    for pagina in range(1, args.paginas + 1):
        fichas, url = recolectar(args.ciudad, pagina)
        if not fichas:
            print(f"  página {pagina}: sin resultados ({url})")
            break
        print(f"  página {pagina}: {len(fichas)} fichas")
        todas.extend(fichas)

    if not todas:
        print("\nNo se recolectó ninguna ficha. Causas posibles:")
        print("  - el directorio cambió de estructura")
        print("  - no hay conexión")
        print("  - la ciudad no existe en el directorio")
        return 1

    # Deduplicar por nombre, conservando la primera aparición.
    vistas: set[str] = set()
    unicas: list[Prospecto] = []
    for f in todas:
        clave = _sin_acentos(f.nombre).lower().strip()
        if clave not in vistas:
            vistas.add(clave)
            unicas.append(f)

    destino = Path(args.salida)
    escribir_csv(unicas, destino)

    con_tel = sum(1 for f in unicas if f.telefono)
    con_web = sum(1 for f in unicas if f.sitio)
    con_correo = sum(1 for f in unicas if f.correo)

    print(f"\n{len(unicas)} prospectos únicos escritos en {destino}")
    print(f"  con teléfono: {con_tel}")
    print(f"  con sitio web: {con_web}")
    print(f"  con correo: {con_correo} (el directorio lo oculta; se busca en el sitio)")
    print(f"  sin dato de contacto: {sum(1 for f in unicas if not f.telefono and not f.sitio)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
