# Rediseño ficha de animal + listado de adopción

**Fecha:** 2026-03-31
**Objetivo:** Aumentar adopciones mejorando la información disponible de cada animal.
**Enfoque elegido:** C — Rediseño completo (ficha + listado)

---

## Problema

La ficha actual de cada animal muestra una sola foto y una descripción de texto libre. No hay información sanitaria estructurada ni indicadores de compatibilidad. Los adoptantes potenciales no tienen suficiente información para tomar una decisión con confianza. El listado de adopción solo permite filtrar por tipo y tamaño; no hay forma de buscar por compatibilidad con niños, otros animales o tipo de vivienda.

---

## Solución

Tres piezas coordinadas:

1. **Base de datos** — nuevos campos en `animals` y nueva tabla `animal_photos`
2. **Panel admin** — formulario de animal ampliado con galería, salud y compatibilidad
3. **Frontend público** — página `/animal/<id>` rediseñada + tarjetas del listado enriquecidas + filtros de compatibilidad

---

## 1. Base de datos

### Nueva tabla `animal_photos`

```sql
CREATE TABLE animal_photos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id   INTEGER NOT NULL REFERENCES animals(id) ON DELETE CASCADE,
    photo_path  TEXT NOT NULL,        -- uploads/fotos/...
    display_order INTEGER DEFAULT 0,
    caption     TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

Máximo 8 fotos por animal. La imagen principal (`animals.image`) se mantiene como portada; las fotos adicionales se almacenan aquí.

### Nuevas columnas en `animals`

**Estado sanitario (boolean, default FALSE):**
- `vaccinated`
- `sterilized`
- `chipped`
- `dewormed`

**Compatibilidad (boolean, default FALSE):**
- `good_with_kids`
- `good_with_cats`
- `good_with_dogs`
- `apartment_ok`
- `high_energy`

**Campo urgencia:**
- `urgent` (boolean, default FALSE) — destaca el animal con badge rojo en el listado

Todos se añaden mediante `ALTER TABLE` en `init_db()` para no romper bases de datos existentes (patrón ya usado en el proyecto).

---

## 2. API — cambios en endpoints existentes y nuevos

### `GET /api/animals` y `GET /api/animals/<id>` — ampliados

La respuesta incluye los nuevos campos:

```json
{
  "id": 42,
  "name": "Luna",
  "photos": [
    {"id": 1, "path": "uploads/fotos/...", "order": 0},
    {"id": 2, "path": "uploads/fotos/...", "order": 1}
  ],
  "health": {
    "vaccinated": true,
    "sterilized": true,
    "chipped": true,
    "dewormed": false
  },
  "compatibility": {
    "good_with_kids": true,
    "good_with_cats": false,
    "good_with_dogs": true,
    "apartment_ok": true,
    "high_energy": false
  },
  "urgent": false
}
```

### `GET /api/animals` — nuevos query params de filtro

- `?kids=1` — filtra `good_with_kids = TRUE`
- `?cats=1` — filtra `good_with_cats = TRUE`
- `?dogs=1` — filtra `good_with_dogs = TRUE`
- `?apartment=1` — filtra `apartment_ok = TRUE`
- `?urgent=1` — filtra `urgent = TRUE`

### Nuevos endpoints de galería

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/admin/animals/<id>/photos` | Subir foto adicional (form-data, campo `photo`) |
| `DELETE` | `/admin/animals/<id>/photos/<photo_id>` | Eliminar foto |
| `POST` | `/admin/animals/<id>/photos/reorder` | Reordenar (JSON: `[{id, order}]`) |
| `POST` | `/admin/animals/<id>/photos/<photo_id>/set-primary` | Copiar esta foto a `animals.image` y marcarla como portada |

Todos requieren `@login_required`. Siguen el patrón de `save_image()` existente (Pillow resize a 1200px, JPEG).

---

## 3. Panel admin — formulario de animal

El template `admin/templates/animal_form.html` se amplía con tres bloques nuevos:

