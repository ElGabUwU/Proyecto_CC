"""
Serializers para la API REST del Sistema de Gestión Comunitaria.
Implementa arquitectura maestro-detalle para Familias y Habitantes.
"""
from rest_framework import serializers
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Familia, Habitante
from datetime import date
import datetime
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

class HabitanteSerializer(serializers.ModelSerializer):
    # Campo combinado para mostrar cédula completa (ej: "V-26123456")
    cedula_completa = serializers.SerializerMethodField()
    
    class Meta:
        model = Habitante
        fields = ['id', 'tipo_cedula', 'cedula', 'cedula_completa', 'nombre', 'apellido', 'genero', 'fecha_nacimiento', 'es_jefe_familia', 'nivel_educativo', 'ocupacion']

    def get_cedula_completa(self, obj):
        """Retorna la cédula con formato completo: V-12345678 o E-12345678"""
        return f"{obj.tipo_cedula}-{obj.cedula}"

    def validate_cedula(self, value):
        # Limpieza de caracteres no numéricos y del prefijo V- o E-
        cedula_limpia = re.sub(r'[^0-9]', '', str(value).strip())
        if not (5 <= len(cedula_limpia) <= 9):
            raise serializers.ValidationError("La cédula de identidad debe tener entre 5 y 9 dígitos.")
        
        # Verificar duplicados excluyendo el registro actual si se está editando
        instance_id = self.instance.id if self.instance else None
        queryset = Habitante.objects.filter(cedula=cedula_limpia, is_deleted=False)
        
        if instance_id:
            # Si tenemos una instancia, excluimos ese habitante específico
            queryset = queryset.exclude(id=instance_id)
        elif hasattr(self.parent, 'instance') and self.parent.instance:
            # Si estamos en modo edición de familia y no tenemos instancia propia aún,
            # excluimos todos los habitantes que ya pertenecen a esta familia
            queryset = queryset.exclude(familia=self.parent.instance)
            
        if queryset.exists():
            raise serializers.ValidationError("Esta cédula ya pertenece a un habitante activo.")
        return cedula_limpia

    def validate_nombre(self, value):
        return value.strip().upper()

    def validate_apellido(self, value):
        return value.strip().upper()

    def validate(self, attrs):
        fecha_nacimiento = attrs.get('fecha_nacimiento')
        es_jefe_familia = attrs.get('es_jefe_familia', False)
        
        if fecha_nacimiento:
            hoy = datetime.date.today()
            if fecha_nacimiento >= hoy:
                raise serializers.ValidationError({"fecha_nacimiento": "La fecha de nacimiento no puede ser igual o posterior al día de hoy."})
            
            # Calcular edad
            edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
            
            if edad > 115:
                raise serializers.ValidationError({"fecha_nacimiento": "Por favor, verifique el año. Excede el límite biológico."})
                
            # Restricción institucional para el Jefe de Familia
            if es_jefe_familia and edad < 18:
                raise serializers.ValidationError(
                    {"es_jefe_familia": f"No se puede designar como Jefe de Familia a un menor de edad (Tiene {edad} años)."}
                )
        return attrs


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
    habitantes = serializers.SerializerMethodField()
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
    
    def get_habitantes(self, obj):
        """Retorna solo los habitantes activos (no eliminados)."""
        habitantes_activos = obj.habitantes.filter(is_deleted=False)
        serializer = HabitanteSerializer(habitantes_activos, many=True)
        return serializer.data

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
from rest_framework import serializers
from django.db import transaction
from .models import Familia, Habitante
from datetime import date
import re
import json

