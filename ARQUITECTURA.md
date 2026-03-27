# 🏗️ Arquitectura del Sistema

## Visión General

Sistema web para gestión de protectora de animales con arquitectura monolítica que sirve tanto el frontend estático como el backend API.

## Diagrama de Arquitectura

### Desarrollo Local
```
┌─────────────────────────────────────────────┐
│           Navegador del Usuario             │
└──────────────┬──────────────────────────────┘
               │
               │ HTTP Requests
               ↓
┌──────────────────────────────────────────────┐
│         Python HTTP Server (8000)            │
│  • Sirve archivos estáticos (HTML/CSS/JS)   │
│  • Redirige llamadas API al puerto 5000     │
└──────────────┬───────────────────────────────┘
               │
               │ API Calls (fetch)
               ↓
┌──────────────────────────────────────────────┐
│           Flask Backend (5000)               │
│  ┌────────────────────────────────────────┐  │
│  │  Routes                                │  │
│  │  • /admin (CMS)                        │  │
│  │  • /api/* (REST API)                   │  │
│  │  • /uploads/* (archivos subidos)       │  │
│  └────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │  Business Logic                        │  │
│  │  • Autenticación (session)             │  │
│  │  • CRUD animales/noticias              │  │
│  │  • Upload de imágenes                  │  │
│  └────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │  Data Layer                            │  │
│  │  • SQLite (protectora.db)              │  │
│  │  • get_db() helper                     │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

### Producción (Railway/Render)
```
┌─────────────────────────────────────────────┐
│              Internet/CDN                    │
└──────────────┬──────────────────────────────┘
               │
               │ HTTPS
               ↓
┌──────────────────────────────────────────────┐
│         Railway/Render (Cloud)               │
│  ┌────────────────────────────────────────┐  │
│  │  Nginx/Gunicorn                        │  │
│  │  • Reverse proxy                       │  │
│  │  • Load balancing                      │  │
│  │  • SSL termination                     │  │
│  └─────────────┬──────────────────────────┘  │
│                │                              │
│                ↓                              │
│  ┌────────────────────────────────────────┐  │
│  │  Flask App Container (Docker)          │  │
│  │  • Sirve static + API en un solo app  │  │
│  │  • Gunicorn workers (2-4)              │  │
│  └─────────────┬──────────────────────────┘  │
│                │                              │
│                ↓                              │
│  ┌────────────────────────────────────────┐  │
│  │  PostgreSQL Database                   │  │
│  │  • Managed service                     │  │
│  │  • Backups automáticos                 │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  Volume Storage (uploads/)             │  │
│  │  • Persistente entre deploys           │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

## Componentes Principales

### 1. Frontend (Estático)

**Ubicación:** `/` (raíz del proyecto)

**Tecnologías:**
- HTML5 + CSS3
- Vanilla JavaScript (ES6+)
- Font Awesome (iconos)
- Sin frameworks (deliberadamente simple)

**Páginas principales:**
- `index.html` - Inicio
- `pages/adopcion.html` - Catálogo de animales
- `pages/dona.html` - Métodos de donación
- `pages/colabora.html` - Formularios de colaboración
- `pages/contacto.html` - Formulario de contacto
- `pages/actualidad.html` - Blog/noticias

**JavaScript modules:**
- `js/main.js` - Código global, carga animales y noticias
- `js/adopcion.js` - Filtros, búsqueda, modales de animales
- `js/contact.js` - Validación de formularios

### 2. Backend (Flask)

**Ubicación:** `/admin`

**Arquitectura:** Single-file application
- Todo el código está en `app.py` (sin blueprints)
- Deliberadamente simple para facilitar mantenimiento

**Estructura de app.py:**
```python
# 1. Imports y configuración
# 2. Funciones helper (get_db, init_db, etc.)
# 3. Decoradores (login_required, role_required)
# 4. Rutas de autenticación (/admin/login, /logout)
# 5. Rutas del panel admin (/admin/*)
# 6. API endpoints (/api/*)
# 7. Servidor de archivos (/uploads/*, /images/*)
# 8. Utilidades (sitemap.xml, CSV export)
```

