from django.http import HttpResponse
# from .resources import PersonResource, TutorsResource
# from .models import Person, Tutors
import pandas as pd
import io
# from .models import Tutors, Students, Person, User
from myapp.decorators import admin_export_required

# @admin_export_required
# def export_persons(request):

#     format_param = request.GET.get('format', 'xlsx')
#     # Exportar solo personas (como en cedulas.html)
#     from .models import Students
#     student_person_ids = Students.objects.filter(is_deleted=False).values_list('person_id', flat=True)
#     persons = Person.objects.filter(is_deleted=False, id__in=student_person_ids)
#     data = []
#     for p in persons:
#         data.append({
#             'Tipo de Documento': p.get_type_document_display() if hasattr(p, 'get_type_document_display') else '',
#             'Número de Documento': p.document_number,
#             'Nombres': p.name,
#             'Apellidos': p.surname,
#             'Teléfono': p.telephone_number,
#             'Email': p.email,
#             'Fecha Nac.': p.date_of_birth.strftime('%d/%m/%Y') if p.date_of_birth else '',
#             'Sexo': p.get_gender_display() if hasattr(p, 'get_gender_display') else '',
#             'País de Origen': p.pais_origen or '',
#             'C.Represe': p.progenitor_document_number or '',
#             'Representante': p.progenitor_name or '',
#         })
#     df = pd.DataFrame(data)
#     if format_param == 'csv':
#         buffer = io.StringIO()
#         df.to_csv(buffer, index=False, encoding='utf-8-sig')
#         content_type = 'text/csv'
#         ext = 'csv'
#         data_out = buffer.getvalue()
#         response = HttpResponse(data_out, content_type=content_type)
#     else:
#         buffer = io.BytesIO()
#         with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
#             df.to_excel(writer, index=False)
#         content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#         ext = 'xlsx'
#         response = HttpResponse(buffer.getvalue(), content_type=content_type)
#     response['Content-Disposition'] = f'attachment; filename="reporte_estudiantes.{ext}"'
#     return response


# @admin_export_required
# def export_tutors(request):
#     format_param = request.GET.get('format', 'xlsx')
#     tutors = Tutors.objects.select_related('person', 'user').all()
#     data = []
#     for t in tutors:
#         p = t.person
#         u = t.user
#         data.append({
#             'Tipo de Documento': p.get_type_document_display() if hasattr(p, 'get_type_document_display') else '',
#             'Número de Documento': p.document_number,
#             'Nombres': p.name,
#             'Apellidos': p.surname,
#             'Teléfono': p.telephone_number,
#             'Email': p.email,
#             'Fecha Nac.': p.date_of_birth.strftime('%d/%m/%Y') if p.date_of_birth else '',
#             'Sexo': p.get_gender_display() if hasattr(p, 'get_gender_display') else '',
#             'País de Origen': p.pais_origen or '',
#             'Usuario': u.username if u else '',
#             'Cargo': t.get_staff_position_display() if hasattr(t, 'get_staff_position_display') else '',
#         })
#     df = pd.DataFrame(data)
#     if format_param == 'csv':
#         buffer = io.StringIO()
#         df.to_csv(buffer, index=False, encoding='utf-8-sig')
#         content_type = 'text/csv'
#         ext = 'csv'
#         data_out = buffer.getvalue()
#         response = HttpResponse(data_out, content_type=content_type)
#     else:
#         buffer = io.BytesIO()
#         with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
#             df.to_excel(writer, index=False)
#         content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#         ext = 'xlsx'
#         response = HttpResponse(buffer.getvalue(), content_type=content_type)
#     response['Content-Disposition'] = f'attachment; filename="reporte_docentes.{ext}"'
#     return response
