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
import base64
from urllib.parse import urlparse

try:
    from PIL import Image as PilImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

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
    form_token = request.form.get('_csrf_token') or request.headers.get('X-CSRFToken')
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

# ============================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================
# Detecta automáticamente si usar PostgreSQL (producción/Render) o SQLite (desarrollo local)
DATABASE_URL = os.environ.get('DATABASE_URL')  # Render proporciona esto automáticamente
USE_POSTGRES = DATABASE_URL is not None and PSYCOPG2_AVAILABLE

if USE_POSTGRES:
    logger.info('🐘 Usando PostgreSQL (producción)')
    # Render proporciona DATABASE_URL con postgres://, pero psycopg2 necesita postgresql://
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
else:
    logger.info('📁 Usando SQLite (desarrollo local)')
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


def compress_image_to_base64(file, max_size=800, quality=75):
    """
    Comprime una imagen y la convierte a base64 para almacenar en base de datos.
    Retorna string base64 con prefijo data:image/jpeg;base64,
    """
    if not PIL_AVAILABLE:
        # Si no hay Pillow, leer archivo directo y convertir a base64
        file.seek(0)
        img_data = file.read()
        b64 = base64.b64encode(img_data).decode('utf-8')
        return f"data:image/jpeg;base64,{b64}"

    try:
        file.seek(0)
        img = PilImage.open(file)
        img = img.convert('RGB')

        # Redimensionar si es muy grande
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), PilImage.LANCZOS)

        # Guardar en buffer de memoria como JPEG comprimido
        buffer = io.BytesIO()
        img.save(buffer, 'JPEG', quality=quality, optimize=True)
        buffer.seek(0)

        # Convertir a base64
        img_data = buffer.getvalue()
        b64 = base64.b64encode(img_data).decode('utf-8')

        logger.info('Imagen comprimida a base64 (tamaño: %d bytes)', len(img_data))
        return f"data:image/jpeg;base64,{b64}"
    except Exception as e:
        logger.error('Error al comprimir imagen: %s', e)
        # Fallback: leer archivo directo
        file.seek(0)
        img_data = file.read()
        b64 = base64.b64encode(img_data).decode('utf-8')
        return f"data:image/jpeg;base64,{b64}"


def send_notification_email(subject, body):
    """Envío de email de notificación al administrador vía SMTP, SendGrid o Mailgun"""
    try:
        provider     = get_setting('email_provider', 'smtp').strip().lower()
        notify_email = get_setting('notify_email', '').strip()
        if not notify_email:
            return  # sin destino, ignorar silenciosamente

        if provider == 'sendgrid':
            import requests as req
            api_key   = get_setting('sendgrid_api_key', '').strip()
            smtp_from = get_setting('smtp_from', '').strip() or 'noreply@protectoraburjassot.org'
            if not api_key:
                logger.warning('SendGrid: api_key no configurada')
                return
            resp = req.post(
                'https://api.sendgrid.com/v3/mail/send',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json={
                    'personalizations': [{'to': [{'email': notify_email}]}],
                    'from': {'email': smtp_from},
                    'subject': subject,
                    'content': [{'type': 'text/plain', 'value': body}]
                },
                timeout=10
            )
            if resp.status_code not in (200, 202):
                logger.warning('SendGrid error %s: %s', resp.status_code, resp.text[:200])
            else:
                logger.info('Email SendGrid enviado a %s', notify_email)

        elif provider == 'mailgun':
            import requests as req
            api_key   = get_setting('mailgun_api_key', '').strip()
            domain    = get_setting('mailgun_domain', '').strip()
            smtp_from = get_setting('smtp_from', '').strip() or f'Protectora <mailgun@{domain}>'
            if not api_key or not domain:
                logger.warning('Mailgun: api_key o dominio no configurados')
                return
            resp = req.post(
                f'https://api.mailgun.net/v3/{domain}/messages',
                auth=('api', api_key),
                data={'from': smtp_from, 'to': notify_email, 'subject': subject, 'text': body},
                timeout=10
            )
            if resp.status_code != 200:
                logger.warning('Mailgun error %s: %s', resp.status_code, resp.text[:200])
            else:
                logger.info('Email Mailgun enviado a %s', notify_email)

        else:  # smtp (por defecto)
            import smtplib
            from email.message import EmailMessage
            smtp_host = get_setting('smtp_host', '').strip()
            smtp_port = int(get_setting('smtp_port', '587') or '587')
            smtp_user = get_setting('smtp_user', '').strip()
            smtp_pass = get_setting('smtp_password', '').strip()
            smtp_from = get_setting('smtp_from', '').strip() or smtp_user
            if not smtp_host or not smtp_user:
                return  # no configurado, ignorar silenciosamente
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From']    = smtp_from
            msg['To']      = notify_email
            msg.set_content(body)
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            logger.info('Email SMTP enviado a %s', notify_email)

    except Exception as e:
        logger.warning('Error al enviar email de notificacion: %s', e)


def send_html_email(to_email, subject, body_html, body_text=None):
    """Envía un email HTML a una dirección usando el proveedor configurado (smtp/sendgrid/mailgun)"""
    import re
    if not body_text:
        body_text = re.sub(r'<[^>]+>', ' ', body_html).strip()
    try:
        provider  = get_setting('email_provider', 'smtp').strip().lower()
        smtp_from = get_setting('smtp_from', '').strip()

        if provider == 'sendgrid':
            import requests as req
            api_key = get_setting('sendgrid_api_key', '').strip()
            if not api_key or not smtp_from:
                logger.warning('SendGrid: falta api_key o smtp_from')
                return False
            resp = req.post(
                'https://api.sendgrid.com/v3/mail/send',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json={
                    'personalizations': [{'to': [{'email': to_email}]}],
                    'from': {'email': smtp_from},
                    'subject': subject,
                    'content': [
                        {'type': 'text/plain', 'value': body_text},
                        {'type': 'text/html',  'value': body_html},
                    ]
                },
                timeout=15
            )
            return resp.status_code in (200, 202)

        elif provider == 'mailgun':
            import requests as req
            api_key = get_setting('mailgun_api_key', '').strip()
            domain  = get_setting('mailgun_domain', '').strip()
            if not api_key or not domain:
                logger.warning('Mailgun: falta api_key o dominio')
                return False
            from_addr = smtp_from or f'Protectora <mailgun@{domain}>'
            resp = req.post(
                f'https://api.mailgun.net/v3/{domain}/messages',
                auth=('api', api_key),
                data={'from': from_addr, 'to': to_email,
                      'subject': subject, 'text': body_text, 'html': body_html},
                timeout=15
            )
            return resp.status_code == 200

        else:  # smtp
            import smtplib
            from email.message import EmailMessage
            smtp_host = get_setting('smtp_host', '').strip()
            smtp_port = int(get_setting('smtp_port', '587') or '587')
            smtp_user = get_setting('smtp_user', '').strip()
            smtp_pass = get_setting('smtp_password', '').strip()
            from_addr = smtp_from or smtp_user
            if not smtp_host or not smtp_user:
                logger.warning('SMTP: host o usuario no configurados')
                return False
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From']    = from_addr
            msg['To']      = to_email
            msg.set_content(body_text)
            msg.add_alternative(body_html, subtype='html')
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            return True

    except Exception as e:
        logger.warning('Error al enviar email a %s: %s', to_email, e)
        return False


def get_setting(key, default=None):
    """Obtener un valor de configuración de site_settings"""
    try:
        db = get_db()
        cursor = db.cursor()
        if USE_POSTGRES:
            cursor.execute('SELECT value FROM site_settings WHERE key = %s', (key,))
        else:
            cursor.execute('SELECT value FROM site_settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        cursor.close()
        return result['value'] if result else default
    except:
        return default


def get_placeholder():
    """Retorna el placeholder correcto para consultas SQL según la BD"""
    return '%s' if USE_POSTGRES else '?'


@app.context_processor
def inject_nav_badges():
    """Inyecta contadores de pendientes en todas las plantillas del panel"""
    if not session.get('user_id'):
        return {}
    try:
        db = get_db()
        unread_contacts = db.execute(
            "SELECT COUNT(*) as c FROM contacts WHERE read = 0"
        ).fetchone()['c']
        pending_adoptions = db.execute(
            "SELECT COUNT(*) as c FROM adoption_requests WHERE status = 'pendiente'"
        ).fetchone()['c']
        pending_visits = db.execute(
            "SELECT COUNT(*) as c FROM visit_requests WHERE status = 'pendiente'"
        ).fetchone()['c']
        return {
            'nav_unread_contacts':   unread_contacts,
            'nav_pending_adoptions': pending_adoptions,
            'nav_pending_visits':    pending_visits,
        }
    except Exception:
        return {
            'nav_unread_contacts':   0,
            'nav_pending_adoptions': 0,
            'nav_pending_visits':    0,
        }


def execute_query(db_or_cursor, query, params=None):
    """
    Ejecuta una consulta SQL adaptando automáticamente los placeholders.
    Convierte ? a %s si estamos usando PostgreSQL.

    Args:
        db_or_cursor: Conexión o cursor de base de datos
        query: Query SQL con placeholders ? (estilo SQLite)
        params: Parámetros de la consulta (tupla o lista)

    Returns:
        Cursor con los resultados
    """
    # Convertir placeholders si es PostgreSQL
    if USE_POSTGRES and '?' in query:
        query = query.replace('?', '%s')

    # Determinar si es conexión o cursor
    if hasattr(db_or_cursor, 'cursor'):
        cursor = db_or_cursor.cursor()
    else:
        cursor = db_or_cursor

    # Ejecutar query
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)

    return cursor


