# Protectora de Animales Burjassot - Sitio Web

Sitio web moderno y responsive para la Protectora de Animales de Burjassot, diseñado para facilitar la adopción, donación y colaboración con la protectora.

## 🎯 Características

- ✅ Diseño responsive (móvil, tablet y desktop)
- ✅ Página de adopción con filtros (perros/gatos)
- ✅ Sistema de donaciones múltiples (Teaming, Bizum, Transferencia, Amazon, Wallapop)
- ✅ Formularios de contacto y empresa solidaria
- ✅ Integración con redes sociales
- ✅ Diseño visual con colores suaves y elementos temáticos
- ✅ Bilingüe (Español/Valenciano)
- ✅ Sistema CMS para gestionar contenido

## 📁 Estructura del Proyecto

```
Python_WEBAMPARO/
├── index.html              # Página principal
├── css/
│   ├── styles.css         # Estilos globales
│   ├── adopcion.css       # Estilos página adopción
│   ├── dona.css           # Estilos página donaciones
│   ├── colabora.css       # Estilos página colabora
│   └── forms.css          # Estilos formularios
├── js/
│   ├── main.js            # JavaScript principal
│   ├── adopcion.js        # Lógica de filtros adopción
│   └── contact.js         # Manejo de formularios
├── pages/
│   ├── adopcion.html      # Animales en adopción
│   ├── contacto.html      # Formulario de contacto
│   ├── dona.html          # Métodos de donación
│   └── colabora.html      # Formas de colaborar
├── images/
│   ├── animales/          # Fotos de animales
│   ├── logos/             # Logos y sponsors
│   └── icons/             # Iconos
├── uploads/               # Archivos subidos
│   ├── fotos/
│   ├── videos/
│   └── pdfs/
├── admin/                 # Panel de administración
│   ├── app.py            # Backend Flask
│   ├── templates/        # Plantillas admin
│   └── static/           # Recursos admin
└── README.md
```

## 🚀 Instalación y Configuración

### Requisitos Previos

- Python 3.8 o superior
- Navegador web moderno
- Editor de código (recomendado: VS Code)

### Instalación del CMS

1. Instalar dependencias de Python:

```bash
cd admin
pip install -r requirements.txt
```

2. Iniciar el servidor de desarrollo:

```bash
python app.py
```

3. Acceder al panel de administración:

```
http://localhost:5000/admin
```

**Credenciales por defecto:**
- Usuario: `admin`
- Contraseña: `protectora2026` (cambiar inmediatamente)

### Despliegue del Sitio Web

#### Opción 1: Servidor Web Local (Desarrollo)

```bash
# Con Python
python -m http.server 8000

# Acceder a:
http://localhost:8000
```

#### Opción 2: Servidor Web en Producción

Subir todos los archivos a tu servidor web (Apache, Nginx, etc.) y configurar:

1. Apuntar el dominio a la carpeta raíz
2. Configurar SSL (recomendado)
3. Configurar permisos para la carpeta `uploads/`

## 📝 Gestión de Contenido

### Añadir Animales en Adopción

1. Acceder al panel admin: `/admin`
2. Ir a "Animales" > "Nuevo animal"
3. Completar el formulario:
   - Nombre
   - Tipo (Perro/Gato)
   - Edad
   - Género
   - Tamaño
   - Descripción
   - Foto (JPG, PNG, máx 5MB)
4. Guardar

### Publicar Noticias

1. Panel admin > "Actualidad" > "Nueva noticia"
2. Completar:
   - Título
   - Fecha
   - Categoría (Campaña/Evento/Blog)
   - Contenido
   - Imagen destacada
3. Publicar

### Subir Documentos PDF

1. Panel admin > "Documentos" > "Subir PDF"
2. Seleccionar archivo
3. Categorizar (Campaña mensual, Manual, etc.)
4. Subir

### Gestionar Adoptados

1. Panel admin > "Animales" > Seleccionar animal
2. Cambiar estado a "Adoptado"
3. Añadir fecha de adopción
4. Guardar

## 🎨 Personalización

### Cambiar Colores

Editar variables CSS en `css/styles.css`:

```css
:root {
    --primary-color: #F4A460;      /* Color principal */
    --secondary-color: #87CEEB;    /* Color secundario */
    --accent-color: #FFB6C1;       /* Color acento */
    /* ... más colores ... */
}
```

### Actualizar Información de Contacto

Editar en todas las páginas HTML:

```html
<li><i class="fas fa-envelope"></i> TU_EMAIL@ejemplo.com</li>
<li><i class="fas fa-phone"></i> +34 XXX XXX XXX</li>
```

### Configurar Redes Sociales

Actualizar enlaces en el header y footer de todas las páginas:

```html
<a href="https://www.facebook.com/TU_PAGINA" target="_blank">
    <i class="fab fa-facebook-f"></i>
</a>
```

### Configurar Datos Bancarios

Editar en `pages/dona.html`:

```html
<span class="code">ES00 0000 0000 00 0000000000</span>
```

## 📱 Funcionalidades Principales

### Sistema de Filtros de Adopción

- Filtrar por tipo (Todos/Perros/Gatos)
- Búsqueda por nombre
- Vista responsive en grid

### Formularios

1. **Contacto**: Formulario general con validación
2. **Empresa Solidaria**: Formulario específico para empresas
3. Validación en tiempo real
4. Mensajes de éxito/error

### Multiidioma

Selector de idioma (ES/VAL) en header:
- Cambia idioma del sitio
- Guarda preferencia en localStorage
- Traducciones en `js/main.js`

## 🔒 Seguridad

### Recomendaciones

1. **Cambiar contraseña admin** inmediatamente
2. **Configurar HTTPS** en producción
3. **Limitar tamaño de archivos** subidos
4. **Validar formularios** en backend
5. **Backup regular** de base de datos

### Archivos Sensibles

No exponer públicamente:
- `/admin/` - Proteger con .htaccess o similar
- Archivos de configuración
- Base de datos

## 📧 Configuración de Email

Para que los formularios envíen emails, configurar en `admin/app.py`:

```python
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USERNAME = 'tu_email@gmail.com'
MAIL_PASSWORD = 'tu_contraseña_aplicacion'
MAIL_DEFAULT_SENDER = 'tu_email@gmail.com'
```

## 🐛 Solución de Problemas

### Las imágenes no se cargan

- Verificar que las rutas sean correctas
- Comprobar permisos de carpeta `images/`
- Verificar que las imágenes existan

### Los filtros no funcionan

- Abrir consola del navegador (F12)
- Verificar errores de JavaScript
- Comprobar que `adopcion.js` esté cargado

### El formulario no se envía

- Verificar configuración de email en backend
- Comprobar que el servidor Flask esté corriendo
- Revisar logs de error

## 📞 Soporte

Para soporte técnico:
- Email: info@protectoraburjassot.com
- Documentación: Este archivo README

## 📄 Licencia

Este proyecto ha sido desarrollado específicamente para la Protectora de Animales de Burjassot.

## 🎉 Agradecimientos

Desarrollado con ❤️ para ayudar a los animales que más lo necesitan.

---

**Versión:** 1.0.0
**Última actualización:** Marzo 2026
