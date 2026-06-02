
# ============================================
# 🆕 NUEVO: Formularios para Gestión Comunitaria
# ============================================
from django import forms
from django.utils import timezone
import datetime
import re
from .models import Familia, Habitante, IngresoComunal, EgresoComunal, ConstanciaResidencia, ActaReunion
import re
from django.core.exceptions import ValidationError
class FamiliaForm(forms.ModelForm):
    """
    Formulario para crear y editar familias (viviendas) en la comunidad.
    Sincronizado con el nuevo modelo unificado.
    """
    nombre_familia = forms.CharField(
        label="Nombre de la Familia / Grupo",
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Familia Rodríguez Peña'
        }),
        help_text="Un nombre identificativo para el grupo familiar o vivienda"
    )
    
    vivienda = forms.CharField(
        label="Número o Tipo de Vivienda",
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Casa Nro. 45 / Apto 3-B'
        }),
        help_text="Identificación física del inmueble"
    )
    
    direccion = forms.CharField(
        label="Dirección Completa",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Calle, avenida, sector, punto de referencia...'
        }),
        help_text="Ubicación detallada dentro del ámbito geográfico del consejo comunal"
    )
    
    catastro = forms.CharField(
        label="Código Catastral",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: CL-2026-XXXX (Opcional)'
        }),
        help_text="Código catastral o de registro de la propiedad si se posee"
    )
    
    observaciones = forms.CharField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Condición de la vivienda, hacinamiento, observaciones adicionales...'
        }),
        help_text="Notas importantes sobre el núcleo familiar"
    )
    
    class Meta:
        model = Familia
        fields = ['nombre_familia', 'vivienda', 'direccion', 'catastro', 'observaciones']   
         


class HabitanteForm(forms.ModelForm):
    """
    Formulario refactorizado para crear y editar habitantes.
    Integra los datos de identidad y socioeconómicos, eliminando la tabla Person.
    """
    
    # Relación con la vivienda, filtrando solo las familias activas
    familia = forms.ModelChoiceField(
        queryset=Familia.objects.filter(is_deleted=False),
        label="Familia / Hogar",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Seleccione la familia a la que pertenece el habitante"
    )
    
    # -------------------------------------------------------------------------
    # CAMPOS DE IDENTIDAD (Anteriormente heredados de Person)
    # -------------------------------------------------------------------------
    cedula = forms.CharField(
        max_length=20,
        label="Cédula de Identidad",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: V-12345678'
        }),
        help_text="Ingrese el documento de identidad del ciudadano"
    )
    
    nombre = forms.CharField(
        max_length=100,
        label="Nombres",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombres completos'
        })
    )
    
    apellido = forms.CharField(
        max_length=100,
        label="Apellidos",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apellidos completos'
        })
    )
    
    fecha_nacimiento = forms.DateField(
        label="Fecha de Nacimiento",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    genero = forms.ChoiceField(
        choices=Habitante.GENERO_CHOICES,
        label="Género / Sexo",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    es_jefe_familia = forms.BooleanField(
        required=False,
        label="¿Es Jefe de Familia?",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Marque esta casilla si esta persona es el sustento o líder principal de la vivienda"
    )
    
    # -------------------------------------------------------------------------
    # CAMPOS SOCIOECONÓMICOS (Datos del Habitante)
    # -------------------------------------------------------------------------
    nivel_educativo = forms.ChoiceField(
        choices=Habitante.NIVEL_EDUCATIVO_CHOICES,
        required=False,
        label="Nivel Educativo",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Último nivel educativo alcanzado"
    )
    
    ocupacion = forms.CharField(
        max_length=100,
        required=False,
        label="Ocupación",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Estudiante, Agricultor, Ama de casa, Comerciante...'
        }),
        help_text="Ocupación o profesión principal"
    )
    
    ingresos_mensuales = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Ingresos Mensuales (Bs.)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        }),
        help_text="Ingresos mensuales aproximados del habitante (opcional)"
    )
    
    condiciones_salud = forms.CharField(
        required=False,
        label="Condiciones de Salud",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Ej: Hipertensión, Diabetes, Asma, Discapacidad motora o ninguna...'
        }),
        help_text="Condiciones de salud o patologías crónicas importantes (opcional)"
    )
    
    class Meta:
        model = Habitante
        # Mapeo exacto de los campos reales que se guardarán en la tabla 'habitantes'
        fields = [
            'familia', 'cedula', 'nombre', 'apellido', 'fecha_nacimiento', 
            'genero', 'es_jefe_familia', 'nivel_educativo', 'ocupacion', 
            'ingresos_mensuales', 'condiciones_salud'
        ]
    
    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        if cedula:
            cedula_clean = cedula.strip().upper()
            # Valida formato V-12345678 o E-12345678
            if not re.match(r'^[VE]-\d{6,8}$', cedula_clean):
                raise ValidationError(
                    "Formato de cédula inválido. Use: V-12345678 o E-12345678"
                )
            self.cleaned_data['cedula'] = cedula_clean
        return cedula


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
            'placeholder': 'Ej: Aporte mensual familia Pérez'
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
        model = IngresoComunal
        fields = ['fecha', 'tipo_ingreso', 'concepto', 'monto', 'soporte_digital', 'observaciones']
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
    
    def clean_fecha(self):
        """Validar que la fecha no sea futura"""
        fecha = self.cleaned_data.get('fecha')
        if fecha and fecha > datetime.date.today():
            raise ValidationError("La fecha del ingreso no puede ser futura.")
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
        """Validar que la fecha no sea futura"""
        fecha = self.cleaned_data.get('fecha')
        if fecha and fecha > datetime.date.today():
            raise ValidationError("La fecha del egreso no puede ser futura.")
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
        help_text="Seleccione la familia para emitir la constancia."
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
            'placeholder': 'Ej: Para tramitar apertura de cuenta bancaria / Inscripción universitaria...'
        }),
        help_text="Especifique el motivo de la solicitud."
    )
    
    class Meta:
        model = ConstanciaResidencia
        fields = ['habitante', 'fecha_documento', 'finalidad']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.generado_por = self.user
        
        # 💡 SOLUCIÓN: Usar campos correctos (nombre, apellido, cedula) y evitar caídas en la BD
        instance.contenido = self.generar_contenido_constancia(instance)
        
        if commit:
            instance.save()
        return instance
    
    def generar_contenido_constancia(self, constancia):
        """Generar el contenido HTML seguro con la semántica del modelo actual"""
        # 🆕 CORRECCIÓN: Accedemos a la familia a través del habitante solicitante
        familia = constancia.habitante.familia 
        
        # Obtenemos directamente los datos del habitante que solicita la constancia
        # para que sea verdaderamente nominal e individual
        solicitante = constancia.habitante
        nombre_solicitante = f"{solicitante.nombre} {solicitante.apellido}"
        cedula_solicitante = solicitante.cedula
        
        # Mantenemos las estadísticas de la familia para el contenido
        total_integrantes = familia.habitantes.filter(is_deleted=False).count() if familia else 0
        nombre_familia = familia.nombre_familia if familia else "S/D"
        direccion_familia = getattr(familia, 'direccion', 'Comunidad Manuel Pulido Méndez') if familia else "Comunidad Manuel Pulido Méndez"
        
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
                <p style="margin: 4px 0;"><strong>CÉDULA DE IDENTIDAD:</strong> V-{cedula_solicitante}</p>
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

