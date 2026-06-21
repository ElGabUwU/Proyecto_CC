
from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils.html import strip_tags
from datetime import date
import datetime
import re
from .models import Comite, Proyecto, ProyectoIntegrante
from .models import (
    Familia, Habitante, IngresoComunal, EgresoComunal, 
    ConstanciaResidencia, ActaReunion, CensoParticipante
)

ORGANISMOS_VENEZUELA_CHOICES = [
    ('', '-- Seleccione el Destino del Trámite --'),
    ('IVSS', 'Instituto Venezolano de los Seguros Sociales (IVSS)'),
    ('SAIME', 'Servicio Administrativo de Identificación, Migración y Extranjería (SAIME)'),
    ('INTT', 'Instituto Nacional de Transporte Terrestre (INTT)'),
    ('BANCO_PUBLICO', 'Banca Pública (Banco de Venezuela, del Tesoro, Bicentenario)'),
    ('BANCO_PRIVADO', 'Banca Privada (Banesco, Provincial, Mercantil, etc.)'),
    ('UNIV_EDUCACION', 'Institución Educativa / Universidades (UPTAI, UPEL, etc.)'),
    ('CORPOELEC', 'Corporación Eléctrica Nacional (CORPOELEC)'),
    ('CANTV', 'Compañía Anónima Nacional Teléfonos de Venezuela (CANTV)'),
    ('JUDICIAL_POLICIAL', 'Organismos Judiciales / Prefectura / Cuerpo Policial'),
    ('TRAMITE_LABORAL', 'Fines Laborales / Empresa Contratante'),
    ('MINISTERIO_PUBLICO', 'Ministerios u Órganos del Estado'),
]

