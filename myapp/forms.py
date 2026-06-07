
from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum
from datetime import date
import datetime
import re
from .models import Comite, Proyecto, ProyectoIntegrante
from .models import (
    Familia, Habitante, IngresoComunal, EgresoComunal, 
    ConstanciaResidencia, ActaReunion, CensoParticipante
)

# ============================================
# 🏠 FORMULARIOS DE GESTIÓN HABITACIONAL
# ============================================

class FamiliaForm(forms.ModelForm):
    """Formulario unificado para la gestión de inmuebles familiares."""
    nombre_familia = forms.CharField(
        label="Nombre de la Familia / Grupo",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Familia Rodríguez Peña'}),
        help_text="Un nombre identificativo para el grupo familiar o vivienda"
    )
    vivienda = forms.CharField(
        label="Número o Tipo de Vivienda",
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Casa Nro. 45 / Apto 3-B'}),
        help_text="Identificación física del inmueble"
    )
    direccion = forms.CharField(
        label="Dirección Completa",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Calles, veredas, puntos de referencia...'}),
        help_text="Ubicación exacta dentro de la comunidad"
    )
    catastro = forms.CharField(
        label="Código Catastral (Opcional)",
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: CAT-12345-TACH'}),
        help_text="Código de registro catastral si aplica"
    )
    observaciones = forms.CharField(
        label="Observaciones Generales",
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Notas sobre la vivienda...'}),
        help_text="Detalles adicionales relevantes"
    )

    class Meta:
        model = Familia
        fields = ['nombre_familia', 'vivienda', 'direccion', 'catastro', 'observaciones']

    def clean_vivienda(self):
        vivienda = self.cleaned_data.get('vivienda', '').strip().upper()
        if not vivienda:
            raise ValidationError("El identificador de la vivienda no puede estar vacío.")
        return vivienda

