"""
Sistema CMS básico para Protectora de Animales Burjassot
Backend Flask para gestión de contenido
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory, flash, abort, Response
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import csv
import io
import json
import re
import secrets
import logging
from datetime import datetime
import sqlite3
from functools import wraps

try:
    from PIL import Image as PilImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    LIMITER_AVAILABLE = True
except ImportError:
    LIMITER_AVAILABLE = False
    logger_placeholder = None  # se inicializa después del logger

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cambiar_en_produccion_por_clave_segura')
CORS(app)

# ============================================
# LOGGING A FICHERO
# ============================================

log_path = os.path.join(os.path.dirname(__file__), 'app.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_path, encoding='utf-8'),
        logging.StreamHandler()          # mantiene salida en consola también
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# RATE LIMITING (protege formularios públicos)
# ============================================

if LIMITER_AVAILABLE:
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=[],          # sin límite global; solo se aplica con @limiter.limit
        storage_uri='memory://',    # en producción usar Redis
    )
else:
    # Stub inocuo si Flask-Limiter no está instalado
    class _NoopLimiter:
        def limit(self, *a, **kw):
            return lambda f: f
    limiter = _NoopLimiter()
    logger.warning('Flask-Limiter no instalado. Rate limiting desactivado. '
                   'Ejecuta: pip install Flask-Limiter')


def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']


def validate_csrf():
    token = session.get('_csrf_token')
    form_token = request.form.get('_csrf_token')
    if not token or token != form_token:
        abort(403)


app.jinja_env.globals['csrf_token'] = generate_csrf_token

# Configuración
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'mp4', 'avi', 'mov'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Crear carpetas de subida al iniciar el módulo (no solo en __main__)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'fotos'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'videos'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'pdfs'), exist_ok=True)

# Base de datos SQLite
DATABASE = 'protectora.db'

# Tamaño máximo de imagen al guardar (en píxeles, lado mayor)
IMAGE_MAX_SIZE = 1200

def save_image(file, filepath):
    """
    Guarda una imagen en disco. Si Pillow está disponible y el archivo
    es una imagen web (jpg/png/gif), la redimensiona a máximo IMAGE_MAX_SIZE px
    manteniendo proporciones y la convierte a JPEG para ahorrar espacio.
    Para otros tipos (pdf, video) guarda directamente sin procesar.
    """
    ext = filepath.rsplit('.', 1)[-1].lower()
    if PIL_AVAILABLE and ext in ('jpg', 'jpeg', 'png', 'gif'):
        try:
            img = PilImage.open(file)
            img = img.convert('RGB')   # elimina canal alpha, compatible con JPEG
            if img.width > IMAGE_MAX_SIZE or img.height > IMAGE_MAX_SIZE:
                img.thumbnail((IMAGE_MAX_SIZE, IMAGE_MAX_SIZE), PilImage.LANCZOS)
            # Forzar extensión .jpg para consistencia
            jpeg_path = os.path.splitext(filepath)[0] + '.jpg'
            img.save(jpeg_path, 'JPEG', quality=85, optimize=True)
            logger.info('Imagen guardada y redimensionada: %s', jpeg_path)
            return jpeg_path
        except Exception as e:
            logger.warning('Error al procesar imagen con Pillow (%s): %s. Guardando sin procesar.', filepath, e)
    file.seek(0)  # rebobinar si Pillow no se usó o falló
    file.save(filepath)
    logger.info('Archivo guardado: %s', filepath)
    return filepath


def get_db():
    """Obtener conexión a base de datos"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """Inicializar base de datos"""
    with app.app_context():
        db = get_db()

        # Tabla de usuarios
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT,
                role TEXT DEFAULT 'editor',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Migración: añadir columnas nuevas a DBs pre-existentes
        for col, definition in [('role', "TEXT DEFAULT 'editor'"), ('is_active', 'BOOLEAN DEFAULT 1')]:
            try:
                db.execute(f'ALTER TABLE users ADD COLUMN {col} {definition}')
            except Exception:
                pass  # columna ya existe

        # Tabla de configuración del sitio (clave-valor)
        db.execute('''
            CREATE TABLE IF NOT EXISTS site_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla de animales
        db.execute('''
            CREATE TABLE IF NOT EXISTS animals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                age TEXT,
                gender TEXT,
                size TEXT,
                description TEXT,
                image TEXT,
                status TEXT DEFAULT 'adoption',
                adoption_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla de noticias
        db.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT,
                content TEXT,
                excerpt TEXT,
                image TEXT,
                date TEXT,
                published BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla de contactos
        db.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                subject TEXT,
                message TEXT,
                read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla de colaboradores (socios, voluntarios, padrinos, acogida, empresa)
        db.execute('''
            CREATE TABLE IF NOT EXISTS collaborators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                message TEXT,
                extra TEXT,
                status TEXT DEFAULT 'pendiente',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla de solicitudes de adopción
        db.execute('''
            CREATE TABLE IF NOT EXISTS adoption_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                animal_id INTEGER NOT NULL,
                animal_name TEXT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                message TEXT,
                status TEXT DEFAULT 'pendiente',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (animal_id) REFERENCES animals(id)
            )
        ''')

        # Crear usuario admin por defecto
        try:
            hashed_password = generate_password_hash('protectora2026')
            db.execute('INSERT INTO users (username, password, email, role, is_active) VALUES (?, ?, ?, ?, ?)',
                      ('admin', hashed_password, 'admin@protectoraburjassot.com', 'superadmin', 1))
        except sqlite3.IntegrityError:
            # Si ya existe, asegurarse de que tiene rol superadmin
            db.execute("UPDATE users SET role = 'superadmin', is_active = 1 WHERE username = 'admin'")

        # Insertar configuración del sitio por defecto (solo si no existe)
        default_settings = [
            ('shelter_name', 'Protectora de Animales Burjassot'),
            ('shelter_description', 'Somos una protectora de animales sin ánimo de lucro. Rescatamos, cuidamos y buscamos hogares para animales heridos o abandonados.'),
            ('contact_email', 'info@protectoraburjassot.com'),
            ('contact_phone', '+34 XXX XXX XXX'),
            ('contact_address', 'Burjassot, Valencia'),
            ('contact_hours', 'Lunes a Viernes 10:00-14:00 y 17:00-20:00'),
            ('social_facebook', 'https://www.facebook.com/protectoraburjassot'),
            ('social_instagram', 'https://www.instagram.com/protectoraburjassot'),
            ('social_twitter', 'https://www.twitter.com/protectoraburjassot'),
            ('maps_embed_url', ''),
        ]
        for key, value in default_settings:
            try:
                db.execute('INSERT INTO site_settings (key, value) VALUES (?, ?)', (key, value))
            except Exception:
                pass  # ya existe

        # Insertar datos de ejemplo si la base de datos está vacía
        animal_count = db.execute('SELECT COUNT(*) as count FROM animals').fetchone()['count']
        if animal_count == 0:
            # Datos de ejemplo de animales
            animales_ejemplo = [
                ('Luna', 'perro', '2 años', 'Hembra', 'Mediano',
                 'Luna es una perrita muy cariñosa que busca un hogar donde le den todo el amor que merece. Es tranquila, obediente y se lleva bien con otros perros.',
                 'images/animales/luna.jpg', 'adoption'),
                ('Max', 'perro', '3 años', 'Macho', 'Grande',
                 'Max es un perro juguetón y lleno de energía. Le encanta pasear y jugar con otros perros. Ideal para familias activas.',
                 'images/animales/max.jpg', 'adoption'),
                ('Misi', 'gato', '1 año', 'Hembra', 'Pequeño',
                 'Misi es una gatita muy tranquila y mimosa. Perfecta para un hogar acogedor. Le encanta dormir al sol y recibir caricias.',
                 'images/animales/misi.jpg', 'adoption'),
                ('Simba', 'gato', '4 años', 'Macho', 'Mediano',
                 'Simba es un gato independiente pero cariñoso. Le gusta su espacio pero también los mimos. Perfecto compañero de hogar.',
                 'images/animales/simba.jpg', 'adoption'),
                ('Rocky', 'perro', '5 años', 'Macho', 'Grande',
                 'Rocky es un perro muy leal y protector. Necesita un hogar con experiencia en perros grandes. Es cariñoso con su familia.',
                 'images/animales/rocky.jpg', 'adoption'),
                ('Bella', 'perro', '1 año', 'Hembra', 'Pequeño',
                 'Bella es una perrita pequeña y juguetona. Perfecta para pisos o casas pequeñas. Muy sociable y cariñosa.',
                 'images/animales/bella.jpg', 'adoption'),
                ('Nala', 'gato', '2 años', 'Hembra', 'Pequeño',
                 'Nala es una gatita muy elegante y cariñosa. Le encanta jugar y explorar. Se adapta bien a la vida en interior.',
                 'images/animales/nala.jpg', 'adoption'),
                ('Toby', 'perro', '6 años', 'Macho', 'Mediano',
                 'Toby es un perro adulto muy tranquilo. Ideal para personas mayores o familias que buscan un compañero calmado.',
                 'images/animales/toby.jpg', 'adoption'),
                ('Mía', 'gato', '3 años', 'Hembra', 'Mediano',
                 'Mía es una gata muy cariñosa que busca un hogar tranquilo. Le gusta la rutina y los ambientes relajados.',
                 'images/animales/mia.jpg', 'adoption'),
                ('Bruno', 'perro', '4 años', 'Macho', 'Grande',
                 'Bruno es un perro muy noble y cariñoso. Le encanta estar con su familia y es muy protector con los niños.',
                 'images/animales/bruno.jpg', 'adoption'),
                ('Pelusa', 'gato', '2 años', 'Hembra', 'Pequeño',
                 'Pelusa ya encontró su hogar! Es una gatita muy feliz con su nueva familia.',
                 'images/animales/pelusa.jpg', 'adopted'),
                ('Rex', 'perro', '3 años', 'Macho', 'Grande',
                 'Rex fue adoptado por una familia maravillosa. Ahora disfruta de largos paseos diarios.',
                 'images/animales/rex.jpg', 'adopted'),
            ]

            for animal in animales_ejemplo:
                db.execute('''
                    INSERT INTO animals (name, type, age, gender, size, description, image, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', animal)

        # Insertar noticias de ejemplo si no hay ninguna
        news_count = db.execute('SELECT COUNT(*) as count FROM news').fetchone()['count']
        if news_count == 0:
            noticias_ejemplo = [
                ('Jornada de adopción este fin de semana', 'evento',
                 'Este sábado y domingo estaremos en la Plaza del Ayuntamiento de Burjassot de 10:00 a 14:00 con algunos de nuestros peludos buscando familia. Ven a conocerlos y quizás encuentres a tu nuevo mejor amigo. Habrá actividades para niños y podrás conocer de primera mano nuestra labor. ¡Te esperamos!',
                 'Ven a conocer a nuestros peludos este sábado y domingo en la Plaza del Ayuntamiento. ¡Te esperamos!',
                 'images/news/adoption-event.jpg', '2026-03-25', 1),
                ('Campaña de esterilización marzo 2026', 'campana',
                 'Gracias a vuestras donaciones y al apoyo de nuestros socios, hemos podido esterilizar a 15 animales durante este mes de marzo. La esterilización es fundamental para controlar la población de animales abandonados y mejorar su salud. Seguimos trabajando para poder ayudar a más animales. ¡Muchas gracias por vuestro apoyo!',
                 'Gracias a vuestras donaciones hemos podido esterilizar a 15 animales este mes. ¡Muchas gracias!',
                 'images/news/campaign.jpg', '2026-03-20', 1),
                ('Nuevo convenio con clínica veterinaria', 'blog',
                 'Tenemos una gran noticia. Hemos llegado a un acuerdo de colaboración con la Clínica Veterinaria San Antonio que nos permitirá reducir los costes en tratamientos veterinarios. Esto significa que podremos ayudar a más animales y ofrecerles la atención médica que necesitan. Agradecemos enormemente a la Clínica San Antonio su compromiso con el bienestar animal.',
                 'Hemos llegado a un acuerdo con la Clínica Veterinaria San Antonio para reducir costes en tratamientos.',
                 'images/news/veterinary.jpg', '2026-03-15', 1),
                ('Buscamos voluntarios para eventos', 'blog',
                 'Necesitamos voluntarios que nos ayuden en nuestros eventos de adopción y recaudación de fondos. Si tienes unas horas libres los fines de semana y quieres colaborar con nosotros, ponte en contacto. No hace falta experiencia previa, solo ganas de ayudar. ¡Únete a nuestro equipo!',
                 'Buscamos personas que quieran ayudarnos en eventos los fines de semana. ¡Únete!',
                 'images/news/volunteers.jpg', '2026-03-10', 1),
                ('Rastrillo solidario - Éxito total', 'evento',
                 'El rastrillo solidario del pasado domingo fue todo un éxito. Conseguimos recaudar más de 800 euros que se destinarán íntegramente a gastos veterinarios. Queremos agradecer a todos los que donaron artículos y a los que vinieron a comprar. También a nuestros voluntarios que hicieron posible este evento. ¡Gracias!',
                 'El rastrillo del domingo recaudó más de 800 euros. ¡Gracias a todos!',
                 'images/news/rastrillo.jpg', '2026-03-05', 1),
            ]

            for noticia in noticias_ejemplo:
                db.execute('''
                    INSERT INTO news (title, category, content, excerpt, image, date, published)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', noticia)

        db.commit()

        # Migración: limpiar rutas de imagen de muestra que no existen en disco
        db.execute("UPDATE animals SET image = NULL WHERE image LIKE 'images/animales/%'")
        db.commit()

# Decorador para rutas protegidas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """Decorador que protege rutas según el rol del usuario logueado"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('No tienes permiso para acceder a esta sección.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def allowed_file(filename):
    """Verificar si el archivo tiene extensión permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================
# RUTAS DE AUTENTICACIÓN
# ============================================

@app.route('/')
def index():
    """Ruta raíz - redirige al panel de admin"""
    return redirect(url_for('login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user and check_password_hash(user['password'], password):
            if not user['is_active']:
                return render_template('login.html', error='Cuenta desactivada. Contacta con el administrador.')
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role'] or 'editor'
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Credenciales incorrectas')

    return render_template('login.html')

@app.route('/admin/logout')
def logout():
    """Cerrar sesión"""
    session.clear()
    return redirect(url_for('login'))

# ============================================
# RUTAS DEL PANEL DE ADMINISTRACIÓN
# ============================================

@app.route('/admin')
@app.route('/admin/dashboard')
@login_required
def dashboard():
    """Panel principal con datos para gráficas Chart.js"""
    db = get_db()

    stats = {
        'total_animals': db.execute('SELECT COUNT(*) as count FROM animals WHERE status = "adoption"').fetchone()['count'],
        'total_adopted': db.execute('SELECT COUNT(*) as count FROM animals WHERE status = "adopted"').fetchone()['count'],
        'total_news':    db.execute('SELECT COUNT(*) as count FROM news').fetchone()['count'],
        'unread_contacts': db.execute('SELECT COUNT(*) as count FROM contacts WHERE read = 0').fetchone()['count'],
    }

    # Estadísticas adicionales para tarjetas extra
    try:
        stats['total_foster']    = db.execute('SELECT COUNT(*) as c FROM animals WHERE status = "foster"').fetchone()['c']
        stats['pending_adopt']   = db.execute("SELECT COUNT(*) as c FROM adoption_requests WHERE status = 'pendiente'").fetchone()['c']
        stats['active_collabs']  = db.execute("SELECT COUNT(*) as c FROM collaborators WHERE status = 'activo'").fetchone()['c']
    except Exception:
        stats['total_foster']   = 0
        stats['pending_adopt']  = 0
        stats['active_collabs'] = 0

    # Datos para gráfica: animales por estado
    rows = db.execute('SELECT status, COUNT(*) as c FROM animals GROUP BY status').fetchall()
    animals_by_status = {r['status']: r['c'] for r in rows}

    # Datos para gráfica: contactos por mes (últimos 6 meses)
    rows = db.execute(
        "SELECT strftime('%Y-%m', created_at) as mes, COUNT(*) as c "
        "FROM contacts "
        "GROUP BY strftime('%Y-%m', created_at) "
        "ORDER BY mes DESC LIMIT 6"
    ).fetchall()
    contacts_by_month = [{'mes': r['mes'], 'c': r['c']} for r in reversed(rows)]

    # Datos para gráfica: colaboradores por tipo
    try:
        rows = db.execute('SELECT type, COUNT(*) as c FROM collaborators GROUP BY type').fetchall()
        collabs_by_type = {r['type']: r['c'] for r in rows}
    except Exception:
        collabs_by_type = {}

    recent_contacts = db.execute('SELECT * FROM contacts ORDER BY created_at DESC LIMIT 5').fetchall()

    return render_template(
        'dashboard.html',
        stats=stats,
        contacts=recent_contacts,
        animals_by_status=animals_by_status,
        contacts_by_month=contacts_by_month,
        collabs_by_type=collabs_by_type,
    )

# ============================================
# GESTIÓN DE ANIMALES
# ============================================

@app.route('/admin/animals')
@login_required
def list_animals():
    """Listar animales con paginación"""
    db = get_db()
    page = max(1, request.args.get('page', 1, type=int))
    per_page = 20
    offset = (page - 1) * per_page
    total = db.execute('SELECT COUNT(*) as n FROM animals').fetchone()['n']
    animals = db.execute(
        'SELECT * FROM animals ORDER BY created_at DESC LIMIT ? OFFSET ?',
        (per_page, offset)
    ).fetchall()
    total_pages = (total + per_page - 1) // per_page
    return render_template('animals.html', animals=animals,
                           page=page, total_pages=total_pages, total=total)

@app.route('/admin/animals/new', methods=['GET', 'POST'])
@login_required
def new_animal():
    """Crear nuevo animal"""
    if request.method == 'POST':
        validate_csrf()
        name = request.form.get('name')
        animal_type = request.form.get('type')
        age = request.form.get('age')
        gender = request.form.get('gender')
        size = request.form.get('size')
        description = request.form.get('description')

        # Manejar subida de imagen (new_animal)
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                if filename:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{timestamp}_{filename}"
                    fotos_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'fotos')
                    os.makedirs(fotos_dir, exist_ok=True)
                    filepath = os.path.join(fotos_dir, filename)
                    saved = save_image(file, filepath)
                    image_path = 'uploads/fotos/' + os.path.basename(saved)

        db = get_db()
        db.execute('''
            INSERT INTO animals (name, type, age, gender, size, description, image)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, animal_type, age, gender, size, description, image_path))
        db.commit()

        flash(f'Animal "{name}" añadido correctamente.', 'success')
        return redirect(url_for('list_animals'))

    return render_template('animal_form.html')

@app.route('/admin/animals/<int:animal_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_animal(animal_id):
    """Editar animal"""
    db = get_db()

    if request.method == 'POST':
        validate_csrf()
        name = request.form.get('name')
        animal_type = request.form.get('type')
        age = request.form.get('age')
        gender = request.form.get('gender')
        size = request.form.get('size')
        description = request.form.get('description')
        status = request.form.get('status')

        # Obtener imagen actual
        current_animal = db.execute('SELECT image FROM animals WHERE id = ?', (animal_id,)).fetchone()
        image_path = current_animal['image']

        # Manejar subida de nueva imagen
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                if filename:  # secure_filename puede devolver cadena vacía
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{timestamp}_{filename}"
                    fotos_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'fotos')
                    os.makedirs(fotos_dir, exist_ok=True)
                    filepath = os.path.join(fotos_dir, filename)
                    saved = save_image(file, filepath)
                    filename = os.path.basename(saved)
                    # Borrar imagen anterior del disco si era un upload
                    if image_path and image_path.startswith('uploads/'):
                        old_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), image_path)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    image_path = f"uploads/fotos/{filename}"

        # Actualizar
        db.execute('''
            UPDATE animals
            SET name=?, type=?, age=?, gender=?, size=?, description=?, status=?, image=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        ''', (name, animal_type, age, gender, size, description, status, image_path, animal_id))
        db.commit()

        flash(f'Animal "{name}" actualizado correctamente.', 'success')
        return redirect(url_for('list_animals'))

    animal = db.execute('SELECT * FROM animals WHERE id = ?', (animal_id,)).fetchone()
    return render_template('animal_form.html', animal=animal)

@app.route('/admin/animals/<int:animal_id>/delete', methods=['POST'])
@login_required
def delete_animal(animal_id):
    """Eliminar animal"""
    db = get_db()
    animal = db.execute('SELECT * FROM animals WHERE id = ?', (animal_id,)).fetchone()
    if animal:
        if animal['image'] and animal['image'].startswith('uploads/'):
            old_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), animal['image'])
            if os.path.exists(old_path):
                os.remove(old_path)
        db.execute('DELETE FROM animals WHERE id = ?', (animal_id,))
        db.commit()
        flash(f'Animal "{animal["name"]}" eliminado.', 'success')
    return redirect(url_for('list_animals'))

# ============================================
# GESTIÓN DE NOTICIAS
# ============================================

@app.route('/admin/news')
@login_required
def list_news():
    """Listar noticias con paginación"""
    db = get_db()
    page = max(1, request.args.get('page', 1, type=int))
    per_page = 15
    offset = (page - 1) * per_page
    total = db.execute('SELECT COUNT(*) as n FROM news').fetchone()['n']
    news = db.execute(
        'SELECT * FROM news ORDER BY date DESC LIMIT ? OFFSET ?',
        (per_page, offset)
    ).fetchall()
    total_pages = (total + per_page - 1) // per_page
    return render_template('news.html', news=news,
                           page=page, total_pages=total_pages, total=total)


@app.route('/admin/news/<int:news_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_news(news_id):
    """Editar noticia"""
    db = get_db()
    if request.method == 'POST':
        validate_csrf()
        title = request.form.get('title')
        category = request.form.get('category')
        content = request.form.get('content')
        excerpt = request.form.get('excerpt')
        date = request.form.get('date')
        published = 1 if request.form.get('published') else 0

        current_news = db.execute('SELECT image FROM news WHERE id = ?', (news_id,)).fetchone()
        image_path = current_news['image']

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                if filename:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{timestamp}_{filename}"
                    fotos_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'fotos')
                    os.makedirs(fotos_dir, exist_ok=True)
                    filepath = os.path.join(fotos_dir, filename)
                    saved = save_image(file, filepath)
                    filename = os.path.basename(saved)
                    if image_path and image_path.startswith('uploads/'):
                        old_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), image_path)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    image_path = f"uploads/fotos/{filename}"

        db.execute('''
            UPDATE news
            SET title=?, category=?, content=?, excerpt=?, image=?, date=?, published=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        ''', (title, category, content, excerpt, image_path, date, published, news_id))
        db.commit()
        flash(f'Noticia "{title}" actualizada correctamente.', 'success')
        return redirect(url_for('list_news'))

    news_item = db.execute('SELECT * FROM news WHERE id = ?', (news_id,)).fetchone()
    if not news_item:
        flash('Noticia no encontrada.', 'error')
        return redirect(url_for('list_news'))
    return render_template('news_form.html', news_item=news_item)


@app.route('/admin/news/<int:news_id>/delete', methods=['POST'])
@login_required
def delete_news(news_id):
    """Eliminar noticia"""
    db = get_db()
    item = db.execute('SELECT * FROM news WHERE id = ?', (news_id,)).fetchone()
    if item:
        if item['image'] and item['image'].startswith('uploads/'):
            old_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), item['image'])
            if os.path.exists(old_path):
                os.remove(old_path)
        db.execute('DELETE FROM news WHERE id = ?', (news_id,))
        db.commit()
        flash(f'Noticia "{item["title"]}" eliminada.', 'success')
    return redirect(url_for('list_news'))


@app.route('/admin/news/new', methods=['GET', 'POST'])
@login_required
def new_news():
    """Crear nueva noticia"""
    if request.method == 'POST':
        validate_csrf()
        title = request.form.get('title')
        category = request.form.get('category')
        content = request.form.get('content')
        excerpt = request.form.get('excerpt')
        date = request.form.get('date')
        published = 1 if request.form.get('published') else 0

        # Manejar subida de imagen
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                if filename:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{timestamp}_{filename}"
                    fotos_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'fotos')
                    os.makedirs(fotos_dir, exist_ok=True)
                    filepath = os.path.join(fotos_dir, filename)
                    saved = save_image(file, filepath)
                    image_path = 'uploads/fotos/' + os.path.basename(saved)

        db = get_db()
        db.execute('''
            INSERT INTO news (title, category, content, excerpt, image, date, published)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (title, category, content, excerpt, image_path, date, published))
        db.commit()

        flash(f'Noticia "{title}" creada correctamente.', 'success')
        return redirect(url_for('list_news'))

    return render_template('news_form.html')

# ============================================
# GESTIÓN DE CONTACTOS
# ============================================

@app.route('/admin/contacts')
@login_required
def list_contacts():
    """Listar mensajes de contacto"""
    db = get_db()
    contacts = db.execute('SELECT * FROM contacts ORDER BY created_at DESC').fetchall()
    return render_template('contacts.html', contacts=contacts)


@app.route('/admin/contacts/<int:contact_id>/read', methods=['POST'])
@login_required
def mark_contact_read(contact_id):
    """Marcar contacto como leído"""
    db = get_db()
    db.execute('UPDATE contacts SET read = 1 WHERE id = ?', (contact_id,))
    db.commit()
    return redirect(url_for('list_contacts'))


@app.route('/admin/contacts/<int:contact_id>/delete', methods=['POST'])
@login_required
def delete_contact(contact_id):
    """Eliminar mensaje de contacto"""
    db = get_db()
    db.execute('DELETE FROM contacts WHERE id = ?', (contact_id,))
    db.commit()
    flash('Mensaje eliminado.', 'success')
    return redirect(url_for('list_contacts'))


# ============================================
# CONFIGURACIÓN
# ============================================

@app.route('/admin/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Cambiar contraseña del administrador"""
    if request.method == 'POST':
        validate_csrf()
        current = request.form.get('current_password', '')
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

        if not check_password_hash(user['password'], current):
            flash('La contraseña actual es incorrecta.', 'error')
        elif new_pw != confirm_pw:
            flash('Las contraseñas nuevas no coinciden.', 'error')
        elif len(new_pw) < 8:
            flash('La contraseña debe tener al menos 8 caracteres.', 'error')
        else:
            db.execute('UPDATE users SET password = ? WHERE id = ?',
                       (generate_password_hash(new_pw), session['user_id']))
            db.commit()
            flash('Contraseña cambiada correctamente.', 'success')
            return redirect(url_for('dashboard'))

    return render_template('change_password.html')


