import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0029_calendario_activo'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActaReunion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=200, verbose_name='Título del Acta')),
                ('fecha_reunion', models.DateTimeField(verbose_name='Fecha y Hora de la Reunión')),
                ('lugar', models.CharField(max_length=200, verbose_name='Lugar de la Reunión')),
                ('asistentes', models.TextField(verbose_name='Lista de Asistentes')),
                ('contenido', models.TextField(verbose_name='Contenido del Acta')),
                ('acuerdos', models.TextField(blank=True, verbose_name='Acuerdos Tomados')),
                ('fecha_generacion', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Generación')),
                ('archivo_pdf', models.FileField(blank=True, null=True, upload_to='actas/', verbose_name='Archivo PDF')),
                ('generado_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL, verbose_name='Generado por')),
            ],
            options={
                'verbose_name': 'Acta de Reunión',
                'verbose_name_plural': 'Actas de Reunión',
                'db_table': 'actas_reunion',
                'ordering': ['-fecha_reunion'],
            },
        ),
        migrations.CreateModel(
            name='EgresoComunal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(verbose_name='Fecha del Egreso')),
                ('tipo_egreso', models.CharField(choices=[('mantenimiento', 'Mantenimiento Comunitario'), ('servicios', 'Servicios Públicos'), ('actividades', 'Actividades Comunitarias'), ('emergencias', 'Emergencias'), ('administrativos', 'Gastos Administrativos'), ('otros', 'Otros Egresos')], default='mantenimiento', max_length=50, verbose_name='Tipo de Egreso')),
                ('concepto', models.CharField(max_length=200, verbose_name='Concepto')),
                ('monto', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Monto (Bs.)')),
                ('beneficiario', models.CharField(blank=True, max_length=200, verbose_name='Beneficiario')),
                ('soporte', models.FileField(blank=True, null=True, upload_to='soportes/egresos/', verbose_name='Soporte')),
                ('observaciones', models.TextField(blank=True, verbose_name='Observaciones')),
                ('fecha_registro', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Registro')),
                ('responsable', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='egresos_registrados', to=settings.AUTH_USER_MODEL, verbose_name='Responsable')),
            ],
            options={
                'verbose_name': 'Egreso Comunal',
                'verbose_name_plural': 'Egresos Comunales',
                'db_table': 'egresos_comunales',
                'ordering': ['-fecha', '-fecha_registro'],
            },
        ),
        migrations.CreateModel(
            name='Familia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='Eliminado')),
                ('deleted_at', models.DateTimeField(blank=True, default=None, null=True, verbose_name='Fecha de eliminación')),
                ('direccion', models.TextField(verbose_name='Dirección Completa')),
                ('numero_vivienda', models.CharField(blank=True, max_length=10, verbose_name='Número de Vivienda')),
                ('telefono_contacto', models.CharField(max_length=15, verbose_name='Teléfono de Contacto')),
                ('fecha_registro', models.DateField(auto_now_add=True, verbose_name='Fecha de Registro')),
                ('observaciones', models.TextField(blank=True, verbose_name='Observaciones')),
                ('jefe_familia', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='myapp.person', verbose_name='Jefe de Familia')),
            ],
            options={
                'verbose_name': 'Familia',
                'verbose_name_plural': 'Familias',
                'db_table': 'familias',
                'ordering': ['-fecha_registro'],
            },
        ),
        migrations.CreateModel(
            name='ConstanciaResidencia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_generacion', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Generación')),
                ('fecha_documento', models.DateField(verbose_name='Fecha del Documento')),
                ('finalidad', models.TextField(verbose_name='Finalidad de la Constancia')),
                ('contenido', models.TextField(verbose_name='Contenido de la Constancia')),
                ('archivo_pdf', models.FileField(blank=True, null=True, upload_to='constancias/', verbose_name='Archivo PDF')),
                ('generado_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL, verbose_name='Generado por')),
                ('familia', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='myapp.familia', verbose_name='Familia')),
            ],
            options={
                'verbose_name': 'Constancia de Residencia',
                'verbose_name_plural': 'Constancias de Residencia',
                'db_table': 'constancias_residencia',
                'ordering': ['-fecha_generacion'],
            },
        ),
        migrations.CreateModel(
            name='IngresoComunal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(verbose_name='Fecha del Ingreso')),
                ('tipo_ingreso', models.CharField(choices=[('aportes', 'Aportes de Familias'), ('donaciones', 'Donaciones'), ('actividades', 'Actividades Comunitarias'), ('subvenciones', 'Subvenciones'), ('otros', 'Otros Ingresos')], default='aportes', max_length=50, verbose_name='Tipo de Ingreso')),
                ('concepto', models.CharField(max_length=200, verbose_name='Concepto')),
                ('monto', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Monto (Bs.)')),
                ('soporte_digital', models.FileField(blank=True, null=True, upload_to='soportes/ingresos/', verbose_name='Soporte Digital')),
                ('observaciones', models.TextField(blank=True, verbose_name='Observaciones')),
                ('fecha_registro', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Registro')),
                ('responsable', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ingresos_registrados', to=settings.AUTH_USER_MODEL, verbose_name='Responsable')),
            ],
            options={
                'verbose_name': 'Ingreso Comunal',
                'verbose_name_plural': 'Ingresos Comunales',
                'db_table': 'ingresos_comunales',
                'ordering': ['-fecha', '-fecha_registro'],
            },
        ),
        migrations.CreateModel(
            name='Habitante',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='Eliminado')),
                ('deleted_at', models.DateTimeField(blank=True, default=None, null=True, verbose_name='Fecha de eliminación')),
                ('parentesco_jefe', models.CharField(choices=[('Jefe', 'Jefe de Familia'), ('Esposa/Esposo', 'Esposa/Esposo'), ('Hijo/Hija', 'Hijo/Hija'), ('Nieto/Nieta', 'Nieto/Nieta'), ('Padre/Madre', 'Padre/Madre'), ('Hermano/Hermana', 'Hermano/Hermana'), ('Otro', 'Otro Parentesco')], default='Jefe', max_length=50, verbose_name='Parentesco con Jefe de Familia')),
                ('nivel_educativo', models.CharField(blank=True, choices=[('ninguno', 'Ninguno'), ('primaria', 'Primaria'), ('secundaria', 'Secundaria'), ('tecnico', 'Técnico Medio'), ('universitario', 'Universitario'), ('postgrado', 'Postgrado')], max_length=100, verbose_name='Nivel Educativo')),
                ('ocupacion', models.CharField(blank=True, max_length=100, verbose_name='Ocupación')),
                ('ingresos_mensuales', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Ingresos Mensuales (Bs.)')),
                ('condiciones_salud', models.TextField(blank=True, verbose_name='Condiciones de Salud')),
                ('fecha_registro_comunitario', models.DateField(auto_now_add=True, verbose_name='Fecha Registro Comunitario')),
                ('familia', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='myapp.familia', verbose_name='Familia')),
                ('persona', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='myapp.person', verbose_name='Persona')),
            ],
            options={
                'verbose_name': 'Habitante',
                'verbose_name_plural': 'Habitantes',
                'db_table': 'habitantes',
                'ordering': ['familia', 'parentesco_jefe', 'persona__name'],
                'unique_together': {('persona', 'familia')},
            },
        ),
    ]
