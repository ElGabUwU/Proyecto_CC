import os, dj_database_url
from pathlib import Path
from decouple import config, Csv
import psycopg2
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent  # Ruta base del proyecto
SECRET_KEY = config('SECRET_KEY')  # Clave secreta para cifrado (cámbiala en producción)
DEBUG = config('DEBUG', default=False, cast=bool)  # Modo de depuración (cambia a False en producción)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())  # Lista de dominios permitidos (agrega aquí tu dominio si es necesario)

LOGIN_URL = '/login/'

# Application definition
INSTALLED_APPS = [
    'jazzmin',  # Tema de administración (opcional)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #aplicaciones personalizadas
    "myapp",
    'import_export', 
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
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

SESSION_SAVE_EVERY_REQUEST = True 
# This tells Django to update the session's expiration time with every request the user makes, effectively resetting the inactivity timer.
SESSION_COOKIE_AGE = 300 
# This sets the session to expire after 300 seconds (5 minutes) of inactivity.
SESSION_EXPIRE_AT_BROWSER_CLOSE = False 
#This ensures the session persists even if the browser is closed, allowing the inactivity timer to be the primary method of session expiration.


ROOT_URLCONF = 'nomina.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],  # Carpeta para tus templates
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'myapp.context_processors.user_role_context',
                'myapp.context_processors.sidebar_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'nomina.wsgi.application'

# ==============================
# BASE DE DATOS CON FALLBACK AUTOMÁTICO
# ==============================

# ==============================
# CONFIGURACIÓN DE MÚLTIPLES BASES DE DATOS
# ==============================

def get_database_config():
    """
    Configura múltiples bases de datos: Railway PostgreSQL como principal y SQLite como local/backup
    """
    databases = {
        'local_db': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    
    # Intentar configurar Railway PostgreSQL como base de datos principal
    try:
        database_url = config('DATABASE_URL')
        databases['default'] = dj_database_url.parse(database_url)
        print("✅ PostgreSQL (Railway) configurado como base de datos principal")
    except Exception as e:
        print(f"⚠️  No se pudo configurar PostgreSQL: {e}")
        print("🔄 Usando SQLite como base de datos principal")
        databases['default'] = databases['local_db'].copy()
    
    return databases

DATABASES = get_database_config()

# Router de bases de datos
#DATABASE_ROUTERS = ['routers_db.db_routers.AuthRouter']

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es'  # Cambia el idioma a español
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static"]  # Carpeta para archivos estáticos

#AUTH_USER_MODEL = 'myapp.User'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================
# CONFIGURACIÓN DE LOGGING
# ==============================
import logging
import warnings

# Suprimir warnings de collation de PostgreSQL
warnings.filterwarnings('ignore', message='.*collation version mismatch.*')

# Configuración de logging para suprimir warnings de PostgreSQL
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends.postgresql': {
            'handlers': ['console'],
            'level': 'ERROR',  # Solo mostrar errores, no warnings
        },
    },
}