class DatabaseWrapper:
    """
    Wrapper para conexión de BD que convierte automáticamente placeholders.
    Permite usar sintaxis SQLite (?) en todo el código, y convierte a PostgreSQL (%s) automáticamente.
    """
    def __init__(self, conn, is_postgres=False):
        self._conn = conn
        self._is_postgres = is_postgres

    def execute(self, query, params=None):
        """Ejecuta query convirtiendo placeholders automáticamente"""
        if self._is_postgres and '?' in query:
            query = query.replace('?', '%s')
        cursor = self._conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor

    def cursor(self):
        """Retorna un cursor envuelto"""
        return WrappedCursor(self._conn.cursor(), self._is_postgres)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()


class WrappedCursor:
    """Cursor que convierte placeholders automáticamente"""
    def __init__(self, cursor, is_postgres=False):
        self._cursor = cursor
        self._is_postgres = is_postgres

    def execute(self, query, params=None):
        if self._is_postgres and '?' in query:
            query = query.replace('?', '%s')
        if params:
            self._cursor.execute(query, params)
        else:
            self._cursor.execute(query)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchmany(self, size=None):
        return self._cursor.fetchmany(size) if size else self._cursor.fetchmany()

    def close(self):
        return self._cursor.close()

    @property
    def rowcount(self):
        return self._cursor.rowcount


def get_db():
    """
    Obtener conexión a base de datos.
    Retorna PostgreSQL en producción (Render) o SQLite en desarrollo local.
    El wrapper convierte automáticamente placeholders ? a %s en PostgreSQL.
    """
    if USE_POSTGRES:
        # PostgreSQL (producción en Render)
        conn = psycopg2.connect(DATABASE_URL)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return DatabaseWrapper(conn, is_postgres=True)
    else:
        # SQLite (desarrollo local)
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return DatabaseWrapper(conn, is_postgres=False)

