# nomina_estudiantes/settings.py
import os, dj_database_url
from pathlib import Path
from decouple import config, Csv
import psycopg2

# ==============================
# CONFIGURACIÓN BÁSICA DEL PROYECTO
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent  # Ruta base del proyecto
SECRET_KEY = config('SECRET_KEY')  # Clave secreta para cifrado (cámbiala en producción)
DEBUG = config('DEBUG', default=False, cast=bool)  # Modo de depuración (cambia a False en producción)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())  # Lista de dominios permitidos (agrega aquí tu dominio si es necesario)
LOGIN_URL = '/login/'
# ==============================
# APLICACIONES INSTALADAS
# ==============================
INSTALLED_APPS = [
    'jazzmin',  # Tema de administración (opcional)
    'django.contrib.admin',         # Panel de administración (opcional, pero útil)
    'django.contrib.contenttypes',  # Tipos de contenido
    'django.contrib.sessions',      # Sesiones (puedes eliminar esto si no usas sesiones)
    'django.contrib.messages',      # Mensajes flash (opcional)
    'django.contrib.auth',          # Autenticación de usuarios
    'django.contrib.staticfiles',   # Archivos estáticos (CSS, JS, imágenes)
    'estudiantes',                  # Tu aplicación personalizada
    'import_export',
    
    # Frameworks de terceros
    'rest_framework',
    
    # App personales
    'myapp', 
]

JAZZMIN_SETTINGS = {
    "site_title": "Academia The Professor",
    "site_header": "Academia The Professor",
    "site_logo": "assets/images/aguila.svg",# Ruta al logo de tu sitio
    "login_logo": "assets/images/aguila.svg",  # Ruta al logo de inicio de sesión
    "site_brand": "Academia The Professor",
    "welcome_sign": "Bienvenido a la Academia The Professor",
    "copyright": "© 2025 Academia The Professor",
    "search_model": ["auth.User", "myapp.Person", "myapp.Courses", "myapp.Students", "myapp.Tutors"],
    "user_avatar": None,  # Puedes agregar un avatar de usuario si lo deseas}
    "icons": {
        "auth.User": "fas fa-user",
        "myapp.Person": "fas fa-user-tie",
        "myapp.Courses": "fas fa-book",
        "myapp.Students": "fas fa-graduation-cap",
        "myapp.Tutors": "fas fa-chalkboard-teacher"},
    "show_ui_builder": True, 
    }

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-teal",
    "accent": "accent-warning",
    "navbar": "navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-olive",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "yeti",
    "dark_mode_theme": "solar",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-outline-info",
        "warning": "btn-warning",
        "danger": "btn-outline-danger",
        "success": "btn-outline-success"
    }
}


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',  # Seguridad básica
    'django.contrib.sessions.middleware.SessionMiddleware',  # Manejo de sesiones
    'django.middleware.common.CommonMiddleware',  # Middleware común
    'django.middleware.csrf.CsrfViewMiddleware',  # Protección CSRF
    'django.contrib.messages.middleware.MessageMiddleware',  # Mensajes flash
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # Protección contra clickjacking
]

ROOT_URLCONF = 'nomina_estudiantes.urls'  # Archivo principal de URLs

# ==============================
# CONFIGURACIÓN DE PLANTILLAS HTML
# ==============================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Carpeta global para plantillas HTML
        'APP_DIRS': True,  # Buscar plantillas dentro de las aplicaciones
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',  # Variables de depuración
                'django.template.context_processors.request',  # Datos de la solicitud HTTP
                'django.contrib.messages.context_processors.messages',  # Mensajes flash
            ],
        },
    },
]

WSGI_APPLICATION = 'nomina_estudiantes.wsgi.application'  # Configuración WSGI

# ==============================
# BASE DE DATOS
# ==============================
# Base de datos: usa DATABASE_URL si existe, sino SQLite (solo en local)
if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.parse(os.environ['DATABASE_URL'])
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ==============================
# VALIDACIÓN DE CONTRASEÑAS (OPCIONAL)
# ==============================
AUTH_PASSWORD_VALIDATORS = [
    # Validadores predeterminados para contraseñas seguras
    # Puedes eliminar esta sección si no usas autenticación
]

# ==============================
# INTERNACIONALIZACIÓN
# ==============================
LANGUAGE_CODE = 'es-co'  # Idioma: Español de Colombia (puedes cambiarlo a 'es-ve' si prefieres)
TIME_ZONE = 'America/Caracas'  # Zona horaria: Caracas, Venezuela
USE_I18N = True  # Habilitar internacionalización
USE_L10N = True  # Habilitar formato localizado
USE_TZ = True  # Usar zonas horarias

# ==============================
# ARCHIVOS ESTÁTICOS (CSS, JS, IMÁGENES)
# ==============================
STATIC_URL = '/static/' # URL base para archivos estáticos
STATICFILES_DIRS = [ 
    BASE_DIR / "static", # Carpeta estática de tu aplicación
]
DATABASES_ROUTERS= ['routers_db.db_routers.AuthRouter']

# Directorio donde se copiarán con collectstatic (en producción)
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ==============================
# CLAVE PRIMARIA AUTOMÁTICA
# ==============================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'  # Tipo de clave primaria predeterminada

# AUTH_USER_MODEL = 'myapp.User' # Modelo de usuario personalizado