class HabitanteForm(forms.ModelForm):
    tipo_cedula = forms.ChoiceField(
        label="Nacionalidad",
        choices=[('V', 'Venezolano/a'), ('E', 'Extranjero/a')],
        initial='V',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    fecha_nacimiento = forms.DateField(
        label="Fecha de Nacimiento",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text="Seleccione la fecha de nacimiento del habitante"
    )

    class Meta:
        model = Habitante
        # ⬇️ Quitamos 'telefono', 'correo' y 'observaciones' porque no existen en el modelo
        fields = [
            'tipo_cedula', 'cedula', 'nombre', 'apellido', 'genero', 
            'fecha_nacimiento', 'es_jefe_familia'
        ]
        widgets = {
            'cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 25123456'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Juan Carlos'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Pérez Rodríguez'}),
            'genero': forms.Select(attrs={'class': 'form-select'}),
            'es_jefe_familia': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    # (Mantén tus funciones clean_cedula, clean_nombre, clean_apellido y clean tal cual las armamos)
    # =========================================================================
    # 1. VALIDACIÓN Y LIMPIEZA DE CÉDULA
    # =========================================================================
    def clean_cedula(self):
        cedula_raw = self.cleaned_data.get('cedula', '').strip()
        
        # Eliminar puntos, guiones o letras accidentales que meta el usuario
        cedula_limpia = re.sub(r'\D', '', cedula_raw)
        
        if not cedula_limpia:
            raise forms.ValidationError("La cédula debe contener caracteres numéricos válidos.")
            
        # Longitud coherente en Venezuela (mínimo 5 para adultos mayores, máximo 9)
        if not (5 <= len(cedula_limpia) <= 9):
            raise forms.ValidationError("La cédula de identidad debe tener entre 5 y 9 dígitos.")
            
        # Validar unicidad (Verificamos si ya existe excluyendo el registro actual si es edición)
        queryset = Habitante.objects.filter(cedula=cedula_limpia, is_deleted=False)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
            
        if queryset.exists():
            raise forms.ValidationError("Ya existe un habitante activo registrado con esta Cédula de Identidad.")
            
        return cedula_limpia
    
    # =========================================================================
    # 2. SENSIBILIDAD A MAYÚSCULAS (Conversión automática e institucional)
    # =========================================================================
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        # Filtro: Solo permitir letras y espacios (atendiendo acentos y la Ñ)
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', nombre):
            raise forms.ValidationError("El nombre solo debe contener letras y espacios.")
        # Guardar en Mayúsculas Sostenidas para uniformidad en constancias impresas
        return nombre.upper()

    def clean_apellido(self):
        apellido = self.cleaned_data.get('apellido', '').strip()
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', apellido):
            raise forms.ValidationError("El apellido solo debe contener letras y espacios.")
        return apellido.upper()

    # =========================================================================
    # 3. INTERDEPENDENCIAS CRÍTICAS (Fecha de Nacimiento vs Jefe de Familia)
    # =========================================================================
    def clean(self):
        cleaned_data = super().clean()
        fecha_nacimiento = cleaned_data.get('fecha_nacimiento')
        es_jefe_familia = cleaned_data.get('es_jefe_familia', False)
        
        if fecha_nacimiento:
            hoy = datetime.date.today()
            
            # Control del futuro
            if fecha_nacimiento >= hoy:
                self.add_error('fecha_nacimiento', "La fecha de nacimiento no puede ser igual o posterior al día de hoy.")
                return cleaned_data
            
            # Calcular edad exacta en años
            edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
            
            # Cota de coherencia biológica extrema
            if edad > 115:
                self.add_error('fecha_nacimiento', "Por favor, verifique el año ingresado. Excede el límite de coherencia de edad.")
            
            # Jefe de Familia debe ser Mayor de Edad
            if es_jefe_familia and edad < 18:
                raise forms.ValidationError(
                    f"Conflicto en Roles: El habitante tiene {edad} años. No se puede designar como Jefe de Familia a un menor de edad."
                )
                
        return cleaned_data
    
    def clean_vivienda(self):
        vivienda = self.cleaned_data.get('vivienda', '').strip().upper()
        
        # Verificar si ya existe esa casa registrada (excluyendo si estamos editando la misma)
        queryset = Familia.objects.filter(vivienda__iexact=vivienda, is_deleted=False)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
            
        if queryset.exists():
            raise forms.ValidationError(
                f"Error de Censo: La vivienda o número de inmueble '{vivienda}' ya se encuentra registrada en el sistema."
            )
            
        return vivienda

class IngresoComunalForm(forms.ModelForm):
    """
    Formulario para registrar ingresos de la caja comunal.
    """
    fecha = forms.DateField(
        label="Fecha del Ingreso",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text="Fecha en que se recibió el ingreso"
    )
    
    concepto = forms.CharField(
        label="Concepto",
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: APORTE MENSUAL FAMILIA PÉREZ'
        }),
        help_text="Descripción del ingreso"
    )
    
    monto = forms.DecimalField(
        label="Monto (Bs.)",
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        }),
        help_text="Monto del ingreso en bolívares"
    )
    
    # Sincronizado con el nombre exacto del campo en tu models.py para evitar colisiones
    soporte = forms.FileField(
        required=False,
        label="Soporte Digital",
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.jpg,.jpeg,.png'
        }),
        help_text="Comprobante o soporte del ingreso (PDF, imagen)"
    )
    
    observaciones = forms.CharField(
        required=False,
        label="Observaciones",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Observaciones adicionales...'
        }),
        help_text="Observaciones adicionales"
    )
    
    class Meta:
        model = IngresoComunal
        fields = ['fecha', 'tipo_ingreso', 'concepto', 'monto', 'soporte', 'observaciones']
        widgets = {
            'tipo_ingreso': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'tipo_ingreso': 'Tipo de Ingreso',
        }
    
    def __init__(self, *args, **kwargs):
        """Inicializar con el usuario actual como responsable"""
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        """Guardar con el usuario como responsable"""
        instance = super().save(commit=False)
        if self.user:
            instance.responsable = self.user
        if commit:
            instance.save()
        return instance
    
    def clean_concepto(self):
        """Sanitiza el concepto a mayúsculas y quita espacios extra"""
        return self.cleaned_data.get('concepto', '').strip().upper()
    
    def clean_fecha(self):
        """Validar que la fecha no sea futura"""
        fecha = self.cleaned_data.get('fecha')
        # Asegurar la extracción de la fecha sin importar si es datetime o date
        if hasattr(fecha, 'date'):
            fecha_evaluar = fecha.date()
        else:
            fecha_evaluar = fecha

        if fecha_evaluar and fecha_evaluar > date.today():
            # 🔑 ASIGNAMOS UN NOMBRE ESPECÍFICO AL ERROR USANDO 'code'
            raise ValidationError(
                "No se pueden registrar transacciones financieras en una fecha futura.",
                code='fecha_futura_prohibida'
            )
        return fecha
    
    def clean_monto(self):
        """Validar que el monto sea positivo"""
        monto = self.cleaned_data.get('monto')
        if monto and monto <= 0:
            raise ValidationError("El monto debe ser mayor a cero.")
        return monto


