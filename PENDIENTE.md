# Pendiente e Mejoras — Protectora de Animales Burjassot

Prioridad: 🔴 Crítico · 🟠 Importante · 🟡 Mejora · 🟢 Opcional  
Última actualización: 27/03/2026

---

## ✅ Implementado (completo)

<details>
<summary>Ver todo lo implementado</summary>

- Conectar contact.js al backend real (`POST /api/contact`)
- Crear páginas faltantes: adoptados.html, nosotros.html, actualidad.html
- Endpoint `GET /api/animals/<id>` y `GET /api/news/<id>`
- Filtro `?type=`, `?status=` y `?limit=` en `/api/animals`
- Edit/delete de noticias en el admin (con modo borrador)
- Página de gestión de contactos en el admin
- Mensajes flash en el admin
- Cambio de contraseña del admin
- `secret_key` desde variable de entorno
- Modo debug controlado por `FLASK_DEBUG`
- Autenticación en `/api/upload`
- Validación (nombre, email, mensaje) en `POST /api/contact`
- CSRF en formularios del admin
- Borrar imagen antigua al editar/eliminar animal o noticia
- Filtro por tamaño en adopcion.html
- El parámetro `?id=` en adopcion.html carga la ficha directamente
- Rediseño completo del header: barra de nav arriba + logo/acciones abajo
- Dropdowns con CSS puro (sin JS) en escritorio; JS solo en móvil
- Hamburger menu funcional con animación X
- SVG placeholders (perro.svg, gato.svg, noticia.svg)
- 10 noticias de muestra (campañas, eventos, blog)
- **Gestión de colaboradores** — tabla `collaborators`; `POST /api/collaborate`; panel `/admin/collaborators`; formularios de socio/voluntariado/acogida/padrino/empresa conectados
- **Solicitudes de adopción** — tabla `adoption_requests`; `POST /api/animals/<id>/adopt`; panel `/admin/adoptions`; formulario inline en modal de adopcion.js
- **Cambio rápido de estado de animal** — `PATCH /api/animals/<id>/status`; select inline en tabla de animales
- **Editor Quill.js en noticias** — integrado en `news_form.html` vía CDN
- **Gestión de usuarios y roles** — tabla `users` con `role`/`is_active`; rutas `/admin/users`; roles: superadmin, editor, visor
- **Configuración del sitio** — tabla `site_settings`; ruta `/admin/settings`; `GET /api/settings` pública; carga dinámica en contacto.html
- **Paginación en el admin** — 20 animales/página y 15 noticias/página con controles de navegación
- **Favicon** — `images/favicon.svg` añadido en todas las páginas HTML
- **robots.txt** — bloquea `/admin/` y `/uploads/` de los buscadores
- **Formulario padrino/madrina** — sección de `colabora.html` conectada al backend
- **Datos de contacto dinámicos** — `contacto.html` carga email, teléfono, dirección, horario y mapa desde `/api/settings`
- **Fix imágenes de muestra** — migración en `init_db()` que limpia rutas `images/animales/*.jpg` → NULL
- **Logging a fichero** — `logging.basicConfig` con `FileHandler('admin/app.log')` + `StreamHandler`; `logger` disponible en todo `app.py`
- **Optimización de imágenes con Pillow** — helper `save_image()` redimensiona a máx 1200 px y convierte a JPEG 85%; se aplica en los 5 puntos de subida de fotos; fallback a `file.save()` si Pillow no está disponible
- **Dashboard con tarjetas clicables** — 7 tarjetas que navegan a la sección correspondiente del admin; tamaño compacto
- **BASE_URL via `<meta name="api-base">`** — todos los HTML públicos leen la URL del backend desde la meta; sin hardcoding en JS
- **i18n.js — VAL en todas las páginas** — `js/i18n.js` con diccionario ES→VAL; incluido en todos los HTML; `changeLanguage()` lo llama; selector de idioma ya funciona en todas las páginas
- **Open Graph** — meta tags `og:type`, `og:site_name`, `og:title`, `og:description` en los 8 HTML públicos
- **Sitemap.xml dinámico** — ruta `/sitemap.xml` en Flask; incluye páginas estáticas + animales en adopción + noticias publicadas; URL base desde `site_settings`
- **Exportar CSV** — botones "Exportar CSV" en contactos y colaboradores del admin; BOM UTF-8 para compatibilidad Excel
- **Rate limiting** — Flask-Limiter en `/api/contact` (5/min), `/api/collaborate` (5/min), `/api/.../adopt` (3/min); stub inocuo si no está instalado
- **Sección "En acogida" en adopcion.html** — tabs "En adopción" / "En acogida" con CSS propio; cambia el `?status=` de la API
- **Estado `reserved`** — al enviar solicitud de adopción el animal pasa a `reserved` automáticamente; badge naranja en la tarjeta; gestionable desde el admin

