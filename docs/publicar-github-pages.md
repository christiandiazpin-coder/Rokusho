# Publicar en GitHub Pages — pasos exactos

La rama `gh-pages` ya está creada en el repositorio local, con **solo** el
contenido público. Falta subirla, y eso requiere tu cuenta de GitHub: no la puedo
hacer por ti.

## Estado actual

```
rama master    ← tu trabajo: código, pruebas, documentos internos
rama gh-pages  ← solo la página, la muestra y este LEEME
```

Verificado en local: la página responde, la muestra responde, y el documento
interno de precios da **404** porque no está en esa rama.

## Paso 1 — crear el repositorio vacío en GitHub

1. Entra a <https://github.com/new>
2. Nombre: `rokusho`
3. Visibilidad: **Public** (Pages gratuito requiere repositorio público)
4. **No** marques «Add a README», ni `.gitignore`, ni licencia: el repo ya tiene
   contenido y esos archivos crearían un conflicto
5. Clic en «Create repository»

GitHub te mostrará una URL como:
`https://github.com/TU-USUARIO/rokusho.git`

## Paso 2 — conectar el repositorio local y subir

En una terminal, dentro de la carpeta del proyecto:

```bash
cd "/run/media/Kainsevenfold/Nuevo vol/Workspace/rokusho"

# Conectar el remoto (reemplaza TU-USUARIO)
git remote add origin https://github.com/TU-USUARIO/rokusho.git

# Subir primero la rama de trabajo
git push -u origin master

# Subir la página
git push origin gh-pages
```

Si te pide credenciales, GitHub ya no acepta contraseña: hay que usar un
**token de acceso personal** como contraseña. Se crea en
<https://github.com/settings/tokens> → «Generate new token (classic)» → marcar
`repo` → copiar el token y pegarlo cuando pida la contraseña.

## Paso 3 — activar Pages

1. En el repositorio: **Settings** (arriba a la derecha)
2. Menú lateral: **Pages**
3. En «Build and deployment»:
   - Source: **Deploy from a branch**
   - Branch: **gh-pages**
   - Carpeta: **/ (root)**
4. **Save**

Espera 1-2 minutos. La URL aparece en esa misma página:

```
https://TU-USUARIO.github.io/rokusho/
```

## Paso 4 — verificar (no lo saltes)

Abre la URL y comprueba:

- [ ] La página carga y se ve igual que en local
- [ ] El botón «Ver un informe completo de ejemplo» abre el informe
- [ ] El botón «Hablar del piloto» abre el correo con el asunto puesto
- [ ] `https://TU-USUARIO.github.io/rokusho/precio-y-venta.md` da **404**

El último punto es el importante: confirma que el documento interno no se publicó.

## Cómo actualizar la página más adelante

La página vive en dos sitios: el original en `docs/venta.html` (rama `master`) y
la copia publicada en `index.html` (rama `gh-pages`). Hay que mantenerlas
sincronizadas:

```bash
# 1. Editar el original
# ... editar docs/venta.html ...

# 2. Llevarlo a la rama publicada
cp docs/venta.html /tmp/venta.html
git checkout gh-pages
cp /tmp/venta.html index.html
git add index.html
git commit -m "Actualiza la pagina"
git push origin gh-pages
git checkout master
git add docs/venta.html
git commit -m "Actualiza la pagina (original)"
```

Esta duplicación es la parte fea del método. Cuando haya más cambios, conviene
automatizarlo con una acción de GitHub que copie el archivo en cada push.

## Si algo falla

**«remote origin already exists»**: ya hay un remoto. Cambiarlo con
`git remote set-url origin <url>`.

**La página da 404 tras activar Pages**: esperar más. La primera publicación
puede tardar varios minutos. Revisar en Settings → Pages si dice «Your site is
live at…».

**La página carga sin estilos**: no debería pasar —la página no tiene
dependencias externas—, pero si ocurre, comprobar que `index.html` está en la
raíz de la rama `gh-pages` y no dentro de una subcarpeta.

**El correo del botón no abre**: los enlaces `mailto:` dependen de que el
visitante tenga un cliente de correo configurado. Es una limitación del método,
no del sitio.

## Lo que falta después de publicar

Una página sin difusión no recibe visitas. El único número que importa es
**cuántos correos reales llegan**. Si en un mes no llega ninguno, el problema no
es el sitio: es a quién se lo estás mostrando.