def init_db():
    """Inicializar base de datos"""
    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        # Definir tipo de autoincremento según BD
        if USE_POSTGRES:
            auto_id = 'SERIAL PRIMARY KEY'
            bool_default_true = 'BOOLEAN DEFAULT TRUE'
            bool_default_false = 'BOOLEAN DEFAULT FALSE'
        else:
            auto_id = 'INTEGER PRIMARY KEY AUTOINCREMENT'
            bool_default_true = 'BOOLEAN DEFAULT 1'
            bool_default_false = 'BOOLEAN DEFAULT 0'

        # Tabla de usuarios
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS users (
                id {auto_id},
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT,
                role TEXT DEFAULT 'editor',
                is_active {bool_default_true},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Migración: añadir columnas nuevas a DBs pre-existentes (solo SQLite)
        if not USE_POSTGRES:
            for col, definition in [('role', "TEXT DEFAULT 'editor'"), ('is_active', 'BOOLEAN DEFAULT 1')]:
                try:
                    cursor.execute(f'ALTER TABLE users ADD COLUMN {col} {definition}')
                except Exception:
                    pass  # columna ya existe

        # Tabla de configuración del sitio (clave-valor)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS site_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla de animales
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS animals (
                id {auto_id},
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
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS news (
                id {auto_id},
                title TEXT NOT NULL,
                category TEXT,
                content TEXT,
                excerpt TEXT,
                image TEXT,
                date TEXT,
                published {bool_default_true},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla de contactos
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS contacts (
                id {auto_id},
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                subject TEXT,
                message TEXT,
                read {bool_default_false},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla de suscriptores al newsletter
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS newsletter_subscribers (
                id {auto_id},
                email TEXT NOT NULL UNIQUE,
                name TEXT,
                subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active {bool_default_true},
                unsubscribe_token TEXT
            )
        ''')

        # Tabla de colaboradores (socios, voluntarios, padrinos, acogida, empresa)
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS collaborators (
                id {auto_id},
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
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS adoption_requests (
                id {auto_id},
                animal_id INTEGER NOT NULL,
                animal_name TEXT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                message TEXT,
                age INTEGER,
                address TEXT,
                city TEXT,
                living_situation TEXT,
                own_or_rent TEXT,
                has_yard TEXT,
                landlord_permission TEXT,
                household_members INTEGER,
                has_children TEXT,
                children_ages TEXT,
                current_pets TEXT,
                pet_experience TEXT,
                work_schedule TEXT,
                hours_home_per_day TEXT,
                why_adopt TEXT,
                vet_name TEXT,
                vet_phone TEXT,
                reference_name TEXT,
                reference_phone TEXT,
                comments TEXT,
                status TEXT DEFAULT 'pendiente',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                {',' if USE_POSTGRES else ', FOREIGN KEY (animal_id) REFERENCES animals(id)'}
                {'FOREIGN KEY (animal_id) REFERENCES animals(id)' if USE_POSTGRES else ''}
            )
        ''')

        # Migración: añadir columnas extendidas a adoption_requests en DBs pre-existentes (solo SQLite)
        if not USE_POSTGRES:
            adoption_extra_cols = [
                ('age',                'INTEGER'),
                ('address',            'TEXT'),
                ('city',               'TEXT'),
                ('living_situation',   'TEXT'),
                ('own_or_rent',        'TEXT'),
                ('has_yard',           'TEXT'),
                ('landlord_permission','TEXT'),
                ('household_members',  'INTEGER'),
                ('has_children',       'TEXT'),
                ('children_ages',      'TEXT'),
                ('current_pets',       'TEXT'),
                ('pet_experience',     'TEXT'),
                ('work_schedule',      'TEXT'),
                ('hours_home_per_day', 'TEXT'),
                ('why_adopt',          'TEXT'),
                ('vet_name',           'TEXT'),
                ('vet_phone',          'TEXT'),
                ('reference_name',     'TEXT'),
                ('reference_phone',    'TEXT'),
                ('comments',           'TEXT'),
            ]
            for col, definition in adoption_extra_cols:
                try:
                    cursor.execute(f'ALTER TABLE adoption_requests ADD COLUMN {col} {definition}')
                except Exception:
                    pass  # columna ya existe
            # Migración: columna notes para seguimiento interno
            try:
                cursor.execute('ALTER TABLE adoption_requests ADD COLUMN notes TEXT')
            except Exception:
                pass

        # Tabla de solicitudes de visita
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS visit_requests (
                id {auto_id},
                animal_id INTEGER,
                animal_name TEXT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                preferred_date TEXT,
                preferred_time TEXT,
                notes TEXT,
                status TEXT DEFAULT 'pendiente',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla de fotos adicionales de animales
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS animal_photos (
                id {auto_id},
                animal_id INTEGER NOT NULL,
                photo_path TEXT NOT NULL,
                display_order INTEGER DEFAULT 0,
                caption TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (animal_id) REFERENCES animals(id)
            )
        ''')

        # Migración: columnas de salud, compatibilidad y urgencia en animals
        health_compat_cols = [
            ('vaccinated',     'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
            ('sterilized',     'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
            ('chipped',        'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
            ('dewormed',       'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
            ('good_with_kids', 'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
            ('good_with_cats', 'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
            ('good_with_dogs', 'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
            ('apartment_ok',   'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
            ('high_energy',    'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
            ('urgent',         'BOOLEAN DEFAULT 0',     'BOOLEAN DEFAULT FALSE'),
        ]
        if not USE_POSTGRES:
            for col, sqlite_def, _ in health_compat_cols:
                try:
                    cursor.execute(f'ALTER TABLE animals ADD COLUMN {col} {sqlite_def}')
                except Exception:
                    pass  # columna ya existe
        else:
            for col, _, pg_def in health_compat_cols:
                try:
                    cursor.execute(f'ALTER TABLE animals ADD COLUMN IF NOT EXISTS {col} {pg_def}')
                except Exception:
                    pass

        # Crear usuario admin por defecto
        placeholder = get_placeholder()
        try:
            hashed_password = generate_password_hash('protectora2026')
            cursor.execute(f'INSERT INTO users (username, password, email, role, is_active) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})',
                      ('admin', hashed_password, 'admin@protectoraburjassot.com', 'superadmin', True if USE_POSTGRES else 1))
        except (sqlite3.IntegrityError if not USE_POSTGRES else psycopg2.IntegrityError):
            # Si ya existe, asegurarse de que tiene rol superadmin
            cursor.execute(f"UPDATE users SET role = 'superadmin', is_active = {placeholder} WHERE username = {placeholder}",
                          (True if USE_POSTGRES else 1, 'admin'))

        # Insertar configuración del sitio por defecto (solo si no existe)
        default_settings = [
            ('shelter_name', 'Protectora de Animales de Burjassot'),
            ('shelter_description', 'Somos una asociación sin ánimo de lucro dedicada al rescate, cuidado y adopción de animales abandonados en Burjassot y alrededores. Trabajamos cada día para darles una segunda oportunidad y encontrarles el hogar que merecen.'),
            ('contact_email', 'info@protectoraburjassot.org'),
            ('contact_phone', '+34 963 123 456'),
            ('contact_address', 'Calle de la Solidaridad, 12, 46100 Burjassot, Valencia'),
            ('contact_hours', 'Lunes a Viernes: 10:00-14:00 y 17:00-20:00 | Sábados: 10:00-14:00 | Domingos: Cerrado'),
            ('social_facebook', 'https://www.facebook.com/protectoraburjassot'),
            ('social_instagram', 'https://www.instagram.com/protectoraburjassot'),
            ('social_twitter', 'https://www.twitter.com/protectoraburjassot'),
            ('maps_embed_url', 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3079.8419858906537!2d-0.4196547!3d39.5076769!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x0%3A0x0!2zMznCsDMwJzI3LjYiTiAwwroyNScxMC42Ilc!5e0!3m2!1ses!2ses!4v1234567890123'),
            ('store_images_in_db', '0'),  # Almacenar imágenes comprimidas en BD (0=no, 1=sí)
            ('donation_bizum', ''),  # Código Bizum para donaciones
            ('donation_iban', 'ES00 0000 0000 00 0000000000'),  # IBAN para transferencias
            ('donation_paypal', ''),  # Email de PayPal para donaciones
            ('donation_teaming_url', 'https://www.teaming.net/protectoraburjassot'),
            ('donation_amazon_wishlist', 'https://www.amazon.es/hz/wishlist/ls/XXXXXXXXX'),
            ('donation_wallapop_url', 'https://es.wallapop.com/u/protectoraburjassot'),
            # Email SMTP para notificaciones
            ('smtp_host', ''),
            ('smtp_port', '587'),
            ('smtp_user', ''),
            ('smtp_password', ''),
            ('smtp_from', ''),
            ('notify_email', ''),
            ('email_provider', 'smtp'),
            ('sendgrid_api_key', ''),
            ('mailgun_api_key', ''),
            ('mailgun_domain', ''),
            # Página Nosotros
            ('about_title', 'Sobre Nosotros'),
            ('about_subtitle', 'Trabajamos cada día para dar una segunda oportunidad a los animales más vulnerables'),
            ('about_mission', 'Nuestra misión es el rescate, recuperación y adopción responsable de animales abandonados o maltratados en Burjassot y sus alrededores. Somos una asociación sin ánimo de lucro, formada por voluntarios comprometidos con el bienestar animal.'),
            ('about_history', 'La Protectora de Animales Burjassot nació gracias a un grupo de vecinos y amantes de los animales preocupados por el abandono animal en el municipio. Desde entonces, hemos rescatado y dado en adopción a cientos de animales.'),
            ('about_team', ''),
            ('about_founded_year', '2008'),
            ('about_animals_rescued', ''),
        ]
        # Insertar settings por defecto solo si no existen (INSERT ... ON CONFLICT)
        for key, value in default_settings:
            cursor.execute(
                f'INSERT INTO site_settings (key, value) VALUES ({placeholder}, {placeholder}) '
                f'ON CONFLICT(key) DO NOTHING',
                (key, value)
            )

        # Insertar datos de ejemplo si la base de datos está vacía
        cursor.execute('SELECT COUNT(*) as count FROM animals')
        animal_count = cursor.fetchone()['count']
        if animal_count == 0:
            # Datos de ejemplo de animales
            animales_ejemplo = [
                # EN ADOPCIÓN - Perros
                ('Luna', 'perro', '2 años', 'Hembra', 'Mediano',
                 'Luna es una perra mestiza muy cariñosa que busca un hogar lleno de amor. Es tranquila, obediente y se lleva bien con otros perros y niños.',
                 'images/animales/luna.jpg', 'adoption'),
                ('Max', 'perro', '3 años', 'Macho', 'Grande',
                 'Max es un pastor alemán cruzado muy juguetón y enérgico. Le encanta pasear, correr y jugar. Ideal para familias activas con jardín.',
                 'images/animales/max.jpg', 'adoption'),
                ('Rocky', 'perro', '5 años', 'Macho', 'Grande',
                 'Rocky es un mastín muy leal y protector. Necesita una familia con experiencia en perros grandes. Es muy cariñoso y tranquilo en casa.',
                 'images/animales/rocky.jpg', 'adoption'),
                ('Bella', 'perro', '1 año', 'Hembra', 'Pequeño',
                 'Bella es una chihuahua mix pequeña y juguetona. Perfecta para pisos o casas pequeñas. Muy sociable, cariñosa y le encantan los mimos.',
                 'images/animales/bella.jpg', 'adoption'),
                ('Toby', 'perro', '6 años', 'Macho', 'Mediano',
                 'Toby es un beagle adulto muy tranquilo y equilibrado. Ideal para personas mayores o familias que buscan un compañero calmado.',
                 'images/animales/toby.jpg', 'adoption'),
                ('Bruno', 'perro', '4 años', 'Macho', 'Grande',
                 'Bruno es un golden retriever muy noble y cariñoso. Le encanta estar con su familia y es excelente con los niños. Muy educado y obediente.',
                 'images/animales/bruno.jpg', 'adoption'),
                ('Coco', 'perro', '8 meses', 'Macho', 'Mediano',
                 'Coco es un cachorro de bodeguero muy activo y juguetón. Necesita una familia que pueda dedicarle tiempo para adiestramiento y juegos.',
                 'images/animales/coco.jpg', 'adoption'),
                ('Nina', 'perro', '7 años', 'Hembra', 'Pequeño',
                 'Nina es una yorkshire senior muy tranquila y mimosa. Busca un hogar donde pasar sus últimos años rodeada de amor y cuidados.',
                 'images/animales/nina.jpg', 'adoption'),
                ('Thor', 'perro', '2 años', 'Macho', 'Grande',
                 'Thor es un husky siberiano muy enérgico. Necesita mucho ejercicio diario y una familia activa. Es muy sociable con perros y personas.',
                 'images/animales/thor.jpg', 'adoption'),
                ('Lola', 'perro', '3 años', 'Hembra', 'Mediano',
                 'Lola es una cocker spaniel muy dulce y cariñosa. Le encanta jugar y dar paseos. Perfecta para familias con niños.',
                 'images/animales/lola.jpg', 'adoption'),

                # EN ADOPCIÓN - Gatos
                ('Misi', 'gato', '1 año', 'Hembra', 'Pequeño',
                 'Misi es una gatita joven muy tranquila y mimosa. Perfecta para un hogar acogedor. Le encanta dormir al sol y recibir caricias.',
                 'images/animales/misi.jpg', 'adoption'),
                ('Simba', 'gato', '4 años', 'Macho', 'Mediano',
                 'Simba es un gato naranja independiente pero cariñoso. Le gusta su espacio pero también los mimos. Perfecto compañero de hogar.',
                 'images/animales/simba.jpg', 'adoption'),
                ('Nala', 'gato', '2 años', 'Hembra', 'Pequeño',
                 'Nala es una gatita siamesa muy elegante y cariñosa. Le encanta jugar y explorar. Se adapta bien a la vida en interior.',
                 'images/animales/nala.jpg', 'adoption'),
                ('Mía', 'gato', '3 años', 'Hembra', 'Mediano',
                 'Mía es una gata tricolor muy cariñosa que busca un hogar tranquilo. Le gusta la rutina y los ambientes relajados.',
                 'images/animales/mia.jpg', 'adoption'),
                ('Bigotes', 'gato', '5 años', 'Macho', 'Mediano',
                 'Bigotes es un gato blanco y negro muy tranquilo. Es perfecto para personas que buscan compañía sin mucho alboroto. Muy independiente.',
                 'images/animales/bigotes.jpg', 'adoption'),
                ('Canela', 'gato', '6 meses', 'Hembra', 'Pequeño',
                 'Canela es una gatita bebé muy juguetona y curiosa. Necesita una familia paciente que le enseñe buenos hábitos. Muy sociable.',
                 'images/animales/canela.jpg', 'adoption'),
                ('Felix', 'gato', '8 años', 'Macho', 'Mediano',
                 'Felix es un gato senior muy tranquilo y cariñoso. Busca un hogar donde vivir sus últimos años con paz y confort.',
                 'images/animales/felix.jpg', 'adoption'),
                ('Luna Gata', 'gato', '2 años', 'Hembra', 'Pequeño',
                 'Luna es una gatita negra muy juguetona y activa. Le encanta trepar y explorar. Ideal para hogares con espacio.',
                 'images/animales/luna_gata.jpg', 'adoption'),

                # EN ACOGIDA - Casa de acogida temporal
                ('Chispa', 'perro', '4 meses', 'Hembra', 'Pequeño',
                 'Chispa es una cachorra que se está recuperando de un rescate. Necesita acogida temporal mientras encuentra familia definitiva.',
                 'images/animales/chispa.jpg', 'foster'),
                ('Mora', 'gato', '3 meses', 'Hembra', 'Pequeño',
                 'Mora es una gatita bebé que necesita familia de acogida. Es muy juguetona y está aprendiendo a socializar.',
                 'images/animales/mora.jpg', 'foster'),
                ('Dante', 'perro', '1 año', 'Macho', 'Mediano',
                 'Dante está en acogida recuperándose de una operación. Es muy cariñoso y necesita un hogar temporal con cuidados especiales.',
                 'images/animales/dante.jpg', 'foster'),

                # ADOPTADOS - Historias de éxito
                ('Pelusa', 'gato', '2 años', 'Hembra', 'Pequeño',
                 'Pelusa encontró su hogar definitivo! Ahora es una gatita muy feliz que disfruta de su nueva familia.',
                 'images/animales/pelusa.jpg', 'adopted'),
                ('Rex', 'perro', '3 años', 'Macho', 'Grande',
                 'Rex fue adoptado por una familia maravillosa. Ahora disfruta de largos paseos diarios y tiene un gran jardín donde jugar.',
                 'images/animales/rex.jpg', 'adopted'),
                ('Cleo', 'gato', '4 años', 'Hembra', 'Mediano',
                 'Cleo encontró un hogar perfecto donde es la reina de la casa. Su familia la adora y ella es muy feliz.',
                 'images/animales/cleo.jpg', 'adopted'),
                ('Bobby', 'perro', '5 años', 'Macho', 'Grande',
                 'Bobby fue adoptado hace 6 meses. Su familia nos cuenta que es un perro maravilloso y están muy contentos juntos.',
                 'images/animales/bobby.jpg', 'adopted'),
            ]

            for animal in animales_ejemplo:
                cursor.execute(f'''
                    INSERT INTO animals (name, type, age, gender, size, description, image, status)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
                ''', animal)

        # Insertar noticias de ejemplo si no hay ninguna
        cursor.execute('SELECT COUNT(*) as count FROM news')
        news_count = cursor.fetchone()['count']
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
                cursor.execute(f'''
                    INSERT INTO news (title, category, content, excerpt, image, date, published)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
                ''', noticia)

        # Migración: limpiar rutas de imagen de muestra que no existen en disco
        if USE_POSTGRES:
            cursor.execute("UPDATE animals SET image = NULL WHERE image LIKE %s", ('images/animales/%',))
        else:
            cursor.execute("UPDATE animals SET image = NULL WHERE image LIKE ?", ('images/animales/%',))

        db.commit()
        cursor.close()
        logger.info('✅ Base de datos inicializada correctamente')

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

def get_pagination_params():
    """Obtener parámetros de paginación, ordenamiento y búsqueda desde request.args"""
    page = max(1, request.args.get('page', 1, type=int))
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(max(10, per_page), 100)  # Entre 10 y 100
    sort_by = request.args.get('sort_by', '')
    sort_order = request.args.get('sort_order', 'desc')
    if sort_order not in ['asc', 'desc']:
        sort_order = 'desc'
    search = request.args.get('search', '').strip()
    return {
        'page': page,
        'per_page': per_page,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'search': search
    }

def build_query_with_filters(base_query, search_columns, search_term, allowed_sort_columns, sort_by, sort_order, default_sort='id'):
    """
    Construir query SQL con búsqueda y ordenamiento

    Args:
        base_query: Query base SQL (ej: 'SELECT * FROM animals WHERE status = ?')
        search_columns: Lista de columnas donde buscar (ej: ['name', 'description'])
        search_term: Término de búsqueda
        allowed_sort_columns: Columnas permitidas para ordenar
        sort_by: Columna para ordenar
        sort_order: 'asc' o 'desc'
        default_sort: Columna por defecto si sort_by no es válido

    Returns:
        tuple: (query_modificada, params_adicionales)
    """
    params = []
    query = base_query
    placeholder = get_placeholder()

    # Agregar búsqueda
    if search_term and search_columns:
        search_conditions = ' OR '.join([f"{col} LIKE {placeholder}" for col in search_columns])
        # Si el query ya tiene WHERE, usar AND, sino agregar WHERE
        if 'WHERE' in query.upper():
            query += f' AND ({search_conditions})'
        else:
            query += f' WHERE ({search_conditions})'
        # Agregar parámetros de búsqueda
        params.extend([f'%{search_term}%'] * len(search_columns))

    # Agregar ordenamiento (solo si hay columna válida)
    if sort_by and sort_by in allowed_sort_columns:
        order = sort_order.upper() if sort_order.upper() in ('ASC', 'DESC') else 'DESC'
        query += f' ORDER BY {sort_by} {order}'
    elif default_sort:
        order = sort_order.upper() if sort_order.upper() in ('ASC', 'DESC') else 'DESC'
        query += f' ORDER BY {default_sort} {order}'

    return query, params

def paginate_query(db, count_query, data_query, count_params, data_params, page, per_page):
    """
    Ejecutar query con paginación

    Args:
        db: Conexión a base de datos
        count_query: Query para contar total de registros
        data_query: Query para obtener datos
        count_params: Parámetros para count_query
        data_params: Parámetros para data_query
        page: Número de página
        per_page: Registros por página

    Returns:
        dict con 'items', 'total', 'page', 'per_page', 'total_pages'
    """
    placeholder = get_placeholder()

    # Contar total
    total = db.execute(count_query, count_params).fetchone()['count']

    # Obtener datos paginados
    offset = (page - 1) * per_page
    data_query += f' LIMIT {placeholder} OFFSET {placeholder}'
    data_params.extend([per_page, offset])
    items = db.execute(data_query, data_params).fetchall()

    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages
    }

# ============================================
# RUTAS DE AUTENTICACIÓN
# ============================================

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
    """Listar animales con paginación, búsqueda y ordenamiento"""
    db = get_db()
    params = get_pagination_params()
    placeholder = get_placeholder()

    # Filtro por estado
    status_filter = request.args.get('status', '')

    # Construir query base
    base_query = 'SELECT * FROM animals'
    count_query = 'SELECT COUNT(*) as count FROM animals'
    query_params = []

    if status_filter:
        where_clause = f' WHERE status = {placeholder}'
        base_query += where_clause
        count_query += where_clause
        query_params.append(status_filter)

    # Columnas donde buscar
    search_columns = ['name', 'description', 'age', 'gender', 'size', 'type']
    allowed_sort_columns = ['id', 'name', 'type', 'age', 'gender', 'size', 'status', 'created_at', 'updated_at']

    # Construir query con búsqueda y ordenamiento
    data_query, search_params = build_query_with_filters(
        base_query,
        search_columns,
        params['search'],
        allowed_sort_columns,
        params['sort_by'],
        params['sort_order'],
        default_sort='created_at'
    )

    # Si hay búsqueda, actualizar también el count_query
    if params['search']:
        count_query, _ = build_query_with_filters(
            count_query,
            search_columns,
            params['search'],
            [],  # No necesitamos sort en count
            '',
            '',
            ''
        )

    # Combinar parámetros
    all_params = query_params + search_params

    # Paginar
    result = paginate_query(
        db,
        count_query,
        data_query,
        query_params + search_params,  # Para count
        all_params.copy(),  # Para data
        params['page'],
        params['per_page']
    )

    return render_template('animals.html',
                           animals=result['items'],
                           page=result['page'],
                           per_page=result['per_page'],
                           total_pages=result['total_pages'],
                           total=result['total'],
                           sort_by=params['sort_by'],
                           sort_order=params['sort_order'],
                           search=params['search'],
                           status_filter=status_filter)

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
        vaccinated     = 1 if request.form.get('vaccinated')     else 0
        sterilized     = 1 if request.form.get('sterilized')     else 0
        chipped        = 1 if request.form.get('chipped')        else 0
        dewormed       = 1 if request.form.get('dewormed')       else 0
        good_with_kids = 1 if request.form.get('good_with_kids') else 0
        good_with_cats = 1 if request.form.get('good_with_cats') else 0
        good_with_dogs = 1 if request.form.get('good_with_dogs') else 0
        apartment_ok   = 1 if request.form.get('apartment_ok')   else 0
        high_energy    = 1 if request.form.get('high_energy')    else 0
        urgent         = 1 if request.form.get('urgent')         else 0

        # Manejar subida de imagen (new_animal)
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                if filename:
                    # Verificar si almacenar en BD o en disco
                    store_in_db = get_setting('store_images_in_db', '0') == '1'

                    if store_in_db:
                        # Comprimir y guardar como base64 en BD
                        image_path = compress_image_to_base64(file)
                    else:
                        # Guardar en disco (método tradicional)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp}_{filename}"
                        fotos_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'fotos')
                        os.makedirs(fotos_dir, exist_ok=True)
                        filepath = os.path.join(fotos_dir, filename)
                        saved = save_image(file, filepath)
                        image_path = 'uploads/fotos/' + os.path.basename(saved)

        db = get_db()
        db.execute('''
            INSERT INTO animals (name, type, age, gender, size, description, image,
                                 vaccinated, sterilized, chipped, dewormed,
                                 good_with_kids, good_with_cats, good_with_dogs,
                                 apartment_ok, high_energy, urgent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, animal_type, age, gender, size, description, image_path,
              vaccinated, sterilized, chipped, dewormed,
              good_with_kids, good_with_cats, good_with_dogs,
              apartment_ok, high_energy, urgent))
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
        vaccinated     = 1 if request.form.get('vaccinated')     else 0
        sterilized     = 1 if request.form.get('sterilized')     else 0
        chipped        = 1 if request.form.get('chipped')        else 0
        dewormed       = 1 if request.form.get('dewormed')       else 0
        good_with_kids = 1 if request.form.get('good_with_kids') else 0
        good_with_cats = 1 if request.form.get('good_with_cats') else 0
        good_with_dogs = 1 if request.form.get('good_with_dogs') else 0
        apartment_ok   = 1 if request.form.get('apartment_ok')   else 0
        high_energy    = 1 if request.form.get('high_energy')    else 0
        urgent         = 1 if request.form.get('urgent')         else 0

        # Obtener imagen actual
        current_animal = db.execute('SELECT image FROM animals WHERE id = ?', (animal_id,)).fetchone()
        image_path = current_animal['image']

        # Manejar subida de nueva imagen
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                if filename:  # secure_filename puede devolver cadena vacía
                    # Verificar si almacenar en BD o en disco
                    store_in_db = get_setting('store_images_in_db', '0') == '1'

                    if store_in_db:
                        # Comprimir y guardar como base64 en BD
                        image_path = compress_image_to_base64(file)
                    else:
                        # Guardar en disco (método tradicional)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp}_{filename}"
                        fotos_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'fotos')
                        os.makedirs(fotos_dir, exist_ok=True)
                        filepath = os.path.join(fotos_dir, filename)
                        saved = save_image(file, filepath)
                        filename = os.path.basename(saved)
                        # Borrar imagen anterior del disco si era un upload (solo si no está en BD)
                        if image_path and image_path.startswith('uploads/'):
                            old_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), image_path)
                            if os.path.exists(old_path):
                                os.remove(old_path)
                        image_path = f"uploads/fotos/{filename}"

        # Actualizar
        db.execute('''
            UPDATE animals
            SET name=?, type=?, age=?, gender=?, size=?, description=?, status=?, image=?,
                vaccinated=?, sterilized=?, chipped=?, dewormed=?,
                good_with_kids=?, good_with_cats=?, good_with_dogs=?,
                apartment_ok=?, high_energy=?, urgent=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        ''', (name, animal_type, age, gender, size, description, status, image_path,
              vaccinated, sterilized, chipped, dewormed,
              good_with_kids, good_with_cats, good_with_dogs,
              apartment_ok, high_energy, urgent,
              animal_id))
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
# GALERÍA DE FOTOS DE ANIMALES
# ============================================

