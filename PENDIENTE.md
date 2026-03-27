# Pendiente e Mejoras — Protectora de Animales Burjassot

Prioridad: 🔴 Crítico · 🟠 Importante · 🟡 Mejora · 🟢 Opcional

---

## 🔴 Bugs / Errores actuales

### 1. Formulario de contacto no llama al backend
`js/contact.js` tiene el `fetch` real comentado. El formulario solo simula un `setTimeout` y escribe en consola. **Los mensajes nunca llegan a la base de datos.**
- **Archivo:** `js/contact.js` función `sendContactForm()`
- **Fix:** Descomentar la llamada a `POST /api/contact` y eliminar el mock.

### 2. El filtro `?type=perro` de la API no funciona
`GET /api/animals?type=perro` no filtra por tipo. La ruta solo aplica el filtro `status`.
- **Archivo:** `admin/app.py` función `api_animals()`
- **Fix:** Añadir `AND type = ?` condicional cuando el parámetro `type` esté presente.

### 3. No existe el endpoint `GET /api/animals/<id>`
`adopcion.js` y el nav enlazan a `adopcion.html?id=X` pero no hay endpoint para obtener un animal por ID.
- **Fix:** Añadir ruta `@app.route('/api/animals/<int:animal_id>')` en `app.py`.

### 4. Al editar un animal, la imagen antigua no se borra del disco
Cuando se sube una nueva imagen en el formulario de edición, la foto anterior queda huérfana en `uploads/fotos/`.
- **Archivo:** `admin/app.py` función `edit_animal()`
- **Fix:** Antes de guardar la nueva imagen, borrar el fichero anterior si existe y empieza por `uploads/`.

### 5. `new_news` no guarda los datos de publicación correctamente
El formulario de nueva noticia no tiene campo `published` (borrador vs publicado). Todo se publica directamente.
- **Archivo:** `admin/templates/news_form.html`, `admin/app.py` función `new_news()`

---

## 🔴 Páginas referenciadas en la navegación que no existen

Los enlaces del menú apuntan a páginas que no se han creado todavía:

| Archivo | Enlace desde |
|---|---|
| `pages/adoptados.html` | Nav de `adopcion.html` → "Adoptados" |
| `pages/nosotros.html` | Nav de todas las páginas → "Nosotros" |
| `pages/actualidad.html` | Nav de todas las páginas → "Actualidad" |

Al no existir, dan **404** y rompen la experiencia de usuario.

---

## 🔴 Seguridad

### 1. `app.secret_key` es débil y pública
`app.secret_key = 'cambiar_en_produccion_por_clave_segura'` — está en el código fuente.
- **Fix:** Leer desde variable de entorno: `os.environ.get('SECRET_KEY', os.urandom(32))`

### 2. Flask corre con `debug=True`
`app.run(debug=True, ...)` expone el debugger de Werkzeug en producción.
- **Fix:** `debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'`

### 3. `/api/upload` sin autenticación
Cualquiera puede subir archivos al servidor llamando directamente a `POST /api/upload`. No requiere sesión de admin.
- **Fix:** Añadir `@login_required` al endpoint o eliminarlo (ya existe la subida en los formularios de animales/noticias).

### 4. Sin validación en `POST /api/contact`
Si `name` o `email` llegan vacíos o como `None`, el `INSERT` guarda `None` en la base de datos sin error.
- **Fix:** Validar campos obligatorios y devolver 400 si faltan.

### 5. Sin protección CSRF en formularios del admin
Los formularios de admin no tienen token CSRF. Un atacante podría crear/borrar animales o noticias engañando al admin.
- **Fix:** Usar `flask-wtf` o implementar tokens CSRF manuales en los formularios.

---

## 🟠 Funcionalidades del admin pendientes

### 1. No hay ruta para editar noticias
Existe `new_news` pero no hay `edit_news` ni `delete_news`.
- **Archivos a crear/modificar:** `admin/app.py`, `admin/templates/news_form.html`
- El formulario `news_form.html` tampoco tiene modo edición (no pre-rellena campos).

### 2. No hay página de gestión de contactos
Los mensajes del formulario se muestran resumidos en el dashboard pero no hay vista completa:
- Ver el mensaje completo
- Marcar como leído / pendiente
- Responder por email

### 3. No hay modo borrador en noticias
El campo `published` existe en la BD pero no se puede gestionar desde el admin:
- Publicar / despublicar una noticia
- Guardar como borrador al crear

### 4. No hay confirmación antes de borrar
Al borrar un animal el formulario hace `POST` directo sin confirmación JavaScript.
- **Fix:** Añadir `confirm()` o un modal de confirmación antes del submit.

### 5. Sin mensajes flash de éxito/error en el admin
Después de crear o editar un animal/noticia, el usuario es redirigido sin ningún feedback visual.
- **Fix:** Usar `flask.flash()` y mostrar los mensajes en `base.html`.

### 6. No hay gestión de usuarios
Existe la tabla `users` pero no hay UI para:
- Cambiar la contraseña del admin
- Crear/eliminar usuarios adicionales

### 7. Sin paginación en listas del admin
`/admin/animals` y `/admin/news` devuelven todos los registros de una vez. Con muchos registros el rendimiento se degrada.

---

## 🟠 API — endpoints incompletos

