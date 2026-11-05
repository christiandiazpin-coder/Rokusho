# Rokusho

Chasis modular de agentes. Un solo motor; le cambias la **medalla** y cambia de oficio.

```
chasis/          el motor: no sabe de ningún rubro
medallas/        el saber: qué sabe el agente y cómo habla
piezas/          el trabajo: qué puede hacer de verdad
```

Un agente es la combinación de tres cosas que se eligen al armarlo:

| Pieza del Medabot | En el código | Qué hace |
|---|---|---|
| Chasis | `chasis/agente.py` | Orquesta el turno: llama al modelo, ejecuta herramientas, devuelve el resultado |
| Medalla | `medallas/<rubro>/medalla.toml` | Define persona, vocabulario, reglas y prohibiciones del rubro |
| Piezas | `piezas/<nombre>/` | Implementa las herramientas que el agente puede usar |

Ninguna de las tres está cableada. Cambiar de rubro es cambiar de carpeta.

## Arrancar

Hace falta Python 3.11 o superior (`tomllib`). Sin dependencias más allá de
`requests` y, para la pieza de medios, `PIL` y `numpy`.

```bash
# Qué hay instalado
python -m chasis.cli medallas
python -m chasis.cli piezas

# Ver el prompt de sistema que se armaría (no llama al modelo)
python -m chasis.cli ver --medalla documentos --piezas archivos

# Darle un encargo de verdad
python -m chasis.cli trabajar \
    --medalla documentos --piezas archivos \
    --carpeta ./ejemplos/cliente \
    --encargo "Resume el contrato e indica de dónde sale cada dato"
```

## El motor de IA

Por defecto usa **DeepSeek** (`deepseek-ai/deepseek-v4.1-flash-1017`), pero
cualquier proveedor compatible con el formato OpenAI sirve.

```bash
# DeepSeek (por defecto) lee DEPLOY_API_KEY
export ROKUSHO_PROVEEDOR=openrouter
export OPENROUTER_API_KEY=...
export ROKUSHO_MODELO=google/gemma-4-31b-it:free

# O cualquier endpoint propio
export ROKUSHO_PROVEEDOR=local
export ROKUSHO_BASE_URL=http://localhost:1234/v1
export ROKUSHO_MODELO=modelo-local
```

La clave nunca se escribe en un log. Si falta, el chasis falla al arrancar y
dice qué variable definir; no arranca a medias.

## Cómo se escribe una medalla

`medallas/mi-rubro/medalla.toml`:

```toml
nombre = "mi rubro"
version = "0.1.0"
descripcion = "Una línea: qué hace este agente."

persona = """
Quién es y cómo trabaja. Qué le importa y qué no negocia.
"""

vocabulario = ["término del rubro: qué significa aquí"]

reglas = ["Lo que el agente debe hacer siempre."]

prohibido = ["Lo que no debe hacer nunca."]
```

Regla del proyecto: **cada prohibición nace de un error real**, no de una
suposición. Una medalla que prohíbe cosas que nunca pasan ocupa contexto y no
protege de nada.

## Cómo se escribe una pieza

`piezas/mi-pieza/pieza.toml` declara las herramientas; `implementacion.py` las
implementa. El chasis falla en voz alta si una declara algo que no existe.

```toml
nombre = "mi-pieza"
version = "0.1.0"
descripcion = "Qué puede hacer."

herramientas = [
  { nombre = "hacer", funcion = "hacer", descripcion = "Qué hace y cuándo usarla.",
    parametros = { texto = "string" } },
]
```

Si la pieza necesita saber dónde trabajar, define `configurar(carpeta)`.
El chasis la llama por referencia al módulo ya importado (reimportar el archivo
crearía otra copia con sus propias variables globales, y la configuración se
aplicaría a la copia que nadie usa).

## El conjunto base

Cinco piezas que todo negocio usa el primer día, más las de oficio:

| Pieza | Para qué | Verificación |
|---|---|---|
| `archivos` | Leer lo que el cliente ya tiene | solo lectura, no sale de su carpeta |
| `informe` | Producir el entregable | HTML imprimible o Markdown |
| `calculo` | Hacer cuentas exactas | `Decimal`, sin `eval` |
| `memoria` | Recordar entre sesiones | cada dato con su fuente |
| `web` | Consultar fuera | rechaza `file://`, marca el contenido externo |

Y las de oficio: `medios` (medir audio y video) y `dispositivo` (identificar
un Android).

## Lo que ya está probado

- **Documentos**: leyó un contrato y separó dato verificado, dato deducido y
  vacíos. Calculó el total anual marcándolo como cálculo propio.
- **Agenda**: detectó un choque de horario de 60 minutos y se negó a inventar
  días y horas que no tenía.
- **Producción audiovisual**: revisó un máster, midió audio y video, y encontró
  un defecto de veredicto en la propia herramienta de medición.

## Rokusho Umbra

El primer Rokusho con oficio: **producción audiovisual documental**. Es el equipo
de 13 agentes del proyecto GrokBot-Multimedia-Agent, que pasa a llamarse
**Rokusho Umbra**. Su medalla es `medallas/produccion-audiovisual/`.

La relación entre los dos proyectos: Umbra es un Rokusho con la medalla
audiovisual puesta y muchas más piezas. Este repo es el esqueleto del que Umbra
sale.

## Principios

1. **No inventar.** «No lo tengo» es una respuesta válida. Un dato inventado
   cuesta más que un dato faltante.
2. **Fallar en voz alta.** Una medalla a medio cargar produciría respuestas del
   rubro equivocado; eso es peor que un error visible.
3. **Medir, no opinar.** Un render no está listo porque el archivo exista, sino
   porque la medición lo confirma.
4. **Cada regla nace de un fallo real.** Si una prohibición no evita un error que
   ya ocurrió, sobra.

## Pruebas

```bash
python -m pytest pruebas/ -q
```

133 pruebas. Cubren el chasis (carga de medallas y piezas, ejecución del agente,
herramientas que fallan sin tumbar el turno), las cinco piezas base y la de
medios. La pieza `web` se prueba contra un servidor HTTP local, no contra
internet: una prueba que falla porque un sitio externo cambió no dice nada del
código.