**Tecnologías:**
- Flask 3.0
- Jinja2 (templates)
- SQLite (desarrollo) / PostgreSQL (producción)
- Werkzeug (passwords, file upload)
- Flask-CORS (API pública)
- Flask-Limiter (rate limiting)

### 3. Base de Datos

**Desarrollo:** SQLite (`admin/protectora.db`)
**Producción:** PostgreSQL (managed by Railway/Render)

**Esquema:**
```sql
users (id, username, password, email, role, is_active)
animals (id, name, type, age, gender, size, description, image, status)
news (id, title, category, content, excerpt, image, date, published)
contacts (id, name, email, phone, subject, message, read)
collaborators (id, type, name, email, phone, message, extra, status)
adoption_requests (id, animal_id, animal_name, name, email, phone, message, status)
site_settings (key, value)
```

### 4. Sistema de Archivos

**Uploads (persistente):**
```
uploads/
  ├── fotos/          # Fotos de animales y noticias
  ├── videos/         # Videos (futuro)
  └── pdfs/           # Documentos (futuro)
```

**Static (código fuente):**
```
images/
  ├── animales/       # Placeholders SVG (perro.svg, gato.svg)
  ├── logos/          # Logos de sponsors
  └── noticia.svg     # Placeholder noticias
```

## Flujos Principales

### 1. Ver Animales en Adopción

```
Usuario → index.html
         ↓ (DOMContentLoaded)
    main.js::loadFeaturedAnimals()
         ↓ (fetch)
    GET /api/animals?status=adoption
         ↓
    Flask::api_animals()
         ↓ (SQL query)
    SELECT * FROM animals WHERE status='adoption'
         ↓
    JSON response
         ↓
    main.js::createAnimalCard() × N
         ↓
    Render en DOM
```

### 2. Subir Nuevo Animal (Admin)

```
Admin → /admin/animals/new
       ↓ (submit form)
    POST /admin/animals/new
       ↓
    Flask::new_animal()
       ↓
    1. Validate CSRF
    2. secure_filename()
    3. save_image() → Pillow resize
    4. INSERT INTO animals
    5. Redirect a /admin/animals
```

### 3. Deploy Automático (CI/CD)

```
Developer → git push origin main
           ↓
    GitHub triggers webhook
           ↓
    GitHub Actions (.github/workflows/deploy.yml)
           ↓
    1. Checkout code
    2. Run tests (if any)
    3. Trigger Railway deploy
           ↓
    Railway
           ↓
    1. Pull from GitHub
    2. Build Docker image (Dockerfile)
    3. Run database migrations (if needed)
    4. Start Gunicorn
    5. Health check
    6. Switch traffic to new version
```

## Decisiones de Arquitectura

### ¿Por qué Single-File Backend?

**Razones:**
1. **Simplicidad:** Proyecto pequeño-mediano, ~800 LOC
2. **Mantenibilidad:** Un solo archivo para revisar
3. **Curva de aprendizaje:** Fácil para nuevos desarrolladores
4. **Sin over-engineering:** No necesita blueprints/modularización aún

**Cuándo migrar a modular:**
- Si supera 1500 LOC
- Si hay múltiples desarrolladores
- Si se añaden muchas features nuevas

### ¿Por qué Dual-Server en Desarrollo?

**Razones:**
1. **Separación de concerns:** Static vs. Dynamic
2. **Desarrollo frontend:** No requiere reiniciar Flask
3. **CORS simple:** localhost:8000 → localhost:5000
4. **Hot reload:** Solo Flask se reinicia en cambios Python

**En Producción:** Un solo servidor (Flask sirve static + API)

### ¿Por qué Docker?

**Razones:**
1. **Consistencia:** Mismo entorno dev/prod
2. **Facilidad deploy:** Railway/Render soportan Docker nativamente
3. **Aislamiento:** Dependencias encapsuladas
4. **Escalabilidad:** Fácil replicar contenedores

