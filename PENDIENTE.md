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
- **Gestión de usuarios y roles** — tabla `users` con `role`/`is_active`; rutas `/admin/users`; roles: superadmin, editor, visor; tabla de permisos por rol
- **Configuración del sitio** — tabla `site_settings`; ruta `/admin/settings`; `GET /api/settings` pública; carga dinámica en contacto.html
- **Paginación en el admin** — 20 animales/página y 15 noticias/página con controles de navegación
- **Búsqueda + filtro en admin animales** — campo texto libre + filtro por estado; bug `ORDER BY` vacío corregido
- **Favicon** — `images/favicon.svg` añadido en todas las páginas HTML
- **robots.txt** — bloquea `/admin/` y `/uploads/` de los buscadores
- **Formulario padrino/madrina** — sección de `colabora.html` conectada al backend
- **Datos de contacto dinámicos** — `contacto.html` carga email, teléfono, dirección, horario y mapa desde `/api/settings`
- **Mapa en contacto.html** — iframe actualiza su `src` con `maps_embed_url` de la API; configurable en Configuración del sitio
- **Fix imágenes de muestra** — migración en `init_db()` que limpia rutas `images/animales/*.jpg` → NULL
- **Logging a fichero** — `logging.basicConfig` con `FileHandler('admin/app.log')` + `StreamHandler`
- **Optimización de imágenes con Pillow** — helper `save_image()` redimensiona a máx 1200 px y convierte a JPEG 85%
- **Dashboard con tarjetas clicables** — navegan a cada sección del admin
- **BASE_URL via `<meta name="api-base">`** — todos los HTML públicos (incluido index.html) leen la URL del backend desde la meta
- **i18n.js — VAL en todas las páginas** — selector ES/VAL funciona en todas las páginas
- **Open Graph** — meta tags `og:type`, `og:site_name`, `og:title`, `og:description` en todos los HTML públicos
- **Sitemap.xml dinámico** — ruta `/sitemap.xml`; incluye páginas estáticas + animales en adopción + noticias publicadas
- **Exportar CSV** — contactos y colaboradores; BOM UTF-8 para compatibilidad Excel
- **Rate limiting** — Flask-Limiter en `/api/contact`, `/api/collaborate`, `/api/.../adopt`
- **Sección "En acogida" en adopcion.html** — tabs "En adopción" / "En acogida"
- **Estado `reserved`** — auto al enviar solicitud de adopción; badge naranja; gestionable en admin
- **Renombrar Contactos → Mensajes** — sidebar admin y título de la página actualizados
- **Botón Visualizar en mensajes** — modal con mensaje completo + botón Responder (mailto)
- **Páginas legales** — Aviso Legal, Política de Privacidad, Política de Cookies con contenido real (RGPD, LSSI-CE)
- **Newsletter** — tabla `newsletter_subscribers`; `POST /api/newsletter/subscribe`; panel `/admin/newsletter`; formulario en footer de index.html con script inline; mensaje de confirmación/error visible
- **Soporte PostgreSQL/SQLite dual** — `DatabaseWrapper` + `get_placeholder()`; detectado por `DATABASE_URL`

</details>

---

## 🟡 SEO y presencia web

| Mejora | Descripción | Estado |
|---|---|---|
| **og:image** | Imagen de previsualización en redes sociales (requiere URL pública de imagen) | Pendiente |
| **Título dinámico** | Cambiar `<title>` al abrir ficha de animal o noticia en modal | Pendiente |

---

## 🟢 Opcionales / futuras

| Idea | Detalle |
|---|---|
| **Notificaciones por email** | Al recibir solicitud de adopción o contacto → smtplib o SendGrid |
| **Paginación en la API pública** | `?page=1&per_page=12` para escalar |
| **Galería de varias fotos por animal** | Tabla `animal_images(animal_id, path, order)` |
| **PWA** | manifest.json + service worker para soporte offline |
| **Modo oscuro** | Toggle en el header, guardar en localStorage |
| **Exportar animales a CSV** | Ampliar exportación CSV a la tabla de animales del admin |
| **Contraseña olvidada** | Reset por email (requiere smtplib) |
| **Dashboard con gráficas** | Chart.js: animales por estado, contactos por mes, etc. |
| **Multiidioma VAL ampliado** | Traducir contenido de artículos de noticias |
| **Despliegue en producción** | Render (Flask + PostgreSQL) + variables de entorno |

