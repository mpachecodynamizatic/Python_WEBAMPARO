"""
Sistema CMS básico para Protectora de Animales Burjassot
Backend Flask para gestión de contenido
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory, flash, abort
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
import re
import secrets
from datetime import datetime
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cambiar_en_produccion_por_clave_segura')
CORS(app)


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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

        # Crear usuario admin por defecto
        try:
            hashed_password = generate_password_hash('protectora2026')
            db.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)',
                      ('admin', hashed_password, 'admin@protectoraburjassot.com'))
        except sqlite3.IntegrityError:
            pass  # Usuario ya existe

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

# Decorador para rutas protegidas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

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
            session['user_id'] = user['id']
            session['username'] = user['username']
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
    """Panel principal"""
    db = get_db()

    stats = {
        'total_animals': db.execute('SELECT COUNT(*) as count FROM animals WHERE status = "adoption"').fetchone()['count'],
        'total_adopted': db.execute('SELECT COUNT(*) as count FROM animals WHERE status = "adopted"').fetchone()['count'],
        'total_news': db.execute('SELECT COUNT(*) as count FROM news').fetchone()['count'],
        'unread_contacts': db.execute('SELECT COUNT(*) as count FROM contacts WHERE read = 0').fetchone()['count']
    }

    recent_contacts = db.execute('SELECT * FROM contacts ORDER BY created_at DESC LIMIT 5').fetchall()

    return render_template('dashboard.html', stats=stats, contacts=recent_contacts)

# ============================================
# GESTIÓN DE ANIMALES
# ============================================

@app.route('/admin/animals')
@login_required
def list_animals():
    """Listar animales"""
    db = get_db()
    animals = db.execute('SELECT * FROM animals ORDER BY created_at DESC').fetchall()
    return render_template('animals.html', animals=animals)

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

        # Manejar subida de imagen
        image_path = None
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
                    file.save(filepath)
                    image_path = f"uploads/fotos/{filename}"

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
                    file.save(filepath)
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
    """Listar noticias"""
    db = get_db()
    news = db.execute('SELECT * FROM news ORDER BY date DESC').fetchall()
    return render_template('news.html', news=news)


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
                    file.save(filepath)
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
                    file.save(filepath)
                    image_path = f"uploads/fotos/{filename}"

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
# API ENDPOINTS (para el frontend)
# ============================================

@app.route('/api/animals')
def api_animals():
    """API para obtener animales"""
    status = request.args.get('status', 'adoption')
    animal_type = request.args.get('type')
    limit = request.args.get('limit', type=int)

    db = get_db()
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
        file.save(filepath)

        return jsonify({
            'success': True,
            'url': f"/uploads/{file_type}/{filename}"
        })

    return jsonify({'error': 'Tipo de archivo no permitido'}), 400

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
# INICIALIZACIÓN
# ============================================

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
