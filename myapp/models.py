from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import AbstractUser, Group, Permission  # Importar la clase User de autenticación

# --- Lógica para Soft Delete (Eliminación Lógica) ---

# Constante para tipos de documento
TIPO_DOCUMENTO_CHOICES = [
    ('V', 'Cédula Venezolana (V)'),
    ('CC', 'Cédula Colombiana (CC)'),
]
GENDER_LIST_PREDIFINED = [
    ('M', 'Masculino'),
    ('F', 'Femenino'),
]
ROLE_LIST_PREDIFINED = [
    ("estudiante", "Estudiante"), 
    ("profesor", "Profesor"),
    ("tutor", "Tutor"), 
    ("admin", "Administrador")
]

# 🆕 NUEVO: Roles para gestión comunitaria
ROLES_COMUNITARIOS = [
    ('admin', 'Administrador del Sistema'),
    ('vocero_finanzas', 'Vocero de Finanzas'),
    ('vocero_secretaria', 'Vocero de Secretaría'),
    ('vocero_salud', 'Vocero de Salud'),
    ('vocero_educacion', 'Vocero de Educación'),
    ('habitante', 'Habitante de la Comunidad'),
]
COURSE_MODALITY_LIST_PREDIFINED = [
    ("virtual", "Virtual"),
    ("presencial", "Presencial")
]
STAFF_POSITION_LIST_PREDIFINED = [
    ("profesor", "Profesor"),
    ("tutor", "Tutor"),
    ("administrador", "Administrador"),
]

PAIS_ORIGEN_CHOICES = [
    ('Venezuela', 'Venezuela'),
    ('Colombia', 'Colombia'),
    ('Argentina', 'Argentina'),
    ('Bolivia', 'Bolivia'),
    ('Brasil', 'Brasil'),
    ('Chile', 'Chile'),
    ('Costa Rica', 'Costa Rica'),
    ('Cuba', 'Cuba'),
    ('República Dominicana', 'República Dominicana'),
    ('Ecuador', 'Ecuador'),
    ('El Salvador', 'El Salvador'),
    ('España', 'España'),
    ('Estados Unidos', 'Estados Unidos'),
    ('Guatemala', 'Guatemala'),
    ('Honduras', 'Honduras'),
    ('México', 'México'),
    ('Nicaragua', 'Nicaragua'),
    ('Panamá', 'Panamá'),
    ('Paraguay', 'Paraguay'),
    ('Perú', 'Perú'),
    ('Puerto Rico', 'Puerto Rico'),
    ('Uruguay', 'Uruguay'),
    ('Otro', 'Otro'),
]

class SoftDeleteManager(models.Manager):
    """
    Manager personalizado para que por defecto solo se muestren
    los registros que no están marcados como eliminados.
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class SoftDeleteModel(models.Model):
    """
    Modelo base abstracto con campos y métodos para la eliminación lógica.
    """
    is_deleted = models.BooleanField(default=False, verbose_name="Eliminado")
    deleted_at = models.DateTimeField(null=True, blank=True, default=None, verbose_name="Fecha de eliminación")

    # Managers
    objects = SoftDeleteManager()  # Manager que filtra los eliminados
    all_objects = models.Manager() # Manager que devuelve todos los objetos

    def delete(self, using=None, keep_parents=False):
        """
        Sobrescribe el método delete para marcar el objeto como eliminado.
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        """
        Método para restaurar un objeto marcado como eliminado.
        """
        self.is_deleted = False
        self.deleted_at = None
        self.save()

    class Meta:
        abstract = True

# --- Fin de la lógica para Soft Delete ---

class Cedula(models.Model):
    class Meta:
        db_table = 'cedulas'
        verbose_name = 'Cédula'
        verbose_name_plural = 'Cédulas'
    """
    Modelo para almacenar registros de personas con cédulas venezolanas o colombianas.
    """
    tipo_documento = models.CharField(
        max_length=2,
        choices=TIPO_DOCUMENTO_CHOICES,
        default='V',
        verbose_name="Tipo de Documento"
    )
    numero_documento = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Número de Documento"
    )
    nombre = models.CharField(max_length=50, verbose_name="Nombre")
    apellido = models.CharField(max_length=50, verbose_name="Apellido")

    def __str__(self):
        return f"{self.get_tipo_documento_display()} - {self.numero_documento} - {self.nombre} {self.apellido}"


