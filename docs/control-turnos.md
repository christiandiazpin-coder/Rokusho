<!-- coderabbit-ai-generated:v1 -->

# Control de consumo y auditoría

Para detener solicitudes adicionales cuando el consumo acumulado informado por el proveedor alcanza un umbral, configura un entero positivo antes de ejecutar el agente:

```bash
export ROKUSHO_MAX_TOKENS_TURNO=10000
python -m chasis.cli trabajar --medalla documentos --piezas archivos --carpeta ./ejemplos/cliente --encargo "Resume el contrato"
```

Sin la variable, el comportamiento anterior se conserva. El umbral suma los tokens de entrada y salida de cada respuesta del proveedor. Si se alcanza mientras hay herramientas pendientes, el agente detiene el encargo antes de ejecutarlas y la CLI devuelve el código 4. Si el proveedor omite los datos de consumo, el agente informa que no puede controlarlo y detiene cualquier trabajo adicional.

Este control es orientativo: una respuesta puede superar el umbral, y los reintentos o peticiones fallidas podrían tener costos que el proveedor no informa. No es un límite monetario garantizado. Para un techo de gasto, configura también un límite en el proveedor. Los adaptadores que construyen `Respuesta` deben indicar `uso_disponible=True` solo cuando conocen ambos conteos de tokens.

Si la auditoría falla, la respuesta incluye un aviso y `Turno.limpio` es falso. Si falla el cálculo de procedencia, el resultado lo indica por separado. Los avisos ayudan a revisar el entregable; no reemplazan la revisión humana.