@app.route('/admin/animals/<int:animal_id>/photos', methods=['POST'])
@login_required
def admin_animal_add_photo(animal_id):
    """Subir foto adicional al animal"""
    validate_csrf()
    db = get_db()
    if not db.execute('SELECT id FROM animals WHERE id = ?', (animal_id,)).fetchone():
        return jsonify({'error': 'Animal no encontrado'}), 404
    count = db.execute(
        'SELECT COUNT(*) as c FROM animal_photos WHERE animal_id = ?', (animal_id,)
    ).fetchone()['c']
    if count >= 8:
        return jsonify({'error': 'Máximo 8 fotos por animal'}), 400
    if 'photo' not in request.files:
        return jsonify({'error': 'No se envió ninguna foto'}), 400
    file = request.files['photo']
    if not file or not file.filename or not allowed_file(file.filename):
        return jsonify({'error': 'Archivo no válido'}), 400
    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({'error': 'Nombre de archivo no válido'}), 400
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    filename = f"{timestamp}_{filename}"
    fotos_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'fotos')
    os.makedirs(fotos_dir, exist_ok=True)
    filepath = os.path.join(fotos_dir, filename)
    saved = save_image(file, filepath)
    photo_path = 'uploads/fotos/' + os.path.basename(saved)
    next_order = db.execute(
        'SELECT COALESCE(MAX(display_order), -1) + 1 as n FROM animal_photos WHERE animal_id = ?',
        (animal_id,)
    ).fetchone()['n']
    try:
        cursor = db.execute(
            'INSERT INTO animal_photos (animal_id, photo_path, display_order) VALUES (?, ?, ?)',
            (animal_id, photo_path, next_order)
        )
        new_id = cursor.lastrowid
        db.commit()
    except Exception:
        if os.path.exists(saved):
            os.remove(saved)
        raise
    return jsonify({'success': True, 'photo': {'id': new_id, 'path': photo_path, 'order': next_order}})