</details>

---

## 🟡 SEO y presencia web

| Mejora | Descripción | Estado |
|---|---|---|
| **og:image** | Imagen de previsualización en redes sociales (requiere imagen pública) | Pendiente |
| **Título dinámico** | Incluir nombre del animal o noticia en `<title>` al abrir modal | Pendiente |
| **Mapa real en contacto.html** | El iframe usa URL de ejemplo — poner URL real de Google Maps en Configuración del sitio | Pendiente |

---

## 🟢 Opcionales / futuras

| Idea | Detalle |
|---|---|
| **Notificaciones por email** | Al recibir solicitud de adopción o contacto → smtplib o SendGrid |
| **Paginación en la API pública** | `?page=1&per_page=12` para escalar |
| **Galería de varias fotos por animal** | Tabla `animal_images(animal_id, path, order)` |
| **GDPR / cookies** | Banner de cookies + página de política de privacidad |
| **PWA** | manifest.json + service worker para soporte offline |
| **Modo oscuro** | Toggle en el header, guardar en localStorage |
| **Exportar adoptados/animales a CSV** | Ampliar exportación CSV también para la tabla de animales |
| **Contraseña olvidada** | Reset por email (requiere smtplib) |
| **Multiidioma VAL ampliado** | Traducir el contenido de los artículos de noticias |

---

## Resumen de estado actual

```
BACKEND (Flask + SQLite)
  OK  CRUD completo: animales, noticias, contactos
  OK  Autenticacion admin (sesion) con roles: superadmin, editor, visor
  OK  CSRF, secret_key env, debug env
  OK  Gestion de colaboradores (socios, voluntarios, padrinos, acogida, empresa)
  OK  Solicitudes de adopcion vinculadas a animal
  OK  Estado 'reserved' — auto al recibir solicitud; gestionable en admin
  OK  Cambio rapido de estado de animal (PATCH /api/animals/<id>/status)
  OK  Paginacion en listas del admin (20 animales/pag, 15 noticias/pag)
  OK  Configuracion del sitio editable en admin (/admin/settings)
  OK  GET /api/settings publica para frontend
  OK  Logging a fichero (admin/app.log) + consola
  OK  Optimizacion de imagenes con Pillow (max 1200px, JPEG 85%)
  OK  Rate limiting: contacto/colabora/adopcion (Flask-Limiter)
  OK  Exportar CSV: contactos y colaboradores
  OK  Sitemap.xml dinamico (/sitemap.xml)

FRONTEND PUBLICO
  OK  Todas las paginas del menu creadas y enlazadas
  OK  Header rediseñado: nav arriba, logo/acciones abajo
  OK  Filtros: tipo, estado, tamaño en adopcion
  OK  Tabs "En adopcion" / "En acogida" en adopcion.html
  OK  Badge "Reservado" en tarjetas de animales reservados
  OK  Formulario de contacto conectado al backend
  OK  Formularios de colabora.html conectados al backend
  OK  Solicitud de adopcion desde la ficha de animal (formulario inline en modal)
  OK  Busqueda por nombre de animal en adopcion.html
  OK  Contacto.html carga email/telefono/direccion/horario y mapa desde API
  OK  Favicon en todas las paginas
  OK  robots.txt
  OK  Open Graph meta tags en todos los HTML
  OK  <meta name="api-base"> — sin BASE_URL hardcodeado en JS
  OK  i18n.js — selector ES/VAL funciona en todas las paginas

PANEL ADMIN
  OK  Animales (nuevo, editar, borrar, imagen, cambio rapido de estado incl. reserved, paginacion)
  OK  Noticias (nuevo, editar, borrar, borrador/publicado, editor Quill.js, paginacion)
  OK  Contactos (lista, marcar leido, borrar, exportar CSV)
  OK  Colaboradores (lista, filtros tipo/estado, cambio estado inline, eliminar, exportar CSV)
  OK  Solicitudes de adopcion (lista, filtros, cambio estado inline, eliminar)
  OK  Configuracion del sitio (datos de contacto, redes sociales, mapa, site_url)
  OK  Usuarios y roles (crear, editar, activar/desactivar, eliminar)
  OK  Dashboard con tarjetas clicables que navegan a cada seccion
  OK  Cambiar contraseña
```