# ============================================
# CONFIGURACIÓN DEL SITIO (datos de contacto)
# ============================================

@app.route('/admin/settings', methods=['GET', 'POST'])
@role_required('superadmin')
def admin_settings():
    """Editar datos de contacto, redes sociales e información del sitio"""
    db = get_db()
    if request.method == 'POST':
        validate_csrf()
        keys = [
            'shelter_name', 'shelter_description',
            'contact_email', 'contact_phone', 'contact_address', 'contact_hours',
            'social_facebook', 'social_instagram', 'social_twitter',
            'maps_embed_url',
        ]
        for key in keys:
            value = request.form.get(key, '').strip()
            db.execute(
                'INSERT INTO site_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) '
                'ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP',
                (key, value)
            )
        db.commit()
        flash('Configuración guardada correctamente.', 'success')
        return redirect(url_for('admin_settings'))

    settings = {row['key']: row['value'] for row in db.execute('SELECT * FROM site_settings').fetchall()}
    return render_template('settings.html', settings=settings)


# ============================================
# GESTIÓN DE USUARIOS Y ROLES
# ============================================

VALID_ROLES = ('superadmin', 'editor', 'viewer')

ROLE_LABELS = {
    'superadmin': 'Superadmin',
    'editor': 'Editor',
    'viewer': 'Visor',
}

