# Recolección de prospectos por región

Sistema para construir la lista de contactos de Rokusho a nivel nacional,
empezando por regiones. **Regla que no se rompe: cada ficha sale de una página
que se leyó, con su URL anotada.** Un dato de contacto inventado es peor que no
tener lista.

## Las fuentes, medidas

Se probaron los directorios chilenos de empresas. Resultado real:

| Fuente | Accesible | Trae | Problema |
|---|---|---|---|
| **yelu.cl** | ✅ Sí | Nombre, dirección, teléfono | Correo oculto tras registro |
| **serviconce.cl** | ✅ Sí | Concepción y Gran Concepción | Solo esa zona |
| amarillas.emol.com | ❌ No | — | Requiere JavaScript |
| amarillas.cl | ❌ No | — | Requiere JavaScript |
| 2x3.cl | ❌ No | — | Requiere JavaScript |
| cylex.cl | ❌ No | — | Requiere JavaScript |
| infoisinfo.cl | ❌ No | — | Requiere JavaScript |
| Mercado Público | ❌ No | — | Requiere JavaScript |

**Conclusión medida:** solo `yelu.cl` sirve de forma programática para todo el
país. Trae nombre, dirección y **teléfono**. El correo está oculto.

## Consecuencia práctica: el canal

Si no hay correo, hay tres canales:

1. **Teléfono / WhatsApp** — el directorio los da. Para pymes de región, una
   llamada funciona mejor que un correo frío.
2. **Sitio web** — muchas fichas tienen enlace. Se visita y se busca el correo
   de contacto ahí, que sí es público.
3. **LinkedIn** — manual, buscando el nombre de la empresa.

**Recomendación:** empezar por el sitio web de cada empresa. Es el correo que la
propia empresa publica para que le escriban, y es verificable.

## El proceso, en cuatro pasos

### Paso 1 — Recolectar (por región)

```bash
python -m herramientas.prospectos --ciudad concepcion --salida prospectos.csv
```

Lee el directorio, extrae las fichas y arma un CSV. Cada fila lleva **la URL de
donde salió**.

### Paso 2 — Enriquecer (buscar el correo en el sitio)

Para cada ficha con sitio web, visitar la página de contacto y buscar un correo
publicado. Solo se acepta un correo **encontrado literalmente en la página**.

### Paso 3 — Clasificar

Una ficha sin correo no se descarta: pasa a la lista de llamadas. Una ficha sin
sitio web ni correo queda como «baja prioridad».

### Paso 4 — Escribir

El agente de marketing redacta un mensaje por destinatario, con la medalla
`marketing` y la pieza `calculo` para verificar el largo.

## Las regiones, por orden

| Orden | Región | Por qué |
|---|---|---|
| 1 | **Valparaíso** | Es donde vive Christian. Cercanía real, y se puede ofrecer reunión presencial |
| 2 | **Biobío** (Concepción) | Segundo polo empresarial del país; el directorio trae 22 fichas |
| 3 | **Maule** (Talca) | Agricultura y agroindustria: muchos contratos que nadie lee |
| 4 | **Antofagasta** | Minería; empresas proveedoras con volumen de documentación |
| 5 | **La Araucanía** (Temuco) | Menos competencia de consultoría |
| 6 | **Coquimbo** (La Serena) | Turismo y servicios |

Santiago **al final**: hay cientos de consultoras con el mismo discurso y es el
mercado más caro de entrar.

## Qué decir en cada región

El mensaje no cambia en la estructura, cambia en el gancho:

- **Regiones con agroindustria:** contratos de suministro, de temporada, de
  arriendo de campos.
- **Regiones mineras:** contratos de servicios, órdenes de compra, actas de
  recepción.
- **Regiones turísticas:** contratos de arriendo comercial, licencias, permisos.

El gancho de regiones, que es la ventaja real:

> «Trabajo desde Villa Alemana, no desde Santiago. Si nos sirve, nos podemos
> juntar.»

En regiones, la cercanía pesa más que el precio.

## Reglas de integridad de la lista

1. **Cada ficha tiene su URL de origen.** Sin URL, la ficha se borra.
2. **Ningún correo se adivina.** Ni `contacto@`, ni `info@`, ni patrones
   inventados. Solo lo que la empresa publica.
3. **Ningún dato se completa «por parecido».** Si el directorio dice «Asesorías
   previsionales», no se convierte en un nombre de fantasía.
4. **Las bajas se respetan.** Si alguien pide no ser contactado, se marca y no
   se vuelve a escribir.

## Lo que este sistema no hace

- No envía nada. El envío es manual y con aprobación.
- No scrapea redes sociales ni datos personales.
- No compra bases de datos.
- No adivina correos.

Todo lo que produce está en un CSV que se puede auditar fila por fila.
