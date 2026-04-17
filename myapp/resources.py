from import_export import resources
from .models import Person, Tutors

class PersonResource(resources.ModelResource):
    class Meta:
        model = Person
        fields = ('id', 'type_document', 'document_number', 'name', 'surname', 'telephone_number', 'email', 'date_of_birth', 'gender', 'nationality', 'progenitor_document_number', 'progenitor_name')

class TutorsResource(resources.ModelResource):
    class Meta:
        model = Tutors
        fields = ('id', 'person', 'user', 'staff_position')
