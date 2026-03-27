# 🚀 Guía de Deployment a Producción

## Opción 1: Railway (Recomendada)

### Ventajas
- ✅ Deploy automático desde GitHub
- ✅ PostgreSQL incluido
- ✅ HTTPS gratuito
- ✅ $5/mes gratis
- ✅ Muy fácil de configurar

### Paso 1: Preparar el Proyecto

1. **Asegúrate de tener todos los archivos:**
   - `Dockerfile`
   - `railway.json`
   - `.dockerignore`
   - `.github/workflows/deploy.yml`

2. **Actualiza `admin/requirements.txt`:**
   ```txt
   Flask==3.0.0
   Flask-CORS==4.0.0
   Werkzeug==3.0.1
   gunicorn==21.2.0
   psycopg2-binary==2.9.9
   Pillow==10.2.0
   Flask-Limiter==3.5.0
   ```

### Paso 2: Crear cuenta en Railway

1. Ve a [railway.app](https://railway.app)
2. Inicia sesión con GitHub
3. Crea un nuevo proyecto

### Paso 3: Conectar GitHub

1. En Railway, selecciona "Deploy from GitHub repo"
2. Autoriza acceso a tu repositorio
3. Selecciona el repositorio `Python_WEBAMPARO`

### Paso 4: Añadir PostgreSQL

1. En tu proyecto Railway, haz clic en "+ New"
2. Selecciona "Database" > "PostgreSQL"
3. Railway creará automáticamente la variable `DATABASE_URL`

### Paso 5: Configurar Variables de Entorno

En Railway, ve a Variables y añade:

```env
SECRET_KEY=tu_clave_secreta_muy_larga_y_aleatoria_aqui
FLASK_ENV=production
PORT=5000
PYTHONUNBUFFERED=1
```

**Generar SECRET_KEY segura:**
```python
import secrets
print(secrets.token_hex(32))
```

### Paso 6: Deploy Automático

1. Cada vez que hagas `git push` a la rama `main`, Railway desplegará automáticamente
2. Railway te dará una URL como: `https://tu-app.railway.app`

### Paso 7: Configurar Dominio (Opcional)

1. En Railway > Settings > Domains
2. Puedes usar el dominio gratuito de Railway o conectar tu propio dominio

---

## Opción 2: Render

### Ventajas
- ✅ Plan gratuito disponible
- ✅ Similar a Railway
- ✅ PostgreSQL incluido

### Pasos:

1. Ve a [render.com](https://render.com)
2. Conecta tu repositorio GitHub
3. Crea un "Web Service"
4. Selecciona "Docker" como entorno
5. Añade PostgreSQL desde el dashboard
6. Configura variables de entorno

**Variables necesarias:**
```env
SECRET_KEY=...
DATABASE_URL=postgresql://...
FLASK_ENV=production
```

---

## Opción 3: Vercel (Frontend) + Railway (Backend)

### Arquitectura Separada

**Ventajas:**
- ✅ Frontend ultrarrápido en Vercel
- ✅ Backend escalable en Railway
- ✅ Mejor rendimiento

**Desventajas:**
- ❌ Más complejo de configurar
- ❌ Necesita configurar CORS correctamente

### Pasos:

#### Backend (Railway):
1. Sigue los pasos de Railway anteriores
2. Anota la URL del backend: `https://api.tu-app.railway.app`

#### Frontend (Vercel):
1. Ve a [vercel.com](https://vercel.com)
2. Conecta tu repositorio
3. Configura como "Other" project
4. En Settings > Environment Variables, añade:
   ```env
   VITE_API_URL=https://api.tu-app.railway.app
   ```

---

## Migración de SQLite a PostgreSQL

Railway usará PostgreSQL automáticamente. Para migrar datos existentes:

### 1. Exportar datos de SQLite (Local)

```python
# admin/export_to_postgres.py
import sqlite3
import json

db = sqlite3.connect('protectora.db')
db.row_factory = sqlite3.Row

# Exportar animales
animals = [dict(row) for row in db.execute('SELECT * FROM animals').fetchall()]
with open('animals_export.json', 'w') as f:
    json.dump(animals, f)

# Exportar noticias
news = [dict(row) for row in db.execute('SELECT * FROM news').fetchall()]
with open('news_export.json', 'w') as f:
    json.dump(news, f)
```

### 2. Importar a PostgreSQL (Producción)

Crea un endpoint temporal en `app.py`:

```python
@app.route('/admin/import-data', methods=['POST'])
@login_required
def import_data():
    # Solo disponible en desarrollo
    if not app.config.get('DEBUG'):
        return jsonify({'error': 'Not available'}), 403

    # Importar desde JSON
    # ... código de importación
```

---

## Checklist Pre-Deploy

- [ ] Cambiar `SECRET_KEY` en variables de entorno
- [ ] Configurar `DATABASE_URL` (PostgreSQL)
- [ ] Añadir dominio personalizado (opcional)
- [ ] Configurar backups de base de datos
- [ ] Probar formularios de contacto
- [ ] Verificar subida de imágenes
- [ ] Configurar monitoreo de errores (opcional: Sentry)
- [ ] Configurar analytics (opcional: Google Analytics)

---

## Monitoreo y Logs

### Railway
```bash
# Ver logs en tiempo real
railway logs --follow
```

### Render
- Dashboard > Logs (tiempo real)

---

## Rollback en caso de error

### Railway
1. Ve a Deployments
2. Selecciona un deployment anterior
3. Click en "Rollback"

### Render
- Similar: Deployments > Restore previous

---

## Troubleshooting

### Error: "Database not found"
- Verifica que `DATABASE_URL` esté configurada
- Railway la crea automáticamente al añadir PostgreSQL

### Error: "Module not found"
- Asegúrate de que `gunicorn` esté en requirements.txt
- Railway ejecutará `pip install -r admin/requirements.txt`

### Error: "Port already in use"
- Railway usa la variable `$PORT` automáticamente
- Verifica que Gunicorn esté usando `0.0.0.0:$PORT`

### Las imágenes no se cargan
- Verifica que la carpeta `uploads/` se cree en el contenedor
- En Railway, considera usar almacenamiento externo (S3, Cloudinary) para producción

---

## Costos Aproximados

| Servicio | Plan Gratuito | Plan Paid |
|----------|--------------|-----------|
| Railway | $5/mes de crédito | Desde $5/mes |
| Render | 750h/mes (1 servicio) | Desde $7/mes |
| Vercel | Ilimitado (hobby) | Desde $20/mes |

**Recomendación para empezar:** Railway plan gratuito ($5 de crédito mensual)

---

## Almacenamiento de Archivos en Producción

Para archivos subidos (fotos de animales), en producción es mejor usar:

1. **Cloudinary** (Recomendado)
   - Gratis hasta 25GB
   - Optimización automática de imágenes
   - CDN incluido

2. **AWS S3**
   - Más complejo pero muy escalable

3. **Railway Volumes**
   - Almacenamiento persistente en Railway
   - Más simple pero más caro

---

## Próximos Pasos

1. Sube tu código a GitHub
2. Conecta Railway
3. Configura variables de entorno
4. Deploy automático funcionará

¿Necesitas ayuda con algún paso específico?
