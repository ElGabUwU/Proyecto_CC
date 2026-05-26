from django import forms
import datetime
import re
from .models import Courses, Levels, Person, TodoItem, User, Tutors, STAFF_POSITION_LIST_PREDIFINED, Units, Group_Levels, Students, Testing

class BasePersonValidationForm(forms.ModelForm):
    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth and date_of_birth > datetime.date.today():
            raise forms.ValidationError("La fecha de nacimiento no puede ser mayor al día de hoy.")
        return date_of_birth

    def clean_document_number(self):
        document_number = self.cleaned_data.get('document_number')
        if document_number and not re.match(r'^[0-9.]+$', document_number):
            raise forms.ValidationError("El número de documento solo puede contener números y puntos.")
        return document_number

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name and not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$', name):
            raise forms.ValidationError("El nombre solo puede contener letras y espacios.")
        return name

    def clean_surname(self):
        surname = self.cleaned_data.get('surname')
        if surname and not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$', surname):
            raise forms.ValidationError("El apellido solo puede contener letras y espacios.")
        return surname

    def clean_telephone_number(self):
        telephone = self.cleaned_data.get('telephone_number')
        TELEFONO_REGEX = re.compile(r'^\+(58|57|54|591|55|56|506|53|1(?:809|829|849|787|939)|593|503|34|1|502|504|52|505|507|595|51|598)(?:[0-9]{7,11})$')
        if telephone and not TELEFONO_REGEX.match(telephone):
            raise forms.ValidationError("El número de teléfono debe tener el formato +[código][número], ej: +584121234567")
        return telephone

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', email):
            raise forms.ValidationError("Ingrese un correo electrónico válido.")
        return email

    def clean_progenitor_document_number(self):
        doc = self.cleaned_data.get('progenitor_document_number')
        if doc and not re.match(r'^[A-Za-z0-9.]+$', doc):
            raise forms.ValidationError("El documento del representante solo puede contener letras, números y puntos.")
        return doc