class FamiliaConHabitantesSerializer(serializers.ModelSerializer):
    # Usamos tu serializador de habitantes maestro-detalle
    habitantes = HabitanteSerializer(many=True, required=False)
    
    class Meta:
        model = Familia
        fields = ['id', 'nombre_familia', 'vivienda', 'direccion', 'catastro', 'observaciones', 'habitantes']
    
    def validate(self, attrs):
        """
        Intercepta, audita mediante reglas socio-demográficas avanzadas y 
        aplana los errores en una estructura de lista JSON limpia y segura.
        """
        errores_planos = {}
        vivienda = attrs.get('vivienda', '').strip().upper()
        habitantes_data = attrs.get('habitantes', [])
        
        # 1. Validar duplicados de Vivienda en la Base de Datos
        queryset_familia = Familia.objects.filter(vivienda__iexact=vivienda, is_deleted=False)
        if self.instance:
            queryset_familia = queryset_familia.exclude(pk=self.instance.pk)
        if queryset_familia.exists():
            errores_planos['Inmueble / Vivienda'] = f"La vivienda o casa '{vivienda}' ya se encuentra registrada en el sistema."

        # Variables de control de flujo
        tiene_jefe = False
        edad_jefe = None
        cedulas_en_lote = set()
        hoy = date.today()

        # Primer recorrido: Extraer edad del Jefe de Familia para validaciones cruzadas relacionales
        for h_data in habitantes_data:
            if h_data.get('es_jefe_familia', False) and h_data.get('fecha_nacimiento'):
                f_nac = h_data.get('fecha_nacimiento')
                edad_jefe = hoy.year - f_nac.year - ((hoy.month, hoy.day) < (f_nac.month, f_nac.day))

        # Segundo recorrido: Auditoría individual y cruzada por cada habitante
        for index, h_data in enumerate(habitantes_data):
            nombre = h_data.get('nombre', '').strip().upper()
            apellido = h_data.get('apellido', '').strip().upper()
            nombre_completo = f"{nombre} {apellido}".strip() if (nombre or apellido) else f"Ciudadano Nro. {index + 1}"
            
            cedula_raw = h_data.get('cedula', '').strip()
            cedula_numerica = re.sub(r'\D', '', cedula_raw)
            es_jefe = h_data.get('es_jefe_familia', False)
            fecha_nac = h_data.get('fecha_nacimiento')
            nivel_educativo = h_data.get('nivel_educativo', '').strip().upper() if h_data.get('nivel_educativo') else ''
            ocupacion = h_data.get('ocupacion', '').strip().upper() if h_data.get('ocupacion') else ''

            # A) Control e integridad de Cédulas de Identidad
            if cedula_numerica:
                if cedula_numerica in cedulas_en_lote:
                    errores_planos[f"Cédula Duplicada ({nombre_completo})"] = f"La cédula num. '{cedula_numerica}' se encuentra repetida dentro de esta misma ficha."
                else:
                    cedulas_en_lote.add(cedula_numerica)

                qs_cedula = Habitante.objects.filter(cedula=cedula_numerica, is_deleted=False)
                if self.instance:
                    qs_cedula = qs_cedula.exclude(familia=self.instance)
                if qs_cedula.exists():
                    errores_planos[f"Cédula ya Registrada ({nombre_completo})"] = f"La cédula '{cedula_numerica}' ya pertenece a un ciudadano censado en otra vivienda."

            # B) Validaciones Cronológicas y Biológicas de Peso
            if fecha_nac:
                if fecha_nac >= hoy:
                    errores_planos[f"Fecha Inválida ({nombre_completo})"] = "La fecha de nacimiento no puede ser igual o posterior al día de hoy."
                    continue
                
                edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
                
                if edad > 115:
                    errores_planos[f"Error Biológico ({nombre_completo})"] = f"La edad calculada es de {edad} years. Por favor verifique el año de nacimiento."

                # C) Jerarquía de la Jefatura del Hogar
                if es_jefe:
                    if edad < 18:
                        errores_planos[f"Menor de Edad Jefe ({nombre_completo})"] = f"Tiene {edad} años. No se puede designar a un menor de edad como Jefe de Familia."
                    if tiene_jefe:
                        errores_planos["Conflicto de Estructura"] = "Se detectaron múltiples Jefes de Familia. Solo puede existir un (1) jefe por cada hogar."
                    tiene_jefe = True

                # D) Validación Coherencia Académica (Nivel Educativo vs Edad)
                if "UNIVERSITARIO" in nivel_educativo or "TECNICO" in nivel_educativo:
                    if edad < 16:
                        errores_planos[f"Incoherencia Académica ({nombre_completo})"] = f"Posee {edad} años. No es lógico asignar un nivel educativo superior o técnico a esa edad."
                
                if edad < 4 and nivel_educativo and not any(x in nivel_educativo for x in ["MATERNAL", "NINGUNO"]):
                    errores_planos[f"Nivel Escolar Inválido ({nombre_completo})"] = f"Un infante de {edad} años no cumple con el rango mínimo de edad para el nivel escolar '{nivel_educativo}'."

                # E) Validación Coherencia Laboral (Protección Legal LOPNNA)
                if ocupacion and not any(x in ocupacion for x in ["NINGUNA", "ESTUDIANTE", "HOGAR", "N/A"]):
                    if edad < 14:
                        errores_planos[f"Inconsistencia Laboral ({nombre_completo})"] = f"El menor posee {edad} años y registra una ocupación laboral activa. Verifique los datos filiales según la normativa legal vigente."

                # F) Relación Generacional Directa contra el Jefe de Familia
                if not es_jefe and edad_jefe is not None:
                    # En una ficha normal un integrante regular no debe superar la edad del jefe por márgenes absurdos a menos que se asigne parentesco
                    if (edad - edad_jefe) > 45:
                        pass # Espacio libre por si deseas añadir filtros de parentesco (Ej: Abuelos)

        # =====================================================================
        # 🔒 FILTRO DE SEGURIDAD, INTERCEPCIÓN DE ATACKS Y ORDENAMIENTO DE SALIDA
        # =====================================================================
        if errores_planos:
            lista_mensajes_seguros = []
            
            # Prioridad 1: Problemas estructurales de la Vivienda o la Jefatura arriba
            for clave, mensaje in errores_planos.items():
                if "Inmueble" in clave or "Vivienda" in clave or "Conflicto" in clave:
                    lista_mensajes_seguros.append(mensaje)
            
            # Prioridad 2: Inconsistencias demográficas de la carga familiar abajo
            for clave, mensaje in errores_planos.items():
                if not ("Inmueble" in clave or "Vivienda" in clave or "Conflicto" in clave):
                    lista_mensajes_seguros.append(mensaje)

            # Ofuscamos los nombres de campos de la BD y variables internas serializando a un array simple
            json_seguro = json.dumps(lista_mensajes_seguros)
            
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(json_seguro)

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """
        Crea la Familia y vincula sus habitantes sanitizando las cédulas de forma estricta.
        Extrae el tipo de cédula (V/E) del formato completo enviado por el frontend.
        """
        habitantes_data = validated_data.pop('habitantes', [])
        
        # Guardar la instancia de Familia de manera limpia
        familia = Familia.objects.create(**validated_data)
        
        # Iterar y poblar la tabla relacional de Habitantes
        for h_data in habitantes_data:
            if 'cedula' in h_data:
                cedula_completa = str(h_data['cedula']).strip()
                # Extraer tipo de cédula (V o E) del formato "V-12345678" o "E-12345678"
                if '-' in cedula_completa:
                    partes = cedula_completa.split('-')
                    tipo_cedula = partes[0].upper() if partes[0] else 'V'
                    cedula_numerica = re.sub(r'\D', '', partes[1] if len(partes) > 1 else cedula_completa)
                else:
                    tipo_cedula = 'V'
                    cedula_numerica = re.sub(r'\D', '', cedula_completa)
                
                h_data['tipo_cedula'] = tipo_cedula
                h_data['cedula'] = cedula_numerica
                
            Habitante.objects.create(familia=familia, **h_data)
            
        return familia

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Actualiza el maestro de la Familia y sincroniza el detalle de los Habitantes
        aplicando conciliación por ID/Cédula y remoción mediante Soft Delete.
        """
        habitantes_data = validated_data.pop('habitantes', None)
        
        # 1. Actualizar los campos nativos del inmueble
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # 2. Sincronización Maestro-Detalle Compleja
        if habitantes_data is not None:
            habitantes_existentes = instance.habitantes.filter(is_deleted=False)
            
            # Mapeos de búsqueda indexada rápidos en memoria
            dict_por_id = {h.id: h for h in habitantes_existentes}
            dict_por_cedula = {h.cedula: h for h in habitantes_existentes}
            
            ids_enviados = set()
            
            for h_data in habitantes_data:
                habitante_id = h_data.get('id')
                cedula_enviada = h_data.get('cedula', '').strip()
                
                # Extraer tipo de cédula (V o E) del formato "V-12345678" o "E-12345678"
                if '-' in cedula_enviada:
                    partes = cedula_enviada.split('-')
                    tipo_cedula = partes[0].upper() if partes[0] else 'V'
                    cedula_limpia = re.sub(r'\D', '', partes[1] if len(partes) > 1 else cedula_enviada)
                else:
                    tipo_cedula = 'V'
                    cedula_limpia = re.sub(r'\D', '', cedula_enviada)
                
                # Normalizamos la cédula y agregamos el tipo antes de realizar comparaciones u operaciones de guardado
                if 'cedula' in h_data:
                    h_data['cedula'] = cedula_limpia
                if 'tipo_cedula' not in h_data:
                    h_data['tipo_cedula'] = tipo_cedula

                habitante_instancia = None
                
                # Intentar enlazar con registro persistido (Por ID primario o por Cédula única)
                if habitante_id and int(habitante_id) in dict_por_id:
                    habitante_instancia = dict_por_id[int(habitante_id)]
                elif cedula_limpia in dict_por_cedula:
                    habitante_instancia = dict_por_cedula[cedula_limpia]
                
                if habitante_instancia:
                    # Actualizar habitante preexistente en la vivienda
                    for attr, value in h_data.items():
                        if attr != 'id':
                            setattr(habitante_instancia, attr, value)
                    habitante_instancia.save()
                    ids_enviados.add(habitante_instancia.id)
                else:
                    # Insertar un nuevo ciudadano agregado a la carga de la ficha familiar
                    h_data.pop('id', None)
                    nuevo = Habitante.objects.create(familia=instance, **h_data)
                    ids_enviados.add(nuevo.id)
            
            # 3. Limpieza remanente automatizada (Soft Delete)
            ids_existentes = set(dict_por_id.keys())
            ids_a_eliminar = ids_existentes - ids_enviados
            if ids_a_eliminar:
                Habitante.objects.filter(
                    pk__in=ids_a_eliminar, 
                    familia=instance, 
                    is_deleted=False
                ).update(is_deleted=True)
        
        return instance
    
    def to_representation(self, instance):
        # Transforma el payload de respuesta de la API usando el serializador detallado
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