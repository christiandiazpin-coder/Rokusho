# Rokusho-001 — Lenovo TB-X306F, 2 GB / 32 GB

Primer Rokusho de campo: devolver a la vida una **Lenovo Tab M10 HD (2ª gen)**,
modelo **TB-X306F**, variante **2 GB de RAM / 32 GB de almacenamiento**.

Estado a 2026-11-05: agente y herramientas listos, plan corregido contra la
guía específica de esta variante. **La tablet todavía no se ha conectado.**

## Corrección importante respecto a la primera versión de este documento

En la primera versión afirmé que, al ser MediaTek, el desbloqueo obligatoriamente
iba por **BROM** con `mtkclient` y que si el BROM estaba protegido había que
abrir la tablet.

**Eso era una generalización mía, y para esta variante es incorrecta.** La guía
específica del modelo 2/32 GB (hilo de XDA dedicado) describe el desbloqueo por
**`fastboot flashing unlock`**, confirmando con volumen arriba en la pantalla.
`mtkclient` sigue disponible como plan B, pero no es el primer camino.

La lección vale para el proyecto: «MediaTek ⇒ BROM» es una regla general que se
rompe en casos concretos. La ficha ahora cita la fuente del modelo, no una
deducción por fabricante.

## La ficha del aparato

| Dato | Valor |
|---|---|
| Nombre comercial | Lenovo Tab M10 HD (2ª gen), Wi-Fi |
| Procesador | MediaTek Helio P22T (MT8768T), 8× Cortex-A53 |
| Gráficos | IMG PowerVR GE8320 |
| Memoria | **2 GB** LPDDR4X / **32 GB** eMMC |
| Pantalla | 10,1", 1280×800 |
| Android de fábrica | Android 10 (API 29) |
| Treble / GSI | sí, admite imagen genérica de sistema |
| Tipo de particiones | **a-only (no SAR)** — importante para elegir la imagen |

Fuentes: ficha del fabricante (PSREF de Lenovo) y el hilo de XDA
«Attempting to install GSI on 2nd Gen Lenovo Tab M10 HD (X306F 2/32GB)».

## Lo que cambia tener 2 GB en vez de 4

No es un detalle: es la diferencia entre «funciona bien» y «funciona, pero se
siente lento». Consecuencias prácticas:

1. **Hay que usar una compilación con ZRAM activado.** En el hilo del modelo se
   reporta una build que baja a la mitad el uso de memoria precisamente por eso.
   Una ROM sin ZRAM en este equipo queda inutilizable.
2. **microG en vez de GApps.** Los servicios de Google pesan demasiado para 2 GB;
   la propia guía del modelo terminó recomendando microG.
3. **La expectativa honesta:** sirve para navegar, leer, ver video y usar apps
   simples. No sirve para multitarea ni para juegos. **No va a quedar como nueva**:
   el Helio P22T con 2 GB es lo que es.

## Las dos trampas documentadas de este modelo

Son las que hacen fracasar los intentos y conviene saberlas antes:

1. **Las compilaciones de LineageOS NO son compatibles con TWRP.** Hay que usar
   el **recovery que viene dentro del ZIP de instalación**. Varias personas
   perdieron tardes enteras flasheando TWRP antes de descubrirlo.
2. **Las particiones son a-only (no SAR).** Una GSI genérica del tipo A/B no
   arranca: queda en bucle. Con la imagen equivocada el síntoma es un bootloop,
   que se recupera desde fastboot.

También hay un reporte de que el equipo **se apaga al transferir más de ~1 GB**
por ADB en algunos casos. Se mitiga usando `adb sideload` desde el recovery (que
es el método que describe la guía) en vez de empujar la imagen por otro medio.

## El plan, en orden

### Fase 0 — antes de tocar nada (sin la tablet conectada)

- [ ] Cargar la tablet por sobre el 60 %.
- [ ] **Respaldar los datos** si todavía arranca (fotos, cuentas, lo que haya).
- [ ] Activar **Opciones de desarrollador** (7 toques en «Número de compilación»).
- [ ] Activar **Depuración USB** y **Desbloqueo de OEM**. Sin «Desbloqueo de OEM»
      activado, `fastboot flashing unlock` se rechaza.

### Fase 1 — leer el aparato (solo lectura)

1. `listar_dispositivos` → debe aparecer la serie y el estado `device`.
2. `identificar <serie>` → modelo, versión de Android, arquitectura reales.
3. `estado_arranque <serie>` → si ya está desbloqueado o no.
4. `ficha` con el modelo leído → confirmar que es la variante 2/32.

**Aquí se decide.** Si el modelo leído no es TB-X306F, todo el plan cambia.

### Fase 2 — respaldo

- [ ] Volcado de las particiones con `mtkclient` en modo lectura (o al menos,
      copia de lo que haya en almacenamiento interno).
- [ ] **Sin respaldo verificado no se escribe nada.**

### Fase 3 — desbloqueo

```bash
adb reboot bootloader
fastboot flashing unlock        # confirmar con volumen arriba en la tablet
fastboot reboot
```

**IRREVERSIBLE en la práctica:** se borran los datos de usuario y aparece el aviso
de arranque desbloqueado en pantalla. Algunas apps con verificación de integridad
(banca, DRM de streaming) pueden dejar de funcionar.

### Fase 4 — recovery y sistema

```bash
adb reboot bootloader
fastboot flash recovery recovery.img     # el que viene DENTRO del ZIP, no TWRP
fastboot reboot recovery
# en el recovery: Apply update → from ADB
adb sideload <lineage>.zip
# luego: Factory reset → Format data
# y finalmente el kernel con ZRAM, por sideload
```

Al final, instalar **microG** y **KernelSU Next** como APK (no por sideload).

### Fase 5 — verificación

- [ ] El equipo arranca y llega al escritorio.
- [ ] WiFi conecta (hay reportes de problemas; la red debe usar WPA2-PSK).
- [ ] Uso de memoria en reposo: si está por sobre ~1,3 GB de 2 GB, la build no
      tiene ZRAM y no sirve para este equipo.
- [ ] Grabar un video de 10 segundos: si se traba, la variante no da para más.

## Herramientas instaladas en este equipo

| Herramienta | Ruta | Estado |
|---|---|---|
| adb | `~/.local/opt/platform-tools/adb` | 37.0.1 |
| fastboot | `~/.local/opt/platform-tools/fastboot` | 37.0.1 |
| mtkclient | `~/.local/opt/mtkclient/mtk.py` | 2.1.4 (plan B) |
| venv propio | `~/.local/opt/mtk-venv` | aislado del de Umbra |

Sin root y sin tocar el sistema. Nota: mtkclient necesita `pycryptodomex`
(instala `Cryptodome`), no `pycryptodome` (instala `Crypto`).

## Lo que falta para arrancar

- [ ] Conectar la tablet con Depuración USB activada
- [ ] Confirmar que «Desbloqueo de OEM» está activado
- [ ] Decidir si se acepta el borrado de datos del desbloqueo

## Riesgos abiertos

- **Nada de este flujo se ha probado contra el aparato real.** Está validado
  contra la guía del modelo, no en ejecución.
- **El autor del plan es el mismo que escribió las herramientas.** La ficha viene
  de fuentes públicas; puede haber subvariantes con otro firmware.
- **La guía de referencia es de la comunidad, no oficial.** Funcionó para varias
  personas en ese hilo, y para otras falló en el último paso.
- **No hay política de aprobación para escrituras.** Antes de la fase 3 hay que
  definir cómo se pide el visto bueno.
