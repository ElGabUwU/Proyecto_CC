"""
Manejador personalizado de excepciones para Django REST Framework.
Convierte errores de validación y permisos en respuestas JSON legibles para el frontend.
"""
from rest_framework.views import exception_handler
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
import json

def custom_exception_handler(exc, context):
    """
    Manejador personalizado que captura excepciones de Django REST Framework
    y las convierte en respuestas JSON con mensajes claros para el frontend.
    """
    # Llamar al manejador predeterminado primero
    response = exception_handler(exc, context)
    
    # Si la respuesta es None, significa que no es una excepción manejada por DRF
    if response is None:
        return None
    
    # Manejar específicamente errores de PermissionDenied (como cédula duplicada)
    if isinstance(exc, PermissionDenied):
        # El mensaje ya viene como un string JSON desde el serializer
        error_message = str(exc.detail)
        
        # Intentar extraer el mensaje si está en formato de lista
        try:
            # Si el mensaje es una lista o string JSON, dejarlo como está
            if isinstance(exc.detail, list):
                response.data = {'detail': exc.detail[0] if len(exc.detail) > 0 else 'Permiso denegado'}
            elif isinstance(exc.detail, str):
                # Intentar parsear si es un string JSON
                try:
                    parsed = json.loads(exc.detail)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        response.data = {'detail': parsed[0]}
                    else:
                        response.data = {'detail': exc.detail}
                except json.JSONDecodeError:
                    response.data = {'detail': exc.detail}
        except Exception:
            response.data = {'detail': error_message}
        
        # Mantener el código de estado 403 Forbidden para PermissionDenied
        response.status_code = 403
    
    # Manejar errores de validación de DRF
    elif isinstance(exc, DRFValidationError):
        if isinstance(exc.detail, dict):
            # Extraer el primer error del diccionario
            for key, value in exc.detail.items():
                if isinstance(value, list):
                    response.data = {'detail': value[0]}
                    break
                else:
                    response.data = {'detail': str(value)}
                    break
        elif isinstance(exc.detail, list):
            response.data = {'detail': exc.detail[0] if len(exc.detail) > 0 else 'Error de validación'}
        else:
            response.data = {'detail': str(exc.detail)}
    
    return response