@app.route('/admin/animals/<int:animal_id>/photos/<int:photo_id>', methods=['DELETE'])
@login_required
def admin_animal_delete_photo(animal_id, photo_id):
    """Eliminar foto del animal"""
    validate_csrf()
    db = get_db()
    photo = db.execute(
        'SELECT * FROM animal_photos WHERE id = ? AND animal_id = ?', (photo_id, animal_id)
    ).fetchone()
    if not photo:
        return jsonify({'error': 'Foto no encontrada'}), 404
    if photo['photo_path'] and photo['photo_path'].startswith('uploads/'):
        full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), photo['photo_path'])
        if os.path.exists(full_path):
            os.remove(full_path)
    db.execute('DELETE FROM animal_photos WHERE id = ? AND animal_id = ?', (photo_id, animal_id))
    db.commit()
    return jsonify({'success': True})


@app.route('/admin/animals/<int:animal_id>/photos/reorder', methods=['POST'])
@login_required
def admin_animal_reorder_photos(animal_id):
    """Reordenar fotos: JSON body = [{id, order}, ...]"""
    validate_csrf()
    data = request.get_json(silent=True)
    if not data or not isinstance(data, list):
        return jsonify({'error': 'Datos inválidos'}), 400
    db = get_db()
    for item in data:
        db.execute(
            'UPDATE animal_photos SET display_order = ? WHERE id = ? AND animal_id = ?',
            (item['order'], item['id'], animal_id)
        )
    db.commit()
    return jsonify({'success': True})


@app.route('/admin/animals/<int:animal_id>/photos/<int:photo_id>/set-primary', methods=['POST'])
@login_required
def admin_animal_set_primary_photo(animal_id, photo_id):
    """Establecer foto como imagen principal del animal (animals.image)"""
    validate_csrf()
    db = get_db()
    photo = db.execute(
        'SELECT photo_path FROM animal_photos WHERE id = ? AND animal_id = ?', (photo_id, animal_id)
    ).fetchone()
    if not photo:
        return jsonify({'error': 'Foto no encontrada'}), 404
    db.execute(
        'UPDATE animals SET image = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (photo['photo_path'], animal_id)
    )
    db.commit()
    return jsonify({'success': True})


# ============================================
# GESTIÓN DE NOTICIAS
# ============================================