La sección "Hazte padrino/madrina" sigue redirigiendo a `adopcion.html`. Conectar con un formulario inline similar al de socio/acogida.

---

## 🟡 Mejoras técnicas

### 1. Optimización de imágenes con Pillow

Las imágenes se guardan sin redimensionar. Una foto de 8MB se sirve tal cual.

- **Fix:** `pip install Pillow` y redimensionar a máximo 1200px en `app.py` al guardar.

### 2. `BASE_URL` hardcodeado a `localhost:5000`

Aparece en `adopcion.js`, `main.js`, `actualidad.html`, `adoptados.html`, `nosotros.html`.

- **Fix:** Usar `<meta name="api-base" content="...">` en el HTML y leerlo desde JS.

### 3. Multiidioma completo (VAL)

El selector ES/VAL solo funciona en `index.html`. Las demás páginas no tienen traducciones.

- **Fix:** Extraer `translations` a `js/i18n.js` e implementarlo en cada página.

### 4. Imágenes de muestra → null en la BD

Los 10 animales de ejemplo tienen rutas de imagen que no existen.

- **Fix SQL:** `UPDATE animals SET image = NULL WHERE image LIKE 'images/animales/%'`

### 5. Sin logging a fichero

Los errores de Flask solo van a la consola.

- **Fix:** Configurar `logging.FileHandler('admin/app.log')` en `app.py`.

---

## 🟡 SEO y presencia web

| Mejora | Descripción |
|---|---|
| **Open Graph** | Meta tags `og:title`, `og:description`, `og:image` en cada página |
| **Favicon** | No hay favicon en los HTML |
| **Titulo dinamico** | Incluir nombre del animal o noticia en `<title>` |
| **Sitemap.xml** | Para indexación en buscadores |
| **robots.txt** | Bloquear `/admin` de los bots |

---

## 🟢 Opcionales / futuras

| Idea | Detalle |
|---|---|
| **Notificaciones por email** | Al recibir solicitud de adopcion o contacto → smtplib o SendGrid |
| **Paginación en la API pública** | `?page=1&per_page=12` para escalar |
| **Galería de varias fotos por animal** | Tabla `animal_images(animal_id, path, order)` |
| **Exportar contactos a CSV** | Boton en `/admin/contacts` → modulo csv de Python |
| **Exportar colaboradores a CSV** | Igual para voluntarios/socios |
| **Dashboard con gráficas** | Chart.js: animales por estado, contactos por mes, etc. |
| **GDPR / cookies** | Banner de cookies + página de politica de privacidad |
| **PWA** | manifest.json + service worker para soporte offline |
| **Reserva de animal** | Estado `reserved` para animales con solicitud activa |
| **Rate limiting en la API** | Evitar spam en el formulario de contacto (Flask-Limiter) |
| **Modo oscuro** | Toggle en el header, guardar en localStorage |

---

## Resumen de estado actual