ROLE_PERMISSIONS = {
    'superadmin': ['Dashboard', 'Animales', 'Noticias', 'Contactos', 'Colaboradores', 'Solicitudes adopción', 'Configuración del sitio', 'Gestión de usuarios'],
    'editor':     ['Dashboard', 'Animales', 'Noticias', 'Contactos', 'Colaboradores', 'Solicitudes adopción'],
    'viewer':     ['Dashboard', 'Animales (solo lectura)', 'Noticias (solo lectura)'],
}


@app.route('/admin/users')
@role_required('superadmin')
def list_users():
    """Listar usuarios del panel de administración"""
    db = get_db()
    users = db.execute(
        'SELECT id, username, email, role, is_active, created_at FROM users ORDER BY created_at'
    ).fetchall()
    return render_template('users.html', users=users, role_labels=ROLE_LABELS,
                           role_permissions=ROLE_PERMISSIONS)


@app.route('/admin/users/new', methods=['GET', 'POST'])
@role_required('superadmin')
def new_user():
    """Crear nuevo usuario"""
    if request.method == 'POST':
        validate_csrf()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'editor')

        if not username or not password:
            flash('Usuario y contraseña son obligatorios.', 'error')
            return render_template('user_form.html', roles=VALID_ROLES, role_labels=ROLE_LABELS,
                                   role_permissions=ROLE_PERMISSIONS)
        if role not in VALID_ROLES:
            flash('Rol no válido.', 'error')
            return render_template('user_form.html', roles=VALID_ROLES, role_labels=ROLE_LABELS,
                                   role_permissions=ROLE_PERMISSIONS)
        if len(password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres.', 'error')
            return render_template('user_form.html', roles=VALID_ROLES, role_labels=ROLE_LABELS,
                                   role_permissions=ROLE_PERMISSIONS)

        db = get_db()
        try:
            db.execute(
                'INSERT INTO users (username, password, email, role, is_active) VALUES (?, ?, ?, ?, 1)',
                (username, generate_password_hash(password), email, role)
            )
            db.commit()
            flash(f'Usuario "{username}" creado correctamente.', 'success')
            return redirect(url_for('list_users'))
        except sqlite3.IntegrityError:
            flash('Ese nombre de usuario ya existe.', 'error')

    return render_template('user_form.html', roles=VALID_ROLES, role_labels=ROLE_LABELS,
                           role_permissions=ROLE_PERMISSIONS)


@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@role_required('superadmin')
def edit_user(user_id):
    """Editar usuario"""
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('list_users'))

    if request.method == 'POST':
        validate_csrf()
        email = request.form.get('email', '').strip()
        role = request.form.get('role', user['role'])
        is_active = 1 if request.form.get('is_active') else 0
        new_password = request.form.get('password', '').strip()

        # Proteger al admin principal
        if user['username'] == 'admin' and (role != 'superadmin' or not is_active):
            flash('No se puede cambiar el rol ni desactivar al usuario "admin" principal.', 'error')
            return render_template('user_form.html', user=user, roles=VALID_ROLES,
                                   role_labels=ROLE_LABELS, role_permissions=ROLE_PERMISSIONS)
        if role not in VALID_ROLES:
            flash('Rol no válido.', 'error')
            return render_template('user_form.html', user=user, roles=VALID_ROLES,
                                   role_labels=ROLE_LABELS, role_permissions=ROLE_PERMISSIONS)
        if new_password and len(new_password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres.', 'error')
            return render_template('user_form.html', user=user, roles=VALID_ROLES,
                                   role_labels=ROLE_LABELS, role_permissions=ROLE_PERMISSIONS)

        if new_password:
            db.execute(
                'UPDATE users SET email=?, role=?, is_active=?, password=? WHERE id=?',
                (email, role, is_active, generate_password_hash(new_password), user_id)
            )
        else:
            db.execute(
                'UPDATE users SET email=?, role=?, is_active=? WHERE id=?',
                (email, role, is_active, user_id)
            )
        db.commit()
        flash(f'Usuario "{user["username"]}" actualizado correctamente.', 'success')
        return redirect(url_for('list_users'))

    return render_template('user_form.html', user=user, roles=VALID_ROLES,
                           role_labels=ROLE_LABELS, role_permissions=ROLE_PERMISSIONS)


@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@role_required('superadmin')
def delete_user(user_id):
    """Eliminar usuario"""
    validate_csrf()
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('list_users'))
    if user['username'] == 'admin':
        flash('No se puede eliminar el usuario "admin" principal.', 'error')
        return redirect(url_for('list_users'))
    if user_id == session.get('user_id'):
        flash('No puedes eliminar tu propia cuenta.', 'error')
        return redirect(url_for('list_users'))
    db.execute('DELETE FROM users WHERE id = ?', (user_id,))
    db.commit()
    flash(f'Usuario "{user["username"]}" eliminado.', 'success')
    return redirect(url_for('list_users'))


