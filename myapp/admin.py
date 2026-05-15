from import_export import resources
from import_export.admin import ImportExportModelAdmin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

# Register your models here.
admin.site.register(Students) #Registro para estudiantes
admin.site.register(Units) #Registro para unidades
admin.site.register(Courses) #Registro para cursos
admin.site.register(Levels) #Registro para niveles
admin.site.register(Group_Levels) #Registro para grupos de niveles
admin.site.register(Grade_Students) #Registro para calificaciones de estudiantes
admin.site.register(Testing) #Registro para evaluaciones
admin.site.register(Tutors) #Registro para tutores

class PersonResource(resources.ModelResource):
    fields = ('id', 'name', 'surname', 'type_document', 'document_number', 'telephone_number',
              'progenitor_name', 'progenitor_document_number', 'email', 'date_of_birth',
              'gender', 'pais_origen')

    class Meta:
        model = Person
@admin.register(Person)
class PersonAdmin(ImportExportModelAdmin):
    resource_class = PersonResource
    list_display= ('id', 'name', 'surname','type_document', 
                   'document_number','telephone_number','progenitor_name',
                   'progenitor_document_number','email', 'date_of_birth', 
                   'gender', 'pais_origen')
    search_fields= ('name', 'surname', 'document_number', 'email')
    list_editable=('email', 'telephone_number', 'date_of_birth',)
    list_per_page= 20
    exclude = ('id',)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display= ('id', 'username', 'email', 'role')
    list_editable=('username', 'email', 'role',)
    list_per_page= 15


# ============================================
# 🆕 NUEVO: Registro de modelos comunitarios
# ============================================

@admin.register(Familia)
class FamiliaAdmin(admin.ModelAdmin):
    list_display = ('id', 'jefe_familia', 'direccion', 'telefono_contacto', 'fecha_registro', 'cantidad_habitantes')
    list_filter = ('fecha_registro', 'is_deleted')
    search_fields = ('jefe_familia__name', 'jefe_familia__surname', 'direccion', 'telefono_contacto')
    raw_id_fields = ('jefe_familia',)
    list_per_page = 20
    
    def cantidad_habitantes(self, obj):
        return obj.habitante_set.count()
    cantidad_habitantes.short_description = 'Habitantes'


@admin.register(Habitante)
class HabitanteAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'surname', 'document_number', 'familia', 'parentesco_jefe', 'nivel_educativo', 'ocupacion')
    list_filter = ('parentesco_jefe', 'nivel_educativo', 'familia', 'is_deleted')
    search_fields = ('name', 'surname', 'document_number', 'familia__jefe_familia__name')
    raw_id_fields = ('familia',)
    list_per_page = 25
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('type_document', 'document_number', 'name', 'surname', 
                      'telephone_number', 'email', 'date_of_birth', 'gender', 'pais_origen')
        }),
        ('Información Comunitaria', {
            'fields': ('familia', 'parentesco_jefe', 'nivel_educativo', 'ocupacion',
                      'ingresos_mensuales', 'condiciones_salud', 'fecha_registro_comunitario')
        }),
        ('Estado', {
            'fields': ('is_deleted', 'deleted_at')
        }),
    )


@admin.register(IngresoComunal)
class IngresoComunalAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'tipo_ingreso', 'concepto', 'monto', 'responsable', 'fecha_registro')
    list_filter = ('tipo_ingreso', 'fecha', 'responsable')
    search_fields = ('concepto', 'responsable__username', 'responsable__email')
    date_hierarchy = 'fecha'
    list_per_page = 20
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('responsable')


@admin.register(EgresoComunal)
class EgresoComunalAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'tipo_egreso', 'concepto', 'monto', 'beneficiario', 'responsable', 'fecha_registro')
    list_filter = ('tipo_egreso', 'fecha', 'responsable')
    search_fields = ('concepto', 'beneficiario', 'responsable__username', 'responsable__email')
    date_hierarchy = 'fecha'
    list_per_page = 20
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('responsable')


@admin.register(ConstanciaResidencia)
class ConstanciaResidenciaAdmin(admin.ModelAdmin):
    list_display = ('id', 'familia', 'fecha_documento', 'fecha_generacion', 'generado_por')
    list_filter = ('fecha_documento', 'fecha_generacion')
    search_fields = ('familia__jefe_familia__name', 'familia__jefe_familia__surname', 'finalidad')
    date_hierarchy = 'fecha_generacion'
    list_per_page = 15
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('familia', 'generado_por')


@admin.register(ActaReunion)
class ActaReunionAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'fecha_reunion', 'lugar', 'asistentes_count', 'generado_por', 'fecha_generacion')
    list_filter = ('fecha_reunion', 'generado_por')
    search_fields = ('titulo', 'lugar', 'asistentes', 'contenido')
    date_hierarchy = 'fecha_reunion'
    list_per_page = 15
    
    def asistentes_count(self, obj):
        return obj.asistentes_count()
    asistentes_count.short_description = 'Asistentes'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('generado_por')