FINALIDAD_RESIDENCIA_CHOICES = [
    ('', '-- Seleccione el Motivo de la Solicitud --'),
    ('APERTURA_CUENTA', 'APERTURA DE CUENTA BANCARIA'),
    ('INSCRIPCION_EDUCATIVA', 'INSCRIPCION EN INSTITUCIÓN EDUCATIVA / UNIVERSIDAD'),
    ('TRAMITES_LABORALES', 'TRÁMITES LABORALES / CONTRATACIÓN'),
    ('SOLICITUD_BECA', 'SOLICITUD DE BECA O AYUDA ECONÓMICA'),
    ('TRAMITES_SALUD', 'TRÁMITES DE SALUD / ASISTENCIA MÉDICA'),
    ('PREFECTURA_CIVIL', 'TRÁMITES CIVILES Y PREFECTURA'),
]
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
    
    observaciones = forms.CharField(
        required=False,
        label="Observaciones",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Observaciones adicionales...'
        }),
    )
    
    class Meta:
        model = IngresoComunal
        fields = ['fecha', 'tipo_ingreso', 'concepto', 'monto', 'soporte_digital', 'observaciones']
        widgets = {
            'tipo_ingreso': forms.Select(attrs={'class': 'form-control'}),
            'soporte_digital': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
        }
        labels = {
            'tipo_ingreso': 'Tipo de Ingreso',
            'soporte_digital': 'Soporte Digital',
        }
        help_texts = {
            'soporte_digital': 'Comprobante o soporte del egreso (PDF, imagen)',
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
    
    observaciones = forms.CharField(
        required=False,
        label="Observaciones",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Observaciones adicionales...'
        }),
    )
    
    class Meta:
        model = EgresoComunal
        fields = ['fecha', 'tipo_egreso', 'concepto', 'monto', 'beneficiario', 'soporte', 'observaciones']
        widgets = {
            'tipo_egreso': forms.Select(attrs={'class': 'form-control'}),
            'soporte': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
        }
        labels = {
            'tipo_egreso': 'Tipo de Egreso',
            'soporte': 'Soporte Digital',
        }
        help_texts = {
            'soporte': 'Comprobante o soporte del egreso (PDF, imagen)',
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
    """Formulario optimizado para el registro controlado de Constancias de Residencia"""
    
    familia = forms.ModelChoiceField(
        queryset=Familia.objects.filter(is_deleted=False).order_by('nombre_familia'),
        label="Seleccionar Grupo Familiar",
        help_text="Seleccione la familia para filtrar los integrantes autorizados."
    )
    
    # 🎯 CAMBIO A CHOICEFIELD: Motivos controlados de presentación en Venezuela
    finalidad = forms.ChoiceField(
        choices=FINALIDAD_RESIDENCIA_CHOICES,
        label="Título / Finalidad de la Constancia"
    )

    class Meta:
        model = ConstanciaResidencia
        fields = ['familia', 'habitante', 'fecha_documento', 'finalidad']
        widgets = {
            'fecha_documento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Aplicamos los estilos visuales uniformes de Bootstrap
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select text-black border-secondary', 'style': 'font-size: 14px;'})
            else:
                field.widget.attrs.update({'class': 'form-control text-black border-secondary', 'style': 'font-size: 14px;'})

        # El queryset inicial de habitantes arranca vacío hasta que AJAX actúe
        self.fields['habitante'].queryset = Habitante.objects.none()

        if 'familia' in self.data:
            try:
                familia_id = int(self.data.get('familia'))
                self.fields['habitante'].queryset = Habitante.objects.filter(familia_id=familia_id, is_deleted=False).order_by('nombre')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.familia:
            self.fields['habitante'].queryset = self.instance.familia.habitante_set.filter(is_deleted=False).order_by('nombre')

    def clean_fecha_documento(self):
        """Candado de seguridad: No fechas futuras ni mayores a 3 días de antigüedad"""
        fecha_doc = self.cleaned_data.get('fecha_documento')
        if fecha_doc:
            if fecha_doc > datetime.date.today():
                raise ValidationError("La fecha formal de la constancia no puede ser una fecha futura.")
            
            limite_pasado = datetime.date.today() - datetime.timedelta(days=3)
            if fecha_doc < limite_pasado:
                raise ValidationError("La fecha de emisión no puede ser mayor a 3 días desde la fecha de solicitud.")
        return fecha_doc

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.generado_por = self.user
            
        # 🎯 TRADUCCIÓN DE LA FINALIDAD: Convertimos el código del Choice al String real legible para el PDF
        finalidad_codigo = self.cleaned_data.get('finalidad')
        finalidad_legible = dict(FINALIDAD_RESIDENCIA_CHOICES).get(finalidad_codigo, finalidad_codigo)
        instance.finalidad = finalidad_legible.upper()
        
        # Compilación del bloque HTML de la constancia antes de almacenar
        instance.texto_constancia = self.generar_contenido_constancia(instance)
        
        if commit:
            instance.save()
        return instance

    def generar_contenido_constancia(self, instance):
        """Compila dinámicamente el cuerpo formal del reporte de residencia"""
        habitante = instance.habitante
        
        # 🎯 CORRECCIÓN: Extraemos la familia directamente desde el habitante relacionado
        familia = getattr(habitante, 'familia', None)
        
        nombre_solicitante = f"{habitante.nombre} {habitante.apellido}".upper()
        cedula_solicitante = f"V-{habitante.cedula}" if habitante.cedula else "S/C"
        
        # Validación de seguridad por si el habitante no tiene asignada una familia todavía
        nombre_familia = familia.nombre_familia.upper() if familia else "SIN NÚCLEO ASIGNADO"
        direccion_familia = f"SECTOR MANUEL PULIDO MÉNDEZ, CALLE PRINCIPAL, CASA N° {familia.id}" if familia else "URBANIZACIÓN MANUEL PULIDO MÉNDEZ"
        
        total_integrantes = Habitante.objects.filter(familia=familia, is_deleted=False).count() if familia else 1
        
        contenido_html = f"""
            <p style="text-align: justify; line-height: 1.6; margin-bottom: 15px;">
                Quienes suscriben, miembros voceros de la Unidad de Contraloría Social y de la Unidad Ejecutiva 
                pertenecientes al <strong>CONSEJO COMUNAL MANUEL PULIDO MÉNDEZ</strong>, 
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
                <strong>FINALIDAD:</strong> Constancia que se expide a petición de la parte interesada para: <strong>{instance.finalidad}</strong>.
            </p>
        """
        return contenido_html

from django import forms
from django.utils import timezone
from .models import ActaReunion

import re
from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import date
from .models import ActaReunion

class ActaReunionForm(forms.ModelForm):
    # 1. Campos explícitos para la interfaz estética del formulario (No alteran el modelo)
    titulo = forms.CharField(
        max_length=200,
        label="Título de la Asamblea",
        widget=forms.TextInput(attrs={
            'placeholder': 'Ej. Acta de Asamblea General Extraordinaria'
        })
    )
    fecha_reunion = forms.DateTimeField(
        initial=timezone.now,
        label="Fecha y Hora de la Reunión",
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local'
        })
    )
    lugar = forms.CharField(
        max_length=200,
        label="Lugar del Encuentro",
        widget=forms.TextInput(attrs={
            'placeholder': 'Ej. Cancha Techada del Sector Manuel Pulido Méndez'
        })
    )
    director_debate = forms.CharField(
        max_length=100,
        label="Director de Debate",
        widget=forms.TextInput(attrs={
            'placeholder': 'Nombre del vocero que dirige el debate'
        })
    )
    tipo_asamblea = forms.ChoiceField(
        choices=[('ORDINARIA', 'Ordinaria'), ('EXTRAORDINARIA', 'Extraordinaria')],
        label="Tipo de Asamblea",
        widget=forms.Select()
    )
    
    problema_identificado = forms.CharField(
        label="Problemática Identificada (Máx. 150 palabras)",
        widget=forms.Textarea(attrs={
            'rows': '3',
            'placeholder': 'Describa detalladamente la problemática planteada por la comunidad...'
        })
    )
    
    propuesta_solucion = forms.CharField(
        label="Propuesta de Solución / Proyecto (Máx. 150 palabras)",
        widget=forms.Textarea(attrs={
            'rows': '3',
            'placeholder': 'Detalle el nombre del proyecto o acciones aprobadas para solventar...'
        })
    )
    
    # 🎯 VALIDACIÓN DE MONTO: Obliga a que sea un monto estrictamente positivo
    monto_estimado = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0.00,  # Bloquea números negativos
        required=False,
        label="Monto Estimado de Financiamiento (Bs.)",
        widget=forms.NumberInput(attrs={
            'placeholder': '0.00 (Dejar vacío si no requiere financiamiento)',
            'step': '0.01'
        })
    )
    banco_receptor = forms.CharField(
        max_length=100,
        required=False,
        label="Banco Receptor",
        widget=forms.TextInput(attrs={
            'placeholder': 'Ej. Banco de Venezuela (Si aplica)'
        })
    )
    
    cuenta_bancaria = forms.CharField(
        max_length=20,
        required=False,
        label="Cuenta Bancaria Comunal",
        widget=forms.TextInput(attrs={
            'placeholder': 'Ingrese los 20 dígitos',
            'maxlength': '20',
            'pattern': '\\d{20}', # Fuerza validación HTML5 de 20 dígitos numéricos
            'class': 'form-control bg-dark text-white border-secondary'
        })
    )
    votos_favor = forms.IntegerField(
        min_value=0,
        label="Votos a Favor",
        widget=forms.NumberInput(attrs={
            'placeholder': 'Cantidad de ciudadanos que aprobaron'
        })
    )
    asistentes = forms.CharField(
        label="Listado de Asistentes",
        widget=forms.Textarea(attrs={
            'rows': '3',
            'placeholder': 'Nombre y apellido de los asistentes separados por comas...'
        })
    )

    class Meta:
        model = ActaReunion
        fields = ['titulo', 'fecha_reunion', 'lugar', 'asistentes']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Aplicamos de forma dinámica tus estilos unificados oscuros
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select bg-dark text-white border-secondary'})
            else:
                field.widget.attrs.update({'class': 'form-control bg-dark text-white border-secondary'})

    # ==========================================================
    # 🔒 SECCIÓN DE CANDADOS DE VALIDACIÓN (CLEAN)
    # ==========================================================
    def clean_titulo(self):
        data = strip_tags(self.cleaned_data.get('titulo', '')).strip()
        if len(data) < 10:
            raise ValidationError("El título es demasiado corto. Debe ser descriptivo.")
        return data

    def clean_lugar(self):
        data = self.cleaned_data.get('lugar', '').strip()
        # Mínimo 5 caracteres y no puede ser solo números o símbolos
        if len(data) < 5 or not re.search(r'[a-zA-Z]', data):
            raise ValidationError("El lugar debe ser una ubicación válida (ej. Cancha Techada).")
        return data.upper()

    def clean_director_debate(self):
        data = strip_tags(self.cleaned_data.get('director_debate', '')).strip()
        if re.search(r'\d', data):
            raise ValidationError("El nombre no puede contener números.")
        return data.upper()

    def clean_problema_identificado(self):
        data = self.cleaned_data.get('problema_identificado', '').strip()
        # 1. Validación de longitud
        if len(data) < 20:
            raise ValidationError("La problemática es demasiado breve. Explique detalladamente.")
        
        # 2. Detector de basura: "asdf", "1234", repetición excesiva
        # Si tiene menos de 6 caracteres únicos, es probablemente basura repetitiva
        if len(set(data.lower())) < 6:
            raise ValidationError("El contenido parece ser basura o texto repetitivo sin sentido.")
            
        return data

    def clean_propuesta_solucion(self):
        data = self.cleaned_data.get('propuesta_solucion', '').strip()
        # Similar a la problemática
        if len(data) < 20:
            raise ValidationError("La propuesta debe ser detallada (mínimo 20 caracteres).")
        
        # Prohibir palabras que parecen generadas al azar (ej: "asdfg")
        if len(set(data.lower())) < 6:
            raise ValidationError("Por favor, describa el proyecto de forma coherente.")
            
        return data

    def clean_cuenta_bancaria(self):
        cuenta = self.cleaned_data.get('cuenta_bancaria', '')
        if cuenta:
            # Limpiamos cualquier carácter que no sea dígito
            cuenta = re.sub(r'\D', '', cuenta)
            if len(cuenta) != 20:
                raise ValidationError("La cuenta bancaria debe tener exactamente 20 dígitos.")
        return cuenta

    def clean_asistentes(self):
        data = strip_tags(self.cleaned_data.get('asistentes', '')).strip()
        if len(data) < 10 or ',' not in data:
            raise ValidationError("Formato inválido. Asegúrese de incluir nombres separados por comas.")
        return data

    # ==========================================================
    # 💾 PROCESAMIENTO CORPORATIVO / S.I.N.C.O.
    # ==========================================================
    def save(self, commit=True):
        acta = super().save(commit=False)
        acta.generado_por = self.user
        
        titulo = self.cleaned_data.get('titulo', 'REUNIÓN')
        lugar = self.cleaned_data.get('lugar', 'Comunidad')
        fecha_reunion = self.cleaned_data.get('fecha_reunion')
        tipo_asamblea = self.cleaned_data.get('tipo_asamblea', 'Ordinaria')
        director_debate = self.cleaned_data.get('director_debate', 'Vocero Autorizado')
        
        problematica = self.cleaned_data.get('problema_identificado', 'No especificada')
        proyecto = self.cleaned_data.get('propuesta_solucion', 'No especificado')
        votos_favor = self.cleaned_data.get('votos_favor', 0)
        asistentes = self.cleaned_data.get('asistentes', '')
        
        monto_estimado = self.cleaned_data.get('monto_estimado') or '0,00'
        banco_receptor = self.cleaned_data.get('banco_receptor', 'NO ASIGNADO')
        cuenta_comunal = self.cleaned_data.get('cuenta_bancaria')
        # Si existe, lo convertimos a string; si es None, asignamos mensaje
        cuenta_str = str(cuenta_comunal) if cuenta_comunal else "NO ASIGNADA"
        
        # Guardamos en el modelo (asumiendo que el campo se llama cuenta_bancaria)
        acta.cuenta_bancaria = cuenta_comunal
        meses = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
            7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        
        if fecha_reunion:
            hora_12 = fecha_reunion.strftime("%I:%M %p")
            fecha_texto = f"Hoy {fecha_reunion.day} del mes de {meses[fecha_reunion.month]} del año {fecha_reunion.year}, siendo las {hora_12}"
        else:
            fecha_texto = "En la fecha correspondiente"

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

