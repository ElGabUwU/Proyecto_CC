from import_export import resources
from import_export.admin import ImportExportModelAdmin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

# Register your models here.
# admin.site.register(Students) #Registro para estudiantes
# admin.site.register(Units) #Registro para unidades
# admin.site.register(Courses) #Registro para cursos
# admin.site.register(Levels) #Registro para niveles
# admin.site.register(Group_Levels) #Registro para grupos de niveles
# admin.site.register(Grade_Students) #Registro para calificaciones de estudiantes
# admin.site.register(Testing) #Registro para evaluaciones
# admin.site.register(Tutors) #Registro para tutores

# class PersonResource(resources.ModelResource):
#     fields = ('id', 'name', 'surname', 'type_document', 'document_number', 'telephone_number',
#               'progenitor_name', 'progenitor_document_number', 'email', 'date_of_birth',
#               'gender', 'pais_origen')

#     class Meta:
#         model = Person
# @admin.register(Person)
# class PersonAdmin(ImportExportModelAdmin):
#     resource_class = PersonResource
#     list_display= ('id', 'name', 'surname','type_document', 
#                    'document_number','telephone_number','progenitor_name',
#                    'progenitor_document_number','email', 'date_of_birth', 
#                    'gender', 'pais_origen')
#     search_fields= ('name', 'surname', 'document_number', 'email')
#     list_editable=('email', 'telephone_number', 'date_of_birth',)
#     list_per_page= 20
#     exclude = ('id',)

# @admin.register(User)
# class UserAdmin(admin.ModelAdmin):
#     list_display= ('id', 'username', 'email', 'role')
#     list_editable=('username', 'email', 'role',)
#     list_per_page= 15


# ============================================
# 🆕 NUEVO: Registro de modelos comunitarios
# ============================================

@admin.register(Familia)
class FamiliaAdmin(admin.ModelAdmin):
    # 'telefono_contacto' eliminado de list_display porque ya no existe en el modelo
    list_display = ('nombre_familia', 'vivienda', 'catastro', 'get_jefe_familia', 'fecha_registro', 'is_deleted')
    list_filter = ('is_deleted', 'fecha_registro')
    search_fields = ('nombre_familia', 'vivienda', 'catastro', 'direccion')
    
    # SOLUCIÓN E002: Se eliminó 'jefe_familia' de raw_id_fields porque ya no es una columna física FK
    raw_id_fields = () 

    # Método personalizado para mostrar el jefe de familia de forma dinámica en la lista
    def get_jefe_familia(self, obj):
        jefe = obj.jefe_familia
        return f"{jefe.nombre} {jefe.apellido}" if jefe else "Sin Jefe Asignado"
    get_jefe_familia.short_description = 'Jefe de Familia'


@admin.register(Habitante)
class HabitanteAdmin(admin.ModelAdmin):
    # SOLUCIÓN E108: Se cambiaron 'name', 'surname' y 'document_number' por 'nombre', 'apellido' y 'cedula'
    # SOLUCIÓN E108/E116: Se cambió 'parentesco_jefe' por 'es_jefe_familia'
    list_display = ('cedula', 'nombre', 'apellido', 'familia', 'es_jefe_familia', 'genero', 'is_deleted')
    list_filter = ('es_jefe_familia', 'genero', 'nivel_educativo', 'is_deleted')
    search_fields = ('cedula', 'nombre', 'apellido', 'ocupacion')
    raw_id_fields = ('familia',)


@admin.register(ConstanciaResidencia)
class ConstanciaResidenciaAdmin(admin.ModelAdmin):
    # SOLUCIÓN E108: El campo 'familia' no está directo en ConstanciaResidencia, se accede mediante el Habitante
    list_display = ('habitante', 'get_familia_solicitante', 'fecha_documento', 'generado_por', 'fecha_generacion')
    list_filter = ('fecha_documento', 'fecha_generacion')
    search_fields = ('habitante__nombre', 'habitante__apellido', 'habitante__cedula', 'finalidad')
    raw_id_fields = ('habitante', 'generado_por')

    # Método para traer la familia del habitante que solicita la constancia
    def get_familia_solicitante(self, obj):
        return obj.habitante.familia.nombre_familia
    get_familia_solicitante.short_description = 'Familia / Hogar'


@admin.register(IngresoComunal)
class IngresoComunalAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'tipo_ingreso', 'concepto', 'monto', 'responsable')
    list_filter = ('tipo_ingreso', 'fecha')
    search_fields = ('concepto', 'observaciones')
    raw_id_fields = ('responsable',)


@admin.register(EgresoComunal)
class EgresoComunalAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'tipo_egreso', 'concepto', 'monto', 'beneficiario', 'responsable')
    list_filter = ('tipo_egreso', 'fecha')
    search_fields = ('concepto', 'beneficiario', 'observaciones')
    raw_id_fields = ('responsable',)


@admin.register(ActaReunion)
class ActaReunionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'fecha_reunion', 'lugar', 'generado_por')
    list_filter = ('fecha_reunion', 'fecha_generacion')
    search_fields = ('titulo', 'contenido', 'acuerdos', 'lugar')
    raw_id_fields = ('generado_por',)