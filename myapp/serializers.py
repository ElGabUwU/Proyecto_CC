"""
Serializers para la API REST del Sistema de Gestión Comunitaria.
Implementa arquitectura maestro-detalle para Familias y Habitantes.
"""
from rest_framework import serializers
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Familia, Habitante
from datetime import date
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

def validar_cedula_venezolana(cedula):
    """
    Valida el formato de cédula venezolana.
    Si vienen solo números, le añade el prefijo 'V-' automáticamente para evitar quiebres.
    Formatos válidos: V-12345678, E-12345678, V12345678, E12345678, 12345678
    """
    if not cedula:
        return cedula
    
    # Normalizar: quitar espacios y pasar a mayúsculas
    cedula = str(cedula).strip().upper()
    
    # NUEVO TRUCO: Si el usuario metió solo números (ej: "30456789"), le asumimos la V- por defecto
    if cedula.isdigit():
        cedula = f"V-{cedula}"
    
    # Patrones válidos
    patron_con_guion = r'^[VE]-\d{6,8}$'
    patron_sin_guion = r'^[VE]\d{6,8}$'
    
    if not (re.match(patron_con_guion, cedula) or re.match(patron_sin_guion, cedula)):
        raise serializers.ValidationError(
            "Formato de cédula inválido. Use: V-12345678 o E-12345678"
        )
    
    # Normalizar con guion si venía pegado (ej: V12345678 -> V-12345678)
    if re.match(patron_sin_guion, cedula):
        cedula = f"{cedula[0]}-{cedula[1:]}"
    
    return cedula
# ============================================
# Mixin para Tolerancia de Claves de Fecha (Frontend-Friendly)
# ============================================

def validar_cedula_unica(cedula, exclude_pk=None):
    """
    Valida que la cédula no esté registrada en otro habitante activo.
    """
    queryset = Habitante.objects.filter(cedula=cedula, is_deleted=False)
    if exclude_pk:
        queryset = queryset.exclude(pk=exclude_pk)

    if queryset.exists():
        raise serializers.ValidationError(
            f"La cédula {cedula} ya está registrada en el sistema."
        )
    return cedula

class FechaToleranteMixin:
    """
    Mixin para interceptar datos crudos del frontend.
    Si el JSON envía 'fecha_nac', lo traduce a 'fecha_nacimiento'
    para que el validador nativo de Django no falle por obligatoriedad.
    """
    def to_internal_value(self, data):
        # Clonar datos para poder mutar de manera segura
        dict_data = data.copy() if hasattr(data, 'copy') else dict(data)
        
        # Si el Frontend envió 'fecha_nac', mapearla transparentemente a 'fecha_nacimiento'
        if 'fecha_nac' in dict_data and 'fecha_nacimiento' not in dict_data:
            dict_data['fecha_nacimiento'] = dict_data['fecha_nac']
            
        return super().to_internal_value(dict_data)

# ============================================
# Serializers para Habitante
# ============================================

class HabitanteSerializer(FechaToleranteMixin, serializers.ModelSerializer):
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
        cedula = data.get('cedula')
        instance = self.instance
        
        if cedula:
            validar_cedula_unica(cedula, exclude_pk=instance.pk if instance else None)
        
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
    # SOLUCIÓN: Declaramos el ID explícitamente como un IntegerField 
    # que no es obligatorio y acepta valores nulos (para registros nuevos).
    id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Habitante
        fields = [
            'id', 'cedula', 'nombre', 'apellido',
            'fecha_nacimiento', 'genero',
            'es_jefe_familia',
            'ocupacion', 'nivel_educativo',
            'ingresos_mensuales', 'condiciones_salud'
        ]
        # Dejamos únicamente el borrado de validadores automáticos para la cédula
        extra_kwargs = {
            'cedula': {
                'validators': [] # Desactiva la validación automática estricta de DRF
            }
        }
    
    def validate_cedula(self, value):
        """Valida únicamente el formato de la cédula."""
        return validar_cedula_venezolana(value)
    
    def validate_fecha_nacimiento(self, value):
        """Valida que la fecha de nacimiento no sea futura."""
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
        jefe = obj.jefe_familia
        if jefe:
            return f"{jefe.nombre} {jefe.apellido}"
        return "Sin jefe asignado"
    
    def get_jefe_cedula(self, obj):
        jefe = obj.jefe_familia
        return jefe.cedula if jefe else "-"

