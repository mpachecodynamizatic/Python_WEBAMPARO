# 🚀 Guía de Inicio Rápido - Protectora Burjassot

## Paso 1: Instalar Dependencias

Abre una terminal en la carpeta `admin/` y ejecuta:

```bash
pip install -r requirements.txt
```

## Paso 2: Iniciar el Servidor CMS

```bash
cd admin
python app.py
```

Verás un mensaje como este:
```
==================================================
CMS Protectora de Animales Burjassot
==================================================
Servidor corriendo en: http://localhost:5000
Panel de administración: http://localhost:5000/admin
Usuario: admin
Contraseña: protectora2026
¡IMPORTANTE! Cambiar la contraseña después del primer login
==================================================
```

## Paso 3: Acceder al Panel de Administración

1. Abre tu navegador
2. Ve a: `http://localhost:5000/admin`
3. Inicia sesión con:
   - **Usuario:** `admin`
   - **Contraseña:** `protectora2026`

## Paso 4: Ver el Sitio Web

Abre otra terminal en la carpeta raíz del proyecto:

```bash
python -m http.server 8000
```

Luego abre tu navegador en: `http://localhost:8000`

## 📋 Primeros Pasos en el Panel Admin

### 1. Añadir tu primer animal

1. Ve a "Animales" > "Añadir animal"
2. Completa los datos:
   - Nombre
   - Tipo (Perro/Gato)
   - Edad, género, tamaño
   - Descripción
   - Foto
3. Haz clic en "Guardar"

### 2. Publicar una noticia

1. Ve a "Noticias" > "Nueva noticia"
2. Escribe el título y contenido
3. Selecciona categoría (Campaña/Evento/Blog)
4. Añade una imagen
5. Publica

### 3. Ver los mensajes de contacto

Los mensajes del formulario de contacto aparecerán en el Dashboard

## 🎨 Personalización Básica

### Cambiar datos de contacto

Edita estos archivos y busca las secciones de contacto:
- `index.html`
- `pages/contacto.html`
- Todos los footers de las páginas

Cambia:
```html
<li><i class="fas fa-envelope"></i> TU_EMAIL@ejemplo.com</li>
<li><i class="fas fa-phone"></i> +34 XXX XXX XXX</li>
```

### Configurar datos bancarios

En `pages/dona.html`, busca y cambia:
```html
<span class="code">ES00 0000 0000 00 0000000000</span>
```

### Actualizar enlaces de redes sociales

En todos los archivos HTML, busca y actualiza:
```html
<a href="https://www.facebook.com/TU_PAGINA" target="_blank">
```

### Añadir logos de sponsors

1. Guarda los logos en `images/logos/`
2. Actualiza el footer de las páginas:
```html
<img src="images/logos/sponsor1.png" alt="Sponsor 1">
```

## 📸 Añadir Imágenes

### Logo de la protectora
- Guarda tu logo como `images/logos/logo.png`
- Tamaño recomendado: 200x200px

### Fotos de animales
- Se suben automáticamente desde el panel admin
- Se guardan en `uploads/fotos/`

### Imagen del banner principal
- Guarda como `images/hero-bg.jpg`
- Tamaño recomendado: 1920x600px

## ⚙️ Configuración Avanzada

### Cambiar contraseña de admin

1. Accede al panel admin
2. Ve a Configuración (cuando esté implementado)
3. O modifica directamente en la base de datos `protectora.db`

### Configurar emails

Edita `admin/app.py` y busca la sección de configuración de email (líneas comentadas):

```python
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USERNAME = 'tu_email@gmail.com'
MAIL_PASSWORD = 'contraseña_de_aplicacion'
```

**Nota:** Para Gmail necesitas una "contraseña de aplicación", no tu contraseña normal.

## 🌐 Despliegue en Producción

### Opción 1: Hosting compartido
1. Sube todos los archivos excepto `admin/` a tu servidor
2. Configura el dominio para que apunte a `index.html`

### Opción 2: Servidor propio
1. Instala un servidor web (Apache/Nginx)
2. Configura para servir los archivos estáticos
3. Para el CMS, usa Gunicorn:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

### Opción 3: Servicios cloud
- **Netlify/Vercel:** Para la parte estática
- **Heroku/Railway:** Para el backend Flask

## 🔒 Seguridad

### ¡IMPORTANTE antes de ir a producción!

1. **Cambiar la clave secreta** en `admin/app.py`:
   ```python
   app.secret_key = 'GENERA_UNA_CLAVE_ALEATORIA_SEGURA_AQUI'
   ```

2. **Cambiar contraseña de admin** inmediatamente

3. **Proteger la carpeta admin:**
   - Configurar autenticación HTTP
   - O usar un firewall

4. **Configurar HTTPS:**
   - Usa Let's Encrypt (gratis)
   - O certificado SSL de tu hosting

## 🆘 Solución de Problemas Comunes

### "No module named 'flask'"
```bash
pip install flask flask-cors
```

### Las imágenes no se cargan
- Verifica que las rutas sean correctas
- Asegúrate de que el servidor esté corriendo

### Los filtros de adopción no funcionan
- Abre la consola del navegador (F12)
- Verifica que no haya errores de JavaScript
- Comprueba que `adopcion.js` esté cargado

### El formulario no envía datos
- Asegúrate de que el servidor Flask esté corriendo
- Verifica la configuración de CORS en `app.py`

## 📞 Contacto y Soporte

Si necesitas ayuda:
1. Revisa el archivo `README.md` completo
2. Consulta la documentación de Flask: https://flask.palletsprojects.com/
3. Contacta al desarrollador

## ✅ Checklist Pre-Lanzamiento

- [ ] Cambiar contraseña de admin
- [ ] Actualizar datos de contacto
- [ ] Configurar datos bancarios y Bizum
- [ ] Añadir logos de la protectora y sponsors
- [ ] Actualizar enlaces de redes sociales
- [ ] Probar todos los formularios
- [ ] Añadir animales de prueba
- [ ] Publicar noticias iniciales
- [ ] Configurar emails
- [ ] Probar en diferentes dispositivos
- [ ] Configurar SSL/HTTPS
- [ ] Hacer backup de la base de datos

---

¡Buena suerte con tu sitio web! 🐾❤️