class DocenteForm(BasePersonValidationForm):
    staff_position = forms.ChoiceField(label='Cargo', choices=STAFF_POSITION_LIST_PREDIFINED, widget=forms.Select(attrs={'class': 'form-control'}))
    document_number = forms.CharField(label='Número de Documento', max_length=20, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escriba su número de documento'}))
    name = forms.CharField(label='Nombre', max_length=50, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escriba sus nombres'}))
    surname = forms.CharField(label='Apellido', max_length=50, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escriba sus apellidos'}))
    telephone_number = forms.CharField(label='Teléfono', max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escriba el número de teléfono'}))
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Escriba su Correo Electrónico'}))
    date_of_birth = forms.DateField(label='Fecha de Nacimiento', widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))

    class Meta:
        model = Person
        fields = [
            'type_document',
            'document_number',
            'name',
            'surname',
            'telephone_number',
            'email',
            'date_of_birth',
            'gender',
            'pais_origen',
        ]
        labels = {
            'type_document': 'Tipo de Documento',
            'document_number': 'Numero de Documento',
            'name': 'Nombres',
            'surname': 'Apellidos',
            'telephone_number': 'Teléfono',
            'email': 'Email',
            'date_of_birth': 'Fecha de Nacimiento',
            'gender': 'Sexo',
            'pais_origen': 'País de origen',
        }
        widgets = {
            'type_document': forms.Select(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'pais_origen': forms.Select(attrs={'class': 'form-control'}),
        }

class CourseForm(forms.ModelForm):
    course_name = forms.CharField(label='Curso', max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre Del Curso'}))
    image_course = forms.ImageField(label='Imagen del Curso', required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control-file'}))
    tutor = forms.ModelChoiceField(queryset=Tutors.objects.all(), label='Tutor', widget=forms.Select(attrs={'class': 'form-control'}))
    class Meta:
        model = Courses
        fields = ['course_name', 'image_course', 'tutor']

class LevelForm(forms.ModelForm):
    level_name = forms.CharField(label='Nombre del Nivel', max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del Nivel'}))
    description = forms.CharField(label='Descripción', max_length=500, widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Descripción del Nivel'}))
    duration = forms.IntegerField(label='Duración', min_value=1, max_value=100, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Duración en horas', 'min': '1'}))
    class Meta:
        model = Levels
        fields = ['level_name', 'description', 'duration']

class UnitForm(forms.ModelForm):
    class Meta:
        model = Units
        fields = ['title', 'pdf_material', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'id': 'material_title'}),
            'pdf_material': forms.ClearableFileInput(attrs={'class': 'form-control', 'id': 'material_pdf'}),
            'content': forms.Textarea(attrs={'id': 'material_content'}),
        }

class TodoItemForm(forms.ModelForm):
    task = forms.CharField(label='Tarea', max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nueva tarea'}))
    due_date = forms.DateField(label='Fecha de Vencimiento', widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    class Meta:
        model = TodoItem
        fields = ['task', 'due_date']


class UserForm(BasePersonValidationForm):
    username = forms.CharField(label='Nombre de Usuario', max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de Usuario'}))
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}))
    email = forms.EmailField(label='Correo Electrónico', widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo Electrónico'}))
    documento = forms.CharField(label='Documento', max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Documento'}))
    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'documento', 'role']
        
        labels = {
            'role': 'Rol'
        }

        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'})
        }

    def clean_documento(self):
        documento = self.cleaned_data.get('documento')
        if documento and not re.match(r'^[0-9.]+$', documento):
            raise forms.ValidationError("El número de documento solo puede contener números y puntos.")
        return documento

class UserUpdateForm(BasePersonValidationForm):
    username = forms.CharField(label='Nombre de Usuario', max_length=150)
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
    documento = forms.CharField(label='Documento', max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Documento'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'documento', 'role']

    def clean_documento(self):
        documento = self.cleaned_data.get('documento')
        if documento and not re.match(r'^[0-9.]+$', documento):
            raise forms.ValidationError("El número de documento solo puede contener números y puntos.")
        return documento


class PersonForm(BasePersonValidationForm):
    document_number = forms.CharField(label='Número de Documento', max_length=20, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escriba su número de documento'}))
    name = forms.CharField(label='Nombre', max_length=50, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escriba sus nombres'}))
    surname = forms.CharField(label='Apellido', max_length=50, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escriba sus apellidos'}))
    telephone_number = forms.CharField(label='Teléfono', max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escriba el número de teléfono'}))
    email = forms.EmailField(label='Email', required=False, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Escriba su Correo Electrónico'}))
    date_of_birth = forms.DateField(label='Fecha de Nacimiento', required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    progenitor_document_number = forms.CharField(label='Número de Documento del Representante', max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escriba el número de documento del representante'}))
    progenitor_name = forms.CharField(label='Nombre del Representante', max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escriba el nombre del representante'}))

    class Meta:
        model = Person
        fields = [
            'type_document',
            'document_number',
            'name',
            'surname',
            'progenitor_name',
            'progenitor_document_number',
            'telephone_number',
            'email',
            'date_of_birth',
            'gender',
            'pais_origen'
        ]
        labels = {
            'type_document': 'Tipo de Documento',
            'document_number': 'Numero de Documento',
            'name': 'Nombres',
            'surname': 'Apellidos',
            'progenitor_name': 'Representante',
            'progenitor_document_number': 'Documento Representante',
            'telephone_number': 'Teléfono',
            'email': 'Email',
            'date_of_birth': 'Fecha de Nacimiento',
            'gender': 'Sexo',
            'pais_origen': 'País de origen',
        }
        widgets = {
            'type_document': forms.Select(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'pais_origen': forms.Select(attrs={'class': 'form-control'}),
        }

class GroupLevelForm(forms.ModelForm):
    name_group_levels = forms.CharField(
        label='Título del Grupo', 
        max_length=100, 
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Nombre del grupo de estudio'
        })
    )
    date_begin = forms.DateField(
        label='Fecha de Inicio', 
        widget=forms.DateInput(attrs={
            'class': 'form-control', 
            'type': 'date'
        })
    )
    date_end = forms.DateField(
        label='Fecha de Fin', 
        widget=forms.DateInput(attrs={
            'class': 'form-control', 
            'type': 'date'
        })
    )
    level = forms.ModelChoiceField(
        queryset=Levels.objects.all(), 
        label='Nivel', 
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    cohort = forms.IntegerField(
        label='Cohorte', 
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Número de cohorte'
        })
    )
    students = forms.ModelMultipleChoiceField(
        queryset=Students.objects.filter(is_deleted=False),
        label='Estudiantes',
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Group_Levels
        fields = ['name_group_levels', 'date_begin', 'date_end', 'study_modality', 'level', 'cohort', 'students']
        labels = {
            'study_modality': 'Modalidad de Estudio',
        }
        widgets = {
            'study_modality': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        date_begin = cleaned_data.get('date_begin')
        date_end = cleaned_data.get('date_end')

        if date_begin and date_end and date_begin >= date_end:
            raise forms.ValidationError("La fecha de inicio debe ser anterior a la fecha de fin.")

        return cleaned_data


class EvaluacionForm(forms.ModelForm):
    """
    Formulario para crear y editar evaluaciones.
    Este formulario se usa para definir evaluaciones que luego se crean masivamente para todos los estudiantes del grupo.
    """
    
    name = forms.CharField(
        label='Título de la Evaluación',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Prueba de Unidad 1 y 2'
        }),
        help_text='Título descriptivo de la evaluación (máximo 200 caracteres)'
    )
    
    description = forms.CharField(
        label='Descripción',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Descripción detallada de la evaluación...'
        }),
        required=False,
        help_text='Descripción opcional con detalles sobre la evaluación'
    )
    
    date = forms.DateField(
        label='Fecha de Evaluación',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text='Fecha en que se realizará la evaluación'
    )
    
    percentage_grade = forms.DecimalField(
        label='Porcentaje de Calificación',
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0',
            'max': '100',
            'placeholder': 'Ej: 25.00'
        }),
        help_text='Peso de esta evaluación en la nota final (0-100%)'
    )
    
    tipo_evaluacion = forms.ChoiceField(
        label='Tipo de Evaluación',
        choices=Testing.TIPOS_EVALUACION,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        help_text='Seleccione el tipo de evaluación'
    )
    
    class Meta:
        model = Testing
        fields = ['name', 'description', 'date', 'percentage_grade', 'tipo_evaluacion']
    
    def clean_date(self):
        """Validar que la fecha no sea anterior a hoy"""
        date = self.cleaned_data.get('date')
        if date and date < datetime.date.today():
            raise forms.ValidationError("La fecha de evaluación no puede ser anterior a hoy.")
        return date
    
    def clean_percentage_grade(self):
        """Validar que el porcentaje esté en el rango correcto"""
        percentage = self.cleaned_data.get('percentage_grade')
        if percentage is not None:
            if percentage < 0:
                raise forms.ValidationError("El porcentaje no puede ser negativo.")
            if percentage > 100:
                raise forms.ValidationError("El porcentaje no puede ser mayor a 100.")
        return percentage
    
    def clean_name(self):
        """Validar que el título no esté vacío y tenga una longitud apropiada"""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if len(name) < 3:
                raise forms.ValidationError("El título debe tener al menos 3 caracteres.")
            if len(name) > 200:
                raise forms.ValidationError("El título no puede exceder 200 caracteres.")
        return name
    
    def __init__(self, *args, **kwargs):
        """Inicializar el formulario con configuraciones adicionales"""
        self.group_level = kwargs.pop('group_level', None)
        super().__init__(*args, **kwargs)
        
        # Si tenemos el grupo, podemos hacer validaciones adicionales
        if self.group_level:
            self.fields['name'].help_text = f'Título para el grupo: {self.group_level.name_group_levels}'
    
    def validate_unique_name_in_group(self):
        """
        Validar que el título sea único en el grupo.
        Esta validación se hace por separado porque necesita el contexto del grupo.
        """
        if not self.group_level:
            return True
            
        name = self.cleaned_data.get('name')
        if name:
            # Verificar si ya existe una evaluación con este nombre en el grupo
            existing = Testing.objects.filter(
                name=name,
                group_level=self.group_level
            ).exists()
            
            # Si estamos editando, excluir la evaluación actual
            if self.instance and self.instance.pk:
                existing = Testing.objects.filter(
                    name=name,
                    group_level=self.group_level
                ).exclude(pk=self.instance.pk).exists()
            
            if existing:
                raise forms.ValidationError(f'Ya existe una evaluación con el título "{name}" en este grupo.')
        
        return True


# ============================================
# 🆕 NUEVO: Formularios para Gestión Comunitaria
# ============================================

from .models import Familia, Habitante, IngresoComunal, EgresoComunal, ConstanciaResidencia, ActaReunion
import re
from django.core.exceptions import ValidationError

class FamiliaForm(forms.ModelForm):
    """
    Formulario para crear y editar familias.
    """
    jefe_familia = forms.ModelChoiceField(
        queryset=Person.objects.filter(is_deleted=False),
        label="Jefe de Familia",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Seleccione la persona que será el jefe de familia"
    )
    
    direccion = forms.CharField(
        label="Dirección Completa",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Calle, avenida, sector, urbanización...'
        }),
        help_text="Dirección completa de la vivienda"
    )
    
    telefono_contacto = forms.CharField(
        label="Teléfono de Contacto",
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: +584121234567'
        }),
        help_text="Teléfono principal de contacto"
    )
    
    numero_vivienda = forms.CharField(
        label="Número de Vivienda",
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 23-A'
        }),
        help_text="Número o identificación de la vivienda (opcional)"
    )
    
    observaciones = forms.CharField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Observaciones adicionales...'
        }),
        help_text="Observaciones adicionales sobre la familia"
    )
    
    class Meta:
        model = Familia
        fields = ['jefe_familia', 'direccion', 'numero_vivienda', 'telefono_contacto', 'observaciones']
    
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
    Formulario para crear y editar habitantes.
    """
    persona = forms.ModelChoiceField(
        queryset=Person.objects.filter(is_deleted=False),
        label="Persona",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Seleccione la persona que será habitante"
    )
    
    familia = forms.ModelChoiceField(
        queryset=Familia.objects.filter(is_deleted=False),
        label="Familia",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Seleccione la familia a la que pertenece el habitante"
    )
    
    parentesco_jefe = forms.ChoiceField(
        choices=Habitante.PARENTESCO_CHOICES,
        label="Parentesco con Jefe de Familia",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Parentesco con el jefe de familia"
    )
    
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
            'placeholder': 'Ej: Estudiante, Empleado, Ama de casa...'
        }),
        help_text="Ocupación principal"
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
        help_text="Ingresos mensuales aproximados (opcional)"
    )
    
    condiciones_salud = forms.CharField(
        required=False,
        label="Condiciones de Salud",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Condiciones de salud relevantes...'
        }),
        help_text="Condiciones de salud importantes (opcional)"
    )
    
    class Meta:
        model = Habitante
        fields = [
            'persona', 'familia', 'parentesco_jefe', 'nivel_educativo',
            'ocupacion', 'ingresos_mensuales', 'condiciones_salud'
        ]
        labels = {  # 👈 Faltaba el nombre del atributo y la llave
            'date_of_birth': 'Fecha de Nacimiento',
            'gender': 'Sexo',
            'pais_origen': 'País de Origen',
        }
        widgets = {
            'type_document': forms.Select(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'pais_origen': forms.Select(attrs={'class': 'form-control'}),
        }
    
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
    Formulario para generar constancias de residencia.
    """
    familia = forms.ModelChoiceField(
        queryset=Familia.objects.filter(is_deleted=False),
        label="Familia",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Seleccione la familia para la constancia"
    )
    
    fecha_documento = forms.DateField(
        label="Fecha del Documento",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text="Fecha que aparecerá en la constancia"
    )
    
    finalidad = forms.CharField(
        label="Finalidad",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Especifique la finalidad de la constancia...'
        }),
        help_text="Finalidad o motivo de la constancia"
    )
    
    class Meta:
        model = ConstanciaResidencia
        fields = ['familia', 'fecha_documento', 'finalidad']
    
    def __init__(self, *args, **kwargs):
        """Inicializar con el usuario actual"""
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        """Guardar con el usuario y contenido generado"""
        instance = super().save(commit=False)
        if self.user:
            instance.generado_por = self.user
        
        # Generar contenido automático de la constancia
        instance.contenido = self.generar_contenido_constancia(instance)
        
        if commit:
            instance.save()
        return instance
    
    def generar_contenido_constancia(self, constancia):
        """Generar el contenido HTML/PDF de la constancia"""
        familia = constancia.familia
        jefe = familia.jefe_familia
        
        contenido = f"""
        <div style="font-family: 'Times New Roman', serif; line-height: 1.6;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h2 style="margin-bottom: 5px;">CONSTANCIA DE RESIDENCIA</h2>
                <p style="margin-top: 0;">N° {constancia.id}</p>
            </div>
            
            <div style="text-align: right; margin-bottom: 20px;">
                <p>Caracas, {constancia.fecha_documento.strftime('%d de %B de %Y')}</p>
            </div>
            
            <div style="margin-bottom: 20px;">
                <p>Quien suscribe, <strong>Consejo Comunal de la Urbanización Manuel Pulido Méndez</strong>, hace constar que:</p>
            </div>
            
            <div style="margin-left: 40px; margin-bottom: 20px;">
                <p><strong>CIUDADANO(A):</strong> {jefe.name} {jefe.surname}</p>
                <p><strong>CÉDULA DE IDENTIDAD:</strong> {jefe.document_number}</p>
                <p><strong>DOMICILIADO EN:</strong> {familia.direccion}</p>
                <p><strong>TELÉFONO:</strong> {familia.telefono_contacto}</p>
            </div>
            
            <div style="margin-bottom: 20px;">
                <p>Reside en esta comunidad junto a su grupo familiar, integrado por {familia.cantidad_habitantes()} personas, 
                y se encuentra debidamente registrado en nuestro sistema de gestión comunitaria.</p>
            </div>
            
            <div style="margin-bottom: 30px;">
                <p><strong>FINALIDAD:</strong> {constancia.finalidad}</p>
            </div>
            
            <div style="text-align: center; margin-top: 50px;">
                <p>_________________________</p>
                <p><strong>Vocero(a) de Secretaría</strong></p>
                <p>Consejo Comunal</p>
                <p>Urbanización Manuel Pulido Méndez</p>
            </div>
            
            <div style="margin-top: 30px; font-size: 0.9em; color: #666;">
                <p><em>Nota: Esta constancia es válida por 30 días a partir de su emisión.</em></p>
            </div>
        </div>
        """
        
        return contenido