class FamiliaDetalleSerializer(serializers.ModelSerializer):
    """
    Serializer detallado para lectura de una familia.
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
    Serializer maestro-detalle para crear Familia + Habitantes transaccionalmente.
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
        if not habitantes or len(habitantes) == 0:
            raise serializers.ValidationError("Debe agregar al menos un habitante.")
        
        # Validar consistencia de Jefes (Regla del consejo comunal)
        jefes = [h for h in habitantes if h.get('es_jefe_familia', False)]
        if len(jefes) != 1:
            raise serializers.ValidationError("Debe designar exactamente un jefe de familia.")
            
        # Validar que no metan la misma cédula dos veces en el mismo formulario
        cedulas = [h.get('cedula') for h in habitantes if h.get('cedula')]
        if len(cedulas) != len(set(cedulas)):
            raise serializers.ValidationError("Hay cédulas duplicadas en el formulario.")
        
        # Validar duplicados EXTERNOS (en otras familias)
        instance = self.instance # La familia que se está editando (si es un PUT)
        for h_data in habitantes:
            cedula = h_data.get('cedula')
            if cedula:
                # Buscar si la cédula ya existe en la BD
                queryset = Habitante.objects.filter(cedula=cedula, is_deleted=False)
                # Si estamos editando, permitimos que la cédula ya exista si pertenece a ESTA familia
                if instance:
                    queryset = queryset.exclude(familia=instance)
                
                if queryset.exists():
                    raise serializers.ValidationError(
                        f"La cédula {cedula} ya está registrada en otro hogar del consejo comunal."
                    )
                    
        return habitantes
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Crea Familia y vincula los habitantes. La relación de jefe de familia
        se infiere automáticamente a través del campo 'es_jefe_familia' en el Habitante.
        """
        habitantes_data = validated_data.pop('habitantes')
        
        # 1. Crear la familia limpiamente con los datos de la vivienda/dirección
        familia = Familia.objects.create(**validated_data)
        
        # 2. Crear los habitantes asociados. 
        # Al guardar cada uno con su bandera 'es_jefe_familia', el modelo Familia 
        # resolverá su propiedad 'jefe_familia' automáticamente en las consultas.
        for h_data in habitantes_data:
            Habitante.objects.create(familia=familia, **h_data)
            
        return familia
    
    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Actualiza la Familia y gestiona el ciclo de vida de los habitantes,
        emparejando por ID o por Cédula si el frontend omitió el ID.
        """
        habitantes_data = validated_data.pop('habitantes', None)
        
        # 1. Actualizar datos propios de la familia
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # 2. Sincronizar el maestro-detalle de los habitantes
        if habitantes_data is not None:
            habitantes_existentes = instance.habitantes.filter(is_deleted=False)
            
            # Mapeos para buscar de forma rápida por ID o por Cédula preexistente en la familia
            dict_por_id = {h.id: h for h in habitantes_existentes}
            dict_por_cedula = {h.cedula: h for h in habitantes_existentes}
            
            ids_enviados = set()
            
            for h_data in habitantes_data:
                habitante_id = h_data.get('id')
                cedula_enviada = h_data.get('cedula')
                
                habitante_instancia = None
                
                # Intentar buscar el habitante por ID
                if habitante_id and int(habitante_id) in dict_por_id:
                    habitante_instancia = dict_por_id[int(habitante_id)]
                # Salvavidas: Si el frontend no mandó ID, buscamos si la cédula ya era de esta familia
                elif cedula_enviada in dict_por_cedula:
                    habitante_instancia = dict_por_cedula[cedula_enviada]
                
                if habitante_instancia:
                    # Actualizar habitante existente
                    for attr, value in h_data.items():
                        if attr != 'id':
                            setattr(habitante_instancia, attr, value)
                    habitante_instancia.save()
                    ids_enviados.add(habitante_instancia.id)
                else:
                    # Es un habitante verdaderamente nuevo en la familia
                    h_data.pop('id', None)
                    nuevo = Habitante.objects.create(familia=instance, **h_data)
                    ids_enviados.add(nuevo.id)
            
            # Limpieza remanente / Soft Delete para los miembros que fueron removidos en la interfaz
            ids_existentes = set(dict_por_id.keys())
            ids_a_eliminar = ids_existentes - ids_enviados
            if ids_a_eliminar:
                Habitante.objects.filter(pk__in=ids_a_eliminar, familia=instance, is_deleted=False).update(is_deleted=True)
        
        return instance
    
    def to_representation(self, instance):
        return FamiliaDetalleSerializer(instance).data
    
# ============================================
# Serializer para actualización parcial de Habitante
# ============================================

class HabitanteUpdateSerializer(FechaToleranteMixin, serializers.ModelSerializer):
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
        if value and value > date.today():
            raise serializers.ValidationError(
                'La fecha de nacimiento no puede ser futura.'
            )
        return value
    
    def validate_es_jefe_familia(self, value):
        if value and self.instance:
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