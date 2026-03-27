"""
Configuración de la aplicación Flask
Separa configuración de desarrollo y producción
"""
import os

class Config:
    """Configuración base"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'cambiar_en_produccion_por_clave_segura')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB

    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

    # Extensiones permitidas
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'mp4', 'avi', 'mov'}

    # Imagen
    IMAGE_MAX_SIZE = 1200


class DevelopmentConfig(Config):
    """Configuración de desarrollo"""
    DEBUG = True
    DATABASE_URI = 'sqlite:///protectora.db'

    # CORS permisivo en desarrollo
    CORS_ORIGINS = '*'


class ProductionConfig(Config):
    """Configuración de producción"""
    DEBUG = False

    # Base de datos PostgreSQL en producción
    DATABASE_URI = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://')

    # CORS restrictivo en producción
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')

    # Secret key obligatoria desde variable de entorno
    if not os.environ.get('SECRET_KEY'):
        raise ValueError("SECRET_KEY debe estar definida en producción")


# Seleccionar configuración según entorno
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Obtener configuración según entorno"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
