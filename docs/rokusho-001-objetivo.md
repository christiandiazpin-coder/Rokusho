# Rokusho-001 — objetivo real: que mi mamá vea YouTube

El objetivo del proyecto no es «instalar un sistema nuevo». Es que la tablet
Sirva para lo que su dueña hace: **ver YouTube**.

Ese cambio de encuadre cambia la recomendación. Lo que sigue es el plan bueno,
no el más impresionante.

## La conclusión primero

**No hace falta flashear para empezar.** El cuello de botella en un equipo de
2 GB no es el sistema operativo: es la **aplicación de YouTube**.

| | App oficial de YouTube | NewPipe |
|---|---|---|
| Tamaño de instalación | 100–146 MB | 10–11 MB |
| Caché que llega a ocupar | ~3 GB | Mínima |
| Procesos en segundo plano | Sí, constantes | Ninguno |
| Anuncios | Sí | No |
| Servicios de Google | Sí (obligatorios) | Ninguno |
| Inicio de sesión con cuenta | Sí | No |

Fuentes: prensa técnica (Android Police, MUO) y el sitio del proyecto NewPipe.

En un equipo con 2 GB, la app oficial más los servicios de Google consumen la
mayor parte de la memoria antes de que el usuario toque nada. NewPipe evita las
dos cosas.

## Plan A — sin riesgo (empezar aquí)

1. Encender la tablet tal como está.
2. Instalar **NewPipe** desde su sitio oficial (`newpipe.net`) o desde F-Droid.
   Se instala como APK: hay que permitir «instalar apps de origen desconocido»
   para el navegador o el gestor de archivos.
3. Usarla una tarde entera como lo haría ella.
4. **Decidir con la experiencia real, no con la teoría.**

Si va bien: **el proyecto termina aquí.** No se desbloquea nada, no se pierde
nada, no hay riesgo. Es el mejor resultado posible.

Si va lento igual, o si se quiere además tener parches de seguridad, entonces
tiene sentido el Plan B.

## Plan B — flashear (solo si el Plan A no alcanza)

Mismo flujo documentado en este archivo, con una diferencia importante: **el
destino no es «LineageOS pelado», es LineageOS + NewPipe**, sin GApps.

- Sin GApps, porque los servicios de Google son justamente lo que no cabe.
- Con microG solo si hace falta alguna app que dependa de ellos.
- Con el kernel de ZRAM, que es lo que hace usable la variante de 2 GB.

### Riesgo propio de este modelo: el WiFi

En el hilo del modelo hay varios reportes de **WiFi que no conecta tras instalar
LineageOS**. Soluciones reportadas:

- `adb shell settings put global restricted_networking_mode 0`
- Asegurarse de que la red use **WPA2-PSK** (no WPA3, no mixto)

Esto es un riesgo que **no existe** en el Plan A. Otra razón para empezar por ahí.

## Qué NO prometer

- **No va a quedar como nueva.** El Helio P22T con 2 GB es lo que es.
- **No va a reproducir video en 1080p con fluidez.** 720p es el objetivo realista
  en esta pantalla de 1280×800, y se ve bien porque es su resolución nativa.
- **No va a servir para multitarea.** Una app a la vez.

## Criterios para decidir si funcionó

Medibles, no impresiones:

- [ ] Un video de 20 minutos se reproduce sin cortes ni trabas.
- [ ] Al cambiar de video, la app responde en menos de 3 segundos.
- [ ] La tablet aguanta una hora de reproducción sin cerrar la app sola.
- [ ] Al volver a la pantalla de inicio y abrir otro video, no se reinicia la app.

Si esas cuatro se cumplen, el objetivo está logrado. Y en el Plan A se cumplen
sin haber tocado el sistema.

## Lo que queda anotado para después

- La tablet tiene Android 10 sin parches de seguridad. Para un equipo que solo
  ve YouTube en casa es aceptable; si se usa para cuentas personales, conviene
  el Plan B por ese motivo y no por rendimiento.
- Si en el futuro se quiere una app de Google concreta (Gmail, Maps), el Plan A
  no la cubre: eso ya requiere Play Store, que es lo que no cabe bien.