# ============================================
# API ENDPOINTS (para el frontend)
# ============================================

@app.route('/api/settings')
def api_settings():
    """API pública para obtener la configuración del sitio (datos de contacto, etc.)"""
    db = get_db()
    rows = db.execute('SELECT key, value FROM site_settings').fetchall()
    return jsonify({row['key']: row['value'] for row in rows})


@app.route('/api/animals')
def api_animals():
    """API para obtener animales"""
    status = request.args.get('status', 'adoption')
    animal_type = request.args.get('type')
    limit = request.args.get('limit', type=int)

    db = get_db()
    # Cuando se pide el listado de adopción, incluir también los reservados
    if status == 'adoption':
        query = 'SELECT * FROM animals WHERE status IN ("adoption", "reserved")'
        params = []
    else:
        query = 'SELECT * FROM animals WHERE status = ?'
        params = [status]
    if animal_type:
        query += ' AND type = ?'
        params.append(animal_type)
    query += ' ORDER BY created_at DESC'
    if limit:
        query += ' LIMIT ?'
        params.append(limit)

    animals = db.execute(query, params).fetchall()
    return jsonify({'animals': [dict(a) for a in animals]})


@app.route('/api/animals/<int:animal_id>')
def api_animal_detail(animal_id):
    """API para obtener un animal por ID"""
    db = get_db()
    animal = db.execute('SELECT * FROM animals WHERE id = ?', (animal_id,)).fetchone()
    if not animal:
        return jsonify({'error': 'Animal no encontrado'}), 404
    return jsonify(dict(animal))

