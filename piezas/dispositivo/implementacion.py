"""Pieza «dispositivo»: identifica y diagnostica un aparato Android/MediaTek.

Todo lo que devuelve viene de adb, de fastboot, del bus USB o de la ficha
verificada. Nada se escribe en el aparato: esta pieza no instala, no borra y no
cambia el gestor de arranque. Esa restricción es deliberada — el diagnóstico
tiene que poder hacerse sin riesgo de dejar el equipo sin arranque.
"""

from __future__ import annotations

import shutil
import subprocess

PROPIEDADES = {
    "ro.product.manufacturer": "fabricante",
    "ro.product.model": "modelo",
    "ro.product.device": "nombre interno",
    "ro.board.platform": "plataforma",
    "ro.build.version.release": "versión de Android",
    "ro.build.version.sdk": "nivel de API",
    "ro.build.display.id": "compilación",
    "ro.product.cpu.abi": "arquitectura",
    "ro.build.characteristics": "tipo de equipo",
}

TIEMPO = 30

# VID de MediaTek: con este identificador aparece el aparato en modo BROM o
# Preloader, que es el nivel con el que trabaja mtkclient.
VID_MTK = "0e8d"

# Modos USB de MediaTek y qué significan.
MODOS_MTK = {
    "2000": "BROM (Boot ROM): el modo de bajo nivel. Es el que permite leer y escribir la memoria.",
    "2011": "Preloader (VCOM): el cargador previo al sistema. También sirve para trabajar con mtkclient.",
    "0003": "Puerto serie de depuración.",
}

# Fichas verificadas contra fuentes públicas. Solo modelos comprobados: si un
# modelo no está aquí, la herramienta lo dice en vez de suponer sus datos.
FICHAS = {
    "TB-X306F": {
        "nombre_comercial": "Lenovo Tab M10 HD (2ª gen), Wi-Fi",
        "procesador": "MediaTek Helio P22T (MT8768T), 8 núcleos Cortex-A53",
        "graficos": "IMG PowerVR GE8320",
        "memoria": "2 GB o 4 GB LPDDR4X (según variante) / 32 GB o 64 GB eMMC",
        "pantalla": "10,1 pulgadas, 1280x800",
        "android_fabrica": "Android 10 (nivel de API 29)",
        "treble": "sí, es compatible con GSI (imágenes genéricas de sistema)",
        "desbloqueo": (
            "fastboot: los reportes de esta variante (2/32 GB) desbloquean con "
            "«adb reboot bootloader» y «fastboot flashing unlock», confirmando con "
            "volumen arriba. mtkclient/BROM queda como plan B si fastboot no coopera. "
            "Lenovo no publica un método oficial para este modelo."
        ),
        "particularidad": (
            "La variante de 2 GB de RAM va justa. Sirve para lo básico (navegar, "
            "leer, ver video) pero no para multitarea. Hay compilaciones para este "
            "equipo con ZRAM activado que bajan a la mitad el uso de memoria: son las "
            "que hay que elegir en la variante de 2 GB. Para aplicaciones de Google, "
            "conviene microG en vez de GApps, que pesa mucho menos."
        ),
        "riesgo": (
            "Dos trampas documentadas para este modelo: (1) las compilaciones de "
            "LineageOS NO son compatibles con TWRP, hay que usar el recovery que viene "
            "dentro del ZIP de instalación; (2) el equipo usa particiones de tipo "
            "a-only (no SAR), así que una GSI genérica A/B no arranca. Con la imagen "
            "equivocada el resultado es un bucle de arranque, recuperable desde fastboot."
        ),
        "fuentes": (
            "ficha del fabricante (PSREF de Lenovo) y el hilo de XDA del modelo "
            "«Attempting to install GSI on 2nd Gen Lenovo Tab M10 HD (X306F 2/32GB)»"
        ),
    },
}


def configurar(carpeta=None) -> None:
    """La pieza no necesita espacio de trabajo; el gancho existe por simetría."""
    return None


def _adb() -> str | None:
    return shutil.which("adb")


def _ejecutar(argumentos: list[str]) -> tuple[int, str, str]:
    """Ejecuta adb. Si falta la herramienta, devuelve un error en vez de lanzar.

    Antes lanzaba RuntimeError. El chasis atrapa las excepciones de herramienta,
    pero una excepción obliga al agente a interpretar el error como fallo de la
    llamada; devolver el texto le permite decírselo al usuario con claridad.
    Una herramienta no debe tumbar el turno para informar de algo previsible.
    """
    binario = _adb()
    if not binario:
        return (1, "", "ERROR: adb no está instalado. Sin adb no se puede hablar "
                       "con el aparato; no supongas su estado.")
    proceso = subprocess.run([binario, *argumentos], capture_output=True,
                             text=True, timeout=TIEMPO)
    return proceso.returncode, proceso.stdout, proceso.stderr


