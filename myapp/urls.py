from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views
from . import views_export
from .views import PersonApiView, DocenteApiView
from .views import change_password

from . import views_comunidad

urlpatterns = [
    path('', views.home, name='home'),  # Esto debe estar definido en views.py
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('welcome/', views.welcome, name='welcome'),

    # Endpoint para cambio de contraseña forzado
    path('change_password/', change_password, name='change_password'),

    
    path('cedulas/', views.PersonView.as_view(), name='cedulas'),
    path('cedulas/editar/<int:id>/', views.UpdatePersonView.as_view(), name='editar_persona'),
    path('cedulas/eliminar/<int:id>/', views.DeletePersonView.as_view(), name='eliminar_persona'),
    path('docentes/', views.DocenteView.as_view(), name='docentes'),
    path('docentes/editar/<int:id>/', views.UpdateDocenteView.as_view(), name='editar_docente'),
    path('cedulas/api/<int:id>/', PersonApiView.as_view(), name='person_api'),
    path('docentes/api/<int:id>/', DocenteApiView.as_view(), name='docente_api'),
    path('docentes/eliminar/<int:id>/', views.DeleteDocenteView.as_view(), name='eliminar_docente'),
    path('usuarios/', views.UserView.as_view(), name='usuarios'),
    path('usuarios/editar/<int:id>/', views.UpdateUserView.as_view(), name='editar_usuario'),
    path('usuarios/eliminar/<int:id>/', views.DeleteUserView.as_view(), name='eliminar_usuario'),
    
    # Perfil de usuario
    path('todolist/', views.TodoListView.as_view(), name='todolist'),
    path('todolist/update/<int:id>/', views.UpdateTodoView.as_view(), name='update_todo'),
    path('todolist/delete/<int:id>/', views.DeleteTodoView.as_view(), name='delete_todo'),
    path('cursos/', views.CourseView.as_view(), name='cursos'),
    path('cursos/editar/<int:id>/', views.UpdateCourseView.as_view(), name='editar_curso'),
    path('cursos/eliminar/<int:id>/', views.DeleteCourseView.as_view(), name='eliminar_curso'),
    path('cursos/<int:course_id>/niveles/', views.LevelView.as_view(), name='niveles'),
    path('niveles/editar/<int:id>/', views.UpdateLevelView.as_view(), name='editar_nivel'),
    path('niveles/eliminar/<int:id>/', views.DeleteLevelView.as_view(), name='eliminar_nivel'),
    path('secciones/<int:level_id>/', views.SeccionView.as_view(), name='secciones'),
    path('secciones/level/<int:level_id>/unit/add/', views.UnitCreateView.as_view(), name='add_unit'),
    path('secciones/unit/<int:unit_id>/edit/', views.UnitUpdateView.as_view(), name='edit_unit'),
    path('secciones/update-order/', views.UpdateUnitOrderView.as_view(), name='update_unit_order'),
    path('secciones/unit/<int:unit_id>/', views.UnitJsonView.as_view(), name='unit_json'),
    path('secciones/unit/delete/<int:unit_id>/', views.DeleteUnitView.as_view(), name='delete_unit'),

# NUEVO

    path('grupos/', views.GrupoView.as_view(), name='grupos'),
    path('grupos/<int:level_id>/', views.GrupoView.as_view(), name='grupos_level'),
    path('grupos/editar/<int:id>/', views.UpdateGrupoView.as_view(), name='editar_grupo'),
    path('grupos/eliminar/<int:id>/', views.DeleteGrupoView.as_view(), name='eliminar_grupo'),
    path('grupos/api/<int:id>/', views.GrupoApiView.as_view(), name='grupo_api'),
    path('grupos/api/<int:id>/students/', views.GrupoStudentsApiView.as_view(), name='grupo_students_api'),
    path('grupos/<int:id>/add-student/', views.AddStudentToGroupView.as_view(), name='add_student_to_group'),
    path('grupos/<int:id>/remove-student/', views.RemoveStudentFromGroupView.as_view(), name='remove_student_from_group'),
    path('api/students/search/', views.StudentSearchApiView.as_view(), name='student_search_api'),

    path('evaluaciones/', views.EvaluacionesListView.as_view(), name='evaluaciones'),
    path('grupos/<int:group_id>/evaluaciones/', views.EvaluacionesListView.as_view(), name='evaluaciones_grupo'),
    path('grupos/<int:group_id>/evaluaciones/crear/', views.CrearEvaluacionView.as_view(), name='crear_evaluacion'),
    path('grupos/<int:group_id>/evaluaciones/<int:evaluacion_id>/editar/', views.EditarEvaluacionView.as_view(), name='editar_evaluacion'),
    path('grupos/<int:group_id>/evaluaciones/<int:evaluacion_id>/eliminar/', views.EliminarEvaluacionView.as_view(), name='eliminar_evaluacion'),
    path('grupos/<int:group_id>/evaluaciones/<int:evaluacion_id>/api/', views.EvaluacionApiView.as_view(), name='evaluacion_api'),
    path('evaluaciones/api/porcentaje-total/<int:group_id>/', views.PorcentajeTotalApiView.as_view(), name='porcentaje_total_api'),
    
    # Calificar evaluación (para profesores)
    path('evaluaciones/<int:evaluacion_id>/calificar/', views.CalificarEvaluacionView.as_view(), name='calificar_evaluacion'),
    
    path('notas/', views.NotasView.as_view(), name='notas'),
    path('addgroup/', views.AñadirGrupoView.as_view(), name='addgroup'),
    path('addgroup/<int:level_id>/', views.AñadirGrupoView.as_view(), name='addgroup_level'),
    path('perfil/', views.perfil_view, name='perfil'),

    path('misnotas/', views.MisNotasView.as_view(), name='mis_notas'),

    # Subir imagen para tinyMCE
    path('upload-image/', views.upload_image, name='upload_image'),

    # test zone (BORRAR AL SALIR DE DESARROLLO)
    path('test-zone/', views.test_zone, name='test_zone'),

    # Pagos (BASICO SOLO VISTA SIN FUNCIONALIDAD)
    path('pagos/', views.PagosView.as_view(), name='pagos'),


    # Exportar datos
    path('cedulas/export/', views_export.export_persons, name='export_persons'),
    path('docentes/export/', views_export.export_tutors, name='export_tutors'),

    # Calendario
    # path('calendario/', views.calendario_view, name='calendario'),
    # path('json/', views.eventos_json, name='eventos_json'),
    # path('guardar-evento/', views.guardar_evento, name='guardar_evento'),
    # path('modificar-evento/<int:evento_id>/', views.modificar_evento, name='modificar_evento'),
    # path('eliminar-evento/<int:evento_id>/', views.eliminar_evento, name='eliminar_evento'),
    # path('json/', views.eventos_json, name='eventos_json'),
    # path('calendario/guardar/', views.guardar_evento, name='guardar_evento'),
    # path('calendario/modificar/<int:evento_id>/', views.modificar_evento, name='modificar_evento'),
    # path('calendario/eliminar/<int:evento_id>/', views.eliminar_evento, name='eliminar_evento'),
    
    
    # Familias
    path('familias/', views_comunidad.familias, name='familias'),
    path('familias/crear/', views_comunidad.crear_familia, name='crear_familia'),
    path('familias/editar/<int:id>/', views_comunidad.editar_familia, name='editar_familia'),
    path('familias/eliminar/<int:id>/', views_comunidad.eliminar_familia, name='eliminar_familia'),
    path('familias/api/<int:id>/', views_comunidad.api_familia, name='api_familia'),
    
    # Habitantes
    path('habitantes/', views_comunidad.habitantes, name='habitantes'),
    path('habitantes/crear/', views_comunidad.crear_habitante, name='crear_habitante'),
    path('habitantes/editar/<int:id>/', views_comunidad.editar_habitante, name='editar_habitante'),
    path('habitantes/eliminar/<int:id>/', views_comunidad.eliminar_habitante, name='eliminar_habitante'),
    path('habitantes/api/<int:id>/', views_comunidad.api_habitante, name='api_habitante'),
    path('habitantes/familia/<int:familia_id>/', views_comunidad.habitantes_familia, name='habitantes_familia'),
    path('habitantes/detalle/<int:id>/', views_comunidad.detalle_habitante, name='detalle_habitante'),
    
    # Finanzas
    path('finanzas/', views_comunidad.finanzas, name='finanzas'),
    path('finanzas/ingresos/crear/', views_comunidad.crear_ingreso, name='crear_ingreso'),
    path('finanzas/ingresos/editar/<int:id>/', views_comunidad.editar_ingreso, name='editar_ingreso'),
    path('finanzas/ingresos/eliminar/<int:id>/', views_comunidad.eliminar_ingreso, name='eliminar_ingreso'),
    path('finanzas/ingresos/api/<int:id>/', views_comunidad.api_ingreso, name='api_ingreso'),
    path('finanzas/egresos/crear/', views_comunidad.crear_egreso, name='crear_egreso'),
    path('finanzas/egresos/editar/<int:id>/', views_comunidad.editar_egreso, name='editar_egreso'),
    path('finanzas/egresos/eliminar/<int:id>/', views_comunidad.eliminar_egreso, name='eliminar_egreso'),
    path('finanzas/egresos/api/<int:id>/', views_comunidad.api_egreso, name='api_egreso'),
    path('finanzas/exportar/', views_comunidad.exportar_finanzas, name='exportar_finanzas'),
    
    # Documentación
    path('documentacion/', views_comunidad.documentacion, name='documentacion'),
    path('documentacion/constancia/', views_comunidad.generar_constancia, name='generar_constancia'),
    path('documentacion/constancia/descargar/<int:id>/', views_comunidad.descargar_constancia, name='descargar_constancia'),
    path('documentacion/constancia/previa/<int:id>/', views_comunidad.previa_constancia, name='previa_constancia'),
    path('documentacion/acta/', views_comunidad.generar_acta, name='generar_acta'),
    path('documentacion/acta/descargar/<int:id>/', views_comunidad.descargar_acta, name='descargar_acta'),
    path('documentacion/acta/previa/<int:id>/', views_comunidad.previa_acta, name='previa_acta'),
    
    # Dashboard Comunitario
    path('dashboard-comunitario/', views_comunidad.dashboard_comunitario, name='dashboard_comunitario'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)