@app.route('/api/news')
def api_news():
    """API para obtener noticias"""
    limit = request.args.get('limit', 10, type=int)

    db = get_db()
    news = db.execute('SELECT * FROM news WHERE published = 1 ORDER BY date DESC LIMIT ?', (limit,)).fetchall()

    return jsonify({'news': [dict(item) for item in news]})


@app.route('/api/news/<int:news_id>')
def api_news_detail(news_id):
    """API para obtener una noticia por ID"""
    db = get_db()
    item = db.execute('SELECT * FROM news WHERE id = ? AND published = 1', (news_id,)).fetchone()
    if not item:
        return jsonify({'error': 'Noticia no encontrada'}), 404
    return jsonify(dict(item))

@app.route('/api/contact', methods=['POST'])
@limiter.limit('5 per minute; 30 per day')
def api_contact():
    """API para recibir contactos"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Datos inválidos'}), 400

    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    subject = data.get('subject', '').strip()
    message = data.get('message', '').strip()

    if not name or not email or not message:
        return jsonify({'error': 'Nombre, email y mensaje son obligatorios'}), 400
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return jsonify({'error': 'Email no válido'}), 400

    db = get_db()
    db.execute('''
        INSERT INTO contacts (name, email, phone, subject, message)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, email, phone, subject, message))
    db.commit()

    return jsonify({'success': True, 'message': 'Mensaje recibido correctamente'})

@app.route('/api/upload', methods=['POST'])
@login_required
def api_upload():
    """API para subir archivos"""
    if 'file' not in request.files:
        return jsonify({'error': 'No se encontró el archivo'}), 400

    file = request.files['file']
    file_type = request.form.get('type', 'fotos')

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"

        upload_subfolder = os.path.join(app.config['UPLOAD_FOLDER'], file_type)
        os.makedirs(upload_subfolder, exist_ok=True)

        filepath = os.path.join(upload_subfolder, filename)
        saved = save_image(file, filepath)
        filename = os.path.basename(saved)

        return jsonify({
            'success': True,
            'url': f"/uploads/{file_type}/{filename}"
        })

    return jsonify({'error': 'Tipo de archivo no permitido'}), 400


# ============================================
# API — COLABORADORES
# ============================================

@app.route('/api/collaborate', methods=['POST'])
@limiter.limit('5 per minute; 20 per day')
def api_collaborate():
    """Recibir solicitudes de colaboración desde el frontend"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Datos inválidos'}), 400

    collab_type = data.get('type', '').strip()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    message = data.get('message', '').strip()
    extra = data.get('extra', '').strip()  # campo adicional según tipo

    valid_types = ['socio', 'padrino', 'voluntario', 'acogida', 'empresa']
    if collab_type not in valid_types:
        return jsonify({'error': 'Tipo de colaboración no válido'}), 400
    if not name or not email:
        return jsonify({'error': 'Nombre y email son obligatorios'}), 400
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return jsonify({'error': 'Email no válido'}), 400

    db = get_db()
    db.execute('''
        INSERT INTO collaborators (type, name, email, phone, message, extra)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (collab_type, name, email, phone, message, extra))
    db.commit()
    return jsonify({'success': True, 'message': 'Solicitud recibida correctamente'})


# ============================================
# ADMIN — GESTIÓN COLABORADORES
# ============================================

@app.route('/admin/collaborators')
@login_required
def list_collaborators():
    db = get_db()
    collab_type = request.args.get('type')
    status = request.args.get('status')
    query = 'SELECT * FROM collaborators WHERE 1=1'
    params = []
    if collab_type:
        query += ' AND type = ?'
        params.append(collab_type)
    if status:
        query += ' AND status = ?'
        params.append(status)
    query += ' ORDER BY created_at DESC'
    collaborators = db.execute(query, params).fetchall()
    return render_template('collaborators.html', collaborators=collaborators,
                           current_type=collab_type, current_status=status)


@app.route('/admin/collaborators/<int:collab_id>/status', methods=['POST'])
@login_required
def update_collaborator_status(collab_id):
    validate_csrf()
    new_status = request.form.get('status')
    if new_status not in ('pendiente', 'activo', 'rechazado'):
        flash('Estado no válido.', 'error')
        return redirect(url_for('list_collaborators'))
    db = get_db()
    db.execute('UPDATE collaborators SET status = ? WHERE id = ?', (new_status, collab_id))
    db.commit()
    flash('Estado actualizado.', 'success')
    return redirect(url_for('list_collaborators'))


@app.route('/admin/collaborators/<int:collab_id>/delete', methods=['POST'])
@login_required
def delete_collaborator(collab_id):
    validate_csrf()
    db = get_db()
    db.execute('DELETE FROM collaborators WHERE id = ?', (collab_id,))
    db.commit()
    flash('Solicitud eliminada.', 'success')
    return redirect(url_for('list_collaborators'))


# ============================================
# API — SOLICITUD DE ADOPCIÓN
# ============================================

@app.route('/api/animals/<int:animal_id>/adopt', methods=['POST'])
@limiter.limit('3 per minute; 10 per day')
def api_adopt(animal_id):
    """Recibir solicitud de adopción de un animal concreto"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Datos inválidos'}), 400

    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    message = data.get('message', '').strip()

    if not name or not email:
        return jsonify({'error': 'Nombre y email son obligatorios'}), 400
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return jsonify({'error': 'Email no válido'}), 400

    db = get_db()
    animal = db.execute('SELECT name FROM animals WHERE id = ?', (animal_id,)).fetchone()
    if not animal:
        return jsonify({'error': 'Animal no encontrado'}), 404

    db.execute('''
        INSERT INTO adoption_requests (animal_id, animal_name, name, email, phone, message)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (animal_id, animal['name'], name, email, phone, message))
    # Marcar el animal como reservado si aún está en adopción
    db.execute(
        'UPDATE animals SET status="reserved", updated_at=CURRENT_TIMESTAMP '
        'WHERE id=? AND status="adoption"',
        (animal_id,)
    )
    db.commit()
    return jsonify({'success': True, 'message': f'Solicitud para adoptar a {animal["name"]} enviada correctamente'})


