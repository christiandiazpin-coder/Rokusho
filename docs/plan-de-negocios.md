# Plan de negocios — Rokusho

Cómo escalar de "un sistema que funciona" a "un negocio que factura".

**Advertencia sobre este documento:** el producto está construido y probado
(283 pruebas, 6 medallas, 7 piezas). **El negocio no está validado**: cero
clientes, cero ingresos, cero conversaciones comerciales. Las cifras de demanda
que aparecen aquí son **estimaciones mías**, no mediciones. Todo lo que diga
"mercado" es una hipótesis hasta que alguien pague.

---

## 1. Dónde estamos exactamente

### Lo que existe y se puede demostrar hoy

| Activo | Estado | Evidencia |
|---|---|---|
| Chasis modular | Funciona | 283 pruebas, 16 commits |
| Medallas base | 6 operativas | Probadas con modelo real |
| Piezas | 7 operativas | Con tests, incluida seguridad |
| Auditoría antialucinación | Integrada | Detecta afirmaciones sin respaldo |
| Página de venta | **Publicada** | `christiandiazpin-coder.github.io/Rokusho/` |
| Informe de muestra | Público | Generado por el sistema, datos ficticios |
| Precio definido | 8 / 18 / 45 UF | Piloto, encargo, mensual |

### Lo que NO existe

- **Un cliente.** Ni uno.
- **Una conversación comercial.** Ni una.
- **Validación del precio.** Los 8 UF son una propuesta, no un dato.
- **Prueba de que el resultado sirva** a alguien que no seas tú.

Esa lista es lo que separa un proyecto de un negocio.

---

## 2. El problema que se resuelve

No se vende "informes". Se vende **trabajo pendiente que nadie alcanza a hacer**:

- Contratos que se firman sin que nadie los lea en detalle
- Cifras que se copian a mano de una planilla a otra
- Informes que se escriben la noche antes porque no hubo otro momento

El cliente no compra un informe: compra **no tener esa deuda encima**.

### Por qué Rokusho y no otra cosa

| Alternativa del cliente | Por qué falla |
|---|---|
| Que lo haga un empleado | No tiene las horas |
| Contratar a alguien | Cuesta un sueldo por un trabajo esporádico |
| ChatGPT / IA genérica | No cita, inventa, y nadie puede verificar |
| Consultora | Cuesta 10 veces más por lo mismo |

**El diferencial verificable:** cada dato lleva la cita de dónde salió. Las
cifras están calculadas, no estimadas. Lo que falta se declara. Y el sistema
tiene una capa que audita las afirmaciones del propio agente.

Eso último — auditarse a sí mismo — **no lo hace ninguna herramienta genérica**.
Es el argumento de venta.

---

## 3. A quién se le vende

Ordenado por facilidad de cierre, no por tamaño de mercado.

### Primero: consultoras y estudios pequeños (2-15 personas)

**Por qué primero:**
- Ya venden informes: entienden el producto sin explicación
- Tienen el problema todos los meses, no una vez al año
- El dueño decide solo: no hay comité de compras
- Pagan por hora de trabajo ahorrada, que es fácil de comparar

**Cómo se les encuentra:** LinkedIn, colegios profesionales, cámaras de comercio
regionales.

### Segundo: pymes con contratos y deudas

Restaurantes, talleres, constructoras pequeñas, clínicas dentales. Tienen
contratos de arriendo, de servicios, de suministro, y nadie los ha leído.

**El gancho concreto:** "¿sabe cuándo se le renueva el contrato y con cuánto
aviso?" Si la respuesta es "creo que...", ahí hay venta.

### Tercero: estudios jurídicos y contadores

Multiplican el volumen: cada cliente suyo es un informe. Pero son más exigentes
y más lentos de convencer. **Para después de tener 3 clientes.**

### A quién NO apuntar todavía

- **Grandes empresas**: ciclos de compra de 6 meses, exigen proveedor formal.
- **Sector público**: licitaciones, garantías, experiencia previa.
- **Universidades**: presupuestos anuales y compras centralizadas.