def herramientas() -> str:
    lineas = ["Herramientas de diagnóstico disponibles en este equipo:"]
    encontradas = 0
    for nombre, argumento in (("adb", "--version"), ("fastboot", "--version")):
        ruta = shutil.which(nombre)
        if ruta:
            encontradas += 1
            try:
                version = subprocess.run([ruta, argumento], capture_output=True,
                                         text=True, timeout=TIEMPO).stdout.strip().splitlines()
            except (OSError, subprocess.SubprocessError):
                version = []
            lineas.append(f"  {nombre}: {ruta}")
            if version:
                lineas.append(f"    {version[0]}")
        else:
            lineas.append(f"  {nombre}: NO instalado")

    mtk = shutil.which("mtk") or shutil.which("mtk.py")
    if mtk:
        lineas.append(f"  mtkclient: {mtk}")
    else:
        posibles = ["/home/" + __import__("os").environ.get("USER", "") + "/.local/opt/mtkclient/mtk.py"]
        encontrado = next((p for p in posibles if __import__("os").path.isfile(p)), None)
        if encontrado:
            lineas.append(f"  mtkclient: {encontrado} (no está en el PATH)")
        else:
            lineas.append("  mtkclient: NO instalado (necesario para MediaTek)")

    if encontradas == 0:
        lineas.append("  Sin adb ni fastboot no hay diagnóstico posible: hay que "
                      "instalarlos antes de seguir.")
    return "\n".join(lineas)


def listar_dispositivos() -> str:
    codigo, salida, error = _ejecutar(["devices", "-l"])
    if codigo != 0:
        return f"ERROR: adb falló (código {codigo}): {error[:300]}"

    aparatos = [l for l in salida.splitlines()[1:] if l.strip()]
    if not aparatos:
        extra = _resumen_usb_mtk()
        return ("No hay ningún aparato conectado por USB en modo Android.\n"
                "Antes de seguir hay que conectarlo, activar la depuración por USB "
                "y autorizar este equipo en la pantalla del aparato."
                + (f"\n\n{extra}" if extra else ""))

    lineas = [f"Aparatos conectados ({len(aparatos)}):"]
    for l in aparatos:
        partes = l.split()
        serie = partes[0]
        estado = partes[1] if len(partes) > 1 else "?"
        lineas.append(f"  serie: {serie}")
        lineas.append(f"    estado: {estado}")
        if estado == "unauthorized":
            lineas.append("    AVISO: el aparato no autorizó a este equipo. Hay que aceptar "
                          "el diálogo de depuración en su pantalla.")
        elif estado == "offline":
            lineas.append("    AVISO: el aparato aparece pero no responde.")
    return "\n".join(lineas)


def _resumen_usb_mtk() -> str:
    """Mira el bus USB por si el aparato está en modo BROM/Preloader."""
    try:
        salida = subprocess.run(["lsusb"], capture_output=True, text=True,
                                timeout=TIEMPO).stdout
    except (OSError, subprocess.SubprocessError):
        return ""
    # Se comparan AMBOS lados en minúsculas: antes solo se bajaba la salida y
    # el patrón llevaba «ID» en mayúscula, así que la detección no encontraba
    # nada nunca. Comprobado con una prueba que simula un aparato en BROM.
    patron = f"id {VID_MTK}:".lower()
    mtk = [l for l in salida.splitlines() if patron in l.lower()]
    if not mtk:
        return ""
    lineas = ["Detectado un aparato MediaTek en el bus USB:"]
    for l in mtk:
        lineas.append(f"  {l.strip()}")
        bajo = l.lower()
        identificador = bajo.split(f"{VID_MTK}:")[1].split()[0] if f"{VID_MTK}:" in bajo else ""
        modo = MODOS_MTK.get(identificador.lower(), "")
        if modo:
            lineas.append(f"    modo: {modo}")
    lineas.append("  En este modo el aparato no habla con adb: se trabaja con mtkclient.")
    return "\n".join(lineas)


def _getprop(serie: str, propiedad: str) -> str:
    codigo, salida, _ = _ejecutar(["-s", serie, "shell", "getprop", propiedad])
    return salida.strip() if codigo == 0 else ""


def identificar(serie: str) -> str:
    if not serie or not serie.strip():
        return "ERROR: falta el identificador del aparato. Usa listar_dispositivos primero."

    codigo, _, error = _ejecutar(["-s", serie, "get-state"])
    if codigo != 0:
        return (f"ERROR: el aparato «{serie}» no responde: {error[:200]}\n"
                "No inventes sus datos: sin respuesta no hay identificación.")

    leidos: dict[str, str] = {}
    for propiedad, etiqueta in PROPIEDADES.items():
        valor = _getprop(serie, propiedad)
        if valor:
            leidos[etiqueta] = valor

    if not leidos:
        return (f"ERROR: el aparato «{serie}» respondió pero no devolvió ninguna propiedad. "
                "No se puede identificar; no supongas el modelo.")

    lineas = [f"Aparato «{serie}» (datos leídos del equipo):"]
    for etiqueta, valor in leidos.items():
        lineas.append(f"  {etiqueta}: {valor}")

    modelo = leidos.get("modelo", "")
    if modelo:
        ficha_datos = _buscar_ficha(modelo)
        if ficha_datos:
            lineas.append(f"\nHay ficha verificada para «{modelo}»: usa la herramienta "
                          "«ficha» para verla antes de proponer pasos.")
        else:
            lineas.append(f"\nNo hay ficha verificada para «{modelo}» en esta pieza. "
                          "No supongas su procesador ni su método de desbloqueo.")
    return "\n".join(lineas)