# ============================================
# ADMIN — SOLICITUDES DE ADOPCIÓN
# ============================================

@app.route('/admin/adoptions')
@login_required
def list_adoptions():
    db = get_db()
    status = request.args.get('status')
    query = 'SELECT * FROM adoption_requests WHERE 1=1'
    params = []
    if status:
        query += ' AND status = ?'
        params.append(status)
    query += ' ORDER BY created_at DESC'
    adoptions = db.execute(query, params).fetchall()
    return render_template('adoptions.html', adoptions=adoptions, current_status=status)


@app.route('/admin/adoptions/<int:req_id>/status', methods=['POST'])
@login_required
def update_adoption_status(req_id):
    validate_csrf()
    new_status = request.form.get('status')
    if new_status not in ('pendiente', 'en_proceso', 'aprobada', 'rechazada'):
        flash('Estado no válido.', 'error')
        return redirect(url_for('list_adoptions'))
    db = get_db()
    db.execute('UPDATE adoption_requests SET status = ? WHERE id = ?', (new_status, req_id))
    db.commit()
    flash('Estado de solicitud actualizado.', 'success')
    return redirect(url_for('list_adoptions'))


@app.route('/admin/adoptions/<int:req_id>/delete', methods=['POST'])
@login_required
def delete_adoption_request(req_id):
    validate_csrf()
    db = get_db()
    db.execute('DELETE FROM adoption_requests WHERE id = ?', (req_id,))
    db.commit()
    flash('Solicitud eliminada.', 'success')
    return redirect(url_for('list_adoptions'))


