"""
Validadores personalizados para el Sistema de Gestión Comunitaria.
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validar_cedula_venezolana(value):
    """
    Valida el formato de cédula venezolana.
    
    Formatos aceptados:
    - V-12345678 (Venezolano con guion)
    - E-12345678 (Extranjero con guion)
    - V12345678 (Venezolano sin guion)
    - E12345678 (Extranjero sin guion)
    
    Args:
        value: String con la cédula a validar
    
    Returns:
        String: Cédula normalizada con formato V-XXXXXXXX o E-XXXXXXXX
    
    Raises:
        ValidationError: Si el formato no es válido
    """
    if not value:
        return value
    
    # Normalizar: quitar espacios y convertir a mayúsculas
    cedula = str(value).strip().upper()
    
    # Patrones válidos
    patron_con_guion = r'^[VE]-\d{6,8}$'
    patron_sin_guion = r'^[VE]\d{6,8}$'
    
    if not (re.match(patron_con_guion, cedula) or re.match(patron_sin_guion, cedula)):
        raise ValidationError(
            _(
                'Formato de cédula inválido. Use el formato V-12345678 (venezolano) '
                'o E-12345678 (extranjero).'
            ),
            code='invalid_cedula_format'
        )
    
    # Normalizar con guion si no lo tiene
    if re.match(patron_sin_guion, cedula):
        cedula = f"{cedula[0]}-{cedula[1:]}"
    
    return cedula


def validar_telefono_venezolano(value):
    """
    Valida el formato de teléfono venezolano.
    
    Formatos aceptados:
    - +584121234567 (internacional)
    - 04121234567 (local)
    - 0412-1234567 (con guion)
    
    Args:
        value: String con el teléfono a validar
    
    Returns:
        String: Teléfono normalizado
    
    Raises:
        ValidationError: Si el formato no es válido
    """
    if not value:
        return value
    
    # Quitar espacios y caracteres especiales excepto + y -
    telefono = str(value).strip()
    telefono_limpio = re.sub(r'[^\d+]', '', telefono)
    
    # Patrones válidos
    patron_internacional = r'^\+58\d{10}$'
    patron_local = r'^0[24]\d{9}$'
    
    if not (re.match(patron_internacional, telefono_limpio) or re.match(patron_local, telefono_limpio)):
        raise ValidationError(
            _(
                'Formato de teléfono inválido. Use: +584121234567 o 04121234567.'
            ),
            code='invalid_phone_format'
        )
    
    return telefono_limpio


def validar_nombre_solo_letras(value):
    """
    Valida que un nombre solo contenga letras y espacios.
    
    Args:
        value: String con el nombre a validar
    
    Returns:
        String: Nombre validado
    
    Raises:
        ValidationError: Si contiene caracteres inválidos
    """
    if not value:
        return value
    
    nombre = str(value).strip()
    
    if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', nombre):
        raise ValidationError(
            _(
                'Este campo solo puede contener letras y espacios.'
            ),
            code='invalid_name_format'
        )
    
    return nombre


def validar_catastro_venezolano(value):
    """
    Valida el formato de código catastral venezolano.
    
    Formato típico: NNN-NN-NN-NN-NN
    
    Args:
        value: String con el código catastral a validar
    
    Returns:
        String: Código normalizado
    
    Raises:
        ValidationError: Si el formato no es válido
    """
    if not value:
        return value
    
    catastro = str(value).strip()
    
    # Patrón flexible: permite varios formatos comunes
    patron = r'^[\d\-\.]+$'
    
    if not re.match(patron, catastro):
        raise ValidationError(
            _(
                'El código catastral solo puede contener números, guiones y puntos.'
            ),
            code='invalid_catastro_format'
        )
    
    return catastro


class UniqueCedulaValidator:
    """
    Validador de clase para verificar que la cédula sea única en el sistema.
    
    Uso en serializers:
        validators = [UniqueCedulaValidator()]
    
    O en fields:
        cedula = serializers.CharField(validators=[UniqueCedulaValidator()])
    """
    
    requires_context = True
    
    def __init__(self, queryset=None):
        self.queryset = queryset
    
    def __call__(self, value, serializer_field):
        # Obtener el modelo del serializer
        model = serializer_field.parent.Meta.model if hasattr(serializer_field, 'parent') else None
        
        if model:
            # Si es Habitante, verificar directamente
            from .models import Habitante
            instance = serializer_field.parent.instance if hasattr(serializer_field, 'parent') else None
            
            queryset = Habitante.objects.filter(cedula=value, is_deleted=False)
            if instance and instance.pk:
                queryset = queryset.exclude(pk=instance.pk)
            
            if queryset.exists():
                raise ValidationError(
                    f"Ya existe un habitante registrado con la cédula {value}.",
                    code='unique_cedula'
                )


class JefeFamiliaValidator:
    """
    Validador para asegurar que solo haya un jefe de familia por hogar.
    
    Uso:
        validators = [JefeFamiliaValidator()]
    """
    
    requires_context = True
    
    def __call__(self, value, serializer_field):
        from .models import Habitante
        
        if not value:
            return
        
        # Obtener el contexto del serializer
        serializer = serializer_field.parent
        instance = serializer.instance if serializer else None
        familia_id = serializer.context.get('familia_id')
        
        # Si estamos editando un habitante existente
        if instance and hasattr(instance, 'familia'):
            familia_id = instance.familia_id
        
        if not familia_id:
            return
        
        # Verificar si ya existe otro jefe en la familia
        jefes_existentes = Habitante.objects.filter(
            familia_id=familia_id,
            es_jefe_familia=True,
            is_deleted=False
        )
        
        if instance and instance.pk:
            jefes_existentes = jefes_existentes.exclude(pk=instance.pk)
        
        if jefes_existentes.exists():
            raise ValidationError(
                "Esta familia ya tiene un jefe de familia asignado.",
                code='unique_jefe_familia'
            )


class MinHabitantesValidator:
    """
    Validador para asegurar un mínimo de habitantes en una familia.
    
    Uso:
        validators = [MinHabitantesValidator(min_habitantes=1)]
    """
    
    def __init__(self, min_habitantes=1):
        self.min_habitantes = min_habitantes
    
    def __call__(self, value):
        if not value or len(value) < self.min_habitantes:
            raise ValidationError(
                f"Debe agregar al menos {self.min_habitantes} habitante(s) a la familia.",
                code='min_habitantes'
            )