@app.route('/admin/news')
@login_required
def list_news():
    """Listar noticias con paginación, búsqueda y ordenamiento"""
    db = get_db()
    params = get_pagination_params()
    placeholder = get_placeholder()

    # Filtro por categoría y estado publicado
    category_filter = request.args.get('category', '')
    published_filter = request.args.get('published', '')

    # Construir query base
    base_query = 'SELECT * FROM news'
    count_query = 'SELECT COUNT(*) as count FROM news'
    query_params = []
    where_clauses = []

    if category_filter:
        where_clauses.append(f'category = {placeholder}')
        query_params.append(category_filter)

    if published_filter:
        where_clauses.append(f'published = {placeholder}')
        query_params.append(int(published_filter))

    if where_clauses:
        where_clause = ' WHERE ' + ' AND '.join(where_clauses)
        base_query += where_clause
        count_query += where_clause

    # Columnas donde buscar
    search_columns = ['title', 'excerpt', 'content', 'category']
    allowed_sort_columns = ['id', 'title', 'category', 'date', 'published', 'created_at']

    # Construir query con búsqueda y ordenamiento
    data_query, search_params = build_query_with_filters(
        base_query,
        search_columns,
        params['search'],
        allowed_sort_columns,
        params['sort_by'],
        params['sort_order'],
        default_sort='date'
    )

    # Si hay búsqueda, actualizar también el count_query
    if params['search']:
        count_query, _ = build_query_with_filters(
            count_query,
            search_columns,
            params['search'],
            [],
            '',
            '',
            ''
        )

    # Combinar parámetros
    all_params = query_params + search_params

    # Paginar
    result = paginate_query(
        db,
        count_query,
        data_query,
        query_params + search_params,
        all_params.copy(),
        params['page'],
        params['per_page']
    )

    return render_template('news.html',
                           news=result['items'],
                           page=result['page'],
                           per_page=result['per_page'],
                           total_pages=result['total_pages'],
                           total=result['total'],
                           sort_by=params['sort_by'],
                           sort_order=params['sort_order'],
                           search=params['search'],
                           category_filter=category_filter,
                           published_filter=published_filter)


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
                    # Verificar si almacenar en BD o en disco
                    store_in_db = get_setting('store_images_in_db', '0') == '1'

                    if store_in_db:
                        # Comprimir y guardar como base64 en BD
                        image_path = compress_image_to_base64(file)
                    else:
                        # Guardar en disco (método tradicional)
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
    """Listar mensajes de contacto con filtro y búsqueda"""
    db = get_db()
    read_filter = request.args.get('filter', '')  # 'unread', 'read' o ''
    search      = request.args.get('search', '').strip()
    placeholder = get_placeholder()

    query  = 'SELECT * FROM contacts WHERE 1=1'
    params = []

    if read_filter == 'unread':
        query += ' AND read = 0'
    elif read_filter == 'read':
        query += ' AND read = 1'

    if search:
        query += f' AND (name LIKE {placeholder} OR email LIKE {placeholder} OR subject LIKE {placeholder} OR message LIKE {placeholder})'
        params.extend([f'%{search}%'] * 4)

    query += ' ORDER BY created_at DESC'
    contacts     = db.execute(query, params).fetchall()
    total_unread = db.execute('SELECT COUNT(*) as c FROM contacts WHERE read = 0').fetchone()['c']
    return render_template('contacts.html', contacts=contacts,
                           read_filter=read_filter, search=search, total_unread=total_unread)


@app.route('/admin/contacts/<int:contact_id>/read', methods=['POST'])
@login_required
def mark_contact_read(contact_id):
    """Marcar contacto como leído"""
    validate_csrf()
    db = get_db()
    db.execute('UPDATE contacts SET read = 1 WHERE id = ?', (contact_id,))
    db.commit()
    # Preservar filtros al redirigir
    return redirect(url_for('list_contacts',
                            filter=request.form.get('filter', ''),
                            search=request.form.get('search', '')))


@app.route('/admin/contacts/<int:contact_id>/delete', methods=['POST'])
@login_required
def delete_contact(contact_id):
    """Eliminar mensaje de contacto"""
    validate_csrf()
    db = get_db()
    db.execute('DELETE FROM contacts WHERE id = ?', (contact_id,))
    db.commit()
    flash('Mensaje eliminado.', 'success')
    return redirect(url_for('list_contacts',
                            filter=request.form.get('filter', ''),
                            search=request.form.get('search', '')))


# ============================================
# NEWSLETTER
# ============================================

@app.route('/admin/newsletter')
@login_required
def list_newsletter_subscribers():
    """Listar suscriptores del newsletter"""
    db = get_db()
    active_filter = request.args.get('active')

    query = 'SELECT * FROM newsletter_subscribers'
    params = []

    if active_filter == '1':
        query += ' WHERE is_active = ' + ('TRUE' if USE_POSTGRES else '1')
    elif active_filter == '0':
        query += ' WHERE is_active = ' + ('FALSE' if USE_POSTGRES else '0')

    query += ' ORDER BY subscribed_at DESC'

    subscribers = db.execute(query, params).fetchall()
    return render_template('newsletter.html', subscribers=subscribers, active_filter=active_filter)


@app.route('/admin/newsletter/<int:subscriber_id>/toggle', methods=['POST'])
@login_required
def toggle_newsletter_subscriber(subscriber_id):
    """Activar/desactivar suscriptor"""
    validate_csrf()
    db = get_db()
    placeholder = get_placeholder()

    cursor = db.execute(f'SELECT is_active FROM newsletter_subscribers WHERE id = {placeholder}', (subscriber_id,))
    row = cursor.fetchone()

    if row:
        new_status = not row[0]
        db.execute(f'UPDATE newsletter_subscribers SET is_active = {placeholder} WHERE id = {placeholder}',
                  (new_status if USE_POSTGRES else (1 if new_status else 0), subscriber_id))
        db.commit()
        flash('Estado del suscriptor actualizado.', 'success')

    return redirect(url_for('list_newsletter_subscribers'))


@app.route('/admin/newsletter/<int:subscriber_id>/delete', methods=['POST'])
@login_required
def delete_newsletter_subscriber(subscriber_id):
    """Eliminar suscriptor"""
    validate_csrf()
    db = get_db()
    placeholder = get_placeholder()
    db.execute(f'DELETE FROM newsletter_subscribers WHERE id = {placeholder}', (subscriber_id,))
    db.commit()
    flash('Suscriptor eliminado.', 'success')
    return redirect(url_for('list_newsletter_subscribers'))