# =========================================================================
# 🪪 FORMULARIO: CARTA DE BUENA CONDUCTA
# =========================================================================
class BuenaConductaForm(forms.Form):
    """Formulario unificado y blindado para la solicitud de Carta de Buena Conducta"""
    
    familia = forms.ModelChoiceField(
        queryset=Familia.objects.filter(is_deleted=False).order_by('nombre_familia'),
        label="Seleccionar Grupo Familiar",
        help_text="Seleccione la familia para filtrar los ciudadanos de manera ágil."
    )
    habitante = forms.ModelChoiceField(
        queryset=Habitante.objects.none(),
        label="Cargar Ciudadano",
        empty_label="Primero seleccione una familia..."
    )
    
    fecha_documento = forms.DateField(
        label="Fecha del Documento",
        initial=timezone.now,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    # 🎯 NUEVOS CAMPOS: Cuantificadores exactos numéricos
    tiempo_residencia_anios = forms.IntegerField(
        label="Años de Residencia en el Sector",
        min_value=0,
        max_value=120,
        initial=1,
        widget=forms.NumberInput(attrs={'placeholder': 'Ej. 5'})
    )
    tiempo_residencia_meses = forms.IntegerField(
        label="Meses Adicionales (Opcional)",
        min_value=0,
        max_value=11,
        initial=0,
        widget=forms.NumberInput(attrs={'placeholder': 'Ej. 0'})
    )
    
    # 🎯 NUEVO CAMPO: Selector cerrado institucional
    organismo_destino = forms.ChoiceField(
        choices=ORGANISMOS_VENEZUELA_CHOICES,
        label="Organismo o Destino del Trámite"
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Inyección dinámica de clases Bootstrap
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select text-black border-secondary', 'style': 'font-size: 14px;'})
            else:
                field.widget.attrs.update({'class': 'form-control text-black border-secondary', 'style': 'font-size: 14px;'})
                
        # Lógica AJAX para el encadenamiento dinámico de integrantes
        if 'familia' in self.data:
            try:
                familia_id = int(self.data.get('familia'))
                self.fields['habitante'].queryset = Habitante.objects.filter(familia_id=familia_id, is_deleted=False).order_by('nombre')
            except (ValueError, TypeError):
                pass
        elif self.initial.get('familia'):
            familia_id = self.initial.get('familia')
            self.fields['habitante'].queryset = Habitante.objects.filter(familia_id=familia_id, is_deleted=False).order_by('nombre')

    def clean(self):
        cleaned_data = super().clean()
        anios = cleaned_data.get('tiempo_residencia_anios')
        meses = cleaned_data.get('tiempo_residencia_meses')

        # Control para evitar registros vacíos en cero absoluto
        if anios == 0 and meses == 0:
            raise ValidationError("El tiempo de residencia ingresado en el sector no puede ser de 0 meses.")
        return cleaned_data

    def clean_fecha_documento(self):
        """Validar que la fecha formal no sea futura ni exceda los 3 días de antigüedad"""
        fecha_doc = self.cleaned_data.get('fecha_documento')
        if fecha_doc:
            if fecha_doc > datetime.date.today():
                raise ValidationError("La fecha formal de la constancia no puede ser una fecha futura.")
            
            limite_pasado = datetime.date.today() - datetime.timedelta(days=3)
            if fecha_doc < limite_pasado:
                raise ValidationError("La fecha de emisión no puede ser mayor a 3 días desde la solicitud de la constancia.")
                
        return fecha_doc
class ConstanciaFallecidoForm(forms.Form):
    """Formulario para la Constancia de Residencia Post-Mortem (Fallecidos) con Blindaje de Seguridad"""
    familia = forms.ModelChoiceField(
        queryset=Familia.objects.filter(is_deleted=False).order_by('nombre_familia'),
        label="Seleccionar Grupo Familiar",
        empty_label="Elija una familia..."
    )
    habitante = forms.ModelChoiceField(
        queryset=Habitante.objects.none(),
        label="Cargar Ciudadano Fallecido",
        empty_label="Primero seleccione una familia..."
    )
    fecha_deceso = forms.DateField(
        label="Fecha del Lamentable Deceso",
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    solicitante_defuncion = forms.CharField(
        label="Familiar Solicitante / Declarante",
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Ej. María Pérez'})
    )
    solicitante_cedula = forms.CharField(
        label="Cédula del Familiar Solicitante",
        max_length=15,
        widget=forms.TextInput(attrs={'placeholder': 'Ej. 14234567'})
    )
    relacion_parentesco = forms.CharField(
        label="Parentesco con el Difunto",
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': 'Ej. ESPOSA, HIJA, HERMANO'})
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select text-black border-secondary', 'style': 'font-size: 14px;'})
            else:
                field.widget.attrs.update({'class': 'form-control text-black border-secondary', 'style': 'font-size: 14px;'})
                
        if 'familia' in self.data:
            try:
                familia_id = int(self.data.get('familia'))
                self.fields['habitante'].queryset = Habitante.objects.filter(familia_id=familia_id, is_deleted=False).order_by('nombre')
            except (ValueError, TypeError):
                pass
        elif self.initial.get('familia'):
            family_id = self.initial.get('familia')
            self.fields['habitante'].queryset = Habitante.objects.filter(familia_id=family_id, is_deleted=False).order_by('nombre')
    
    # 🔒 BLINDAJE: Solicitante / Declarante
    def clean_solicitante_defuncion(self):
        nombre = self.cleaned_data.get('solicitante_defuncion', '').strip().upper()
        
        # 1. Validación de longitud mínima
        if len(nombre) < 6:
            raise ValidationError("El nombre del solicitante es demasiado corto. Introduzca nombre y apellido válidos.")
            
        # 2. Expresión regular para admitir solo letras, espacios y acentos venezolanos
        if not re.match(r'^[A-ZÁÉÍÓÚÑ ]+$', nombre):
            raise ValidationError("El nombre del solicitante solo debe contener caracteres alfabéticos.")
            
        # 3. Escudo anti-repeticiones (Evita trampas como "AAAAAA BBBBBB")
        if re.search(r'(.)\1{3,}', nombre):
            raise ValidationError("El nombre introducido contiene demasiados caracteres repetidos seguidos.")
            
        return nombre

    # 🔒 BLINDAJE: Parentesco
    def clean_relacion_parentesco(self):
        parentesco = self.cleaned_data.get('relacion_parentesco', '').strip().upper()
        
        if len(parentesco) < 3:
            raise ValidationError("La relación de parentesco es demasiado corta (Ej: HIJO, CONYUGE, MADRE).")
            
        if not re.match(r'^[A-ZÁÉÍÓÚÑ /-]+$', parentesco):
            raise ValidationError("El parentesco no debe contener números ni caracteres especiales.")
            
        return parentesco

    # 🔒 BLINDAJE: Cédula de Identidad
    def clean_solicitante_cedula(self):
        # Limpiamos puntos, guiones y letras de origen (V-, E-) si el usuario las pone
        cedula = self.cleaned_data.get('solicitante_cedula', '').strip().upper()
        cedula = cedula.replace('.', '').replace('-', '').replace('V', '').replace('E', '').strip()
        
        # 1. Validar que sean solo dígitos numéricos
        if not cedula.isdigit():
            raise ValidationError("La cédula del solicitante debe contener únicamente números.")
            
        # 2. Rango lógico de cédulas en Venezuela (entre 500.000 y 45.000.000 para personas aptas para declarar)
        num_cedula = int(cedula)
        if num_cedula < 500000 or num_cedula > 45000000:
            raise ValidationError("El número de cédula introducido no pertenece a un rango válido en el territorio nacional.")
            
        # 3. Evitar patrones basura como "12345678" o "1111111"
        if cedula in ["12345678", "87654321"] or len(set(cedula)) == 1:
            raise ValidationError("Número de cédula inválido o genérico detectado.")
            
        return cedula

    # 🔒 BLINDAJE: Consistencia Cronológica
    def clean_fecha_deceso(self):
        fecha_dec = self.cleaned_data.get('fecha_deceso')
        if fecha_dec:
            # 1. Evitar viajes en el tiempo
            if fecha_dec > date.today():
                raise ValidationError("La fecha del deceso no puede ser una fecha en el futuro.")
            
            # 2. Límite de antigüedad legal/comunal (60 días atrás)
            limite_pasado = date.today() - datetime.timedelta(days=60)
            if fecha_dec < limite_pasado:
                raise ValidationError("La fecha del deceso no puede superar los 60 días de antigüedad desde la solicitud de esta constancia.")
                
        return fecha_dec
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
            'placeholder': 'Describa los objetivos, alcance y detalles del proyecto...',
            'maxlength': '1000',
            'id': 'id_descripcion_proyecto'
        }),
        help_text="Descripción detallada del proyecto (máximo 1000 caracteres)"
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
            'placeholder': 'Describa el objetivo y alcance del censo...',
            'maxlength': '1000',
            'id': 'id_descripcion_censo'
        }),
        help_text="Descripción detallada del censo (máximo 1000 caracteres)"
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
        
        
# REPORTE FORM
class ReporteDemograficoForm(forms.Form):
    """
    Formulario de control y sanitización avanzada para la 
    configuración de Reportes Demográficos.
    """
    titulo_reporte = forms.CharField(
        label="Nombre del Reporte",
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': 'Ej: CENSO DE NIÑOS MAYORES A 15 AÑOS'
        }),
        help_text="Escriba un nombre descriptivo para identificarlo en el historial."
    )
    filtro_genero = forms.ChoiceField(
        choices=[
            ('TODOS', 'Todos (Masculino y Femenino)'),
            ('M', 'Solo Masculino'),
            ('F', 'Solo Femenino')
        ],
        widget=forms.Select(attrs={'class': 'form-select bg-dark text-white border-secondary'})
    )
    filtro_edad = forms.ChoiceField(
        choices=[
            ('TODOS', 'Todas las edades (Población general)'),
            ('MENOR_12', 'Niños (Menores a 12 años)'),
            ('MENOR_16', 'Adolescentes (Menores a 16 años)'),
            ('TERCERA_EDAD', 'Adultos Mayores / 3ra Edad (>= 60 años)')
        ],
        widget=forms.Select(attrs={'class': 'form-select bg-dark text-white border-secondary'})
    )

    def clean_titulo_reporte(self):
        titulo = self.cleaned_data.get('titulo_reporte', '').strip()

        # 🔒 1. Validación de longitud mínima para que tenga sentido semántico
        if len(titulo) < 6:
            raise forms.ValidationError("El nombre del reporte es demasiado corto. Debe tener al menos 6 caracteres.")

        # 🔒 2. Evitar que introduzcan solo números o símbolos maliciosos
        if re.match(r'^[0-9\W_]+$', titulo):
            raise forms.ValidationError("El nombre del reporte no puede contener únicamente números o símbolos.")

        # 🔒 3. Sanitización institucional: Guardar limpio y en MAYÚSCULAS
        return titulo.upper()