class ActaReunionForm(forms.ModelForm):
    """
    Formulario depurado para asambleas del consejo comunal.
    """
    class Meta:
        model = ActaReunion
        fields = ['titulo', 'fecha_reunion', 'lugar', 'asistentes', 'contenido', 'acuerdos']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-secondary', 'placeholder': 'Ej: Asamblea General Extraordinaria'}),
            'fecha_reunion': forms.DateTimeInput(attrs={'class': 'form-control bg-dark text-white border-secondary', 'type': 'datetime-local'}),
            'lugar': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-secondary', 'placeholder': 'Ej: Cancha Deportiva del Sector'}),
            'asistentes': forms.Textarea(attrs={'class': 'form-control bg-dark text-white border-secondary', 'rows': 3, 'placeholder': 'Nombres o número de cédulas de los voceros...'}),
            'contenido': forms.Textarea(attrs={'class': 'form-control bg-dark text-white border-secondary', 'rows': 5, 'placeholder': 'Describa los puntos clave tratados...'}),
            'acuerdos': forms.Textarea(attrs={'class': 'form-control bg-dark text-white border-secondary', 'rows': 3, 'placeholder': 'Decisiones tomadas en la asamblea...'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.generado_por = self.user
        
        # Mantenemos el formateador dinámico para el PDF histórico
        instance.contenido_formateado = self.formatear_contenido_acta(instance)
        
        if commit:
            instance.save()
        return instance

    def formatear_contenido_acta(self, acta):
        """Formatear de forma elegante la asamblea"""
        return f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h3 style="margin-bottom: 2px;">CONSEJO COMUNAL MANUEL PULIDO MÉNDEZ</h3>
                <h4 style="margin-top: 0; color: #475569;">{acta.titulo}</h4>
            </div>
            <p><strong>LUGAR Y FECHA:</strong> {acta.lugar} - {acta.fecha_reunion.strftime('%d/%m/%Y %I:%M %p')}</p>
            <hr style="border: 0; border-top: 1px solid #cbd5e1;">
            <p><strong>PUNTOS DISCUTIDOS:</strong></p>
            <div style="white-space: pre-line; text-align: justify; padding-left: 10px;">{acta.contenido}</div>
        </div>
        """
        
        return contenido


# ============================================
# 🆕 NUEVO: Formularios para Gestión de Proyectos
# ============================================

from .models import Comite, Proyecto, ProyectoIntegrante

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
            from datetime import date
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
            from datetime import date
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
        