@app.route('/admin/newsletter/export')
@login_required
def export_newsletter_csv():
    """Exportar suscriptores a CSV"""
    db = get_db()
    rows = db.execute(
        'SELECT email, name, subscribed_at, is_active '
        'FROM newsletter_subscribers WHERE is_active = ' + ('TRUE' if USE_POSTGRES else '1') +
        ' ORDER BY subscribed_at DESC'
    ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Email', 'Nombre', 'Fecha suscripción'])
    for r in rows:
        writer.writerow([r['email'], r['name'] or '', r['subscribed_at']])

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=newsletter_subscribers.csv'
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    return response


@app.route('/admin/newsletter/send', methods=['POST'])
@login_required
def send_newsletter_email():
    """Enviar un newsletter HTML a todos los suscriptores activos"""
    validate_csrf()
    subject   = request.form.get('subject', '').strip()
    body_html = request.form.get('body_html', '').strip()

    if not subject or not body_html or body_html == '<p><br></p>':
        flash('El asunto y el contenido son obligatorios.', 'error')
        return redirect(url_for('list_newsletter_subscribers'))

    db = get_db()
    active_val = 'TRUE' if USE_POSTGRES else '1'
    subscribers = db.execute(
        f'SELECT email, name FROM newsletter_subscribers WHERE is_active = {active_val}'
    ).fetchall()

    if not subscribers:
        flash('No hay suscriptores activos a quienes enviar el newsletter.', 'error')
        return redirect(url_for('list_newsletter_subscribers'))

    sent   = 0
    errors = 0
    for sub in subscribers:
        ok = send_html_email(sub['email'], subject, body_html)
        if ok:
            sent += 1
        else:
            errors += 1

    if errors == 0:
        flash(f'Newsletter enviado correctamente a {sent} suscriptor{"es" if sent != 1 else ""}.', 'success')
    elif sent > 0:
        flash(f'Envío completado: {sent} enviados, {errors} con error.', 'warning')
    else:
        flash(f'No se pudo enviar el newsletter. Comprueba la configuración del correo.', 'error')

    return redirect(url_for('list_newsletter_subscribers'))


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
            'donation_bizum', 'donation_iban', 'donation_paypal',
            'donation_teaming_url', 'donation_amazon_wishlist', 'donation_wallapop_url',
            'smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'smtp_from', 'notify_email',
            'email_provider', 'sendgrid_api_key', 'mailgun_api_key', 'mailgun_domain',
            'about_title', 'about_subtitle', 'about_mission', 'about_history', 'about_team',
            'about_founded_year', 'about_animals_rescued',
        ]
        for key in keys:
            value = request.form.get(key, '').strip()
            db.execute(
                'INSERT INTO site_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) '
                'ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP',
                (key, value)
            )

        # Manejar checkbox de almacenamiento en BD (solo se envía si está marcado)
        store_in_db = '1' if request.form.get('store_images_in_db') else '0'
        db.execute(
            'INSERT INTO site_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) '
            'ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP',
            ('store_images_in_db', store_in_db)
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
    """API para obtener animales con fotos, salud y compatibilidad"""
    status = request.args.get('status', 'adoption')
    animal_type = request.args.get('type')
    limit = request.args.get('limit', type=int)
    filter_kids      = request.args.get('kids')
    filter_cats      = request.args.get('cats')
    filter_dogs      = request.args.get('dogs')
    filter_apartment = request.args.get('apartment')
    filter_urgent    = request.args.get('urgent')

    db = get_db()
    if status == 'adoption':
        query = 'SELECT * FROM animals WHERE status IN ("adoption", "reserved")'
        params = []
    else:
        query = 'SELECT * FROM animals WHERE status = ?'
        params = [status]
    if animal_type:
        query += ' AND type = ?'
        params.append(animal_type)
    if filter_kids:
        query += ' AND good_with_kids = 1'
    if filter_cats:
        query += ' AND good_with_cats = 1'
    if filter_dogs:
        query += ' AND good_with_dogs = 1'
    if filter_apartment:
        query += ' AND apartment_ok = 1'
    if filter_urgent:
        query += ' AND urgent = 1'
    query += ' ORDER BY urgent DESC, created_at DESC'
    if limit:
        query += ' LIMIT ?'
        params.append(limit)

    animals = db.execute(query, params).fetchall()
    result = []
    for a in animals:
        animal_dict = dict(a)
        photos = db.execute(
            'SELECT id, photo_path, display_order FROM animal_photos WHERE animal_id = ? ORDER BY display_order',
            (a['id'],)
        ).fetchall()
        animal_dict['photos'] = [dict(p) for p in photos]
        result.append(animal_dict)
    return jsonify({'animals': result})


@app.route('/api/animals/<int:animal_id>')
def api_animal_detail(animal_id):
    """API para obtener un animal por ID, incluyendo fotos y campos nuevos"""
    db = get_db()
    animal = db.execute('SELECT * FROM animals WHERE id = ?', (animal_id,)).fetchone()
    if not animal:
        return jsonify({'error': 'Animal no encontrado'}), 404
    animal_dict = dict(animal)
    photos = db.execute(
        'SELECT id, photo_path, display_order FROM animal_photos WHERE animal_id = ? ORDER BY display_order',
        (animal_id,)
    ).fetchall()
    animal_dict['photos'] = [dict(p) for p in photos]
    similar = db.execute(
        'SELECT id, name, type, image FROM animals WHERE type = ? AND status IN ("adoption","reserved") AND id != ? LIMIT 3',
        (animal['type'], animal_id)
    ).fetchall()
    animal_dict['similar'] = [dict(s) for s in similar]
    return jsonify(animal_dict)

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

    # Notificación por email al administrador
    try:
        send_notification_email(
            subject=f'[Protectora] Nuevo mensaje de {name}',
            body=f'Nombre: {name}\nEmail: {email}\nTeléfono: {phone or "-"}\nAsunto: {subject or "-"}\n\nMensaje:\n{message}'
        )
    except Exception:
        pass

    return jsonify({'success': True, 'message': 'Mensaje recibido correctamente'})

@app.route('/api/adoption-request', methods=['POST'])
@limiter.limit('3 per minute; 10 per day')
def api_adoption_request():
    """API para recibir solicitudes de adopción"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Datos inválidos'}), 400

    # Campos obligatorios
    animal_id = data.get('animal_id')
    animal_name = data.get('animal_name', '').strip()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()

    if not animal_id or not name or not email or not phone:
        return jsonify({'error': 'Animal, nombre, email y teléfono son obligatorios'}), 400
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return jsonify({'error': 'Email no válido'}), 400

    # Campos opcionales pero importantes
    age = data.get('age')
    address = data.get('address', '').strip()
    city = data.get('city', '').strip()
    living_situation = data.get('living_situation', '').strip()
    own_or_rent = data.get('own_or_rent', '').strip()
    has_yard = data.get('has_yard', '').strip()
    landlord_permission = data.get('landlord_permission', '').strip()
    household_members = data.get('household_members')
    has_children = data.get('has_children', '').strip()
    children_ages = data.get('children_ages', '').strip()
    current_pets = data.get('current_pets', '').strip()
    pet_experience = data.get('pet_experience', '').strip()
    work_schedule = data.get('work_schedule', '').strip()
    hours_home_per_day = data.get('hours_home_per_day', '').strip()
    why_adopt = data.get('why_adopt', '').strip()
    vet_name = data.get('vet_name', '').strip()
    vet_phone = data.get('vet_phone', '').strip()
    reference_name = data.get('reference_name', '').strip()
    reference_phone = data.get('reference_phone', '').strip()
    comments = data.get('comments', '').strip()
    message = data.get('message', '').strip()

    db = get_db()
    placeholder = get_placeholder()
    db.execute(f'''
        INSERT INTO adoption_requests (
            animal_id, animal_name, name, email, phone, message,
            age, address, city, living_situation, own_or_rent, has_yard,
            landlord_permission, household_members, has_children, children_ages,
            current_pets, pet_experience, work_schedule, hours_home_per_day,
            why_adopt, vet_name, vet_phone, reference_name, reference_phone,
            comments
        ) VALUES (
            {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder},
            {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder},
            {placeholder}, {placeholder}, {placeholder}, {placeholder},
            {placeholder}, {placeholder}, {placeholder}, {placeholder},
            {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder},
            {placeholder}
        )
    ''', (
        animal_id, animal_name, name, email, phone, message,
        age, address, city, living_situation, own_or_rent, has_yard,
        landlord_permission, household_members, has_children, children_ages,
        current_pets, pet_experience, work_schedule, hours_home_per_day,
        why_adopt, vet_name, vet_phone, reference_name, reference_phone,
        comments
    ))
    db.commit()

    # Notificación por email al administrador
    try:
        send_notification_email(
            subject=f'[Protectora] Solicitud de adopción: {animal_name} — {name}',
            body=f'Solicitante: {name}\nEmail: {email}\nTeléfono: {phone}\nAnimal: {animal_name} (ID {animal_id})\nCiudad: {city or "-"}\n\nMensaje:\n{message or "-"}'
        )
    except Exception:
        pass

    return jsonify({'success': True, 'message': 'Solicitud de adopción recibida correctamente'})

@app.route('/api/newsletter/subscribe', methods=['POST'])
@limiter.limit('3 per minute; 10 per hour')
def api_newsletter_subscribe():
    """API para suscribirse al newsletter"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Datos inválidos'}), 400

    email = data.get('email', '').strip().lower()
    name = data.get('name', '').strip()

    if not email:
        return jsonify({'error': 'El email es obligatorio'}), 400
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return jsonify({'error': 'Email no válido'}), 400

    db = get_db()
    placeholder = get_placeholder()

    # Generar token único para desuscribirse
    import secrets
    unsubscribe_token = secrets.token_urlsafe(32)

    try:
        # Intentar insertar nuevo suscriptor
        db.execute(f'''
            INSERT INTO newsletter_subscribers (email, name, unsubscribe_token, is_active)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
        ''', (email, name, unsubscribe_token, True if USE_POSTGRES else 1))
        db.commit()
        return jsonify({'success': True, 'message': 'Suscripción confirmada. ¡Gracias por unirte a nuestra newsletter!'})
    except (sqlite3.IntegrityError if not USE_POSTGRES else psycopg2.IntegrityError):
        # Email ya existe
        # Reactivar suscripción si estaba inactiva
        cursor = db.execute(f'SELECT is_active FROM newsletter_subscribers WHERE email = {placeholder}', (email,))
        row = cursor.fetchone()
        if row:
            is_active = row[0]
            if not is_active:
                db.execute(f'UPDATE newsletter_subscribers SET is_active = {placeholder}, name = {placeholder} WHERE email = {placeholder}',
                          (True if USE_POSTGRES else 1, name, email))
                db.commit()
                return jsonify({'success': True, 'message': 'Suscripción reactivada. ¡Bienvenido de nuevo!'})
            else:
                return jsonify({'error': 'Este email ya está suscrito a la newsletter'}), 400
        return jsonify({'error': 'Error al procesar la suscripción'}), 500

@app.route('/api/newsletter/unsubscribe/<token>', methods=['POST', 'GET'])
def api_newsletter_unsubscribe(token):
    """API para darse de baja del newsletter"""
    db = get_db()
    placeholder = get_placeholder()

    cursor = db.execute(f'SELECT email FROM newsletter_subscribers WHERE unsubscribe_token = {placeholder}', (token,))
    row = cursor.fetchone()

    if not row:
        return jsonify({'error': 'Token inválido'}), 404

    db.execute(f'UPDATE newsletter_subscribers SET is_active = {placeholder} WHERE unsubscribe_token = {placeholder}',
              (False if USE_POSTGRES else 0, token))
    db.commit()

    return jsonify({'success': True, 'message': 'Te has dado de baja correctamente. Lamentamos verte partir.'})

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
    collaborators_raw = db.execute(query, params).fetchall()
    # Pre-format JSON in extra field for readability in template
    collaborators = []
    for c in collaborators_raw:
        c = dict(c)
        if c.get('extra') and c['extra'].startswith('{'):
            try:
                parsed = json.loads(c['extra'])
                label_map = {
                    'living_situation': 'Vivienda', 'has_yard': 'Jardín/patio',
                    'space_available': 'Espacio disponible', 'current_pets': 'Mascotas actuales',
                    'pet_experience': 'Experiencia', 'hours_home_per_day': 'Horas en casa/día',
                    'foster_duration': 'Duración acogida', 'species_preference': 'Especie preferida',
                    'household_members': 'Personas en hogar', 'city': 'Municipio',
                }
                lines = [f"{label_map.get(k, k)}: {v}" for k, v in parsed.items() if v]
                c['extra_pretty'] = '\n'.join(lines)
            except Exception:
                c['extra_pretty'] = c['extra']
        else:
            c['extra_pretty'] = c.get('extra', '')
        collaborators.append(c)
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
    placeholder  = get_placeholder()
    current_status = request.args.get('status', '')
    search         = request.args.get('search', '').strip()
    animal_filter  = request.args.get('animal', '').strip()
    query  = 'SELECT * FROM adoption_requests WHERE 1=1'
    params = []
    if current_status:
        query += f' AND status = {placeholder}'
        params.append(current_status)
    if search:
        query += f' AND (name LIKE {placeholder} OR email LIKE {placeholder} OR phone LIKE {placeholder})'
        params.extend([f'%{search}%'] * 3)
    if animal_filter:
        query += f' AND animal_name LIKE {placeholder}'
        params.append(f'%{animal_filter}%')
    query += ' ORDER BY created_at DESC'
    adoptions = db.execute(query, params).fetchall()
    return render_template('adoptions.html', adoptions=adoptions, current_status=current_status,
                           search=search, animal_filter=animal_filter)


@app.route('/admin/adoptions/<int:req_id>/notes', methods=['POST'])
@login_required
def save_adoption_notes(req_id):
    """Guardar notas internas de seguimiento en una solicitud de adopción"""
    validate_csrf()
    notes = request.form.get('notes', '').strip()
    db = get_db()
    db.execute('UPDATE adoption_requests SET notes = ? WHERE id = ?', (notes, req_id))
    db.commit()
    flash('Notas guardadas.', 'success')
    return redirect(url_for('list_adoptions',
                            status=request.form.get('current_status', ''),
                            search=request.form.get('search', ''),
                            animal=request.form.get('animal_filter', '')))


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
# API — SOLICITUD DE VISITA
# ============================================

@app.route('/api/visit-request', methods=['POST'])
@limiter.limit('5 per minute; 20 per day')
def api_visit_request():
    """Registrar solicitud de visita para conocer un animal"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Datos inválidos'}), 400
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    animal_id = data.get('animal_id')
    animal_name = data.get('animal_name', '').strip()
    preferred_date = data.get('preferred_date', '').strip()
    preferred_time = data.get('preferred_time', '').strip()
    notes = data.get('notes', '').strip()
    if not name or not email:
        return jsonify({'error': 'Nombre y email son obligatorios'}), 400
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return jsonify({'error': 'Email no válido'}), 400
    db = get_db()
    db.execute(
        'INSERT INTO visit_requests (animal_id, animal_name, name, email, phone, preferred_date, preferred_time, notes) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (animal_id, animal_name, name, email, phone, preferred_date, preferred_time, notes)
    )
    db.commit()
    send_notification_email(
        f'Nueva solicitud de visita: {animal_name or "(sin animal especificado)"}',
        f'Nombre: {name}\nEmail: {email}\nTeléfono: {phone or "—"}\n'
        f'Animal: {animal_name or "—"}\nFecha preferida: {preferred_date or "—"}\n'
        f'Hora preferida: {preferred_time or "—"}\nNotas: {notes or "—"}'
    )
    return jsonify({'success': True, 'message': 'Solicitud de visita enviada correctamente'})


# ============================================
# ADMIN — GESTIÓN DE VISITAS / CITAS
# ============================================

@app.route('/admin/visits')
@login_required
def list_visits():
    db = get_db()
    current_status = request.args.get('status', '')
    search = request.args.get('search', '').strip()
    query = 'SELECT * FROM visit_requests WHERE 1=1'
    params = []
    if current_status:
        query += ' AND status = ?'
        params.append(current_status)
    if search:
        query += ' AND (name LIKE ? OR email LIKE ? OR animal_name LIKE ?)'
        like = f'%{search}%'
        params.extend([like, like, like])
    query += ' ORDER BY created_at DESC'
    visits = [dict(v) for v in db.execute(query, params).fetchall()]
    total_pending = db.execute("SELECT COUNT(*) as c FROM visit_requests WHERE status='pendiente'").fetchone()['c']
    return render_template('visits.html', visits=visits, current_status=current_status,
                           search=search, total_pending=total_pending)


@app.route('/admin/visits/<int:visit_id>/status', methods=['POST'])
@login_required
def update_visit_status(visit_id):
    validate_csrf()
    new_status = request.form.get('status')
    if new_status not in ('pendiente', 'confirmada', 'cancelada', 'completada'):
        flash('Estado no válido.', 'error')
        return redirect(url_for('list_visits'))
    db = get_db()
    db.execute('UPDATE visit_requests SET status = ? WHERE id = ?', (new_status, visit_id))
    db.commit()
    flash('Estado de visita actualizado.', 'success')
    return redirect(url_for('list_visits',
                            status=request.form.get('current_status', ''),
                            search=request.form.get('search', '')))


@app.route('/admin/visits/<int:visit_id>/delete', methods=['POST'])
@login_required
def delete_visit(visit_id):
    validate_csrf()
    db = get_db()
    db.execute('DELETE FROM visit_requests WHERE id = ?', (visit_id,))
    db.commit()
    flash('Solicitud de visita eliminada.', 'success')
    return redirect(url_for('list_visits',
                            status=request.form.get('current_status', ''),
                            search=request.form.get('search', '')))


# ============================================
# PÁGINA PÚBLICA — NOSOTROS
# ============================================

@app.route('/nosotros')
def public_nosotros():
    """Página pública 'Sobre nosotros', contenido editable desde el admin"""
    db = get_db()
    settings = {r['key']: r['value'] for r in db.execute('SELECT key, value FROM site_settings').fetchall()}
    return render_template('nosotros.html', settings=settings)


# ============================================
# FICHA PÚBLICA DE ANIMAL
# ============================================

@app.route('/animal/<int:animal_id>')
@app.route('/animal/<int:animal_id>/<slug>')
def public_animal_page(animal_id, slug=None):
    """Página pública con ficha completa de un animal (URL propia para SEO)"""
    db = get_db()
    animal = db.execute('SELECT * FROM animals WHERE id = ?', (animal_id,)).fetchone()
    if not animal:
        abort(404)
    animal = dict(animal)
    # Normalizar slug para URL canónica
    correct_slug = re.sub(r'[^a-z0-9]+', '-', (animal['name'] or '').lower()).strip('-')
    if slug != correct_slug:
        return redirect(url_for('public_animal_page', animal_id=animal_id, slug=correct_slug), 301)
    settings = {r['key']: r['value'] for r in db.execute('SELECT key, value FROM site_settings').fetchall()}
    return render_template('animal_public.html', animal=animal, settings=settings)


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
# SERVIR ARCHIVOS ESTÁTICOS DEL FRONTEND
# ============================================

@app.route('/')
def serve_index():
    """Servir página principal"""
    static_folder = os.path.dirname(os.path.dirname(__file__))
    return send_from_directory(static_folder, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Servir archivos estáticos (CSS, JS, HTML)"""
    static_folder = os.path.dirname(os.path.dirname(__file__))
    return send_from_directory(static_folder, filename)

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
