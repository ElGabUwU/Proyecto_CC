import logging
import os
from django.db import connections, OperationalError

class AuthRouter:
    """
    Router de bases de datos personalizado para Django que maneja múltiples bases de datos:
    - Apps internas de Django (auth, admin, sessions) van a 'local_db' (SQLite)
    - Apps personalizadas (myapp) van a 'default' (PostgreSQL Railway) o 'local_db' según disponibilidad
    """

    # Apps internas de Django que siempre van a local_db
    internal_app_labels = {'admin', 'contenttypes', 'sessions', 'auth', 'messages', 'staticfiles'}
    
    # Apps personalizadas que pueden ir a cualquier base de datos
    custom_app_labels = {'myapp'}
    
    def _get_available_db_for_custom_apps(self):
        """
        Determina qué base de datos usar para apps personalizadas.
        Prioridad: default (PostgreSQL) -> local_db (SQLite)
        """
        # Verificar si se fuerza el uso de SQLite
        if os.getenv('USE_SQLITE', 'False').lower() == 'true':
            return 'local_db'
            
        # Intentar usar PostgreSQL primero
        try:
            connections['default'].ensure_connection()
            return 'default'
        except (OperationalError, Exception):
            logging.warning("PostgreSQL no disponible, usando SQLite local")
            return 'local_db'
    
    def db_for_read(self, model, **hints):
        """Determina qué base de datos usar para operaciones de lectura"""
        if model._meta.app_label in self.internal_app_labels:
            return 'local_db'
        elif model._meta.app_label in self.custom_app_labels:
            return self._get_available_db_for_custom_apps()
        return None

    def db_for_write(self, model, **hints):
        """Determina qué base de datos usar para operaciones de escritura"""
        if model._meta.app_label in self.internal_app_labels:
            return 'local_db'
        elif model._meta.app_label in self.custom_app_labels:
            return self._get_available_db_for_custom_apps()
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Permite relaciones entre objetos de la misma base de datos
        """
        db_set = {'default', 'local_db'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Controla en qué base de datos se aplican las migraciones
        """
        if app_label in self.internal_app_labels:
            # Apps internas solo en local_db
            return db == 'local_db'
        elif app_label in self.custom_app_labels:
            # Apps personalizadas pueden ir a cualquier base de datos
            return True
        return None