# ============================================
# API — CAMBIO RÁPIDO DE ESTADO DE ANIMAL
# ============================================

@app.route('/api/animals/<int:animal_id>/status', methods=['PATCH'])
@login_required
def api_animal_quick_status(animal_id):
    """Cambiar el estado de un animal sin entrar al formulario completo"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Datos inválidos'}), 400
    new_status = data.get('status', '').strip()
    if new_status not in ('adoption', 'adopted', 'foster', 'reserved'):
        return jsonify({'error': 'Estado no válido'}), 400
    db = get_db()
    db.execute('UPDATE animals SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
               (new_status, animal_id))
    db.commit()
    return jsonify({'success': True, 'status': new_status})


# ============================================
# SERVIDOR DE ARCHIVOS ESTÁTICOS
# ============================================

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Servir archivos subidos"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/images/<path:filename>')
def static_images(filename):
    """Servir imágenes estáticas del proyecto"""
    images_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'images')
    return send_from_directory(images_folder, filename)

# ============================================
# SITEMAP.XML DINÁMICO
# ============================================

@app.route('/sitemap.xml')
def sitemap_xml():
    """Genera un sitemap.xml con las rutas públicas del sitio"""
    db = get_db()

    # Leer URL base del sitio desde configuración (o usar localhost por defecto)
    try:
        settings = {r['key']: r['value'] for r in
                    db.execute('SELECT key, value FROM site_settings').fetchall()}
        site_url = (settings.get('site_url') or 'http://localhost:8000').rstrip('/')
    except Exception:
        site_url = 'http://localhost:8000'

    animals = db.execute(
        'SELECT id, updated_at FROM animals WHERE status IN ("adoption","reserved") ORDER BY updated_at DESC'
    ).fetchall()
    news = db.execute(
        'SELECT id, date FROM news WHERE published=1 ORDER BY date DESC'
    ).fetchall()

    static_pages = [
        ('/', '1.0', 'weekly'),
        ('/pages/adopcion.html', '0.9', 'daily'),
        ('/pages/actualidad.html', '0.8', 'weekly'),
        ('/pages/colabora.html', '0.7', 'monthly'),
        ('/pages/dona.html', '0.7', 'monthly'),
        ('/pages/nosotros.html', '0.6', 'monthly'),
        ('/pages/contacto.html', '0.6', 'monthly'),
    ]

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

    for path, priority, freq in static_pages:
        lines.append(
            f'  <url><loc>{site_url}{path}</loc>'
            f'<changefreq>{freq}</changefreq><priority>{priority}</priority></url>'
        )
    for a in animals:
        lines.append(
            f'  <url><loc>{site_url}/pages/adopcion.html?id={a["id"]}</loc>'
            f'<changefreq>weekly</changefreq><priority>0.8</priority></url>'
        )
    for n in news:
        lines.append(
            f'  <url><loc>{site_url}/pages/actualidad.html#noticia-{n["id"]}</loc>'
            f'<changefreq>monthly</changefreq><priority>0.6</priority></url>'
        )

    lines.append('</urlset>')
    return Response('\n'.join(lines), mimetype='application/xml')


# ============================================
# EXPORTAR CSV (ADMIN)
# ============================================

@app.route('/admin/contacts/export')
@login_required
def export_contacts_csv():
    """Exportar todos los mensajes de contacto a CSV"""
    db = get_db()
    rows = db.execute(
        'SELECT name, email, phone, subject, message, created_at, read '
        'FROM contacts ORDER BY created_at DESC'
    ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Nombre', 'Email', 'Teléfono', 'Asunto', 'Mensaje', 'Fecha', 'Leído'])
    for r in rows:
        writer.writerow([
            r['name'], r['email'], r['phone'] or '', r['subject'] or '',
            r['message'], r['created_at'], 'Sí' if r['read'] else 'No'
        ])

    output.seek(0)
    logger.info('Exportación CSV contactos por usuario %s', session.get('username'))
    return Response(
        '\ufeff' + output.getvalue(),          # BOM para Excel
        mimetype='text/csv; charset=utf-8-sig',
        headers={'Content-Disposition': 'attachment; filename=contactos.csv'}
    )


@app.route('/admin/collaborators/export')
@login_required
def export_collaborators_csv():
    """Exportar todos los colaboradores a CSV"""
    db = get_db()
    rows = db.execute(
        'SELECT name, email, phone, type, status, message, created_at '
        'FROM collaborators ORDER BY created_at DESC'
    ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Nombre', 'Email', 'Teléfono', 'Tipo', 'Estado', 'Mensaje', 'Fecha'])
    for r in rows:
        writer.writerow([
            r['name'], r['email'], r['phone'] or '', r['type'],
            r['status'], r['message'] or '', r['created_at']
        ])

    output.seek(0)
    logger.info('Exportación CSV colaboradores por usuario %s', session.get('username'))
    return Response(
        '\ufeff' + output.getvalue(),
        mimetype='text/csv; charset=utf-8-sig',
        headers={'Content-Disposition': 'attachment; filename=colaboradores.csv'}
    )

if __name__ == '__main__':
    # Crear carpetas necesarias
    os.makedirs(os.path.join(UPLOAD_FOLDER, 'fotos'), exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_FOLDER, 'videos'), exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_FOLDER, 'pdfs'), exist_ok=True)

    # Inicializar base de datos
    init_db()

    # Iniciar servidor
    print("=" * 50)
    print("CMS Protectora de Animales Burjassot")
    print("=" * 50)
    print("Servidor corriendo en: http://localhost:5000")
    print("Panel de administración: http://localhost:5000/admin")
    print("Usuario: admin")
    print("Contraseña: protectora2026")
    print("¡IMPORTANTE! Cambiar la contraseña después del primer login")
    print("=" * 50)

    app.run(debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true', host='0.0.0.0', port=5000)
