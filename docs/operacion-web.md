<!-- coderabbit-ai-generated:v1 -->

# Operación de la pieza web

La pieza acepta HTTP y HTTPS. Por defecto rechaza direcciones locales, privadas y otras direcciones no públicas. Valida todas las direcciones DNS y comprueba cada redirección. Se conecta directamente a una dirección verificada, sin volver a resolver el nombre; HTTPS conserva la validación del certificado y del nombre original.

Si se necesita una dirección interna de confianza, la persona que ejecuta Rokusho puede autorizar IP concretas:

```bash
export ROKUSHO_WEB_IPS_PERMITIDAS=127.0.0.1,192.168.1.50
```

La excepción permite cualquier puerto y sitio servido desde esas IP, incluidas las redirecciones hacia ellas. Úsala solo para redes y servicios de confianza. Sin la variable no hay excepciones. Una lista inválida bloquea las consultas.

La pieza realiza conexiones directas y no utiliza las variables de proxy del sistema. Solicita contenido sin compresión y rechaza respuestas comprimidas. Algunos sitios o redes que exijan un proxy podrían necesitar una integración adicional. El contenido descargado sigue siendo información no confiable: las marcas del texto y la revisión humana no garantizan que el modelo ignore instrucciones maliciosas.