```
BACKEND (Flask + SQLite)
  OK  CRUD completo: animales, noticias, contactos
  OK  Autenticacion admin (sesion)
  OK  CSRF, secret_key env, debug env
  OK  Gestion de colaboradores (socios, voluntarios, padrinos, acogida, empresa)
  OK  Solicitudes de adopcion vinculadas a animal
  OK  Cambio rapido de estado de animal (PATCH /api/animals/<id>/status)
  --  Sin paginacion

FRONTEND PUBLICO
  OK  Todas las paginas del menu creadas y enlazadas
  OK  Header rediseñado: nav arriba, logo/acciones abajo
  OK  Filtros: tipo, estado, tamaño en adopcion
  OK  Formulario de contacto conectado al backend
  OK  Formularios de colabora.html (socio, voluntariado, acogida, empresa) conectados
  OK  Solicitud de adopcion desde la ficha de animal (formulario inline en modal)
  OK  Búsqueda por nombre de animal en adopcion.html
  --  Sin mapa en contacto
  --  Padrino/madrina sigue sin formulario propio

PANEL ADMIN
  OK  Animales (nuevo, editar, borrar, imagen, cambio rapido de estado)
  OK  Noticias (nuevo, editar, borrar, borrador/publicado, editor Quill.js)
  OK  Contactos (lista, marcar leido, borrar)
  OK  Colaboradores (lista, filtros tipo/estado, cambio estado inline, eliminar)
  OK  Solicitudes de adopcion (lista, filtros, cambio estado inline, eliminar)
  OK  Cambiar contraseña
  --  Sin paginacion
```


---

## 🔴 Crítico — Colaboradores sin gestión

### La sección "Colabora" no guarda datos en ningún sitio

`pages/colabora.html` muestra formularios de: socio, padrino/madrina, voluntariado, acogida, empresa solidaria. **Ninguno de ellos envía datos al backend.** Son formularios estáticos que o bien no hacen nada, o redirigen al email.

Esto significa que la protectora **no puede gestionar quién quiere colaborar** desde ningún panel.

**Lo que hay que construir:**

| Pieza | Descripción |
|---|---|
| Tabla BD `collaborators` | `id, type, name, email, phone, message, status, created_at` |
| `POST /api/collaborate` | Endpoint que recibe el formulario y guarda en BD |
| `GET /admin/collaborators` | Lista en el admin con filtro por tipo y estado |
| `POST /admin/collaborators/<id>/status` | Cambiar estado (pendiente/activo/rechazado) |
| `admin/templates/collaborators.html` | Plantilla de la lista |
| Conectar formularios en `colabora.html` | `fetch` a `/api/collaborate` con tipo correcto |

**Respuesta directa:** Ahora mismo los colaboradores **no se gestionan desde ningún sitio**. Los formularios de colabora.html son decorativos. Hay que implementarlo desde cero.

---

## 🔴 Crítico — Formulario de solicitud de adopción

No hay forma de solicitar la adopción de un animal concreto. El flujo termina en "Contacto general".

**Lo que falta:**

| Pieza | Descripción |
|---|---|
| Tabla BD `adoption_requests` | `id, animal_id, name, email, phone, message, status, created_at` |
| `POST /api/animals/<id>/adopt` | Guarda la solicitud vinculada al animal |
| `GET /admin/adoptions` | Lista de solicitudes en el admin |
| Botón "Solicitar adopción" en ficha de animal | En `adopcion.html`, abre modal con formulario |

---

## 🟠 Importante — Acciones rápidas en el admin

### Cambiar estado de animal sin entrar al formulario

La única forma de marcar un animal como adoptado es entrar en el formulario completo.

- **Fix:** Select de estado en la tabla de animales → `PATCH /api/animals/<id>/status`

### Paginación en listas del admin

`/admin/animals` y `/admin/news` devuelven todos los registros. Con muchos animales esto es lento.

- **Fix:** Añadir `LIMIT/OFFSET` + controles de página en las plantillas.

### Editor de texto enriquecido para noticias

El campo "contenido" es un textarea plano. No permite negritas, listas ni enlaces.

- **Fix:** Integrar Quill.js (CDN, sin npm) en `news_form.html`.

---

## 🟠 Importante — Mejoras de frontend

### 1. Sección de animales en acogida

Falta el estado `foster` (acogida temporal). La página de adopción podría tener una pestaña "En acogida".

### 2. Modal de ficha de animal más completa

Añadir en el modal:
- Botón "Solicitar adopción" con formulario inline
- Botón "Compartir" (URL directa `adopcion.html?id=X`)

### 3. Mapa en contacto.html

La dirección aparece como texto. Integrar un `<iframe>` de Google Maps o Leaflet.js.

### 4. Búsqueda por nombre de animal

En `adopcion.html` no hay búsqueda por nombre. Añadir `<input type="search">` con filtro en tiempo real.

---

## 🟡 Mejoras técnicas