---

## 4. El producto, escalonado

| Nivel | Precio | Qué se entrega | Para qué sirve |
|---|---|---|---|
| **Piloto** | 8 UF | 1 informe, 5-15 páginas, 5 días | Probar sin riesgo |
| **Encargo** | 18 UF | Varios documentos de un corpus | Caso de uso real |
| **Mensual** | 45 UF | Hasta 4 entregables/mes + memoria | Cliente recurrente |

### La regla de escalada

**El piloto es obligatorio.** No se vende el mensual sin piloto hecho. Razón: sin
un resultado que el cliente haya visto, el mensual es una promesa a ciegas.

### Por qué se cobra por entregable y no por hora

Por hora, el cliente negocia el tiempo y compara con un sueldo.
Por entregable, compara con **lo que cuesta hacerlo o encargarlo**, que es la
única comparación donde ganas.

---

## 5. El embudo, con números honestos

### Cuántos contactos hacen falta

Sin datos propios, uso una referencia conservadora de venta B2B por contacto
directo: **1-3% de conversión** de mensaje en frío a conversación, y **20-30%**
de conversación a piloto.

| Etapa | Tasa supuesta | Para conseguir |
|---|---|---|
| Mensajes enviados | — | 100 |
| Respuestas | 3% | 3 |
| Pilotajes vendidos | 30% | **1** |

Conclusión incómoda pero real: **hay que contactar decenas de personas para
vender el primer piloto.** Si mandas 5 correos y no pasa nada, no significa que
el producto falle.

### Lo que hay que medir desde el primer día

| Métrica | Dónde se anota | Qué indica |
|---|---|---|
| Mensajes enviados | Hoja de cálculo | Esfuerzo real |
| Respuestas | Ídem | Si el mensaje funciona |
| Conversaciones | Ídem | Si el interés existe |
| **Pilotos vendidos** | Ídem | **El único número que importa** |
| UF facturadas | Ídem | Si el precio se sostiene |

Sin esta tabla, cualquier conclusión sobre el negocio es una impresión.

---

## 6. El agente de marketing: qué hará realmente

Aclaración importante: **el agente no puede vender.** No manda correos, no
persigue clientes, no cierra. Lo que hace es **producir el material** y
**preparar el contacto**.

### Lo que el agente hace bien

1. **Escribir el texto de contacto personalizado** por destinatario, sin inventar
   pruebas ni testimonios.
2. **Preparar el argumento** según el tipo de cliente (consultora, pyme, estudio).
3. **Redactar el seguimiento** después de una reunión, con lo hablado.
4. **Convertir un caso real en material de muestra** (con datos anonimizados).
5. **Verificar el largo** de cada texto según el canal, con la pieza de cálculo.

### Lo que el agente NO puede hacer

- Enviar correos (requiere política de aprobación que aún no existe)
- Inventar casos de éxito
- Prometer plazos o precios no autorizados

### El flujo de trabajo real

```
1. Yo elijo 10 destinatarios concretos
2. El agente escribe un mensaje por destinatario, distinto cada uno
3. Yo lo reviso y lo envío desde mi correo
4. Anoto en la tabla quién respondió
5. El agente prepara el material para quien respondió
```

**El agente reduce el costo por contacto de ~20 minutos a ~3.** Eso es lo que
permite mandar 100 en vez de 10.

---

## 7. Primeros 90 días

### Mes 1 — Validar que alguien responde

- [ ] Lista de **50 consultoras y pymes** de la Región de Valparaíso, con nombre
      y contacto real. Sin lista, no hay campaña.
- [ ] El agente escribe los 50 mensajes, uno distinto por destinatario.
- [ ] Enviar 10 por semana. Anotar todo.
- [ ] **Meta:** 2 respuestas. No 2 clientes: 2 respuestas.

**Si hay cero respuestas en 30 envíos**, el problema es el mensaje o la lista.
Se cambia uno y se repite. No se concluye que "no hay mercado".

### Mes 2 — Convertir la primera respuesta en piloto

