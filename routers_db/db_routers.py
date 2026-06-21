import logging
import os
from django.db import connections, OperationalError

class AuthRouter:
    """
    Router de bases de datos optimizado:
    Garantiza que todas las aplicaciones (internas y personalizadas) coexistan 
    en la misma base de datos activa para permitir relaciones (ForeignKeys).
    """

    # Agrupamos todas las apps conocidas del proyecto
    project_app_labels = {'admin', 'contenttypes', 'sessions', 'auth', 'messages', 'staticfiles', 'myapp', 'nomina'}
    
    def _get_active_db(self):
        """
        Determina dinámicamente cuál es la base de datos principal activa.
        Prioridad: default (PostgreSQL) -> local_db (SQLite)
        """
        # Verificar si se fuerza el uso de SQLite desde el entorno
        if os.getenv('USE_SQLITE', 'False').lower() == 'true':
            return 'local_db'
            
        # Intentar conectar a PostgreSQL
        try:
            connections['default'].ensure_connection()
            return 'default'
        except (OperationalError, Exception):
            logging.warning("PostgreSQL no disponible localmente. Desviando flujo a SQLite de respaldo.")
            return 'local_db'
    
    def db_for_read(self, model, **hints):
        """Redirige las lecturas a la base de datos activa"""
        if model._meta.app_label in self.project_app_labels:
            return self._get_active_db()
        return None


    def db_for_write(self, model, **hints):
        """Redirige las escrituras a la base de datos activa"""
        if model._meta.app_label in self.project_app_labels:
            return self._get_active_db()
        return None
    
    def allow_relation(self, obj1, obj2, **hints):
        """
        Permite relaciones únicamente si ambos objetos están 
        en la misma base de datos física.
        """
        if obj1._state.db == obj2._state.db:
            return True
        return False
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Controla de forma segura dónde se deben aplicar las migraciones.
        """
        active_db = self._get_active_db()
        
        # Obliga a que las migraciones se ejecuten en la base de datos que está activa en ese momento
        if app_label in self.project_app_labels:
            return db == active_db
            
        return None