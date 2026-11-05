# Guía para continuar Rokusho

Este documento existe para que otra persona —o otra IA— pueda tomar el proyecto
sin que se le explique desde cero. Dice qué está hecho, qué no, y qué se decide
antes de escribir una línea.

Estado a 2026-11-05: chasis funcionando, 26 pruebas en verde, tres medallas y dos
piezas reales probadas contra un proveedor de IA en producción.

## Qué es Rokusho, en una frase

Un motor de agentes que no sabe de ningún rubro: el oficio se le pone encima con
una **medalla** y el trabajo con **piezas**. Cambiar de salud a finanzas no es
reescribir el sistema: es cambiar una carpeta.

## Mapa del código

| Archivo | Qué hace | Dónde se toca |
|---|---|---|
| `chasis/config.py` | Proveedor, modelo, claves | Para cambiar de motor de IA |
| `chasis/medalla.py` | Carga y valida medallas | Para agregar campos a la medalla |
| `chasis/pieza.py` | Carga piezas e importa su código | Para agregar campos a la pieza |
| `chasis/ia.py` | Habla con el proveedor, reintenta | Para cambiar el protocolo |
| `chasis/agente.py` | El turno: prompt, herramientas, bucle | Para cambiar cómo trabaja el agente |
| `chasis/cli.py` | La puerta de entrada | Para agregar comandos |

Regla de diseño que ha costado caro y hay que mantener: **el chasis no menciona
ningún rubro**. Si aparece la palabra «salud» o «video» dentro de `chasis/`, algo
se filtró y hay que sacarlo a una medalla.

## Qué está probado y cómo

```bash
python -m pytest pruebas/ -q     # 26 passed
```

Las pruebas no llaman a la red: usan un cliente falso. La pieza de medios sí usa
ffmpeg, generando videos de control (negro, gris uniforme, imagen con detalle).

Lo que se probó contra el modelo real (ver `docs/mediciones.md`):

- La medalla de documentos leyó un contrato y separó verificado / deducido / vacío.
- La medalla de agenda detectó un choque de horario y se negó a inventar horas.
- La medalla audiovisual revisó un máster y encontró un defecto en la propia
  herramienta de medición.

## Las decisiones que faltan

Estas no las puede tomar quien escriba el código; son del dueño del producto.

1. **¿Cuál es la primera medalla comercial?** Hay tres universales
   (`comunicacion`, `agenda`, `documentos`) y una de oficio
   (`produccion-audiovisual`). La recomendación escrita antes era empezar por
   documentos, porque se le vende rápido a una pyme y se compara contra trabajo
   humano. Está sin decidir.

2. **¿El primer Rokusho de cliente es la tablet?** Se habló de Rokusho-001 como
   un agente de ingeniería inversa para darle segunda vida a una tablet vieja.
   Falta el modelo exacto del equipo.

3. **Licencia del proyecto.** Está sin definir. Importa antes de que el repo sea
   público o se entregue a un cliente.

4. **Precio.** No hay cifra escrita. Sin precio no hay venta, y sin venta el
   proyecto sigue siendo una demostración.

## Cómo agregar una medalla

1. Crear `medallas/<nombre>/medalla.toml` con `nombre`, `version`, `descripcion`,
   `persona`, y opcionalmente `vocabulario`, `reglas`, `prohibido`.
2. Correr `python -m chasis.cli ver --medalla <nombre>` para ver el prompt que
   resulta.
3. **Cada prohibición tiene que nacer de un error que ya ocurrió.** Una medalla
   que prohíbe cosas que nunca pasan gasta contexto y no protege de nada.

## Cómo agregar una pieza

1. Crear `piezas/<nombre>/pieza.toml` declarando herramientas.
2. Implementarlas en `piezas/<nombre>/implementacion.py`, con el mismo nombre que
   declara el TOML.
3. Si necesita saber dónde trabajar, definir `configurar(carpeta)`.
4. Correr `python -m chasis.cli piezas`: si declara algo que no existe, lo dice.

**Trampa ya pagada:** no reimportar `implementacion.py` para configurarla. Crea
una segunda copia del módulo con sus propias globales, y la configuración se
aplica a la copia que nadie usa. El chasis ya expone `pieza.configurar` para eso.

## Cómo se verifica que una pieza no miente

Una herramienta no está lista porque devuelva algo, sino porque lo que devuelve
coincide con la realidad. Para la pieza de medios eso significa: generar un video
de control cuyo resultado se conoce de antemano y comprobar que la herramienta
dice lo que corresponde.

Ese control encontró que el veredicto de fotograma clasificaba mal tanto un negro
pleno como una lámina oscura. Sin el control, el error habría pasado inadvertido
porque el texto de salida «sonaba» razonable.

## Riesgos abiertos

- El autor de las pruebas es el autor del chasis; los casos que no se me
  ocurrieron no están cubiertos.
- No hay límite de gasto por turno. `max_pasos` acota los turnos, no el costo.
- Las piezas actuales son de solo lectura. Una pieza que escriba necesita su
  propia política de aprobación antes de existir.
- Las medallas de agenda y documentos se probaron una vez cada una. Una corrida
  no distingue comportamiento estable de casualidad.

## Relación con Rokusho Umbra

**Rokusho Umbra** es el primer Rokusho con oficio: producción audiovisual
documental. Es el equipo de 13 agentes que antes se llamaba
`GrokBot-Multimedia-Agent`. Umbra es un Rokusho con la medalla audiovisual puesta
y muchas más piezas; este repo es el esqueleto del que sale.

Nada de Umbra se modifica desde acá. Son repos separados a propósito: el chasis
tiene que poder probarse sin arrastrar 21.000 líneas de producción de video.