class Calendario(models.Model):
    """
    Modelo para gestionar eventos del calendario.
    """
    titulo = models.CharField(max_length=200, verbose_name="Título")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    fecha_inicio = models.DateTimeField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Fin")
    creador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    activo = models.BooleanField(default=True, verbose_name="Evento Activo")

    def __str__(self):
        return self.titulo
    
    class Meta:
        db_table = 'calendario'
        verbose_name = 'Evento de calendario'
        verbose_name_plural = 'Eventos de calendario'


# MODELOS DE NUEVA BASE DE DATOS ACADEMIA
class Person(SoftDeleteModel):
    type_document = models.CharField(max_length=2, choices=TIPO_DOCUMENTO_CHOICES, default='V')
    document_number = models.CharField(
    max_length=20, 
    unique=True,
    error_messages={
    'unique': 'Ya existe una persona registrada con este número de documento.'
    })
    name= models.CharField(max_length=50)
    surname= models.CharField(max_length=50)
    progenitor_name= models.CharField(max_length=50, blank=True, null=True)
    progenitor_document_number= models.CharField(max_length=20, blank=True, null=True)
    telephone_number=models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_LIST_PREDIFINED, default='H')
    pais_origen = models.CharField("País de origen", max_length=50, choices=PAIS_ORIGEN_CHOICES, blank=True, null=True)
    class Meta:
        db_table = 'personas'
        verbose_name = 'Persona'
        verbose_name_plural = 'Personas'
        
    def __str__(self):
        return f"{self.name} ({self.document_number})"

class Students(SoftDeleteModel):
    """
    Modelo que representa a un estudiante de la academia.
    Relaciona a la persona, usuario y los grupos a los que pertenece.
    """
    date_register = models.DateField()
    status = models.CharField(max_length=50)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)

    class Meta:
        db_table = 'estudiantes'
        verbose_name = 'Estudiante'
        verbose_name_plural = 'Estudiantes'

    def __str__(self):
        return f"{self.person.name} ({self.user.username})"
    

class Grade_Students(models.Model):
    """
    Modelo que almacena las calificaciones de los estudiantes en un grupo específico.
    Conecta las notas con evaluaciones específicas.
    """
    grades = models.DecimalField(max_digits=5, decimal_places=2)
    observations = models.TextField(blank=True, null=True)
    student = models.ForeignKey('Students', on_delete=models.CASCADE)
    group_level = models.ForeignKey('Group_Levels', on_delete=models.CASCADE)
    evaluacion = models.ForeignKey('Testing', on_delete=models.CASCADE, null=True, blank=True, 
                                   verbose_name='Evaluación', help_text='Evaluación asociada a esta nota')

    class Meta:
        db_table = 'notas_estudiantes'
        verbose_name = 'Nota de estudiante'
        verbose_name_plural = 'Notas de estudiantes'
        # Constraint: Un estudiante no puede tener dos notas para la misma evaluación
        unique_together = ['student', 'evaluacion']

    def __str__(self):
        evaluacion_name = self.evaluacion.name if self.evaluacion else "Sin evaluación"
        return f"{self.grades} - {self.student.person.name} - {evaluacion_name}"