### ¿Por qué PostgreSQL en Producción?

**SQLite limitaciones:**
- No concurrencia de escritura
- No escalable horizontalmente
- No backups automáticos
- No adecuado para producción web

**PostgreSQL ventajas:**
- Concurrent writes
- Backups automáticos (managed service)
- Mejor rendimiento en producción
- JSON support (futuro)

## Seguridad

### Implementadas

1. **Password hashing:** Werkzeug (bcrypt)
2. **CSRF protection:** Token en todos los formularios admin
3. **Session-based auth:** Flask sessions
4. **SQL injection:** Parametrized queries
5. **File upload:** Validation + secure_filename()
6. **Rate limiting:** Flask-Limiter en API pública
7. **HTTPS:** Automático en Railway/Render

### Pendientes (Recomendadas para Producción)

1. **2FA** para admin
2. **Audit logging** (quién modificó qué)
3. **Image scanning** (malware en uploads)
4. **CSP headers** (Content Security Policy)
5. **Backup automático** diario de DB

## Escalabilidad

### Actual (Monolítico)

**Capacidad:**
- ~100 usuarios concurrentes
- ~1000 animales en DB
- ~10MB imágenes/día

**Limitaciones:**
- Un solo servidor
- Uploads en disco local
- Sin cache

### Futuro (si crece)

**Opción 1: Vertical Scaling**
- Más CPU/RAM en Railway
- PostgreSQL con más conexiones
- Simple, funciona hasta 1000 usuarios

**Opción 2: Horizontal Scaling**
```
Load Balancer
  ├── App Instance 1
  ├── App Instance 2
  └── App Instance 3
       ↓
PostgreSQL (managed)
       ↓
S3/Cloudinary (uploads)
```

**Opción 3: Microservicios (overkill para este proyecto)**
- API Gateway
- Animals Service
- News Service
- Upload Service
- Etc.

## Monitoreo

### Logs

**Desarrollo:**
- Console output (print/logger)
- `admin/app.log` (rotativo)

**Producción:**
- Railway/Render dashboard logs
- Opcional: Sentry (error tracking)
- Opcional: LogDNA/Papertrail

### Métricas

**Railway/Render incluyen:**
- CPU/Memory usage
- Request count
- Response time
- Error rate

## Backup y Disaster Recovery

### Desarrollo
```bash
# Backup manual
.\hacer_backup.bat

# Estructura:
backups/
  └── backup_20260327_143022/
      ├── protectora.db
      └── uploads/
```

### Producción

**Base de datos:**
- Railway: Automated daily backups
- Render: Point-in-time recovery

**Uploads:**
- Recomendado: Cloudinary (CDN + backup)
- Alternativa: Railway Volumes (caro)

**Recovery Time Objective (RTO):** < 1 hora
**Recovery Point Objective (RPO):** < 24 horas

## Performance

### Optimizaciones Actuales

1. **Image resize:** Pillow limita a 1200px
2. **Lazy loading:** Imágenes solo cuando visible
3. **SQL indexes:** En id, status, type
4. **Static caching:** Browser cache headers

### Futuras (si necesario)

1. **Redis cache:** Para queries frecuentes
2. **CDN:** CloudFlare para static
3. **Database indexes:** Para búsquedas complejas
4. **Lazy pagination:** Cargar animales bajo demanda

## Costos Estimados

### Desarrollo
- **Gratis** (localhost)

### Producción (Railway Starter)
- **$5/mes:** Incluye app + PostgreSQL
- **+$5/mes:** Si supera límites (poco probable)
- **+$10/mes:** Volumen persistente 1GB (opcional)

### Producción (Alternativas)
- **Render Free:** $0/mes (con limitaciones)
- **Heroku:** $7/mes + $9/mes PostgreSQL
- **DigitalOcean:** $6/mes droplet + $15/mes DB

## Referencias

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Railway Docs](https://docs.railway.app/)
- [PostgreSQL Best Practices](https://wiki.postgresql.org/wiki/Don%27t_Do_This)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/settings.html)
