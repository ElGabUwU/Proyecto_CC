from django.db import models
from django.conf import settings
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
        
        # Restricción en la Base de Datos (PostgreSQL): 
        # Evita que existan dos jefes activos en la misma familia.
        constraints = [
            models.UniqueConstraint(
                fields=['familia'],
                condition=models.Q(es_jefe_familia=True, is_deleted=False),
                name='unique_jefe_activo_por_familia'
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
    asistentes = models.TextField(verbose_name="Lista de Asistentes")  # Separados por comas o texto libre
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
        return len(self.asistentes.split(',')) if self.asistentes else 0