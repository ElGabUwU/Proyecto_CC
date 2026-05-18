"""
Serializers para la API REST del Sistema de Gestión Comunitaria.
Implementa arquitectura maestro-detalle para Familias y Habitantes.
"""
from rest_framework import serializers
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Familia, Habitante
import re


# ============================================
# Validators Personalizados
# ============================================

def validar_cedula_venezolana(cedula):
    """
    Valida el formato de cédula venezolana.
    Formatos válidos: V-12345678, E-12345678, V12345678, E12345678
    """
    if not cedula:
        return cedula
    
    # Normalizar: quitar espacios y convertir a mayúsculas
    cedula = cedula.strip().upper()
    
    # Patrones válidos
    patron_con_guion = r'^[VE]-\d{6,8}$'
    patron_sin_guion = r'^[VE]\d{6,8}$'
    
    if not (re.match(patron_con_guion, cedula) or re.match(patron_sin_guion, cedula)):
        raise serializers.ValidationError(
            "Formato de cédula inválido. Use: V-12345678 o E-12345678"
        )
    
    # Normalizar con guion si no lo tiene
    if re.match(patron_sin_guion, cedula):
        cedula = f"{cedula[0]}-{cedula[1:]}"
    
    return cedula


def validar_cedula_unica(cedula, exclude_pk=None):
    """
    Valida que la cédula sea única en el sistema.
    """
    queryset = Habitante.objects.filter(cedula=cedula, is_deleted=False)
    if exclude_pk:
        queryset = queryset.exclude(pk=exclude_pk)
    
    if queryset.exists():
        raise serializers.ValidationError(
            f"Ya existe un habitante registrado con la cédula {cedula}"
        )
    
    return cedula


# ============================================
# Serializers para Habitante
# ============================================

class HabitanteSerializer(serializers.ModelSerializer):
    """
    Serializer completo para Habitante.
    Usado para lectura y operaciones individuales.
    """
    edad = serializers.SerializerMethodField(read_only=True)
    genero_display = serializers.CharField(source='get_genero_display', read_only=True)
    nivel_educativo_display = serializers.CharField(source='get_nivel_educativo_display', read_only=True)
    es_jefe_display = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Habitante
        fields = [
            'id', 'familia', 'cedula', 'nombre', 'apellido',
            'fecha_nacimiento', 'edad', 'genero', 'genero_display',
            'es_jefe_familia', 'es_jefe_display',
            'ocupacion', 'nivel_educativo', 'nivel_educativo_display',
            'ingresos_mensuales', 'condiciones_salud',
            'fecha_registro_comunitario', 'is_deleted'
        ]
        read_only_fields = ['id', 'fecha_registro_comunitario', 'is_deleted']
    
    def get_edad(self, obj):
        """Calcula la edad basada en la fecha de nacimiento."""
        from datetime import date
        if not obj.fecha_nacimiento:
            return None
        
        today = date.today()
        age = today.year - obj.fecha_nacimiento.year
        if (today.month, today.day) < (obj.fecha_nacimiento.month, obj.fecha_nacimiento.day):
            age -= 1
        return age
    
    def get_es_jefe_display(self, obj):
        """Retorna representación legible del jefe de familia."""
        return "Sí" if obj.es_jefe_familia else "No"
    
    def validate_cedula(self, value):
        """Valida el formato y unicidad de la cédula."""
        return validar_cedula_venezolana(value)
    
    def validate(self, data):
        """Validaciones a nivel de objeto."""
        # Validar unicidad de cédula
        cedula = data.get('cedula')
        instance = self.instance
        
        if cedula:
            validar_cedula_unica(cedula, exclude_pk=instance.pk if instance else None)
        
        # Validar fecha de nacimiento
        from datetime import date
        fecha_nacimiento = data.get('fecha_nacimiento')
        if fecha_nacimiento and fecha_nacimiento > date.today():
            raise serializers.ValidationError({
                'fecha_nacimiento': 'La fecha de nacimiento no puede ser futura.'
            })
        
        return data


class HabitanteNestedSerializer(serializers.ModelSerializer):
    """
    Serializer anidado para Habitante.
    Usado dentro de FamiliaConHabitantesSerializer.
    Sin el campo 'familia' ya que se asigna desde el padre.
    """
    class Meta:
        model = Habitante
        fields = [
            'id', 'cedula', 'nombre', 'apellido',
            'fecha_nacimiento', 'genero',
            'es_jefe_familia',
            'ocupacion', 'nivel_educativo',
            'ingresos_mensuales', 'condiciones_salud'
        ]
        extra_kwargs = {
            'id': {'read_only': True, 'required': False},
        }
    
    def validate_cedula(self, value):
        """Valida el formato de la cédula."""
        return validar_cedula_venezolana(value)
    
    def validate_fecha_nacimiento(self, value):
        """Valida que la fecha de nacimiento no sea futura."""
        from datetime import date
        if value and value > date.today():
            raise serializers.ValidationError(
                'La fecha de nacimiento no puede ser futura.'
            )
        return value


