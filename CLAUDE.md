# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Website for "Protectora de Animales Burjassot" (animal shelter). **Single-server architecture:**

- **Flask Server (port 5000)**: Serves everything - static frontend files, REST API, and admin panel
  - Static files (HTML/CSS/JS)
  - REST API endpoints (/api/*)
  - Admin panel (/admin/*)
  - File uploads (/uploads/*)
  - Images (/images/*)

**Simple, unified architecture** - one Flask server does it all.

## Running the Project

```bat
.\run.bat        # Start Flask server (handles venv, dependencies, port check)
.\stop.bat       # Stop Flask server
```

**Critical**: Always use `run.bat`. The batch script handles:
- Virtual environment creation/activation
- Automatic dependency installation if missing
- Port 5000 availability check
- Flask server startup

**Access URLs:**
- Public site: `http://localhost:5000`
- Admin panel: `http://localhost:5000/admin`
- API: `http://localhost:5000/api/*`

### Other Utilities

```bat
.\hacer_backup.bat                  # Backup database + uploads to timestamped folder
.\restaurar_backup.bat              # Restore from backup
.\limpiar_entorno.bat               # Clean environment (delete venv, cache, db)
.\instalar_dependencias.bat         # Force reinstall all dependencies
```

## Architecture Details

### Server Architecture

| Component | Technology | Port | Command |
|-----------|-----------|------|---------|
| Full Stack App | Flask (`admin/app.py`) | 5000 | Auto-started by run.bat |

**Flask serves everything:**
- `/` → index.html (homepage)
- `/pages/*` → Static HTML pages
- `/css/*`, `/js/*` → Static assets
- `/admin/*` → Admin panel (Jinja2 templates)
- `/api/*` → REST API (JSON)
- `/uploads/*` → User-uploaded files
- `/images/*` → Static images & placeholders

### Key Files

- `admin/app.py` - **Single file containing ALL backend logic** (no blueprints, no modules)
- `admin/protectora.db` - SQLite database (auto-created on first run with sample data)
- `admin/requirements.txt` - Flask==3.0.0, Flask-CORS==4.0.0, Werkzeug==3.0.1
- `js/main.js` - Homepage: loads featured animals + news from API
- `js/adopcion.js` - Adoption page: filters, search, animal cards with modals
- `test_api.html` - Diagnostic tool for testing API endpoints

## Image Handling (Critical)

### Database Image Paths

The `image` column in `animals` and `news` tables stores relative paths with two formats:

| Path Format | Meaning | Served By |
|-------------|---------|-----------|
| `uploads/fotos/TIMESTAMP_filename.jpg` | Admin-uploaded file | Flask at `/uploads/...` |
| `images/animales/luna.jpg` (legacy) | Sample data - **files don't exist** | Falls through to placeholder |
| `NULL` | No image set | Falls through to placeholder |

### Default Images by Type

When rendering animal images, use this pattern:

```javascript
function getAnimalImage(animal) {
    // If admin-uploaded image exists
    if (animal.image && animal.image.startsWith('uploads/')) {
        return `http://localhost:5000/${animal.image}`;
    }
    // Fallback to type-specific placeholder
    const type = (animal.type === 'gato') ? 'gato' : 'perro';
    return `../images/animales/${type}.svg`;  // adjust ../ based on page depth
}
```

Default images:
- **Dogs**: `images/perro.jpg` or `images/animales/perro.svg`
- **Cats**: `images/gato.jpg` or `images/animales/gato.svg`
- **News**: `images/noticia.svg`

### onerror Handler Pattern

**Always** set `this.onerror = null` first to prevent infinite retry loops:

```html
<!-- CORRECT -->
<img src="..." onerror="this.onerror=null; this.src='../images/perro.jpg'">

<!-- WRONG - infinite loop if fallback also fails -->
<img src="..." onerror="this.src='placeholder.jpg'">
```

## Flask Backend Conventions

### Single-File Architecture

- All routes, database logic, and API endpoints are in `admin/app.py`
- No blueprints, no separate modules
- Database path: `DATABASE = 'protectora.db'` (relative to `admin/` CWD)

### File Upload Pattern

When handling file uploads, **always**:

1. Check `secure_filename()` result (can return empty string)
2. Create upload directory before saving
3. Use timestamped filenames to avoid conflicts

```python
if 'image' in request.files:
    file = request.files['image']
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        if filename:  # secure_filename can return ''
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            fotos_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'fotos')
            os.makedirs(fotos_dir, exist_ok=True)  # ALWAYS before save
            filepath = os.path.join(fotos_dir, filename)
            file.save(filepath)
            image_path = f"uploads/fotos/{filename}"
```

### Database Access

```python
def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row  # Returns dict-like rows
    return db

# Usage
db = get_db()
animals = db.execute('SELECT * FROM animals WHERE status = ?', ('adoption',)).fetchall()
db.commit()  # Don't forget for INSERT/UPDATE/DELETE
```

## API Endpoints

All endpoints return JSON. Frontend consumes these via fetch():

| Method | Path | Query Params | Description |
|--------|------|--------------|-------------|
| GET | `/api/animals` | `?status=adoption&type=perro&limit=N` | List animals |
| GET | `/api/animals/<id>` | - | Single animal details |
| GET | `/api/news` | `?limit=N` | List published news |
| GET | `/api/news/<id>` | - | Single news item |
| POST | `/api/contact` | - | Submit contact form (JSON body) |

Example:
```javascript
const response = await fetch('http://localhost:5000/api/animals?status=adoption');
const data = await response.json();
const animals = data.animals || [];
```

## Database Schema

### animals table
- `id`, `name`, `type` (perro/gato), `age`, `gender`, `size`, `description`
- `image` (path: uploads/fotos/... or NULL)
- `status` (adoption/adopted/fostered/reserved)
- `created_at`, `updated_at`

### news table
- `id`, `title`, `category` (evento/campana/blog), `content`, `excerpt`
- `image`, `date`, `published` (boolean)
- `created_at`, `updated_at`

### contacts table
- `id`, `name`, `email`, `phone`, `subject`, `message`
- `read` (boolean), `created_at`

## Admin Panel

- URL: `http://localhost:5000/admin`
- Default credentials: `admin` / `protectora2026`
- Authentication: session-based with `@login_required` decorator
- **Important**: Change default password before production deployment

## Browser Caching

After fixing JavaScript bugs, increment version query parameter to bust cache:

```html
<!-- Before -->
<script src="../js/adopcion.js?v=2"></script>

<!-- After fix -->
<script src="../js/adopcion.js?v=3"></script>
```

## Windows Batch File Encoding

All `.bat` files use **ASCII-only encoding**:
- No UTF-8 characters or emojis
- Use `[OK]`, `[ERROR]`, `[!]` instead of ✅❌⚠️
- This prevents "comando no reconocido" errors on Windows

## CSS Architecture

- `css/styles.css` - Global variables, layout, header, footer
  - CSS variables: `--primary-color`, `--secondary-color`, `--accent-color`
- Page-specific: `adopcion.css`, `dona.css`, `colabora.css`, `forms.css`
- Admin panel has separate CSS in `admin/static/css/`

## Common Pitfalls

1. **Forgetting to create upload directories**: Always `os.makedirs(..., exist_ok=True)` before `file.save()`
2. **Empty secure_filename()**: Always check `if filename:` after `secure_filename()`
3. **Wrong image paths**: Use relative paths in DB (`uploads/fotos/...`), not absolute
4. **Missing db.commit()**: Required after INSERT/UPDATE/DELETE operations
5. **Infinite onerror loops**: Always set `this.onerror=null` first
6. **Browser cache**: Increment `?v=N` in script tags after JS changes

## Sample Data

On first run, `init_db()` seeds the database with:
- 12 sample animals (10 for adoption, 2 adopted)
- 5 sample news items
- Default admin user

Sample animal images reference `images/animales/luna.jpg` etc. - **these files don't exist**. They correctly fall through to SVG placeholders via the `getAnimalImage()` pattern.

## Security Notes

Before production:
1. Change `app.secret_key` in `admin/app.py`
2. Change default admin password
3. Configure HTTPS
4. Protect `/admin` route with additional authentication
5. Set up proper CORS restrictions (currently allows all origins for development)
