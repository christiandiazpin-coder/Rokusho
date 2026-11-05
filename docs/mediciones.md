# Registro de mediciones

Lo que sigue no es una lista de logros: son las cosas que se probaron, lo que
salió y los defectos que aparecieron. Cada defecto de esta lista se encontró
midiendo, no leyendo el código.

Fecha: 2026-11-05.

## 1. El chasis arranca y habla con un proveedor real

`deepseek-ai/deepseek-v4.1-flash-1017` vía `DEPLOY_API_KEY`. HTTP 200. 418 modelos
disponibles en OpenRouter con la misma clave, 16 gratuitos.

Defecto encontrado: el modelo devuelve el texto en `reasoning_content`, no en
`content`, cuando razona y se queda sin tokens para la respuesta. Sin respaldo,
el turno se perdía completo. Corregido en `chasis/ia.py`: se lee `content`, luego
`reasoning_content`, luego `reasoning`.

## 2. La medalla cambia el oficio (prueba central del concepto)

Mismo chasis, mismo modelo, mismo proveedor. Solo cambia la medalla.

**Medalla `documentos`**, con un contrato de 11 líneas:

> Separó «dato verificado» (850.000 pesos, cláusula TERCERO, línea 7) de «dato
> deducido» (850.000 × 12 = 10.200.000, marcado explícitamente como cálculo
> propio) y de «vacío» (no dice moneda, no menciona IVA, no indica causales de
> término). Cerró con: «no voy a redactar un resumen con cifras o cláusulas
> supuestas».

**Medalla `agenda`**, con una lista de pendientes sin horas:

> Detectó el choque de 12:00–13:00 entre dos turnos de bodega y se negó a poner
> día y hora a las tareas: «No les pongo día ni hora porque no tengo la
> disponibilidad de Ana».

El mismo motor produjo dos profesionales distintos. Eso es lo que el proyecto
afirma, y ahora está medido.

## 3. Defecto del chasis: la configuración se aplicaba a una copia del módulo

El agente no veía ningún archivo y respondía «no existe la carpeta de trabajo».

Causa: `cli.py` reimportaba `implementacion.py` para llamar a `configurar()`. Ese
segundo import creaba **otra instancia del módulo**, con sus propias variables
globales. La carpeta se fijaba en la copia y la pieza leía la original.

Comprobado:

```
mismo modulo: True
globals compartidos: False
TRABAJO pieza : .../rokusho/trabajo
TRABAJO cli   : .../rokusho/trabajo
```

Corregido: la pieza guarda una referencia a su propio `configurar` al cargarse
(`chasis/pieza.py`, `_gancho_configuracion`), y el CLI la llama por esa
referencia. Cubierto por `test_gancho_configurar_se_llama_sobre_el_modulo_de_la_pieza`.

**Lo que este fallo enseña:** el agente actuó correctamente. No inventó el
contenido del contrato, dijo qué necesitaba y por qué. El bug era del chasis, y
se vio porque el agente se negó a rellenar el hueco.

## 4. Defecto de la pieza de medios: el veredicto del fotograma estaba mal

Revisando el reel con la medalla audiovisual, el agente reportó:

> «en todos estos fotogramas el veredicto automático dice "plano con imagen",
> incluso en los de 0,00 % de píxeles claros. Ese texto no es fiable; me guío
> por las cifras».

Reproducido: `media 27.2`, `claros 0.00 %` → veredicto «plano con imagen».

Causa: el veredicto miraba solo la luminancia media (`media >= 10` = imagen).

Primer intento de arreglo: umbrales sobre media y desviación. **También estaba
mal**: clasificaba como «casi negro» el tramo 34,6–39 s del reel, que en realidad
es el gráfico «El delirio necesita dos fallas», perfectamente legible.

La causa del error: se asumió que «media baja = plano negro» sin mirar la imagen.
Al extraer los fotogramas se vio que una lámina antigua oscura tiene media 18 y
desviación 19 — se ve bien; un negro de verdad tiene desviación ~0.

Corregido: el veredicto se decide por **contraste (desviación)**, no por media.

| t (s) | media | desviación | claros | veredicto correcto |
|---|---|---|---|---|
| 2 | 142,9 | 65,9 | 49,58 % | plano con imagen |
| 17,1 | 27,2 | 17,6 | 0,00 % | imagen muy oscura con detalle |
| 35 | 17,7 | 19,3 | 0,91 % | imagen muy oscura con detalle |
| 40 | 43,2 | 26,9 | 0,03 % | plano con imagen |
| 45 | 48,8 | 41,1 | 3,14 % | plano con imagen |

Cubierto por `pruebas/test_medios.py`, que genera videos de control con ffmpeg
(negro, gris uniforme, imagen con detalle) en vez de depender de material del
proyecto.

## 5. Un error en el trabajo previo que el agente destapó

El reel `REEL-umbral.mp4` se había verificado con muestras puntuales. El agente
barrió los bordes y encontró un tramo de 0,2–0,3 s de negro pleno en 16,95–17,15 s
(un fundido entre la cita y el metraje Lumière).

En disco: el reel tiene un fundido intencional ahí. Pero **la verificación
anterior no lo había detectado** porque se muestrearon fotogramas sueltos y no
los bordes de cada corte. La lección no es que el reel esté mal: es que muestrear
el centro de un plano no dice nada sobre sus bordes.

## 6. Estado de las pruebas

```
26 passed
```

Cubren: carga de medallas (válida, inexistente, sin persona, TOML roto, tipo
equivocado), carga de piezas (declara función inexistente, sin implementación,
dos piezas con la misma herramienta), ejecución del agente (herramienta
inexistente, JSON roto, herramienta que explota, agotamiento de pasos) y la pieza
de medios (veredicto por contraste, ruta fuera del espacio de trabajo, medición
real).

## Riesgos abiertos

- **El autor de las pruebas es el autor del chasis.** Los casos límite que no se
  me ocurrieron no están cubiertos. Un tercero hostil encontraría más.
- **El agente de agenda y el de documentos se probaron una vez cada uno.** Una
  sola corrida no distingue un comportamiento estable de una casualidad.
- **No hay límite de gasto.** Una pieza con un bucle podría consumir tokens sin
  tope; `max_pasos` acota los turnos, no el costo.
- **La pieza de archivos es de solo lectura**, pero las piezas futuras que
  escriban necesitarán su propia política de aprobación.