def _buscar_ficha(modelo: str) -> dict | None:
    clave = modelo.strip().upper().replace("LENOVO", "").strip()
    if clave in FICHAS:
        return FICHAS[clave]
    for nombre, datos in FICHAS.items():
        if nombre in clave or clave in nombre:
            return datos
    return None


def ficha(modelo: str) -> str:
    if not modelo or not modelo.strip():
        return "ERROR: falta el modelo (por ejemplo TB-X306F)."

    datos = _buscar_ficha(modelo)
    if not datos:
        return (
            f"No hay ficha verificada para «{modelo}».\n"
            f"Modelos con ficha: {', '.join(sorted(FICHAS))}.\n"
            "Sin ficha no se puede afirmar el procesador ni el método de desbloqueo: "
            "hay que averiguarlo con identificar o con el propio aparato."
        )

    lineas = [f"Ficha de {datos['nombre_comercial']}:"]
    for clave in ("procesador", "graficos", "memoria", "pantalla", "android_fabrica",
                  "treble", "desbloqueo", "particularidad", "riesgo", "fuentes"):
        if clave in datos:
            etiqueta = clave.replace("_", " ")
            lineas.append(f"  {etiqueta}: {datos[clave]}")
    return "\n".join(lineas)


def estado_arranque(serie: str) -> str:
    if not serie or not serie.strip():
        return "ERROR: falta el identificador del aparato."

    codigo, _, error = _ejecutar(["-s", serie, "get-state"])
    if codigo != 0:
        return f"ERROR: el aparato «{serie}» no responde: {error[:200]}"

    valor = _getprop(serie, "ro.boot.verifiedbootstate")
    desbloqueo = _getprop(serie, "ro.boot.flash.locked")
    oem = _getprop(serie, "sys.oem_unlock_allowed")

    lineas = [f"Estado del gestor de arranque de «{serie}»:"]
    if desbloqueo:
        estados = {"1": "BLOQUEADO", "0": "DESBLOQUEADO"}
        lineas.append(f"  arranque bloqueado: {desbloqueo} → "
                      f"{estados.get(desbloqueo, 'valor no reconocido')}")
    if valor:
        significado = {
            "green": "arranque verificado, sistema original intacto",
            "yellow": "arranque con clave propia: sistema modificado",
            "orange": "arranque desbloqueado, sin verificación",
            "red": "verificación FALLIDA",
        }
        lineas.append(f"  estado de verificación: {valor} → "
                      f"{significado.get(valor, 'valor no reconocido')}")
    if oem:
        lineas.append(f"  desbloqueo permitido por el fabricante: {oem} "
                      f"({'sí' if oem == '1' else 'no'})")

    if len(lineas) == 1:
        return (f"El aparato «{serie}» no expone el estado de arranque por esta vía.\n"
                "No se puede concluir si está bloqueado: hay que comprobarlo en el modo "
                "de arranque del propio aparato, no suponerlo.")

    lineas.append("\nCon el arranque bloqueado, instalar otro sistema requiere "
                  "desbloquearlo primero.")
    return "\n".join(lineas)


def modo_mtk() -> str:
    """Comprueba si hay un MediaTek en modo BROM/Preloader en el bus USB."""
    try:
        salida = subprocess.run(["lsusb"], capture_output=True, text=True,
                                timeout=TIEMPO).stdout
    except (OSError, subprocess.SubprocessError) as e:
        return f"ERROR: no se pudo leer el bus USB: {e}"

    # Se comparan AMBOS lados en minúsculas: antes solo se bajaba la salida y
    # el patrón llevaba «ID» en mayúscula, así que la detección no encontraba
    # nada nunca. Comprobado con una prueba que simula un aparato en BROM.
    patron = f"id {VID_MTK}:".lower()
    mtk = [l for l in salida.splitlines() if patron in l.lower()]
    if not mtk:
        return ("No hay ningún aparato MediaTek en modo BROM/Preloader.\n"
                "Si el aparato está encendido normalmente, aparece por adb, no aquí.\n"
                "Para entrar en BROM: apagado, mantener volumen arriba y bajar y "
                "conectar el USB; o, si está protegido, hace falta un punto de prueba.")

    lineas = ["Aparato MediaTek detectado en el bus USB:"]
    for l in mtk:
        lineas.append(f"  {l.strip()}")
        partes = l.lower().split(f"{VID_MTK}:")
        if len(partes) > 1:
            identificador = partes[1].split()[0]
            modo = MODOS_MTK.get(identificador)
            lineas.append(f"    modo: {modo or 'identificador no reconocido'}")
    lineas.append("\nEn este modo se trabaja con mtkclient. Comprueba con su comando "
                  "de lectura de tabla de particiones antes de escribir nada.")
    return "\n".join(lineas)
