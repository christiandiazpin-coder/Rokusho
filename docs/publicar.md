# Publicar la página de venta sin gastar

La página está pensada para esto: **un solo archivo, cero dependencias**. No
carga CSS remoto, ni fuentes de Google, ni JavaScript. Pesa 12 KB y funciona
abierta desde un pendrive.

Eso la hace desplegable en cualquier host estático gratuito, y también en un
servidor propio el día que lo tengas.

## Qué se publica

```
docs/
├── venta.html              ← la página
├── muestra/
│   └── ejemplo-informe.html ← el informe de muestra
└── precio-y-venta.md       ← NO publicar (uso interno)
```

`precio-y-venta.md` es un documento de trabajo: dice que los precios no están
validados por el mercado. Eso es para ti, no para el cliente.

## Antes de publicar: dos cosas que corregir

### 1. El enlace a la muestra

La página no enlaza al informe de muestra, y es lo que más vende: el cliente
puede abrir un entregable real antes de escribir. Se añade un enlace.

### 2. El correo expuesto

`mailto:` en texto plano lo cosechan los robots de spam. Hay dos salidas:

- **Un formulario** (requiere un servicio, aunque sea gratuito), o
- **El correo escrito de forma que un humano lo lea y un robot no**
  (`christiandiazpin [arroba] gmail.com`), sabiendo que pierdes el clic directo.

Para el primer cliente conviene el clic directo. El spam se resuelve después;
perder el contacto no.

## Opciones gratuitas, comparadas

| Opción | Coste | A favor | En contra |
|---|---|---|---|
| **GitHub Pages** | Gratis | Ya tienes cuenta; versionado; HTTPS | URL `usuario.github.io/rokusho` |
| **Netlify** | Gratis | Arrastrar carpeta y listo; formularios gratis | Requiere cuenta nueva |
| **Cloudflare Pages** | Gratis | Rápido; HTTPS; sin límite de ancho de banda | Requiere dominio propio para lo bueno |
| **Vercel** | Gratis | Despliegue desde Git | Pensado para apps, no para una página |

**Recomendación: GitHub Pages.** Ya tienes el repo de Rokusho, la página queda
versionada junto al código, y el día que compres un dominio solo cambias el DNS.

## Cómo publicarlo en GitHub Pages

### Paso 1 — dejar la página como índice

GitHub Pages sirve `index.html` en la raíz de la rama que publiques. Hay dos
caminos:

**A. Rama `gh-pages` (no toca la rama principal de trabajo):**

```bash
cd rokusho
git checkout --orphan gh-pages
git rm -rf .
cp docs/venta.html index.html
mkdir -p muestra && cp docs/muestra/ejemplo-informe.html muestra/
git add index.html muestra/
git commit -m "Página de venta"
git push origin gh-pages
git checkout main
```

**B. Carpeta `/docs` en la rama principal:**

En GitHub → Settings → Pages → Source: «Deploy from a branch», rama `main`,
carpeta `/docs`. Pero serviría `docs/index.html`, así que hay que renombrar
`venta.html` a `index.html`.

El camino **A** es más limpio: no mezcla la página publicada con la
documentación interna.

### Paso 2 — activar Pages

Settings → Pages → Branch: `gh-pages`, carpeta `/ (root)` → Save.

Queda en `https://<usuario>.github.io/rokusho/`.

### Paso 3 — verificar que no se publicó lo interno

Abrir la URL y confirmar que:

- [ ] La página carga y se ve igual que en local
- [ ] El enlace de la muestra abre el informe
- [ ] El botón de contacto abre el correo con el asunto puesto
- [ ] **`precio-y-venta.md` NO es accesible** (`.../precio-y-venta.md` debe dar 404)

Ese último punto importa: si se publica la carpeta `docs/` entera, el documento
interno queda expuesto, y ahí dice que los precios no están validados.

## El día que compres dominio

`rokusho.com` está tomado desde 2015 (expira en 2027, con bloqueos de dominio
activo). `rokusho.org` y `roksho.com` también. **`rokusho.net` estaba libre** al
momento de escribir esto.

Para vender a empresas chilenas, `rokusho.cl` da más confianza que cualquier
`.com`, y se consulta en NIC Chile.

Advertencia sobre las ofertas de «$1 el primer año»: la renovación de `.com`
ronda 15-20 USD anuales, y las extensiones baratas (`.info`, `.online`) suelen
renovarse bastante más caras. El precio que importa es el del segundo año.

## Lo que hay que medir después de publicar

Una página sin visitas no valida nada. Lo mínimo:

- [ ] Cuántas visitas recibe (GitHub Pages no da estadísticas; hay que añadir un
      contador externo o mirar los logs de Netlify si se usa esa opción)
- [ ] Cuántos clics al correo
- [ ] **Cuántos correos reales llegan** — ese es el único número que importa

Si en un mes no llega ningún correo, el problema no es el host: es el mensaje o
el canal por donde se comparte la página.
