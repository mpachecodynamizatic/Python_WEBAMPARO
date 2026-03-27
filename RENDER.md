# 🚀 Guía de Deployment en Render

## ¿Qué es Render?

Render es una plataforma moderna de deployment similar a Heroku/Railway, con:
- ✅ **Plan gratuito** (750 horas/mes)
- ✅ **Deploy automático** desde GitHub
- ✅ **PostgreSQL gratis** incluido
- ✅ **HTTPS automático**
- ✅ **Muy fácil de usar**

---

## Paso 1: Preparar tu Código

### 1.1 Asegúrate de tener estos archivos

Ya están creados en tu proyecto:
- ✅ `admin/requirements.txt` (con gunicorn y psycopg2-binary)
- ✅ `render.yaml` (configuración automática)

### 1.2 Sube tu código a GitHub

```bash
# Si aún no tienes un repositorio Git
git init
git add .
git commit -m "Preparar para deployment en Render"

# Crear repositorio en GitHub y subirlo
git remote add origin https://github.com/TU-USUARIO/TU-REPO.git
git push -u origin main
```

---

## Paso 2: Crear Cuenta en Render

1. Ve a [render.com](https://render.com)
2. Haz clic en **"Get Started for Free"**
3. Inicia sesión con **GitHub**
4. Autoriza a Render para acceder a tus repositorios

---

## Paso 3: Crear el Servicio Web

### Opción A: Usando render.yaml (Automático) ⭐ **Recomendado**

1. En el dashboard de Render, haz clic en **"New +"**
2. Selecciona **"Blueprint"**
3. Conecta tu repositorio de GitHub
4. Render detectará automáticamente el `render.yaml`
5. Haz clic en **"Apply"**
6. ¡Listo! Render creará automáticamente:
   - El servicio web
   - La base de datos PostgreSQL
   - Las variables de entorno

### Opción B: Manual (Paso a Paso)

Si prefieres configurarlo manualmente:

#### 3.1 Crear Web Service

1. En Render dashboard: **"New +" → "Web Service"**
2. Conecta tu repositorio GitHub
3. Configura:
   ```
   Name: protectora-burjassot
   Runtime: Python 3
   Build Command: pip install -r admin/requirements.txt
   Start Command: gunicorn --bind 0.0.0.0:$PORT --workers 2 --chdir admin app:app
   ```

#### 3.2 Crear PostgreSQL Database

1. En Render dashboard: **"New +" → "PostgreSQL"**
2. Configura:
   ```
   Name: protectora-db
   Database: protectora
   User: protectora
   ```
3. Selecciona el plan **Free**
4. Crea la base de datos

#### 3.3 Conectar la Base de Datos

1. Ve a tu Web Service
2. En **"Environment"** → **"Environment Variables"**
3. Añade:
   ```
   DATABASE_URL = <copia la "External Database URL" de tu PostgreSQL>
   SECRET_KEY = <genera una clave aleatoria>
   FLASK_ENV = production
   ```

**Generar SECRET_KEY:**
```python
import secrets
print(secrets.token_hex(32))
```

---

## Paso 4: Configurar Variables de Entorno

En el dashboard de Render → Tu servicio → **Environment**:

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `SECRET_KEY` | (generada automáticamente) | Clave secreta de Flask |
| `FLASK_ENV` | `production` | Entorno de ejecución |
| `DATABASE_URL` | (de PostgreSQL) | URL de conexión a base de datos |

---

## Paso 5: Deploy

### Primera vez:
Render detectará el push y desplegará automáticamente. Verás logs en tiempo real.

### Deployments futuros:
Cada vez que hagas `git push` a la rama `main`, Render desplegará automáticamente.

---

## Paso 6: Verificar el Deploy

1. Ve a **"Logs"** en tu servicio para ver si inició correctamente
2. Espera a que el status sea **"Live"** (verde)
3. Haz clic en la URL de tu aplicación (algo como: `https://protectora-burjassot.onrender.com`)

### URLs importantes:
```
Sitio público: https://tu-app.onrender.com
Panel admin:   https://tu-app.onrender.com/admin
```

**Credenciales por defecto:**
- Usuario: `admin`
- Contraseña: `protectora2026` (cámbiala inmediatamente)

---

## Paso 7: Migrar Datos (Opcional)

Si tienes datos en tu SQLite local que quieres migrar a PostgreSQL:

### 7.1 Exportar desde SQLite local

Crea un archivo `export_data.py`:

```python
import sqlite3
import json

db = sqlite3.connect('admin/protectora.db')
db.row_factory = sqlite3.Row

# Exportar animales
animals = [dict(row) for row in db.execute('SELECT * FROM animals').fetchall()]
with open('animals.json', 'w', encoding='utf-8') as f:
    json.dump(animals, f, ensure_ascii=False, indent=2)

# Exportar noticias
news = [dict(row) for row in db.execute('SELECT * FROM news').fetchall()]
with open('news.json', 'w', encoding='utf-8') as f:
    json.dump(news, f, ensure_ascii=False, indent=2)

print("Datos exportados a animals.json y news.json")
```

```bash
python export_data.py
```

### 7.2 Importar a PostgreSQL en Render

1. Conecta a tu base de datos Render:
   ```bash
   # Copia la "External Database URL" de Render
   # Ejemplo: postgresql://user:pass@host/database

   # Conéctate usando psql (si lo tienes instalado)
   psql <tu-database-url>
   ```

2. O usa un endpoint temporal en tu app para importar los JSON
   (Solo disponible en modo development, añade seguridad)

---

## Configuración Avanzada

### Dominio Personalizado

1. En Render → Tu servicio → **"Settings"** → **"Custom Domains"**
2. Añade tu dominio (ej: `www.protectoraburjassot.com`)
3. Configura los registros DNS según las instrucciones de Render
4. Render configurará HTTPS automáticamente

### Almacenamiento de Archivos

⚠️ **Importante:** Render NO tiene almacenamiento persistente para archivos subidos.

**Solución:** Usar un servicio externo para uploads:

#### Opción 1: Cloudinary (Recomendado)
- Gratis hasta 25GB
- Optimización de imágenes automática
- CDN incluido

```bash
pip install cloudinary
```

Modifica `admin/app.py` para subir a Cloudinary en lugar de disco local.

#### Opción 2: AWS S3
- Más complejo pero muy escalable
- Requiere cuenta AWS

---

## Monitoreo y Logs

### Ver Logs en Tiempo Real
1. Dashboard → Tu servicio → **"Logs"**
2. Ver últimas 100 líneas de log
3. Buscar errores

### Métricas
1. Dashboard → Tu servicio → **"Metrics"**
2. CPU, Memory, Request count
3. Gratis en plan free

---

## Troubleshooting

### Error: "Application failed to start"

**Solución:**
1. Verifica logs en Render
2. Asegúrate de que `requirements.txt` incluye gunicorn
3. Verifica que el Start Command sea correcto:
   ```
   gunicorn --bind 0.0.0.0:$PORT --workers 2 --chdir admin app:app
   ```

### Error: "Database connection failed"

**Solución:**
1. Verifica que `DATABASE_URL` esté configurada
2. Asegúrate de que `psycopg2-binary` esté en requirements.txt
3. En Render, verifica que la base de datos esté "Available"

### Error: "Module not found"

**Solución:**
1. Añade el módulo faltante a `admin/requirements.txt`
2. Haz commit y push
3. Render redesplegará automáticamente

### Las imágenes subidas desaparecen

**Explicación:**
Render reinicia los contenedores periódicamente, borrando archivos subidos.

**Solución:**
Usar Cloudinary o S3 para almacenamiento de imágenes (ver sección arriba).

---

## Diferencias entre Desarrollo y Producción

| Aspecto | Desarrollo (Local) | Producción (Render) |
|---------|-------------------|---------------------|
| Base de datos | SQLite | PostgreSQL |
| Servidor | Flask dev server | Gunicorn |
| Puerto | 5000 | Asignado por Render ($PORT) |
| HTTPS | No | Sí (automático) |
| Uploads | Disco local | Cloudinary/S3 recomendado |
| URL | localhost:5000 | tu-app.onrender.com |

---

## Actualizar la Aplicación

```bash
# Hacer cambios en el código
git add .
git commit -m "Descripción de los cambios"
git push origin main

# Render despliega automáticamente
# Recibirás notificación cuando termine
```

---

## Rollback (Volver a Versión Anterior)

1. Dashboard → Tu servicio → **"Events"**
2. Encuentra el deploy que funcionaba
3. Haz clic en **"Rollback to this version"**

---

## Plan Gratuito vs. Paid

### Plan Gratuito
- ✅ 750 horas/mes (suficiente para 1 app)
- ✅ PostgreSQL incluido
- ✅ HTTPS
- ⚠️ La app duerme después de 15 min de inactividad
- ⚠️ Primer request después de dormir es lento (~30 seg)

### Plan Paid ($7/mes)
- ✅ App siempre activa
- ✅ Más recursos (CPU/RAM)
- ✅ Sin suspensión

**Recomendación:** Empieza con plan gratuito. Actualiza solo si necesitas que esté siempre activa.

---

## Costos Aproximados

| Servicio | Plan Free | Plan Starter |
|----------|-----------|--------------|
| Web Service | $0 (750h/mes) | $7/mes |
| PostgreSQL | $0 (90 días) | $7/mes |
| **Total** | **$0** | **$14/mes** |

**Nota:** El PostgreSQL gratuito expira después de 90 días. Después necesitas el plan paid.

---

## Checklist Pre-Deployment

Antes de desplegar, verifica:

- [ ] Código subido a GitHub
- [ ] `admin/requirements.txt` incluye gunicorn y psycopg2-binary
- [ ] Cambiaste la `SECRET_KEY` en variables de entorno
- [ ] PostgreSQL creada y conectada
- [ ] Probado localmente con `run.bat`
- [ ] Commit y push a GitHub

---

## Próximos Pasos Después del Deploy

1. **Cambiar contraseña de admin**
   - Ve a `/admin/change-password`

2. **Configurar Cloudinary** (para imágenes)
   - Crea cuenta en cloudinary.com
   - Añade credenciales en variables de entorno
   - Modifica código para subir a Cloudinary

3. **Añadir Google Analytics** (opcional)
   - Para monitorear visitas

4. **Configurar dominio personalizado** (opcional)
   - Comprar dominio
   - Configurar DNS

---

## Soporte

- **Documentación Render:** https://render.com/docs
- **Community Forum:** https://community.render.com
- **Status:** https://status.render.com

---

## Resumen Rápido

```bash
# 1. Subir a GitHub
git add .
git commit -m "Preparar para Render"
git push origin main

# 2. Ir a render.com
# 3. New + → Blueprint
# 4. Conectar repo GitHub
# 5. Apply
# 6. ¡Listo! 🎉
```

**Tu app estará en:** `https://protectora-burjassot.onrender.com`

¿Necesitas ayuda con algún paso específico?
