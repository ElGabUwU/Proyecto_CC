from django.db import models
from django.conf import settings
from datetime import date
from django.db.models import Q
from django.core.exceptions import ValidationError

# Nota: Asumo que mantienes tu clase base SoftDeleteModel para borrado lógico.
# Si no la tienes definida en este archivo, recuerda importarla de tu mixin/base.
class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False, verbose_name="Eliminado")

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()


class Familia(SoftDeleteModel):
    """
    Representa un grupo familiar o vivienda dentro del consejo comunal.
    Según el diagrama: Familias (nombre_familia, vivienda, direccion, catastro)
    """
    nombre_familia = models.CharField(max_length=100, verbose_name="Nombre de la Familia/Grupo")
    vivienda = models.CharField(max_length=50, verbose_name="Número o Tipo de Vivienda")
    direccion = models.TextField(verbose_name="Dirección Completa")
    catastro = models.CharField(max_length=50, blank=True, null=True, verbose_name="Código Catastral")
    fecha_registro = models.DateField(auto_now_add=True, verbose_name="Fecha de Registro")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")

    class Meta:
        db_table = 'familias'
        verbose_name = 'Familia'
        verbose_name_plural = 'Familias'
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"{self.nombre_familia} - Casa/Apto: {self.vivienda}"

    def cantidad_habitantes(self):
        """Retorna la cantidad de habitantes activos en esta familia"""
        return self.habitantes.filter(is_deleted=False).count()

    @property
    def jefe_familia(self):
        """Retorna el habitante que es jefe de esta familia, si existe"""
        return self.habitantes.filter(es_jefe_familia=True, is_deleted=False).first()


class Habitante(SoftDeleteModel):
    
    TIPO_CEDULA_CHOICES = [
    ('V', 'Venezolano/a'),
    ('E', 'Extranjero/a'),
    ]
    tipo_cedula = models.CharField(max_length=1, choices=TIPO_CEDULA_CHOICES, default='V')
    cedula = models.CharField(max_length=15, unique=True) # Tu campo existente
    
    """
    Representa a un ciudadano de la comunidad. 
    Funde los datos de identidad personal con los datos socio-comunitarios.
    """
    GENERO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('O', 'Otro'),
    ]

    NIVEL_EDUCATIVO_CHOICES = [
        ('ninguno', 'Ninguno'),
        ('primaria', 'Primaria'),
        ('secundaria', 'Secundaria'),
        ('tecnico', 'Técnico Medio'),
        ('universitario', 'Universitario'),
        ('postgrado', 'Postgrado'),
    ]

    # Relación fuerte: Si se elimina la familia lógicamente o físicamente
    familia = models.ForeignKey(
        Familia, 
        on_delete=models.CASCADE, 
        related_name='habitantes', 
        verbose_name="Familia / Hogar"
    )
    
    # Datos de Identidad (Antes en la tabla Person)
    cedula = models.CharField(max_length=20, unique=True, verbose_name="Cédula de Identidad")
    nombre = models.CharField(max_length=100, verbose_name="Nombres")
    apellido = models.CharField(max_length=100, verbose_name="Apellidos")
    fecha_nacimiento = models.DateField(verbose_name="Fecha de Nacimiento")
    genero = models.CharField(max_length=1, choices=GENERO_CHOICES, verbose_name="Género")
    
    # Control de Liderazgo Familiar
    es_jefe_familia = models.BooleanField(default=False, verbose_name="¿Es Jefe de Familia?")
    
    # Datos Socioeconómicos del antiguo Habitante
    ocupacion = models.CharField(max_length=100, blank=True, verbose_name="Ocupación")
    nivel_educativo = models.CharField(
        max_length=50, 
        choices=NIVEL_EDUCATIVO_CHOICES, 
        blank=True, 
        verbose_name="Nivel Educativo"
    )
    ingresos_mensuales = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Ingresos Mensuales (Bs.)"
    )
    condiciones_salud = models.TextField(blank=True, verbose_name="Condiciones de Salud")
    fecha_registro_comunitario = models.DateField(auto_now_add=True, verbose_name="Fecha de Registro")

    class Meta:
        db_table = 'habitantes'
        verbose_name = 'Habitante'
        verbose_name_plural = 'Habitantes'
        ordering = ['familia', '-es_jefe_familia', 'apellido', 'nombre']
        
        constraints = [
            # 1. Regla del Consejo Comunal: Un solo jefe activo por cada grupo familiar
            models.UniqueConstraint(
                fields=['familia'],
                condition=models.Q(es_jefe_familia=True, is_deleted=False),
                name='unique_jefe_activo_por_familia'
            ),
            
            # 2. Regla del Estado Venezolano / Sistema: La cédula debe ser única en todo el sistema 
            # (ignorando lógicamente los registros que hayan sido borrados con soft delete)
            models.UniqueConstraint(
                fields=['cedula'],
                condition=models.Q(is_deleted=False),
                name='unique_cedula_habitante_activo'
            )
        ]

    def __str__(self):
        rango = "Jefe" if self.es_jefe_familia else "Miembro"
        return f"{self.cedula} - {self.nombre} {self.apellido} ({rango})"

    def clean(self):
        """Validación a nivel de formulario/clean de Django"""
        super().clean()
        if self.es_jefe_familia and not self.is_deleted:
            # Validar si ya existe otro jefe en la familia (excluyéndose a sí mismo si está editando)
            jefes_existentes = Habitante.objects.filter(
                familia=self.familia, 
                es_jefe_familia=True, 
                is_deleted=False
            )
            if self.pk:
                jefes_existentes = jefes_existentes.exclude(pk=self.pk)
            
            if jefes_existentes.exists():
                raise ValidationError({
                    'es_jefe_familia': 'Esta familia ya posee un Jefe de Familia registrado y activo.'
                })


