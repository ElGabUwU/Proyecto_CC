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