class EgresoComunalForm(forms.ModelForm):
    """
    Formulario para registrar egresos de la caja comunal.
    """
    fecha = forms.DateField(
        label="Fecha del Egreso",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text="Fecha en que se realizó el egreso"
    )
    
    concepto = forms.CharField(
        label="Concepto",
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Compra materiales limpieza'
        }),
        help_text="Descripción del egreso"
    )
    
    monto = forms.DecimalField(
        label="Monto (Bs.)",
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        }),
        help_text="Monto del egreso en bolívares"
    )
    
    beneficiario = forms.CharField(
        required=False,
        label="Beneficiario",
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Juan Pérez o Empresa XYZ'
        }),
        help_text="Persona o empresa que recibió el pago (opcional)"
    )

    soporte_digital = forms.FileField(
        required=False,
        label="Soporte Digital",
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.jpg,.jpeg,.png'
        }),
        help_text="Comprobante o soporte del ingreso (PDF, imagen)"
    )
    
    observaciones = forms.CharField(
        required=False,
        label="Observaciones",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Observaciones adicionales...'
        }),
        help_text="Observaciones adicionales"
    )
    
    class Meta:
        model = EgresoComunal
        fields = ['fecha', 'tipo_egreso', 'concepto', 'monto', 'beneficiario', 'soporte', 'observaciones']
        widgets = {
            'tipo_egreso': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'tipo_egreso': 'Tipo de Egreso',
        }
    
    def __init__(self, *args, **kwargs):
        """Inicializar con el usuario actual como responsable"""
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        """Guardar con el usuario como responsable"""
        instance = super().save(commit=False)
        if self.user:
            instance.responsable = self.user
        if commit:
            instance.save()
        return instance
    
    def clean_fecha(self):
        """Validar que la fecha no sea futura con código de error explícito"""
        fecha = self.cleaned_data.get('fecha')
        
        # Garantizar extracción de la fecha plana si viene como datetime
        if hasattr(fecha, 'date'):
            fecha_evaluar = fecha.date()
        else:
            fecha_evaluar = fecha

        if fecha_evaluar and fecha_evaluar > datetime.date.today():
            # 🔑 LE DA IDENTIDAD TÉCNICA AL ERROR ESPECÍFICO
            raise ValidationError(
                "No se pueden registrar transacciones financieras en una fecha futura.",
                code='fecha_futura_prohibida'
            )
        return fecha
    
    def clean_monto(self):
        """Validar que el monto sea positivo"""
        monto = self.cleaned_data.get('monto')
        if monto and monto <= 0:
            raise ValidationError("El monto debe ser mayor a cero.")
        return monto


