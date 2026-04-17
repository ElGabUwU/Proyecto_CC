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