class Testing(models.Model):
    """
    Modelo que representa una evaluación aplicada a un estudiante en un grupo.
    """
    TIPOS_EVALUACION = [
        ('examen', 'Examen'),
        ('quiz', 'Quiz'),
        ('tarea', 'Tarea'),
        ('proyecto', 'Proyecto'),
        ('participacion', 'Participación'),
        ('personalizada', 'Evaluación Personalizada'),
    ]
    
    name = models.CharField(max_length=200)  # Aumentado de 100 a 200
    description = models.TextField()
    percentage_grade = models.DecimalField(max_digits=5, decimal_places=2)
    date = models.DateField()
    tipo_evaluacion = models.CharField(
        max_length=50, 
        choices=TIPOS_EVALUACION, 
        default='examen',
        verbose_name='Tipo de Evaluación'
    )
    student = models.ForeignKey(Students, on_delete=models.CASCADE)
    group_level = models.ForeignKey('Group_Levels', on_delete=models.CASCADE)

    def get_estado(self):
        """
        Calcula el estado de la evaluación basándose en:
        - Total de estudiantes del grupo
        - Notas asignadas para esta evaluación
        - Si la fecha ya pasó
        """
        from django.utils import timezone
        
        try:
            # Obtener total de estudiantes del grupo (activos)
            total_estudiantes = self.group_level.students.filter(is_deleted=False).count()
            
            # Contar cuántos estudiantes tienen nota para esta evaluación específica
            notas_asignadas = Grade_Students.objects.filter(
                evaluacion__name=self.name,
                evaluacion__group_level=self.group_level,
                grades__isnull=False
            ).count()
            
            # Verificar si la fecha ya pasó
            fecha_pasada = self.date < timezone.now().date()
            
            # Determinar el estado
            if notas_asignadas == 0:
                # No hay notas asignadas
                if fecha_pasada:
                    return 'vencida'  # La fecha pasó y no se ha calificado
                else:
                    return 'pendiente'  # Aún no llega la fecha
            elif notas_asignadas < total_estudiantes:
                # Hay algunas notas pero no todas
                return 'en_progreso'
            else:
                # Todos los estudiantes tienen nota
                return 'completada'
        except Exception as e:
            return 'pendiente'
    
    def get_estado_display(self):
        """
        Retorna el estado en formato legible.
        """
        estado = self.get_estado()
        estados = {
            'completada': 'Completada',
            'en_progreso': 'En Progreso',
            'pendiente': 'Pendiente',
            'vencida': 'Vencida'
        }
        return estados.get(estado, 'Pendiente')
    
    def get_estado_badge_class(self):
        """
        Retorna la clase CSS para el badge del estado.
        """
        estado = self.get_estado()
        clases = {
            'completada': 'bg-success',
            'en_progreso': 'bg-warning',
            'pendiente': 'bg-secondary',
            'vencida': 'bg-danger'
        }
        return clases.get(estado, 'bg-secondary')
    
    def get_progreso_calificacion(self):
        """
        Retorna el progreso de calificación (estudiantes con nota / total estudiantes del grupo)
        """
        try:
            # Contar estudiantes activos del grupo
            total_estudiantes = self.group_level.students.filter(is_deleted=False).count()
            
            # Contar cuántos estudiantes tienen nota para esta evaluación
            notas_asignadas = Grade_Students.objects.filter(
                evaluacion__name=self.name,
                evaluacion__group_level=self.group_level,
                grades__isnull=False
            ).count()
            
            return {
                'estudiantes_con_notas': notas_asignadas,
                'total_estudiantes': total_estudiantes,
                'porcentaje': round((notas_asignadas / total_estudiantes * 100), 1) if total_estudiantes > 0 else 0
            }
        except Exception as e:
            return {
                'estudiantes_con_notas': 0,
                'total_estudiantes': 0,
                'porcentaje': 0
            }

    @staticmethod
    def calcular_estado_evaluacion(nombre_evaluacion, grupo):
        """
        Método estático para calcular el estado de una evaluación específica en un grupo
        """
        from django.utils import timezone
        
        try:
            # Obtener una evaluación de referencia para la fecha
            evaluacion_ref = Testing.objects.filter(
                name=nombre_evaluacion,
                group_level=grupo
            ).first()
            
            if not evaluacion_ref:
                return 'pendiente'
            
            # Total de estudiantes activos del grupo
            total_estudiantes = grupo.students.filter(is_deleted=False).count()
            
            # Contar notas para esta evaluación
            notas_asignadas = Grade_Students.objects.filter(
                evaluacion__name=nombre_evaluacion,
                evaluacion__group_level=grupo,
                grades__isnull=False
            ).count()
            
            # Verificar si la fecha ya pasó
            fecha_pasada = evaluacion_ref.date < timezone.now().date()
            
            # Determinar el estado
            if notas_asignadas == 0:
                return 'vencida' if fecha_pasada else 'pendiente'
            elif notas_asignadas < total_estudiantes:
                return 'en_progreso'
            else:
                return 'completada'
                
        except Exception as e:
            return 'pendiente'

    class Meta:
        db_table = 'evaluaciones'
        verbose_name = 'Evaluación'
        verbose_name_plural = 'Evaluaciones'
        # Constraint: Un estudiante no puede tener dos evaluaciones con el mismo nombre en el mismo grupo
        unique_together = ['name', 'student', 'group_level']    

    def __str__(self):
        return f"{self.name} ({self.date}) - {self.student.person.name}"
    