---

## Resumen de estado actual

```
BACKEND (Flask + SQLite/PostgreSQL)
  OK  CRUD completo: animales, noticias, contactos
  OK  Autenticacion admin (sesion) con roles: superadmin, editor, visor
  OK  CSRF, secret_key env, debug env
  OK  Gestion de colaboradores (socios, voluntarios, padrinos, acogida, empresa)
  OK  Solicitudes de adopcion vinculadas a animal
  OK  Estado reserved — auto al recibir solicitud; gestionable en admin
  OK  Cambio rapido de estado de animal (PATCH /api/animals/<id>/status)
  OK  Paginacion + busqueda + filtro en listas del admin (bug ORDER BY corregido)
  OK  Configuracion del sitio editable en admin (/admin/settings)
  OK  GET /api/settings publica para frontend
  OK  Logging a fichero (admin/app.log) + consola
  OK  Optimizacion de imagenes con Pillow (max 1200px, JPEG 85%)
  OK  Rate limiting: contacto/colabora/adopcion (Flask-Limiter)
  OK  Exportar CSV: contactos y colaboradores
  OK  Sitemap.xml dinamico (/sitemap.xml)
  OK  Newsletter: suscripcion publica + panel admin + exportar CSV
  OK  Soporte PostgreSQL/SQLite dual (DatabaseWrapper)

FRONTEND PUBLICO
  OK  Todas las paginas del menu creadas y enlazadas
  OK  Header rediseñado: nav arriba, logo/acciones abajo
  OK  Filtros: tipo, estado, tamaño en adopcion
  OK  Tabs En adopcion / En acogida en adopcion.html
  OK  Badge Reservado en tarjetas de animales reservados
  OK  Formulario de contacto conectado al backend
  OK  Formularios de colabora.html conectados al backend (todos los tipos)
  OK  Solicitud de adopcion desde la ficha de animal (formulario inline en modal)
  OK  Busqueda por nombre de animal en adopcion.html
  OK  Contacto.html carga email/telefono/direccion/horario y mapa desde API
  OK  Mapa iframe actualiza src con maps_embed_url de la API
  OK  Favicon en todas las paginas
  OK  robots.txt
  OK  Open Graph meta tags en todos los HTML publicos
  OK  <meta name="api-base"> en todos los HTML publicos (incl. index.html)
  OK  i18n.js — selector ES/VAL funciona en todas las paginas
  OK  Paginas legales: Aviso Legal, Politica de Privacidad, Politica de Cookies
  OK  Newsletter: formulario en footer de index.html con feedback visible al usuario

PANEL ADMIN
  OK  Animales (nuevo, editar, borrar, imagen, busqueda, filtro estado, cambio rapido estado, paginacion)
  OK  Noticias (nuevo, editar, borrar, borrador/publicado, editor Quill.js, paginacion)
  OK  Mensajes (lista, marcar leido, visualizar completo en modal, borrar, exportar CSV)
  OK  Colaboradores (lista, filtros tipo/estado, cambio estado inline, eliminar, exportar CSV)
  OK  Solicitudes de adopcion (lista, filtros, cambio estado inline, eliminar)
  OK  Configuracion del sitio (datos de contacto, redes sociales, mapa embed URL, site_url)
  OK  Usuarios y roles (crear, editar, activar/desactivar, eliminar, tabla de permisos por rol)
  OK  Newsletter (lista suscriptores, activar/desactivar, eliminar, exportar CSV)
  OK  Dashboard con tarjetas clicables que navegan a cada seccion
  OK  Cambiar contraseña
```