**Bloque galería:**
- Grid de thumbnails de las fotos actuales
- Botón "+" para subir fotos adicionales (AJAX, sin recargar)
- Botones ↑↓ para reordenar (sin librerías de drag-and-drop, evita nuevas dependencias JS)
- Botón eliminar en cada foto (✕)
- La foto principal sigue siendo `animals.image`; se puede cambiar haciendo clic en "Establecer como principal"

**Bloque estado sanitario:**
- 4 checkboxes: Vacunado, Esterilizado, Con chip, Desparasitado
- Guardados como booleanos en `animals`

**Bloque compatibilidad:**
- 5 checkboxes con emoji: 👶 Bueno con niños, 🐱 Convive con gatos, 🐕 Convive con perros, 🏠 Apto para piso, ⚡ Muy activo
- Checkbox adicional: ⚠ Urgente (activa badge rojo en el listado)

---

## 4. Página pública `/animal/<id>` — rediseño

Renderizada por Jinja2 en `admin/templates/animal_public.html`. Layout de dos columnas:

**Columna izquierda — galería:**
- Foto principal grande con navegación ←→ por teclado y clic en thumbnails
- Fila de thumbnails debajo (máx. 8, scroll horizontal en móvil)
- Lightbox al hacer clic en la foto principal

**Columna derecha — información:**
- Nombre, tipo, género, edad, tamaño, tiempo en la protectora
- Sección "Estado sanitario": badges verdes para los campos TRUE, badge amarillo "Pendiente" para FALSE
- Sección "Compatibilidad": solo se muestran badges azules para los campos TRUE. Los campos FALSE no generan badge — la ausencia de badge es suficiente. Excepción: si `good_with_cats = FALSE` y `good_with_dogs = FALSE` se muestra "🐱 No con gatos" / "🐕 No con perros" en rosado, ya que es información relevante que el adoptante necesita conocer explícitamente.
- Campo "Su historia" (el `description` existente)
- CTAs: "Quiero adoptar" (abre formulario de solicitud), "Solicitar visita" (enlaza a `/pages/acogida.html`), "Compartir" (Web Share API con fallback a copiar URL)

**Sección inferior — animales similares:**
- 3 animales del mismo tipo en adopción, excluido el actual
- Tarjetas compactas que enlazan a sus fichas

**SEO:**
- `<title>` con nombre del animal
- `<meta description>` con excerpt de la descripción
- Open Graph con foto principal
- URL canónica `/animal/<id>/<slug>` (el slug ya existe en el código actual)

---

## 5. Página de adopción — listado rediseñado

Cambios en `pages/adopcion.html` y `js/adopcion.js`:

**Tarjetas (`adopcion.js`):**
- Muestran los 3 tags de compatibilidad más relevantes directamente visibles
- Indicador de número de fotos (📷 N) si el animal tiene fotos adicionales
- Badge "⚠ Urgente" en rojo si `urgent = true`
- El botón/clic ya no abre modal — navega a `/animal/<id>/<slug>`
- El modal existente se elimina

**Filtros (barra superior):**
- Se añaden checkboxes de compatibilidad: Niños, Gatos, Perros, Piso
- Checkbox "Solo urgentes"
- Los filtros se acumulan (AND lógico): si marcas Niños + Piso, solo aparecen animales que cumplen ambos
- Los filtros se pasan como query params a `GET /api/animals`

**Paginación:** sin cambios, ya funciona.

---

## 6. Compatibilidad y migración

- Las nuevas columnas de `animals` se añaden con `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` (patrón existente en `init_db()`), así bases de datos existentes no se rompen
- Todos los nuevos campos tienen valores por defecto (`FALSE`/`0`), así los animales existentes se muestran correctamente sin datos (los badges de compatibilidad simplemente no aparecen si todos son `FALSE`)
- `GET /api/animals` mantiene compatibilidad total: los nuevos campos son aditivos en la respuesta JSON
- La URL `/animal/<id>` ya existe — solo se rediseña el template

---

## 7. Fuera de alcance

- Vídeo embebido (YouTube/Vimeo) — se puede añadir en iteración posterior
- Historia narrativa como campo separado del `description` — se reutiliza el campo existente
- Portal de seguimiento para adoptantes — iteración futura
- Integración con redes sociales (visibilidad/captación) — segunda prioridad identificada, iteración separada