# ============================================
# Serializers para Familia
# ============================================

class FamiliaListSerializer(serializers.ModelSerializer):
    """
    Serializer ligero para listado de familias.
    Incluye conteo de habitantes y datos básicos del jefe.
    """
    cantidad_habitantes = serializers.ReadOnlyField()
    jefe_nombre = serializers.SerializerMethodField()
    jefe_cedula = serializers.SerializerMethodField()
    
    class Meta:
        model = Familia
        fields = [
            'id', 'nombre_familia', 'vivienda', 'direccion',
            'catastro', 'fecha_registro', 'observaciones',
            'cantidad_habitantes', 'jefe_nombre', 'jefe_cedula',
            'is_deleted'
        ]
        read_only_fields = ['id', 'fecha_registro', 'is_deleted']
    
    def get_jefe_nombre(self, obj):
        """Retorna el nombre completo del jefe de familia."""
        jefe = obj.jefe_familia
        if jefe:
            return f"{jefe.nombre} {jefe.apellido}"
        return "Sin jefe asignado"
    
    def get_jefe_cedula(self, obj):
        """Retorna la cédula del jefe de familia."""
        jefe = obj.jefe_familia
        return jefe.cedula if jefe else "-"


class FamiliaDetalleSerializer(serializers.ModelSerializer):
    """
    Serializer detallado para lectura de una familia.
    Incluye todos los habitantes relacionados.
    """
    habitantes = HabitanteSerializer(many=True, read_only=True)
    jefe_familia = serializers.SerializerMethodField()
    cantidad_habitantes = serializers.ReadOnlyField()
    
    class Meta:
        model = Familia
        fields = [
            'id', 'nombre_familia', 'vivienda', 'direccion',
            'catastro', 'fecha_registro', 'observaciones',
            'habitantes', 'jefe_familia', 'cantidad_habitantes',
            'is_deleted'
        ]
        read_only_fields = ['id', 'fecha_registro', 'is_deleted']
    
    def get_jefe_familia(self, obj):
        """Retorna los datos del jefe de familia."""
        jefe = obj.jefe_familia
        if jefe:
            return {
                'id': jefe.id,
                'cedula': jefe.cedula,
                'nombre': jefe.nombre,
                'apellido': jefe.apellido,
                'genero': jefe.genero,
            }
        return None