class Units(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField(blank=True, null=True)
    pdf_material = models.FileField(upload_to='materials/', blank=True, null=True)
    topic_order = models.IntegerField()
    level = models.ForeignKey('Levels', on_delete=models.CASCADE, related_name='units', null=True)
    class Meta:
        db_table = 'unidades'
        verbose_name = 'Unidad'
        verbose_name_plural = 'Unidades'

    def __str__(self):
        return f"{self.title} (Tema {self.topic_order})"

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
class User(AbstractUser, SoftDeleteModel):
    must_change_password = models.BooleanField(default=False, verbose_name="Debe cambiar contraseña")
    email = models.EmailField(unique=True)
    documento = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=50, choices=ROLE_LIST_PREDIFINED, default='estudiante')
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True, blank=True)

    REQUIRED_FIELDS = ['first_name','last_name','documento', 'role', 'email']

    groups = models.ManyToManyField(
        Group,
        related_name='usuarios_sistema_user_set',
        blank=True,
        help_text='Los grupos a los que pertenece este usuario.',
        verbose_name='grupos'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='usuarios_sistema_user_permissions_set',
        blank=True,
        help_text='Permisos específicos para este usuario.',
        verbose_name='permisos de usuario'
    )
    class Meta:
        db_table = 'usuarios_sistema'
        verbose_name = 'Usuario del sistema'
        verbose_name_plural = 'Usuarios del sistema'
    
    def __str__(self):
        return f"{self.username} ({self.role})"
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""    

class Tutors(SoftDeleteModel):
    staff_position = models.CharField(max_length=50, choices=STAFF_POSITION_LIST_PREDIFINED, default='tutor')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)

    class Meta:
        db_table = 'tutores'
        verbose_name = 'Tutor'
        verbose_name_plural = 'Tutores'
    
    def __str__(self):
        return f"{self.person.name} ({self.staff_position})"
class Courses(SoftDeleteModel):
    course_name = models.CharField(max_length=100)
    image_course = models.ImageField(upload_to='courses_images/', blank=True, null=True, help_text="Imagen del curso")
    tutor = models.ForeignKey(Tutors, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        # Nota: El campo study_modality no existe en el modelo, se debe corregir o añadir.
        # Usando course_name por ahora.
        return f"{self.course_name}"

    class Meta:
        db_table = 'cursos'
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'

class Levels(models.Model):
    level_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    duration = models.IntegerField(help_text="Duración en horas")
    course = models.ForeignKey(Courses, on_delete=models.CASCADE)
    class Meta:
        db_table = 'niveles'
        verbose_name = 'Nivel'
        verbose_name_plural = 'Niveles'

    def __str__(self):
        return f"{self.level_name} ({self.course.course_name})"
    
class Group_Levels(models.Model):
    """
    Modelo que representa un grupo de nivel en la academia.
    Un grupo puede tener muchos estudiantes y un nivel asociado.
    """
    name_group_levels = models.CharField(max_length=100)
    date_begin = models.DateField()
    date_end = models.DateField()
    study_modality = models.CharField(max_length=50, choices=COURSE_MODALITY_LIST_PREDIFINED, default='presential')
    level = models.ForeignKey('Levels', on_delete=models.CASCADE)
    students = models.ManyToManyField('Students', related_name='group_levels', blank=True)
    cohort = models.IntegerField(help_text="Cohorte del Grupo", blank=True, null=True)

    class Meta:
        db_table = 'grupos_niveles'
        verbose_name = 'Grupo Nivel'
        verbose_name_plural = 'Grupos Niveles'

    def __str__(self):
        return f"{self.name_group_levels} ({self.level.level_name})"

class TodoItem(models.Model):
    task = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    due_date = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=20, choices=[('low', 'Baja'), ('medium', 'Media'), ('high', 'Alta')], default='medium', verbose_name="Prioridad")
    class Meta:
        db_table = 'tareas'
        verbose_name = 'Tarea'
        verbose_name_plural = 'Tareas'

    def __str__(self):
        return self.task


# ============================================
# 🆕 NUEVO: Modelos para Gestión Comunitaria
# ============================================

