
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
         
    def clean_telefono_contacto(self):
        """Validar formato de teléfono venezolano"""
        telefono = self.cleaned_data.get('telefono_contacto')
        if telefono:
            # Formato: +58 412 1234567 o 0412-1234567
            pattern = r'^(\+58\s?\d{3}\s?\d{7}|04\d{2}[-.]?\d{7})$'
            if not re.match(pattern, telefono.replace(' ', '').replace('-', '').replace('.', '')):
                raise ValidationError(
                    "Formato de teléfono inválido. Use: +584121234567 o 0412-1234567"
                )
        return telefono
    
    def clean_jefe_familia(self):
        """Validar que el jefe de familia no sea ya jefe de otra familia"""
        jefe_familia = self.cleaned_data.get('jefe_familia')
        if jefe_familia:
            # Verificar si ya es jefe de otra familia (excluyendo esta si estamos editando)
            familias_existentes = Familia.objects.filter(jefe_familia=jefe_familia)
            if self.instance and self.instance.pk:
                familias_existentes = familias_existentes.exclude(pk=self.instance.pk)
            
            if familias_existentes.exists():
                raise ValidationError(
                    f"{jefe_familia.name} {jefe_familia.surname} ya es jefe de otra familia."
                )
        return jefe_familia


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
    
    def clean_document_number(self):
        """Validar formato de cédula venezolana"""
        document_number = self.cleaned_data.get('document_number')
        type_document = self.cleaned_data.get('type_document')
        
        if document_number and type_document:
            # Para cédula venezolana: V-12345678 o E-12345678
            if type_document == 'V':
                pattern = r'^[VE]-\d{6,8}$'
                if not re.match(pattern, document_number):
                    raise ValidationError(
                        "Formato de cédula venezolana inválido. Use: V-12345678 o E-12345678"
                    )
        return document_number


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
    
    soporte = forms.FileField(
        required=False,
        label="Soporte",
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.jpg,.jpeg,.png'
        }),
        help_text="Factura, recibo o comprobante del egreso"
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