class FamiliaConHabitantesSerializer(serializers.ModelSerializer):
    """
    Serializer maestro-detalle para crear Familia + Habitantes en una operación.
    Implementa nested write para crear todo transaccionalmente.
    """
    habitantes = HabitanteNestedSerializer(many=True, required=True)
    
    class Meta:
        model = Familia
        fields = [
            'id', 'nombre_familia', 'vivienda', 'direccion',
            'catastro', 'observaciones', 'habitantes'
        ]
        read_only_fields = ['id']
    
    def validate_habitantes(self, habitantes):
        """
        Valida la lista de habitantes antes de guardar.
        - Al menos 1 habitante requerido
        - Exactamente 1 jefe de familia
        - Cédulas únicas en la lista y en el sistema
        """
        if not habitantes or len(habitantes) == 0:
            raise serializers.ValidationError(
                "Debe agregar al menos un habitante a la familia."
            )
        
        # Validar exactamente un jefe de familia
        jefes = [h for h in habitantes if h.get('es_jefe_familia', False)]
        if len(jefes) == 0:
            raise serializers.ValidationError(
                "Debe designar exactamente un jefe de familia."
            )
        if len(jefes) > 1:
            raise serializers.ValidationError(
                "Solo puede haber un jefe de familia por hogar."
            )
        
        # Validar cédulas únicas en la lista
        cedulas = [h.get('cedula') for h in habitantes if h.get('cedula')]
        if len(cedulas) != len(set(cedulas)):
            raise serializers.ValidationError(
                "Hay cédulas duplicadas en la lista de habitantes."
            )
        
        # Validar cédulas únicas en el sistema
        # Obtener la familia actual si estamos editando
        instance = self.instance
        familia_id = instance.id if instance else None
        
        for habitante_data in habitantes:
            cedula = habitante_data.get('cedula')
            if cedula:
                # Normalizar cédula
                cedula_normalizada = validar_cedula_venezolana(cedula)
                habitante_data['cedula'] = cedula_normalizada
                
                # Verificar unicidad en BD
                queryset = Habitante.objects.filter(cedula=cedula_normalizada, is_deleted=False)
                
                # Si estamos editando una familia, excluir habitantes de esta familia
                if familia_id:
                    queryset = queryset.exclude(familia_id=familia_id)
                
                # Si el habitante tiene ID (está siendo editado), excluirlo también
                habitante_id = habitante_data.get('id')
                if habitante_id:
                    queryset = queryset.exclude(pk=habitante_id)
                
                if queryset.exists():
                    raise serializers.ValidationError(
                        f"La cédula {cedula_normalizada} ya está registrada en el sistema."
                    )
        
        return habitantes
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Crea Familia y sus Habitantes en una transacción atómica.
        """
        habitantes_data = validated_data.pop('habitantes')
        
        # Crear la familia
        familia = Familia.objects.create(**validated_data)
        
        # Crear cada habitante vinculado a la familia
        for habitante_data in habitantes_data:
            Habitante.objects.create(familia=familia, **habitante_data)
        
        return familia
    
    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Actualiza Familia y sus Habitantes en una transacción atómica.
        Estrategia: Actualizar habitantes existentes, crear nuevos, eliminar los que no están en la lista.
        """
        habitantes_data = validated_data.pop('habitantes', None)
        
        # Actualizar datos de la familia
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Si se proporcionaron habitantes, actualizar
        if habitantes_data is not None:
            # Obtener IDs de habitantes existentes
            habitantes_existentes = instance.habitantes.filter(is_deleted=False)
            ids_existentes = set(habitantes_existentes.values_list('id', flat=True))
            ids_enviados = set()
            
            # Procesar cada habitante en los datos enviados
            for habitante_data in habitantes_data:
                habitante_id = habitante_data.get('id')
                
                if habitante_id and habitante_id in ids_existentes:
                    # Actualizar habitante existente
                    try:
                        habitante = Habitante.objects.get(
                            pk=habitante_id, 
                            familia=instance, 
                            is_deleted=False
                        )
                        for attr, value in habitante_data.items():
                            if attr != 'id':  # No actualizar el ID
                                setattr(habitante, attr, value)
                        habitante.save()
                        ids_enviados.add(habitante_id)
                    except Habitante.DoesNotExist:
                        # Si no existe, crear nuevo
                        habitante_data.pop('id', None)  # Remover ID inválido
                        Habitante.objects.create(familia=instance, **habitante_data)
                else:
                    # Crear nuevo habitante
                    habitante_data.pop('id', None)  # Remover ID si existe pero no es válido
                    Habitante.objects.create(familia=instance, **habitante_data)
            
            # Soft delete de habitantes que no fueron enviados en la lista
            ids_a_eliminar = ids_existentes - ids_enviados
            if ids_a_eliminar:
                Habitante.objects.filter(
                    pk__in=ids_a_eliminar, 
                    familia=instance, 
                    is_deleted=False
                ).update(is_deleted=True)
        
        return instance
    
    def to_representation(self, instance):
        """
        Retorna la representación completa después de guardar.
        """
        return FamiliaDetalleSerializer(instance).data


# ============================================
# Serializer para actualización parcial de Habitante
# ============================================

class HabitanteUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para actualizar un habitante individualmente.
    """
    class Meta:
        model = Habitante
        fields = [
            'nombre', 'apellido', 'fecha_nacimiento', 'genero',
            'es_jefe_familia', 'ocupacion', 'nivel_educativo',
            'ingresos_mensuales', 'condiciones_salud'
        ]
    
    def validate_fecha_nacimiento(self, value):
        from datetime import date
        if value and value > date.today():
            raise serializers.ValidationError(
                'La fecha de nacimiento no puede ser futura.'
            )
        return value
    
    def validate_es_jefe_familia(self, value):
        """
        Valida que no haya otro jefe de familia activo.
        """
        if value and self.instance:
            # Verificar si ya hay otro jefe en la familia
            jefes_existentes = Habitante.objects.filter(
                familia=self.instance.familia,
                es_jefe_familia=True,
                is_deleted=False
            ).exclude(pk=self.instance.pk)
            
            if jefes_existentes.exists():
                raise serializers.ValidationError(
                    "Esta familia ya tiene un jefe de familia asignado."
                )
        
        return value