class Familia(SoftDeleteModel):
    """
    Modelo que representa una familia en la comunidad.
    Una familia tiene un jefe de familia y puede tener múltiples habitantes.
    """
    jefe_familia = models.ForeignKey(Person, on_delete=models.PROTECT, verbose_name="Jefe de Familia")
    direccion = models.TextField(verbose_name="Dirección Completa")
    numero_vivienda = models.CharField(max_length=10, blank=True, verbose_name="Número de Vivienda")
    telefono_contacto = models.CharField(max_length=15, verbose_name="Teléfono de Contacto")
    fecha_registro = models.DateField(auto_now_add=True, verbose_name="Fecha de Registro")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    
    class Meta:
        db_table = 'familias'
        verbose_name = 'Familia'
        verbose_name_plural = 'Familias'
        ordering = ['-fecha_registro']
    
    def __str__(self):
        return f"Familia {self.jefe_familia.name} - {self.direccion}"
    
    def cantidad_habitantes(self):
        """Retorna la cantidad de habitantes en la familia"""
        return self.habitante_set.count()


class Habitante(SoftDeleteModel):
    """
    Modelo que representa a un habitante de la comunidad.
    Relaciona una Persona con una Familia y datos comunitarios.
    """
    PARENTESCO_CHOICES = [
        ('Jefe', 'Jefe de Familia'),
        ('Esposa/Esposo', 'Esposa/Esposo'),
        ('Hijo/Hija', 'Hijo/Hija'),
        ('Nieto/Nieta', 'Nieto/Nieta'),
        ('Padre/Madre', 'Padre/Madre'),
        ('Hermano/Hermana', 'Hermano/Hermana'),
        ('Otro', 'Otro Parentesco'),
    ]
    
    NIVEL_EDUCATIVO_CHOICES = [
        ('ninguno', 'Ninguno'),
        ('primaria', 'Primaria'),
        ('secundaria', 'Secundaria'),
        ('tecnico', 'Técnico Medio'),
        ('universitario', 'Universitario'),
        ('postgrado', 'Postgrado'),
    ]
    
    persona = models.ForeignKey(Person, on_delete=models.CASCADE, verbose_name="Persona")
    familia = models.ForeignKey(Familia, on_delete=models.CASCADE, verbose_name="Familia")
    parentesco_jefe = models.CharField(
        max_length=50, 
        choices=PARENTESCO_CHOICES, 
        default='Jefe',
        verbose_name="Parentesco con Jefe de Familia"
    )
    nivel_educativo = models.CharField(
        max_length=100, 
        choices=NIVEL_EDUCATIVO_CHOICES, 
        blank=True,
        verbose_name="Nivel Educativo"
    )
    ocupacion = models.CharField(max_length=100, blank=True, verbose_name="Ocupación")
    ingresos_mensuales = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Ingresos Mensuales (Bs.)"
    )
    condiciones_salud = models.TextField(blank=True, verbose_name="Condiciones de Salud")
    fecha_registro_comunitario = models.DateField(auto_now_add=True, verbose_name="Fecha Registro Comunitario")
    
    class Meta:
        db_table = 'habitantes'
        verbose_name = 'Habitante'
        verbose_name_plural = 'Habitantes'
        ordering = ['familia', 'parentesco_jefe', 'persona__name']
        unique_together = ['persona', 'familia']  # Una persona solo puede ser habitante de una familia
    
    def __str__(self):
        return f"{self.persona.name} {self.persona.surname} - {self.get_parentesco_jefe_display()}"
    
    # Propiedades para acceder a los datos de la persona fácilmente
    @property
    def name(self):
        return self.persona.name
    
    @property
    def surname(self):
        return self.persona.surname
    
    @property
    def document_number(self):
        return self.persona.document_number
    
    @property
    def telephone_number(self):
        return self.persona.telephone_number
    
    @property
    def email(self):
        return self.persona.email
    
    @property
    def date_of_birth(self):
        return self.persona.date_of_birth
    
    @property
    def gender(self):
        return self.persona.gender
    
    @property
    def pais_origen(self):
        return self.persona.pais_origen


class IngresoComunal(models.Model):
    """
    Modelo para registrar ingresos de la caja comunal.
    """
    TIPO_INGRESO_CHOICES = [
        ('aportes', 'Aportes de Familias'),
        ('donaciones', 'Donaciones'),
        ('actividades', 'Actividades Comunitarias'),
        ('subvenciones', 'Subvenciones'),
        ('otros', 'Otros Ingresos'),
    ]
    
    fecha = models.DateField(verbose_name="Fecha del Ingreso")
    tipo_ingreso = models.CharField(
        max_length=50, 
        choices=TIPO_INGRESO_CHOICES, 
        default='aportes',
        verbose_name="Tipo de Ingreso"
    )
    concepto = models.CharField(max_length=200, verbose_name="Concepto")
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto (Bs.)")
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='ingresos_registrados',
        verbose_name="Responsable"
    )
    soporte_digital = models.FileField(
        upload_to='soportes/ingresos/', 
        blank=True, 
        null=True,
        verbose_name="Soporte Digital"
    )
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    
    class Meta:
        db_table = 'ingresos_comunales'
        verbose_name = 'Ingreso Comunal'
        verbose_name_plural = 'Ingresos Comunales'
        ordering = ['-fecha', '-fecha_registro']
    
    def __str__(self):
        return f"{self.fecha} - {self.concepto} - Bs. {self.monto}"