| Endpoint | Estado | Notas |
|---|---|---|
| `GET /api/animals` | ✅ Funciona | Falta filtro por `type` |
| `GET /api/animals/<id>` | ❌ No existe | Necesario para ficha de animal |
| `GET /api/news` | ✅ Funciona | |
| `GET /api/news/<id>` | ❌ No existe | Necesario para página de noticia individual |
| `POST /api/contact` | ✅ Funciona | Sin validación |
| `PATCH /api/animals/<id>/status` | ❌ No existe | Para marcar adoptado sin entrar al formulario |

---

## 🟡 Mejoras de experiencia de usuario (frontend)

### 1. Soporte multiidioma incompleto
El selector ES/VAL solo afecta a `index.html` (vía `js/main.js`). Las páginas `adopcion.html`, `contacto.html`, `dona.html` y `colabora.html` no tienen traducciones al valenciano.

### 2. Ficha individual de animal no implementada
El botón "Conocer más" enlaza a `adopcion.html?id=X` pero no hay lógica en `adopcion.js` para detectar el parámetro `?id` y mostrar el animal preseleccionado. Requiere el endpoint `GET /api/animals/<id>`.

### 3. Página de animales adoptados
`pages/adoptados.html` no existe. Sería una galería de animales con `status = 'adopted'` usando `GET /api/animals?status=adopted`.

### 4. Filtro por tamaño en adopción
El formulario de animal tiene campo `size` (Pequeño/Mediano/Grande) pero la página de adopción no permite filtrar por tamaño.

### 5. Galería de imágenes en la ficha de animal
Actualmente solo se guarda una imagen por animal. Se podría añadir una tabla `animal_images` para múltiples fotos.

---

## 🟡 Mejoras técnicas / deuda técnica

### 1. `contact.js` conectar al backend real
Descomentar el fetch y eliminar el mock. Sección marcada con `/* ... */` en `sendContactForm()`.

### 2. `BASE_URL` hardcodeado a `localhost`
`http://localhost:5000` aparece en `adopcion.js` y `main.js`. En producción apuntaría a una URL diferente.
- **Fix:** Leer el API URL desde un `<meta>` tag o variable global inyectada desde el HTML.

### 3. Optimización de imágenes subidas
Las imágenes se guardan tal cual se suben. Si el usuario sube una foto de 10MB, así se sirve.
- **Mejora:** Añadir redimensionado automático con `Pillow` al guardar (`pip install Pillow`).

### 4. Las imágenes de muestra de la BD no existen
Los 12 animales de ejemplo tienen `image = 'images/animales/luna.jpg'` etc. Esos archivos no existen y siempre caen al SVG placeholder.
- **Fix A:** Actualizar la BD para poner `image = NULL` en los datos de ejemplo.
- **Fix B:** Añadir imágenes reales de la protectora.

### 5. Sin logging estructurado
Flask corre con el logger por defecto. Los errores de la aplicación no se guardan a fichero.
- **Fix:** Configurar `logging.FileHandler` o usar `flask.logging`.

### 6. Sin backup automático de la BD
`admin/protectora.db` es el único almacén de datos y no está en `.gitignore`.
- hay un `hacer_backup.bat` pero no se ejecuta automáticamente.

---

## 🟢 Mejoras opcionales / futuras

- **Notificaciones por email** al admin cuando llega un contacto nuevo (hay un comentario en `api_contact()` pero no está implementado).
- **Paginación en la API** con parámetros `?page=1&per_page=12` para escalar.
- **Búsqueda de noticias** en la futura `actualidad.html`.
- **Mapa de ubicación** en `contacto.html` (Google Maps embed o Leaflet.js).
- **SEO / Open Graph** — las páginas no tienen meta tags `og:image`, `og:description` para compartir en redes.
- **PWA** — añadir `manifest.json` y service worker para soporte offline básico.
- **Favicon** — no hay `favicon.ico` ni `<link rel="icon">` en los HTML.
- **Exportar contactos** a CSV desde el panel admin.
- **GDPR / aviso de cookies** — la web no tiene banner de cookies ni política de privacidad enlazada correctamente.

---

## Resumen de prioridades

```
IMPLEMENTADO ✅:
  [x] Conectar contact.js al backend real
  [x] Crear páginas faltantes (adoptados, nosotros, actualidad)
  [x] Endpoint GET /api/animals/<id>
  [x] Endpoint GET /api/news/<id>
  [x] Filtro ?type= en /api/animals
  [x] Edit/delete de noticias en el admin
  [x] Página de gestión de contactos
  [x] Modo borrador en noticias
  [x] Mensajes flash en el admin
  [x] Cambio de contraseña
  [x] secret_key desde variable de entorno
  [x] Quitar debug=True
  [x] Autenticación en /api/upload
  [x] Validación en /api/contact
  [x] CSRF en formularios admin
  [x] Borrar imagen antigua al editar/eliminar animal o noticia
  [x] Filtro por tamaño en adopcion.html
  [x] ?id= en adopcion.html carga la ficha directamente

PENDIENTE (mejoras opcionales):
  [ ] Notificaciones por email al recibir contacto
  [ ] Paginación en la API y en el admin
  [ ] Imágenes de muestra en la BD → null o añadir fotos reales
  [ ] Optimización de imágenes subidas (redimensionar con Pillow)
  [ ] SEO / Open Graph meta tags
  [ ] Favicon
  [ ] Mapa en contacto.html
  [ ] Exportar contactos a CSV
```