- [ ] Reunión de 20 minutos con quien respondió.
- [ ] Escuchar el problema concreto antes de ofrecer nada.
- [ ] Ofrecer el piloto a 8 UF.
- [ ] **Meta: 1 piloto vendido.** Aunque sea a precio reducido, tiene que pagarse.

**Por qué pagado y no gratis:** un piloto gratis convierte la conversación en
"a ver si me convence" y pone al vendedor a la defensiva.

### Mes 3 — Entregar y medir

- [ ] Producir el informe con el sistema.
- [ ] **Cronometrar el trabajo real**, contando la revisión humana.
- [ ] Comparar con lo que el cliente pagaba antes (tiempo o dinero).
- [ ] Pedir el segundo encargo.

**La medición crítica:** cuántas horas humanas costó. Si el piloto de 8 UF
consume 10 horas, el precio está mal y hay que subirlo o el proceso mejorar.

---

## 8. Economía del negocio

### Costos reales hoy

| Concepto | Costo |
|---|---|
| Hosting (GitHub Pages) | $0 |
| Modelos de IA (DeepSeek, saldo) | ~$0,002 por turno |
| Dominio | $0 (no comprado) |
| **Total mensual fijo** | **≈ $0** |

Esa es la ventaja real: **el costo marginal de producir un informe más es casi
cero**. Todo lo que se cobra menos el tiempo humano es margen.

### Cuánto vale tu hora

| Escenario | Ingreso | Horas | Por hora |
|---|---|---|---|
| 1 piloto/mes | 8 UF ($330.000) | 10 h | $33.000 |
| 3 pilotos/mes | 24 UF ($990.000) | 30 h | $33.000 |
| 2 mensuales | 90 UF ($3.714.000) | 40 h | $92.850 |

**El mensual es donde está el negocio**, no el piloto. El piloto sirve para
llegar al mensual.

### El techo real

Con una sola persona revisando, el techo está en **4-6 entregables al mes**
(~90-135 UF ≈ $3,7M-5,6M). Para pasar de ahí hace falta delegar la revisión, que
es otra fase y otro problema.

---

## 9. Los riesgos, sin adornos

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Nadie responde | **Alta** | Cambiar mensaje/lista, no el producto |
| El piloto no convence | Media | Medir horas; quizá el alcance es muy grande |
| El precio es alto para el mercado | Media | Bajar el piloto a 5 UF, no el valor |
| El precio es bajo y no cubre el tiempo | **Alta** | Subir a 12 UF tras los primeros 3 |
| Un cliente pide algo fuera de alcance | Alta | Decir no; el medallero no cubre todo |
| Dependencia de un solo proveedor de IA | Media | El chasis ya soporta varios |
| El agente inventa en un entregable | Baja | Auditoría integrada + revisión humana |

### El riesgo mayor, dicho claro

**Que el producto sea bueno y el negocio no exista.** Un sistema excelente que
nadie compra no es un negocio: es un proyecto. La única forma de saberlo es
contactar gente.

---

## 10. Lo que hay que decidir

Son decisiones tuyas, no del sistema:

1. **¿Cuántas horas por semana puedes dedicar a vender?** Sin eso, el plan no
   tiene fechas.
2. **¿Vas a facturar como persona o como empresa?** Afecta el precio y el IVA.
3. **¿Aceptas un piloto a precio reducido** (5 UF) para el primero, o mantienes 8?
4. **¿Cuál es la región inicial?** Valparaíso es lo lógico por cercanía.
5. **¿Cuánto tiempo le das antes de concluir que no funciona?** Recomiendo 90
   días con 50 contactos como mínimo antes de cambiar de estrategia.

---

## 11. Lo que este plan no promete

- No promete clientes. Los consigue alguien hablando con gente.
- No promete que 8 UF sea el precio correcto. Se ajusta con los primeros datos.
- No promete que el mercado quiera esto. Eso es exactamente lo que hay que
  averiguar.

Lo que sí ofrece: un producto que funciona, un precio razonado, un diferencial
verificable y un plan concreto para descubrir si alguien paga.