class EgresoComunal(models.Model):
    """
    Modelo para registrar egresos de la caja comunal.
    """
    TIPO_EGRESO_CHOICES = [
        ('mantenimiento', 'Mantenimiento Comunitario'),
        ('servicios', 'Servicios Públicos'),
        ('actividades', 'Actividades Comunitarias'),
        ('emergencias', 'Emergencias'),
        ('administrativos', 'Gastos Administrativos'),
        ('otros', 'Otros Egresos'),
    ]
    
    fecha = models.DateField(verbose_name="Fecha del Egreso")
    tipo_egreso = models.CharField(
        max_length=50, 
        choices=TIPO_EGRESO_CHOICES, 
        default='mantenimiento',
        verbose_name="Tipo de Egreso"
    )
    concepto = models.CharField(max_length=200, verbose_name="Concepto")
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto (Bs.)")
    beneficiario = models.CharField(max_length=200, blank=True, verbose_name="Beneficiario")
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='egresos_registrados',
        verbose_name="Responsable"
    )
    soporte = models.FileField(
        upload_to='soportes/egresos/', 
        blank=True, 
        null=True,
        verbose_name="Soporte"
    )
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    
    class Meta:
        db_table = 'egresos_comunales'
        verbose_name = 'Egreso Comunal'
        verbose_name_plural = 'Egresos Comunales'
        ordering = ['-fecha', '-fecha_registro']
    
    def __str__(self):
        return f"{self.fecha} - {self.concepto} - Bs. {self.monto}"


class ConstanciaResidencia(models.Model):
    """
    Modelo para registrar constancias de residencia generadas.
    """
    familia = models.ForeignKey(Familia, on_delete=models.CASCADE, verbose_name="Familia")
    fecha_generacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Generación")
    fecha_documento = models.DateField(verbose_name="Fecha del Documento")
    finalidad = models.TextField(verbose_name="Finalidad de la Constancia")
    contenido = models.TextField(verbose_name="Contenido de la Constancia")
    generado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        verbose_name="Generado por"
    )
    archivo_pdf = models.FileField(
        upload_to='constancias/', 
        blank=True, 
        null=True,
        verbose_name="Archivo PDF"
    )
    
    class Meta:
        db_table = 'constancias_residencia'
        verbose_name = 'Constancia de Residencia'
        verbose_name_plural = 'Constancias de Residencia'
        ordering = ['-fecha_generacion']
    
    def __str__(self):
        return f"Constancia {self.familia} - {self.fecha_documento}"


class ActaReunion(models.Model):
    """
    Modelo para registrar actas de reuniones comunitarias.
    """
    titulo = models.CharField(max_length=200, verbose_name="Título del Acta")
    fecha_reunion = models.DateTimeField(verbose_name="Fecha y Hora de la Reunión")
    lugar = models.CharField(max_length=200, verbose_name="Lugar de la Reunión")
    asistentes = models.TextField(verbose_name="Lista de Asistentes")
    contenido = models.TextField(verbose_name="Contenido del Acta")
    acuerdos = models.TextField(blank=True, verbose_name="Acuerdos Tomados")
    generado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        verbose_name="Generado por"
    )
    fecha_generacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Generación")
    archivo_pdf = models.FileField(
        upload_to='actas/', 
        blank=True, 
        null=True,
        verbose_name="Archivo PDF"
    )
    
    class Meta:
        db_table = 'actas_reunion'
        verbose_name = 'Acta de Reunión'
        verbose_name_plural = 'Actas de Reunión'
        ordering = ['-fecha_reunion']
    
    def __str__(self):
        return f"{self.titulo} - {self.fecha_reunion}"
    
    def asistentes_count(self):
        """Retorna la cantidad de asistentes"""
        return len(self.asistentes.split(',')) if self.asistentes else 0