class ConstanciaResidenciaForm(forms.ModelForm):
    """
    Formulario optimizado para generar constancias de residencia 
    en la Urbanización Manuel Pulido Méndez.
    """
    familia = forms.ModelChoiceField(
        queryset=Familia.objects.filter(is_deleted=False).order_by('nombre_familia'),
        label="Familia / Núcleo Familiar",
        widget=forms.Select(attrs={'class': 'form-select bg-dark text-white border-secondary', 'id': 'select_familia'}),
        help_text="Seleccione la familia para filtrar u obtener apoyo visual si es necesario."
    )
    
    fecha_documento = forms.DateField(
        label="Fecha del Documento",
        initial=timezone.now,
        widget=forms.DateInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'type': 'date'
        }),
        help_text="Fecha formal de emisión que aparecerá en el impreso."
    )
    
    finalidad = forms.CharField(
        label="Finalidad o Motivo",
        widget=forms.Textarea(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'rows': 3,
            'placeholder': 'Ej: PARA TRAMITAR APERTURA DE CUENTA BANCARIA / INSCRIPCIÓN UNIVERSITARIA...'
        }),
        help_text="Especifique el motivo de la solicitud."
    )
    
    class Meta:
        model = ConstanciaResidencia
        fields = ['habitante', 'fecha_documento', 'finalidad']
        widgets = {
            'habitante': forms.Select(attrs={'class': 'form-select bg-dark text-white border-secondary select2'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Filtro de seguridad: Solo permitir emitir constancias a habitantes activos
        self.fields['habitante'].queryset = Habitante.objects.filter(is_deleted=False).order_by('apellido', 'nombre')
    
    def clean_finalidad(self):
        """Sanitiza el motivo a mayúsculas limpias para el documento legal"""
        return self.cleaned_data.get('finalidad', '').strip().upper()

    def clean_fecha_documento(self):
        """Validar que la fecha del documento no sea una incoherencia futura"""
        fecha_doc = self.cleaned_data.get('fecha_documento')
        if fecha_doc and fecha_doc > datetime.date.today():
            raise ValidationError("La fecha formal de la constancia no puede ser una fecha futura.")
        return fecha_doc
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.generado_por = self.user
        
        # 🔑 CORRECCIÓN DE MAPEO: El campo real en tu models.py es 'texto_constancia'
        instance.texto_constancia = self.generar_contenido_constancia(instance)
        
        if commit:
            instance.save()
        return instance
    
    def generar_contenido_constancia(self, constancia):
        """Generar el contenido HTML seguro con la semántica del modelo actual"""
        # Accedemos a la familia a través de la relación del habitante solicitante
        familia = constancia.habitante.familia 
        solicitante = constancia.habitante
        
        nombre_solicitante = f"{solicitante.nombre} {solicitante.apellido}".upper()
        
        # CORRECCIÓN: Si la cédula ya tiene el prefijo 'V-' o 'E-', lo dejamos intacto
        cedula_raw = solicitante.cedula if solicitante.cedula else "S/C"
        cedula_solicitante = cedula_raw if "-" in cedula_raw or len(cedula_raw) > 9 else f"V-{cedula_raw}"
        
        total_integrantes = familia.habitantes.filter(is_deleted=False).count() if familia else 1
        nombre_familia = familia.nombre_familia.upper() if familia else "S/D"
        direccion_familia = getattr(familia, 'direccion', 'Comunidad Manuel Pulido Méndez').upper() if familia else "COMUNIDAD MANUEL PULIDO MÉNDEZ"
        
        contenido = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #1a1a1a;">
            <div style="text-align: center; margin-bottom: 25px;">
                <h3 style="margin-bottom: 5px; text-transform: uppercase;">CONSTANCIA DE RESIDENCIA</h3>
                <p style="margin-top: 0; font-weight: bold;">Control N° {constancia.id or 'NUEVO'}</p>
            </div>
            
            <p style="text-align: justify; margin-bottom: 15px;">
                Quien suscribe, los Voceros y Voceras pertenecientes al <strong>CONSEJO COMUNAL MANUEL PULIDO MÉNDEZ</strong>, 
                ubicado en el Municipio Junín del Estado Táchira, hacen constar por medio de la presente que el ciudadano(a):
            </p>
            
            <div style="margin-left: 20px; margin-bottom: 20px; background: #f8fafc; padding: 10px; border-radius: 4px;">
                <p style="margin: 4px 0;"><strong>NOMBRES Y APELLIDOS:</strong> {nombre_solicitante}</p>
                <p style="margin: 4px 0;"><strong>CÉDULA DE IDENTIDAD:</strong> {cedula_solicitante}</p>
                <p style="margin: 4px 0;"><strong>NÚCLEO FAMILIAR:</strong> {nombre_familia}</p>
                <p style="margin: 4px 0;"><strong>DIRECCIÓN COMPLETA:</strong> {direccion_familia}</p>
            </div>
            
            <p style="text-align: justify; margin-bottom: 15px;">
                Reside en el ámbito geográfico de esta comunidad junto a su grupo familiar, el cual se encuentra integrado por 
                un total de <strong>{total_integrantes}</strong> personas, debidamente censadas y verificadas bajo los registros internos de nuestra organización comunitaria.
            </p>
            
            <p style="text-align: justify; margin-bottom: 25px;">
                <strong>FINALIDAD:</strong> Constancia que se expide a petición de la parte interesada para fines de: <em>{constancia.finalidad}</em>.
            </p>
        </div>
        """
        return contenido

from django import forms
from django.utils import timezone
from .models import ActaReunion

class ActaReunionForm(forms.ModelForm):
    # 1. Campos explícitos para la interfaz estética del formulario (No alteran el modelo)
    titulo = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'Ej. Acta de Asamblea General Extraordinaria'
        })
    )
    fecha_reunion = forms.DateTimeField(
        initial=timezone.now,
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control bg-dark text-white border-secondary'
        })
    )
    lugar = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'Ej. Cancha Techada del Sector Manuel Pulido Méndez'
        })
    )
    director_debate = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'Nombre del vocero que dirige el debate'
        })
    )
    tipo_asamblea = forms.ChoiceField(
        choices=[('ORDINARIA', 'Ordinaria'), ('EXTRAORDINARIA', 'Extraordinaria')],
        widget=forms.Select(attrs={'class': 'form-select bg-dark text-white border-secondary'})
    )
    problema_identificado = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'rows': '3',
            'placeholder': 'Describa detalladamente la problemática planteada por la comunidad...'
        })
    )
    propuesta_solucion = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'rows': '3',
            'placeholder': 'Detalle el nombre del proyecto o acciones aprobadas para solventar...'
        })
    )
    monto_estimado = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': '0.00 (Dejar vacío si no requiere financiamiento)'
        })
    )
    banco_receptor = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'Ej. Banco de Venezuela (Si aplica)'
        })
    )
    cuenta_bancaria = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': '20 dígitos de la cuenta comunal'
        })
    )
    votos_favor = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'Cantidad de ciudadanos que aprobaron'
        })
    )
    asistentes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'rows': '3',
            'placeholder': 'Nombre y apellido de los asistentes separados por comas...'
        })
    )

    class Meta:
        model = ActaReunion
        # Mapeamos únicamente los campos reales que existen en la base de datos de tu modelo
        fields = ['titulo', 'fecha_reunion', 'lugar', 'asistentes']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        # 1. Instanciamos el objeto sin guardarlo en la base de datos todavía
        acta = super().save(commit=False)
        
        # 2. Asociamos el usuario validador que extrajimos de la vista
        acta.generado_por = self.user
        
        # 3. Extraemos de forma segura los valores del formulario limpitos (cleaned_data)
        titulo = self.cleaned_data.get('titulo', 'REUNIÓN')
        lugar = self.cleaned_data.get('lugar', 'Comunidad')
        fecha_reunion = self.cleaned_data.get('fecha_reunion')
        tipo_asamblea = self.cleaned_data.get('tipo_asamblea', 'Ordinaria')
        director_debate = self.cleaned_data.get('director_debate', 'Vocero Autorizado')
        problematica = self.cleaned_data.get('problematica', 'No especificada')
        proyecto = self.cleaned_data.get('proyecto', 'No especificado')
        votos_favor = self.cleaned_data.get('votos_favor', 0)
        asistentes = self.cleaned_data.get('asistentes', '') # Nombres separados por comas
        
        # 🔑 AQUÍ EXTRAEMOS LOS CAMPOS DE LA INTERFAZ SIN ASIGNARLOS AL MODELO DIRECTAMENTE
        monto_estimado = self.cleaned_data.get('monto_estimado', '0,00')
        banco_receptor = self.cleaned_data.get('banco_receptor', 'No asignado')
        cuenta_comunal = self.cleaned_data.get('cuenta_comunal', 'No asignada')
        
        # Formatear la fecha para la redacción legal venezolana
        if fecha_reunion:
            fecha_texto = fecha_reunion.strftime("Hoy %d del mes de %B del año %Y, siendo las %I:%M %p")
        else:
            fecha_texto = "En la fecha correspondiente"

        # 🔑 COMPILACIÓN REDACCIONAL CONTEXTUAL (Formato Ministerio / SINCO)
        # Aquí incrustamos el monto, banco y cuenta directamente en la narrativa unificada
        acta.contenido = (
            f"{fecha_texto}, constituidos en asamblea de ciudadanos y ciudadanas en el lugar: {lugar}, "
            f"como Máxima Instancia de Deliberación y Decisión para el ejercicio del Poder Popular; reunidos "
            f"en mayoría simple de conformidad con el artículo 22 de la Ley Orgánica de los Consejos Comunales. "
            f"La presente sesión de carácter {tipo_asamblea.upper()} fue dirigida por el Director de Debate: {director_debate}, "
            f"procediendo a evaluar los puntos aprobados. Se identificó el problema central enfocado en '{problematica}', "
            f"determinando que la solución idónea es la ejecución del proyecto denominado '{proyecto}', por un monto "
            f"estimado de Bs. {monto_estimado}. Para los fines de la carga y asignación del recurso financiero en el "
            f"Sistema de Integración Comunal (SINCO), se ratifica que la cuenta bancaria de la organización "
            f"corresponde al banco {banco_receptor}, N° {cuenta_comunal}. Finalmente, evaluados los aportes de los "
            f"miembros mayoritarios del sector, y con la presencia de los ciudadanos ({asistentes}), los puntos de la "
            f"agenda quedan plenamente APROBADOS por una votación de {votos_favor} votos a favor."
        )

        if commit:
            acta.save()
        return acta

# ============================================
# 🆕 NUEVO: Formularios para Gestión de Proyectos
# ============================================

class ComiteForm(forms.ModelForm):
    """
    Formulario para crear y editar comités.
    """
    nombre = forms.CharField(
        label="Nombre del Comité",
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Comité de Finanzas Sector Norte'
        }),
        help_text="Nombre descriptivo del comité"
    )
    
    tipo_comite = forms.ChoiceField(
        choices=Comite.TIPO_COMITE_CHOICES,
        label="Tipo de Comité",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Seleccione el tipo de comité"
    )
    
    descripcion = forms.CharField(
        label="Descripción",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Descripción del comité y sus funciones...'
        }),
        help_text="Descripción opcional del comité"
    )
    
    vocero_principal = forms.ModelChoiceField(
        queryset=Habitante.objects.filter(is_deleted=False),
        label="Vocero Principal",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Persona responsable del comité (opcional)"
    )
    
    activo = forms.BooleanField(
        label="Comité Activo",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Desmarque si el comité está inactivo"
    )
    
    class Meta:
        model = Comite
        fields = ['nombre', 'tipo_comite', 'descripcion', 'vocero_principal', 'activo']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['nombre'].widget.attrs['readonly'] = False


class ProyectoForm(forms.ModelForm):
    """
    Formulario para crear y editar proyectos comunitarios.
    """
    nombre = forms.CharField(
        label="Nombre del Proyecto",
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Construcción de cancha deportiva'
        }),
        help_text="Nombre descriptivo del proyecto (máximo 200 caracteres)"
    )
    
    fecha_inicio = forms.DateField(
        label="Fecha de Inicio",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text="Fecha estimada de inicio del proyecto"
    )
    
    fecha_fin = forms.DateField(
        label="Fecha de Fin Estimada",
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text="Fecha estimada de finalización (opcional)"
    )
    
    descripcion = forms.CharField(
        label="Descripción del Proyecto",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Describa los objetivos, alcance y detalles del proyecto...'
        }),
        help_text="Descripción detallada del proyecto"
    )
    
    monto_estimado = forms.DecimalField(
        label="Monto Estimado (Bs.)",
        max_digits=12,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0',
            'placeholder': '0.00'
        }),
        help_text="Monto estimado en bolívares"
    )
    
    estatus = forms.ChoiceField(
        choices=Proyecto.ESTATUS_CHOICES,
        label="Estatus del Proyecto",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Estado actual del proyecto"
    )
    
    comite = forms.ModelChoiceField(
        queryset=Comite.objects.filter(is_deleted=False, activo=True),
        label="Comité Responsable",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Seleccione el comité encargado del proyecto",
        empty_label="-- Seleccione un comité --"
    )
    
    class Meta:
        model = Proyecto
        fields = ['nombre', 'fecha_inicio', 'fecha_fin', 'descripcion', 'monto_estimado', 'estatus', 'comite']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Si es un nuevo proyecto, preestablecer la fecha de inicio
        if not self.instance.pk:
            self.fields['fecha_inicio'].initial = date.today()
    
    def clean_fecha_fin(self):
        """Validar que la fecha de fin sea posterior a la fecha de inicio"""
        fecha_inicio = self.cleaned_data.get('fecha_inicio')
        fecha_fin = self.cleaned_data.get('fecha_fin')
        
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise forms.ValidationError(
                "La fecha de fin no puede ser anterior a la fecha de inicio."
            )
        return fecha_fin
    
    def clean_monto_estimado(self):
        """Validar que el monto sea positivo"""
        monto = self.cleaned_data.get('monto_estimado')
        if monto is not None and monto < 0:
            raise forms.ValidationError("El monto estimado debe ser un valor positivo.")
        return monto
    
    def save(self, commit=True):
        """Guardar con el usuario como creador"""
        instance = super().save(commit=False)
        if self.user and not instance.pk:
            instance.creado_por = self.user
        if commit:
            instance.save()
        return instance


class AsignarHabitanteForm(forms.ModelForm):
    """
    Formulario para asignar un habitante a un proyecto.
    """
    habitante = forms.ModelChoiceField(
        queryset=Habitante.objects.filter(is_deleted=False),
        label="Habitante",
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'data-placeholder': 'Buscar por nombre o cédula...'
        }),
        help_text="Seleccione el habitante a asignar"
    )
    
    rol = forms.ChoiceField(
        choices=ProyectoIntegrante.ROL_CHOICES,
        label="Rol en el Proyecto",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Rol que desempeñará el habitante en el proyecto"
    )
    
    observaciones = forms.CharField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Observaciones adicionales...'
        }),
        help_text="Observaciones sobre la asignación (opcional)"
    )
    
    class Meta:
        model = ProyectoIntegrante
        fields = ['habitante', 'rol', 'observaciones']
    
    def __init__(self, *args, **kwargs):
        self.proyecto = kwargs.pop('proyecto', None)
        super().__init__(*args, **kwargs)
        
        # Optimizar queryset con select_related
        self.fields['habitante'].queryset = self.fields['habitante'].queryset.select_related(
            'familia'
        )
    
    def clean_habitante(self):
        """Validar que el habitante no esté ya asignado al proyecto"""
        habitante = self.cleaned_data.get('habitante')
        
        if self.proyecto and habitante:
            # Verificar si ya está asignado
            existe = ProyectoIntegrante.objects.filter(
                proyecto=self.proyecto,
                habitante=habitante
            ).exists()
            
            if existe:
                raise forms.ValidationError(
                    f"Este habitante ya está asignado al proyecto."
                )
        
        return habitante
    
    def save(self, commit=True):
        """Guardar con el proyecto"""
        instance = super().save(commit=False)
        if self.proyecto:
            instance.proyecto = self.proyecto
        if commit:
            instance.save()
        return instance


# ============================================
# 🆕 NUEVO: Formularios para Gestión de Censos
# ============================================

from .models import Censo, CensoParticipante

class CensoForm(forms.ModelForm):
    """
    Formulario para crear y editar censos comunitarios.
    """
    nombre_censo = forms.CharField(
        label="Nombre del Censo",
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Censo Poblacional 2026'
        }),
        help_text="Nombre identificativo de la campaña de censo"
    )
    
    fecha_inicio = forms.DateField(
        label="Fecha de Inicio",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text="Fecha de inicio del censo"
    )
    
    fecha_fin = forms.DateField(
        label="Fecha de Cierre",
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text="Fecha de cierre estimada (opcional)"
    )
    
    descripcion = forms.CharField(
        label="Descripción",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Describa el objetivo y alcance del censo...'
        }),
        help_text="Descripción detallada del censo"
    )
    
    categoria_enfoque = forms.ChoiceField(
        choices=Censo.CATEGORIA_ENFOQUE_CHOICES,
        label="Categoría de Enfoque",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Seleccione la categoría principal del censo"
    )
    
    estatus = forms.ChoiceField(
        choices=Censo.ESTATUS_CHOICES,
        label="Estatus del Censo",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Estado actual del censo"
    )
    
    class Meta:
        model = Censo
        fields = ['nombre_censo', 'fecha_inicio', 'fecha_fin', 'descripcion', 'categoria_enfoque', 'estatus']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Si es un nuevo censo, preestablecer la fecha de inicio
        if not self.instance.pk:
            self.fields['fecha_inicio'].initial = date.today()
    
    def clean_fecha_fin(self):
        """Validar que la fecha de fin sea posterior a la fecha de inicio"""
        fecha_inicio = self.cleaned_data.get('fecha_inicio')
        fecha_fin = self.cleaned_data.get('fecha_fin')
        
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise forms.ValidationError(
                "La fecha de cierre no puede ser anterior a la fecha de inicio."
            )
        return fecha_fin
    
    def save(self, commit=True):
        """Guardar con el usuario como creador"""
        instance = super().save(commit=False)
        if self.user and not instance.pk:
            instance.creado_por = self.user
        if commit:
            instance.save()
        return instance


class AsignarParticipanteForm(forms.ModelForm):
    """
    Formulario para asignar un habitante a un censo.
    """
    habitante = forms.ModelChoiceField(
        queryset=Habitante.objects.filter(is_deleted=False),
        label="Habitante",
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'data-placeholder': 'Buscar por nombre o cédula...'
        }),
        help_text="Seleccione el habitante a registrar en el censo"
    )
    
    observaciones = forms.CharField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Observaciones adicionales...'
        }),
        help_text="Notas sobre la participación del habitante (opcional)"
    )
    
    class Meta:
        model = CensoParticipante
        fields = ['habitante', 'observaciones']
    
    def __init__(self, *args, **kwargs):
        self.censo = kwargs.pop('censo', None)
        super().__init__(*args, **kwargs)
        
        # Optimizar queryset con select_related
        self.fields['habitante'].queryset = self.fields['habitante'].queryset.select_related(
            'familia'
        ).order_by('nombre')
    
    def clean_habitante(self):
        """Validar que el habitante no esté ya registrado en el censo"""
        habitante = self.cleaned_data.get('habitante')
        
        if self.censo and habitante:
            # Verificar si ya está registrado
            existe = CensoParticipante.objects.filter(
                censo=self.censo,
                habitante=habitante
            ).exists()
            
            if existe:
                raise forms.ValidationError(
                    f"Este habitante ya está registrado en este censo."
                )
        
        return habitante
    
    def save(self, commit=True):
        """Guardar con el censo"""
        instance = super().save(commit=False)
        if self.censo:
            instance.censo = self.censo
        if commit:
            instance.save()
        return instance
        