class IngresoComunal(models.Model):
    """
    Modelo para registrar ingresos de la caja comunal (Módulo Finanzas).
    """
    TIPO_INGRESO_CHOICES = [
        ('aportes', 'Aportes de Familias'),
        ('donaciones', 'Donaciones'),
        ('actividades', 'Actividades Comunitarias'),
        ('subvenciones', 'Subvenciones'),
        ('otros', 'Otros Ingresos'),
    ]
    
    fecha = models.DateField(verbose_name="Fecha del Ingreso")
    tipo_ingreso = models.CharField(max_length=50, choices=TIPO_INGRESO_CHOICES, default='aportes', verbose_name="Tipo de Ingreso")
    concepto = models.CharField(max_length=200, verbose_name="Concepto")
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto (Bs.)")
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ingresos_registrados', verbose_name="Responsable")
    soporte_digital = models.FileField(upload_to='soportes/ingresos/', blank=True, null=True, verbose_name="Soporte Digital")
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
    Modelo para registrar egresos de la caja comunal (Módulo Finanzas).
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
    tipo_egreso = models.CharField(max_length=50, choices=TIPO_EGRESO_CHOICES, default='mantenimiento', verbose_name="Tipo de Egreso")
    concepto = models.CharField(max_length=200, verbose_name="Concepto")
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto (Bs.)")
    beneficiario = models.CharField(max_length=200, blank=True, verbose_name="Beneficiario")
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='egresos_registrados', verbose_name="Responsable")
    soporte = models.FileField(upload_to='soportes/egresos/', blank=True, null=True, verbose_name="Soporte")
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
    Según tu nuevo diagrama, el modelo Constancias se vincula con un Habitante (id_habitante), 
    lo cual es correcto porque la constancia de residencia es nominal e individual.
    """
    habitante = models.ForeignKey(Habitante, on_delete=models.CASCADE, related_name='constancias', verbose_name="Habitante Solicitante")
    fecha_generacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Generación")
    fecha_documento = models.DateField(verbose_name="Fecha del Documento")
    finalidad = models.TextField(verbose_name="Finalidad de la Constancia")
    contenido = models.TextField(verbose_name="Contenido de la Constancia")
    generado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="Generado por")
    archivo_pdf = models.FileField(upload_to='constancias/', blank=True, null=True, verbose_name="Archivo PDF")
    
    class Meta:
        db_table = 'constancias_residencia'
        verbose_name = 'Constancia de Residencia'
        verbose_name_plural = 'Constancias de Residencia'
        ordering = ['-fecha_generacion']
    
    def __str__(self):
        return f"Constancia de {self.habitante.nombre} {self.habitante.apellido} - {self.fecha_documento}"


class ActaReunion(models.Model):
    """
    Modelo para registrar las Asambleas de Ciudadanos y sus acuerdos.
    """
    titulo = models.CharField(max_length=200, verbose_name="Título del Acta")
    fecha_reunion = models.DateTimeField(verbose_name="Fecha y Hora de la Reunión")
    lugar = models.CharField(max_length=200, verbose_name="Lugar de la Reunión")
    asistentes = models.TextField(verbose_name="Lista de Asistentes")
    cuenta_bancaria = models.CharField(max_length=20, null=True, blank=True, verbose_name="Cuenta Bancaria Comunal")
    contenido = models.TextField(verbose_name="Contenido del Acta")
    acuerdos = models.TextField(blank=True, verbose_name="Acuerdos Tomados")
    generado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="Generado por")
    fecha_generacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Generación")
    archivo_pdf = models.FileField(upload_to='actas/', blank=True, null=True, verbose_name="Archivo PDF")
    
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


# ============================================
# 🆕 NUEVO: Modelos para Gestión de Proyectos Comunitarios
# ============================================

class Comite(SoftDeleteModel):
    """
    Modelo que representa un comité del consejo comunal.
    Los proyectos se asignan a comités específicos.
    """
    TIPO_COMITE_CHOICES = [
        ('finanzas', 'Comité de Finanzas'),
        ('salud', 'Comité de Salud'),
        ('educacion', 'Comité de Educación'),
        ('vivienda', 'Comité de Vivienda'),
        ('deporte', 'Comité de Deporte y Recreación'),
        ('cultura', 'Comité de Cultura'),
        ('seguridad', 'Comité de Seguridad'),
        ('alimentacion', 'Comité de Alimentación'),
        ('medio_ambiente', 'Comité de Medio Ambiente'),
        ('otro', 'Otro Comité'),
    ]
    
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Comité")
    tipo_comite = models.CharField(
        max_length=50, 
        choices=TIPO_COMITE_CHOICES, 
        default='otro',
        verbose_name="Tipo de Comité"
    )
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    vocero_principal = models.ForeignKey(
        Habitante, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='comites_dirigidos',
        verbose_name="Vocero Principal"
    )
    fecha_creacion = models.DateField(auto_now_add=True, verbose_name="Fecha de Creación")
    activo = models.BooleanField(default=True, verbose_name="Comité Activo")
    
    class Meta:
        db_table = 'comites'
        verbose_name = 'Comité'
        verbose_name_plural = 'Comités'
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_comite_display()})"
    
    def cantidad_proyectos_activos(self):
        """Retorna la cantidad de proyectos activos del comité"""
        return self.proyectos.filter(is_deleted=False).exclude(estatus='cancelado').count()


class Proyecto(SoftDeleteModel):
    """
    Modelo que representa un proyecto comunitario.
    """
    ESTATUS_CHOICES = [
        ('planificacion', 'Planificación'),
        ('ejecucion', 'Ejecución'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ]
    
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Proyecto")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(null=True, blank=True, verbose_name="Fecha de Fin Estimada")
    descripcion = models.TextField(verbose_name="Descripción del Proyecto")
    monto_estimado = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name="Monto Estimado (Bs.)",
        help_text="Monto estimado en bolívares"
    )
    estatus = models.CharField(
        max_length=20, 
        choices=ESTATUS_CHOICES, 
        default='planificacion',
        verbose_name="Estatus del Proyecto"
    )
    comite = models.ForeignKey(
        Comite, 
        on_delete=models.PROTECT, 
        related_name='proyectos',
        verbose_name="Comité Responsable"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proyectos_creados',
        verbose_name="Creado por"
    )
    
    class Meta:
        db_table = 'proyectos'
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.nombre} ({self.get_estatus_display()})"
    
    def get_estatus_badge_class(self):
        """Retorna la clase CSS del badge según el estatus"""
        clases = {
            'planificacion': 'bg-info',
            'ejecucion': 'bg-warning',
            'finalizado': 'bg-success',
            'cancelado': 'bg-danger',
        }
        return clases.get(self.estatus, 'bg-secondary')
    
    def cantidad_integrantes(self):
        """Retorna la cantidad de integrantes del proyecto"""
        return self.integrantes.count()
    
    def duracion_dias(self):
        """Calcula la duración del proyecto en días"""
        if self.fecha_inicio and self.fecha_fin:
            return (self.fecha_fin - self.fecha_inicio).days
        return None


class ProyectoIntegrante(models.Model):
    """
    Modelo intermedio para la relación Proyecto - Habitante.
    Permite registrar el rol y fecha de asignación de cada integrante.
    """
    ROL_CHOICES = [
        ('coordinador', 'Coordinador'),
        ('ejecutor', 'Ejecutor'),
        ('contralor', 'Contralor'),
        ('colaborador', 'Colaborador'),
        ('beneficiario', 'Beneficiario'),
    ]
    
    proyecto = models.ForeignKey(
        Proyecto, 
        on_delete=models.CASCADE,
        related_name='integrantes',
        verbose_name="Proyecto"
    )
    habitante = models.ForeignKey(
        'Habitante',
        on_delete=models.CASCADE,
        related_name='proyectos_asignados',
        verbose_name="Habitante"
    )
    rol = models.CharField(
        max_length=20, 
        choices=ROL_CHOICES, 
        default='colaborador',
        verbose_name="Rol en el Proyecto"
    )
    fecha_asignacion = models.DateField(auto_now_add=True, verbose_name="Fecha de Asignación")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    
    class Meta:
        db_table = 'proyecto_integrantes'
        verbose_name = 'Integrante de Proyecto'
        verbose_name_plural = 'Integrantes de Proyecto'
        unique_together = ['proyecto', 'habitante']  # Un habitante solo puede estar una vez en cada proyecto
        ordering = ['proyecto', 'rol', 'habitante__nombre']
    
    def __str__(self):
        return f"{self.habitante.nombre} {self.habitante.apellido} - {self.get_rol_display()} en {self.proyecto.nombre}"
    @property
    def nombre_habitante(self):
        return f"{self.habitante.nombre} {self.habitante.apellido}"

    @property
    def documento_habitante(self):
        return self.habitante.cedula  # El campo en Habitante es 'cedula'


# ============================================
# 🆕 NUEVO: Modelos para Gestión de Censos Comunitarios
# ============================================

class Censo(SoftDeleteModel):
    """
    Modelo que representa una campaña de censo comunitario.
    Permite registrar habitantes participantes en cada censo.
    """
    CATEGORIA_ENFOQUE_CHOICES = [
        ('salud', 'Salud'),
        ('educacion', 'Educación'),
        ('vivienda', 'Vivienda'),
        ('desempleo', 'Desempleo'),
        ('nutricion', 'Nutrición'),
        ('seguridad', 'Seguridad'),
        ('servicios_publicos', 'Servicios Públicos'),
        ('poblacion', 'Censo Poblacional'),
        ('general', 'General'),
    ]
    
    ESTATUS_CHOICES = [
        ('activo', 'Activo'),
        ('cerrado', 'Cerrado'),
        ('archivado', 'Archivado'),
    ]
    
    nombre_censo = models.CharField(
        max_length=200, 
        verbose_name="Nombre del Censo",
        help_text="Nombre identificativo de la campaña de censo"
    )
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Fecha de Cierre"
    )
    descripcion = models.TextField(
        verbose_name="Descripción",
        help_text="Descripción detallada del objetivo del censo"
    )
    categoria_enfoque = models.CharField(
        max_length=50,
        choices=CATEGORIA_ENFOQUE_CHOICES,
        default='general',
        verbose_name="Categoría de Enfoque"
    )
    estatus = models.CharField(
        max_length=20,
        choices=ESTATUS_CHOICES,
        default='activo',
        verbose_name="Estatus del Censo"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='censos_creados',
        verbose_name="Creado por"
    )
    # Relación ManyToMany con Habitante a través de CensoParticipante
    participantes = models.ManyToManyField(
        'Habitante',
        through='CensoParticipante',
        related_name='censos_participados',
        blank=True,
        verbose_name="Participantes"
    )
    
    class Meta:
        db_table = 'censos'
        verbose_name = 'Censo'
        verbose_name_plural = 'Censos'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.nombre_censo} ({self.get_estatus_display()})"
    
    def get_estatus_badge_class(self):
        """Retorna la clase CSS del badge según el estatus"""
        clases = {
            'activo': 'bg-success',
            'cerrado': 'bg-secondary',
            'archivado': 'bg-light text-dark',
        }
        return clases.get(self.estatus, 'bg-secondary')
    
    def get_categoria_badge_class(self):
        """Retorna la clase CSS del badge según la categoría"""
        clases = {
            'salud': 'bg-danger',
            'educacion': 'bg-primary',
            'vivienda': 'bg-warning text-dark',
            'desempleo': 'bg-info',
            'nutricion': 'bg-success',
            'seguridad': 'bg-dark',
            'servicios_publicos': 'bg-secondary',
            'poblacion': 'bg-purple',
            'general': 'bg-light text-dark',
        }
        return clases.get(self.categoria_enfoque, 'bg-secondary')
    
    def cantidad_participantes(self):
        """Retorna la cantidad de participantes en el censo"""
        return self.participantes.count()
    
    def duracion_dias(self):
        """Calcula la duración del censo en días"""
        if self.fecha_inicio and self.fecha_fin:
            return (self.fecha_fin - self.fecha_inicio).days
        return None
    
    def esta_activo(self):
        """Verifica si el censo está activo"""
        return self.estatus == 'activo'


class CensoParticipante(models.Model):
    """
    Modelo intermedio para la relación Censo - Habitante.
    Registra qué habitantes participan en cada censo con fecha y observaciones.
    """
    censo = models.ForeignKey(
        Censo,
        on_delete=models.CASCADE,
        related_name='participantes_censo',
        verbose_name="Censo"
    )
    habitante = models.ForeignKey(
        'Habitante',
        on_delete=models.CASCADE,
        related_name='participaciones_censo',
        verbose_name="Habitante"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones",
        help_text="Notas adicionales sobre la participación del habitante"
    )
    
    class Meta:
        db_table = 'censo_participantes'
        verbose_name = 'Participante de Censo'
        verbose_name_plural = 'Participantes de Censo'
        unique_together = ['censo', 'habitante']  # Un habitante solo puede registrarse una vez por censo
        ordering = ['censo', 'fecha_registro', 'habitante__nombre']
    
    def __str__(self):
        return f"{self.habitante.nombre} {self.habitante.apellido} - {self.censo.nombre_censo}"
    @property
    def nombre_habitante(self):
        return f"{self.habitante.nombre} {self.habitante.apellido}"
        
    @property
    def documento_habitante(self):
        return self.habitante.cedula
    
    # @property
    # def telefono_habitante(self):
    #     return self.habitante.telefono or ''

from django.db import models
from django.conf import settings
from datetime import date
from django.db.models import Q

class ReporteDemografico(models.Model):
    """
    Modelo para la configuración, control y auditoría de reportes 
    estructurados de Familias y Habitantes del Consejo Comunal.
    """
    OPCIONES_GENERO = [
        ('TODOS', 'Todos'),
        ('M', 'Masculino'),
        ('F', 'Femenino'),
    ]
    
    OPCIONES_EDAD = [
        ('TODOS', 'Todas las edades'),
        ('MENOR_12', 'Niños (Menores a 12 años)'),
        ('MENOR_16', 'Adolescentes (Menores a 16 años)'),
        ('TERCERA_EDAD', 'Adultos Mayores / 3ra Edad (>= 60 años)'),
    ]

    OPCIONES_FORMATO = [
        ('PDF', 'Documento PDF (.pdf)'),
        ('EXCEL', 'Hoja de Cálculo (.xlsx)'),
        ('AMBOS', 'Ambos Formatos'),
    ]

    # 1. Metadatos del Reporte
    titulo_reporte = models.CharField(max_length=150, verbose_name="Título del Reporte")
    solicitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="Generado por"
    )
    fecha_generacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")

    # 2. Parámetros / Filtros aplicados (Condiciones)
    filtro_genero = models.CharField(max_length=5, choices=OPCIONES_GENERO, default='TODOS', verbose_name="Filtro de Género")
    filtro_edad = models.CharField(max_length=15, choices=OPCIONES_EDAD, default='TODOS', verbose_name="Segmentación por Edad")
    incluir_datos_familia = models.BooleanField(default=True, verbose_name="Desglosar por Grupo Familiar")
    
    formato_salida = models.CharField(max_length=10, choices=OPCIONES_FORMATO, default='AMBOS', verbose_name="Formato Solicitado")
    
    # 3. Campos de auditoría opcionales (por si deseas guardar el archivo físico en el servidor)
    archivo_pdf = models.FileField(upload_to='reportes/pdfs/', blank=True, null=True, verbose_name="Archivo PDF")
    archivo_excel = models.FileField(upload_to='reportes/excels/', blank=True, null=True, verbose_name="Archivo Excel")

    class Meta:
        db_table = 'cc_reportes_demograficos'
        verbose_name = 'Reporte Demográfico'
        verbose_name_plural = 'Reportes Demográficos'
        ordering = ['-fecha_generacion']

    def __str__(self):
        return f"{self.titulo_reporte} - {self.fecha_generacion.strftime('%d/%m/%Y %H:%M')}"