class ActaReunionForm(forms.ModelForm):
    """
    Formulario para generar actas de reuniones.
    """
    titulo = forms.CharField(
        label="Título del Acta",
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Acta de Asamblea General Ordinaria'
        }),
        help_text="Título descriptivo del acta"
    )
    
    fecha_reunion = forms.DateTimeField(
        label="Fecha y Hora de la Reunión",
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        help_text="Fecha y hora en que se realizó la reunión"
    )
    
    lugar = forms.CharField(
        label="Lugar de la Reunión",
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Salón Comunal, Casa de la Familia Pérez'
        }),
        help_text="Lugar donde se realizó la reunión"
    )
    
    asistentes = forms.CharField(
        label="Lista de Asistentes",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Nombre y apellido de los asistentes, separados por comas...'
        }),
        help_text="Lista completa de asistentes a la reunión"
    )
    
    contenido = forms.CharField(
        label="Contenido del Acta",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Describa los puntos tratados en la reunión...'
        }),
        help_text="Contenido detallado de lo tratado en la reunión"
    )
    
    acuerdos = forms.CharField(
        required=False,
        label="Acuerdos Tomados",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Lista de acuerdos tomados en la reunión...'
        }),
        help_text="Acuerdos y decisiones tomadas (opcional)"
    )
    
    class Meta:
        model = ActaReunion
        fields = ['titulo', 'fecha_reunion', 'lugar', 'asistentes', 'contenido', 'acuerdos']
    
    def __init__(self, *args, **kwargs):
        """Inicializar con el usuario actual"""
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        """Guardar con el usuario y contenido formateado"""
        instance = super().save(commit=False)
        if self.user:
            instance.generado_por = self.user
        
        # Formatear contenido del acta
        instance.contenido = self.formatear_contenido_acta(instance)
        
        if commit:
            instance.save()
        return instance
    
    def formatear_contenido_acta(self, acta):
        """Formatear el contenido del acta para PDF/HTML"""
        contenido = f"""
        <div style="font-family: 'Times New Roman', serif; line-height: 1.6;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h2 style="margin-bottom: 5px;">ACTA DE REUNIÓN</h2>
                <h3 style="margin-top: 0; color: #555;">{acta.titulo}</h3>
            </div>
            
            <div style="margin-bottom: 20px;">
                <p><strong>Fecha y Hora:</strong> {acta.fecha_reunion.strftime('%d de %B de %Y, %I:%M %p')}</p>
                <p><strong>Lugar:</strong> {acta.lugar}</p>
                <p><strong>Asistentes ({acta.asistentes_count()} personas):</strong> {acta.asistentes}</p>
            </div>
            
            <div style="margin-bottom: 20px;">
                <h4 style="border-bottom: 1px solid #ccc; padding-bottom: 5px;">CONTENIDO DE LA REUNIÓN</h4>
                <div style="white-space: pre-line; margin-left: 20px;">
                    {acta.contenido}
                </div>
            </div>
        """
        
        if acta.acuerdos:
            contenido += f"""
            <div style="margin-bottom: 20px;">
                <h4 style="border-bottom: 1px solid #ccc; padding-bottom: 5px;">ACUERDOS TOMADOS</h4>
                <div style="white-space: pre-line; margin-left: 20px;">
                    {acta.acuerdos}
                </div>
            </div>
            """
        
        contenido += f"""
            <div style="text-align: center; margin-top: 50px;">
                <p>_________________________</p>
                <p><strong>Secretario(a) de Actas</strong></p>
                <p>Consejo Comunal</p>
                <p>Urbanización Manuel Pulido Méndez</p>
            </div>
            
            <div style="margin-top: 30px; font-size: 0.9em; color: #666;">
                <p><em>Acta generada el {acta.fecha_generacion.strftime('%d/%m/%Y %I:%M %p')}</em></p>
            </div>
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
        queryset=Person.objects.filter(is_deleted=False),
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
            'persona', 'familia'
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
