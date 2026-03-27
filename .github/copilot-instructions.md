# Copilot Instructions — Protectora de Animales Burjassot

## Project overview

Animal shelter website for "Protectora de Animales Burjassot". Two-tier architecture:

| Layer | Technology | Port |
|---|---|---|
| Static frontend | HTML/CSS/Vanilla JS, served by Python HTTP server | 8000 |
| Backend CMS | Flask 3.0.0 + SQLite, `admin/app.py` | 5000 |

The backend acts both as a REST API (consumed by the frontend) and as a server-side rendered admin panel via Jinja2 templates.

## Running the project

```bat
.\run.bat        # starts both servers (handles venv, deps, ports)
.\stop.bat       # stops both
```

> Always use `run.bat`. Do **not** start Flask or the HTTP server manually — the script handles port conflict checks, venv activation, and dependency installation automatically.

## Architecture map

```
Python_WEBAMPARO/
├── index.html              # Homepage — uses js/main.js
├── pages/                  # Public pages (adopcion, dona, colabora, contacto)
├── css/                    # Per-page stylesheets + global styles.css
├── js/
│   ├── main.js             # Homepage: loads featured animals + latest news cards
│   ├── adopcion.js         # Adoption page: filters, search, animal cards & modals
│   └── contact.js          # Contact form validation & submission
├── images/
│   ├── animales/           # SVG placeholders: perro.svg, gato.svg
│   └── noticia.svg         # News placeholder (root of images/)
├── uploads/                # Files saved by admin uploads (NOT committed)
│   └── fotos/              # Animal photos — served by Flask at /uploads/fotos/
├── admin/
│   ├── app.py              # ALL backend logic (routes, DB, file handling)
│   ├── protectora.db       # SQLite database (auto-created on first run)
│   ├── requirements.txt    # Flask==3.0.0, Flask-CORS==4.0.0, Werkzeug==3.0.1
│   └── templates/          # Jinja2 admin templates
```

## Image URL conventions (critical)

The `image` column in the `animals` and `news` tables stores relative paths. Two types exist:

| Path prefix | Meaning | Served by |
|---|---|---|
| `uploads/fotos/TIMESTAMP_file.ext` | Admin-uploaded file | Flask at `http://localhost:5000/uploads/...` |
| `images/animales/NAME.jpg` (legacy) | Sample data, **files do not exist** | Falls through to SVG placeholder |
| `null` | No image set | Falls through to SVG placeholder |

**Always use `getAnimalImage(animal)`** (defined in `adopcion.js` and `main.js`) to resolve image URLs. Never use `animal.image` directly as a `src` attribute.

```js
// Canonical pattern — replicate this whenever rendering animal images
function getAnimalImage(animal) {
    if (animal.image && animal.image.startsWith('uploads/')) {
        return `http://localhost:5000/${animal.image}`;
    }
    const type = (animal.type === 'gato') ? 'gato' : 'perro';
    return `../images/animales/${type}.svg`;  // adjust path depth per page
}
```

For news images, use `uploads/` check → fallback to `images/noticia.svg`.

## onerror handler rule

**Always** set `this.onerror = null` as the first statement in any `onerror` to prevent infinite retry loops:

```html
<!-- CORRECT -->
<img src="..." onerror="this.onerror=null; this.src='fallback.svg'">

<!-- WRONG — causes infinite 404 loop if fallback also fails -->
<img src="..." onerror="this.src='placeholder.jpg'">
```

## Flask backend conventions

- **`admin/app.py`** is the single file for all backend logic. No blueprints or separate modules.
- **Database**: SQLite, accessed via `get_db()` helper. `DATABASE = 'protectora.db'` — path is relative to the `admin/` CWD where Flask runs.
- **File uploads**: `UPLOAD_FOLDER = <project_root>/uploads`. Always call `os.makedirs(target_dir, exist_ok=True)` before every `file.save()` call.
- **`secure_filename()` can return an empty string** (e.g. for filenames with only special characters). Always guard: `filename = secure_filename(f.filename); if filename:`.
- **Flask routes for static assets**:
  - `/uploads/<path:filename>` → serves from `uploads/`
  - `/images/<path:filename>` → serves from `images/` (for SVG placeholders)
- **CORS**: enabled globally for all routes (development setup).
- **Secret key** (`app.secret_key`) must be changed before any production deploy.

## API endpoints (consumed by frontend JS)

| Method | Path | Description |
|---|---|---|
| GET | `/api/animals` | All animals; query params: `?status=adoption&type=perro&limit=N` |
| GET | `/api/animals/<id>` | Single animal |
| GET | `/api/news` | News list; query params: `?limit=N&published=1` |
| POST | `/api/contact` | Submit contact form (JSON body) |

## Admin panel

- URL: `http://localhost:5000/admin`
- Default credentials: `admin` / `protectora2026` (session-based auth)
- All admin routes require `@login_required` decorator

## Browser caching gotcha

After fixing a JS bug, increment the version query parameter in the HTML `<script>` tag to bust the browser cache:

```html
<script src="../js/adopcion.js?v=3"></script>
```

Current versions: `main.js?v=2`, `adopcion.js?v=2`.

## Sample data note

On first run, the DB is seeded with 10 sample animals whose `image` field contains `images/animales/luna.jpg` etc. — **these image files do not exist**. They correctly fall through to the SVG placeholder via `getAnimalImage()`.

## CSS architecture

- `css/styles.css` — global variables (`--primary-color`, `--secondary-color`, `--accent-color`), layout, header, footer
- Page-specific files: `adopcion.css`, `dona.css`, `colabora.css`, `forms.css`
- Admin has its own CSS under `admin/static/css/`

## Language support

Bilingual ES/VAL selector in the header. Translations are defined inline in `js/main.js` (`translations` object). Preference is stored in `localStorage`.
