# Rokusho-001 — Lenovo TB-X306F

Primer Rokusho de campo: devolver a la vida una **Lenovo Tab M10 HD (2ª gen)**,
modelo **TB-X306F**, la tablet que estaba guardada.

Estado a 2026-11-05: agente armado, herramientas instaladas, plan de 9 pasos
validado contra el modelo. **La tablet todavía no se ha conectado**, así que no
hay ningún dato leído del aparato.

## La ficha del aparato (verificada en fuentes públicas)

| Dato | Valor |
|---|---|
| Nombre comercial | Lenovo Tab M10 HD (2ª gen), Wi-Fi |
| Procesador | MediaTek Helio P22T (MT8768T), 8× Cortex-A53 |
| Gráficos | IMG PowerVR GE8320 |
| Memoria | 2 o 4 GB LPDDR4X / 32 o 64 GB eMMC |
| Pantalla | 10,1", 1280×800 |
| Android de fábrica | Android 10 (API 29) |
| Treble / GSI | sí, admite imagen genérica de sistema |

Fuentes: ficha del fabricante (PSREF de Lenovo), foro XDA del modelo y guías
públicas de la comunidad.

## La decisión que cambia todo: es MediaTek

En un Qualcomm se desbloquea con `fastboot oem unlock`. **En MediaTek no.** El
desbloqueo va por **BROM**, el modo de arranque de bajo nivel, con `mtkclient`.

Y aquí está el riesgo real del proyecto: si el BROM está **protegido**, no se
entra por software. Hay que **abrir la tablet** y usar un punto de prueba (test
point). Eso convierte el proyecto en desarmar el equipo.

Ningún plan que ignore esto es honesto. Puede que salga fácil o puede que haya
que abrirla; se sabrá en el paso 4.

## Los tres desenlaces posibles

Son tres, y los tres son resultados válidos:

1. **BROM accesible** → se puede desbloquear, respaldar e instalar una GSI.
   Es el buen caso.
2. **BROM protegido** → hay proyecto solo si se acepta abrir la tablet. Si no,
   el resultado es «no se puede sin desarmarla».
3. **Sin GSI útil para el equipo** → se puede desbloquear pero no hay sistema
   publicado que valga la pena. Se dice antes de escribir nada.

## Expectativa honesta sobre el resultado

La variante de **2 GB de RAM va justa**. La de 4 GB da buen resultado con una
GSI liviana. En ninguna de las dos «queda como nueva»: el rendimiento lo pone el
Helio P22T, no el sistema operativo. Lo que sí se gana es un Android moderno con
parches, en vez de un Android 10 sin soporte.

## Lo que hay instalado en este equipo

| Herramienta | Ruta | Estado |
|---|---|---|
| adb | `~/.local/opt/platform-tools/adb` | 37.0.1, funciona |
| fastboot | `~/.local/opt/platform-tools/fastboot` | 37.0.1, funciona |
| mtkclient | `~/.local/opt/mtkclient/mtk.py` | 2.1.4, funciona |
| entorno de mtkclient | `~/.local/opt/mtk-venv` | propio, no toca el de Umbra |

Se instalaron **sin root y sin tocar el sistema**: todo vive en `~/.local/opt`.

Nota: mtkclient necesita `pycryptodomex`, no `pycryptodome`. El segundo instala
el paquete `Crypto`; mtkclient importa `Cryptodome`, que solo trae el primero.
Ese detalle costó un rato y está anotado para no repetirlo.

## Cómo se usa

El agente necesita el PATH con adb y fastboot:

```bash
export PATH="$HOME/.local/opt/platform-tools:$PATH"
cd "/run/media/Kainsevenfold/Nuevo vol/Workspace/rokusho"
"<venv>/python" -m chasis.cli trabajar \
  --medalla revivir-dispositivos --piezas dispositivo \
  --encargo "Revisa la tablet conectada y dime en qué estado está"
```

O directamente las herramientas, sin el agente:

```bash
cd "/run/media/Kainsevenfold/Nuevo vol/Workspace/rokusho"
"<venv>/python" -c "
import sys; sys.path.insert(0,'.')
from chasis.pieza import cargar
p = cargar('dispositivo')
for h in p.herramientas:
    print('='*20, h.nombre); print(h.funcion() if not h.parametros else '')
"
```

## El plan de 9 pasos

El agente lo produce tal cual; resumido:

1. **Preparación** (sin conectar): cargar la tablet sobre 60 %, respaldar los
   datos de la usuaria, activar Depuración USB en Opciones de desarrollador.
   Riesgo: ninguno.
2. **Conectar y listar** con `listar_dispositivos`. Debe verse la serie y el
   estado `device`. Riesgo: ninguno.
3. **Estado del arranque** con `estado_arranque`. Es el dato que decide si el
   proyecto existe. Riesgo: ninguno.
4. **Comprobar modo MTK** con `modo_mtk`: apagar la tablet, mantener volumen y
   conectar. Debe aparecer como BROM o Preloader. Si no aparece: cable, timing
   de teclas o permisos USB (udev). Riesgo: ninguno.
5. **Confirmar la ficha** con el modelo leído del aparato, no con el que dijimos.
6. **Decisión de viabilidad.** Aquí se para o se sigue.
7. **Respaldo completo** con mtkclient. Sin volcado verificado no se escribe
   nada. Es el paso que más gente se salta y el que permite volver.
8. **Desbloqueo.** IRREVERSIBLE: se pierden los datos de usuario, queda el aviso
   de arranque y algunas apps con verificación de integridad (banca, DRM) dejan
   de funcionar.
9. **Instalar el sistema.** Solo con el modelo confirmado y una imagen publicada
   para ese modelo. Si no existe, se dice que no existe.

## Lo que falta para arrancar

- [ ] Conectar la tablet (USB + Depuración USB activada)
- [ ] Confirmar la variante de RAM (2 o 4 GB): cambia la expectativa de resultado
- [ ] Decidir si se acepta abrir la tablet si el BROM está protegido
- [ ] Leer la etiqueta trasera para confirmar el modelo exacto

## Riesgos abiertos

- **El autor del plan es el mismo que escribió las herramientas.** La ficha del
  modelo viene de fuentes públicas, no del aparato; puede haber variantes con
  distinto BROM.
- **Nada de esto se ha probado contra el aparato real.** Todo el flujo está
  validado en lógica, no en ejecución. El primer contacto dirá mucho.
- **Las herramientas no escriben**: la pieza `dispositivo` es de solo lectura a
  propósito. El desbloqueo y el flasheo se harán con mtkclient directamente,
  con el comando a la vista antes de ejecutarlo.
- **No hay política de aprobación para escrituras todavía.** Antes del paso 8 hay
  que decidir cómo se pide el visto bueno.