### 1. Optimización de imágenes con Pillow

Las imágenes se guardan sin redimensionar. Una foto de 8MB se sirve tal cual.

- **Fix:** `pip install Pillow` y redimensionar a máximo 1200px en `app.py` al guardar.

### 2. `BASE_URL` hardcodeado a `localhost:5000`

Aparece en `adopcion.js`, `main.js`, `actualidad.html`, `adoptados.html`, `nosotros.html`.

- **Fix:** Usar `<meta name="api-base" content="...">` en el HTML y leerlo desde JS.

### 3. Multiidioma completo (VAL)

El selector ES/VAL solo funciona en `index.html`. Las demás páginas no tienen traducciones.

- **Fix:** Extraer `translations` a `js/i18n.js` e implementarlo en cada página.

### 4. Imágenes de muestra → null en la BD

Los 10 animales de ejemplo tienen rutas de imagen que no existen.

- **Fix SQL:** `UPDATE animals SET image = NULL WHERE image LIKE 'images/animales/%'`

### 5. Sin logging a fichero

Los errores de Flask solo van a la consola.

- **Fix:** Configurar `logging.FileHandler('admin/app.log')` en `app.py`.

---

## 🟡 SEO y presencia web

| Mejora | Descripción |
|---|---|
| **Open Graph** | Meta tags `og:title`, `og:description`, `og:image` en cada página |
| **Favicon** | No hay favicon en los HTML |
| **Titulo dinamico** | Incluir nombre del animal o noticia en `<title>` |
| **Sitemap.xml** | Para indexación en buscadores |
| **robots.txt** | Bloquear `/admin` de los bots |

---

## 🟢 Opcionales / futuras

| Idea | Detalle |
|---|---|
| **Notificaciones por email** | Al recibir solicitud de adopcion o contacto → smtplib o SendGrid |
| **Paginación en la API pública** | `?page=1&per_page=12` para escalar |
| **Galería de varias fotos por animal** | Tabla `animal_images(animal_id, path, order)` |
| **Exportar contactos a CSV** | Boton en `/admin/contacts` → modulo csv de Python |
| **Exportar colaboradores a CSV** | Igual para voluntarios/socios |
| **Dashboard con gráficas** | Chart.js: animales por estado, contactos por mes, etc. |
| **GDPR / cookies** | Banner de cookies + página de politica de privacidad |
| **PWA** | manifest.json + service worker para soporte offline |
| **Reserva de animal** | Estado `reserved` para animales con solicitud activa |
| **Rate limiting en la API** | Evitar spam en el formulario de contacto (Flask-Limiter) |
| **Modo oscuro** | Toggle en el header, guardar en localStorage |

---

## Resumen de estado actual

```
BACKEND (Flask + SQLite)
  OK  CRUD completo: animales, noticias, contactos
  OK  Autenticacion admin (sesion)
  OK  CSRF, secret_key env, debug env
  --  Sin gestion de colaboradores (socios, voluntarios, padrinos...)
  --  Sin solicitudes de adopcion
  --  Sin paginacion

FRONTEND PUBLICO
  OK  Todas las paginas del menu creadas y enlazadas
  OK  Header rediseñado: nav arriba, logo/acciones abajo
  OK  Filtros: tipo, estado, tamaño en adopcion
  OK  Formulario de contacto conectado al backend
  --  Formularios de colabora.html no envian datos
  --  No hay solicitud de adopcion desde la ficha de animal
  --  Sin busqueda por nombre de animal
  --  Sin mapa en contacto
  --  Las secciones Aviso Legal | Política de Privacidad | Política de Cookies no sale nada.

PANEL ADMIN
  OK  Animales (nuevo, editar, borrar, imagen)
  OK  Noticias (nuevo, editar, borrar, borrador/publicado)
  OK  Contactos (lista, marcar leido, borrar)
  OK  Cambiar contraseña
  --  Sin gestion de colaboradores
  --  Sin solicitudes de adopcion
  --  Sin cambio rapido de estado de animal
  --  Sin editor de texto enriquecido para noticias
  --  Sin paginacion
  --  Renombrar la seccion de Contactos por Mensajes
  --  En los mensajes añadir una accion que sea visualizar, ha de abrir el mensaje para poder verlo completo.

```
