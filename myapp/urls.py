from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from . import views_comunidad
from . import views_proyectos
from . import views_actividad
from .views import PersonApiView, DocenteApiView
from .views import change_password

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('welcome/', views.welcome, name='welcome'),

    # ============================================
    # Dashboard Comunitario
    # ============================================
    # path('welcome/', views_comunidad.welcome, name='dashboard_comunitario'),
    # Endpoint para cambio de contraseña forzado
    path('change_password/', change_password, name='change_password'),

    # ============================================
    # NUEVA ARQUITECTURA: Familias y Habitantes (Maestro-Detalle)
    # ============================================
    
    # Vistas de Template
    path('comunidad/familias/', views_comunidad.familias, name='familias'),
    path('comunidad/familias/gestion/', views_comunidad.familia_unificada, name='familia_unificada'),
    path('comunidad/familias/gestion/<int:familia_id>/', views_comunidad.familia_unificada, name='editar_familia_unificada'),
    path('comunidad/familias/eliminar/<int:id>/', views_comunidad.eliminar_familia, name='eliminar_familia'),
    
    # API REST para Familias
    path('api/familias/', views_comunidad.FamiliaAPIView.as_view(), name='api_familias_lista'),
    path('api/familias/<int:familia_id>/', views_comunidad.FamiliaAPIView.as_view(), name='api_familia_detalle'),
    
    # ============================================
    # Habitantes (Vistas independientes para gestión individual)
    # ============================================
    path('habitantes/', views_comunidad.habitantes, name='habitantes'),
    path('habitantes/detalle/<int:id>/', views_comunidad.detalle_habitante, name='detalle_habitante'),
    
    # ============================================
    # Finanzas
    # ============================================
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
    
    # ============================================
    # Documentación
    # ============================================
# 📁 Módulo de Gestión Documental Principal
    path('comunidad/documentacion/', views_comunidad.documentacion, name='documentacion'),
    path('documentacion/formulario/<str:tipo_tramite>/', views_comunidad.cargar_formulario_dinamico, name='cargar_formulario_dinamico'),
    # Procesamiento de Formularios (POST)
    path('comunidad/documentacion/constancia/generar/', views_comunidad.generar_constancia, name='generar_constancia'),
    path('comunidad/documentacion/acta/generar/', views_comunidad.generar_acta, name='generar_acta'),
    path('documentacion/buena-conducta/', views_comunidad.generar_buena_conducta, name='generar_buena_conducta'),
    path('documentacion/post-mortem/', views_comunidad.generar_post_mortem, name='generar_post_mortem'),
    # Descarga e Impresión de PDFs Reales
    path('comunidad/documentacion/constancia/descargar/<int:id>/', views_comunidad.descargar_constancia, name='descargar_constancia'),
    path('comunidad/documentacion/acta/descargar/<int:id>/', views_comunidad.descargar_acta, name='descargar_acta'),

    # ============================================
    # 🆕 NUEVO: Gestión de Proyectos Comunitarios
    # ============================================
    
    # Comités
    path('proyectos/comites/', views_proyectos.comites, name='comites'),
    path('proyectos/comites/crear/', views_proyectos.crear_comite, name='crear_comite'),
    path('proyectos/comites/editar/<int:id>/', views_proyectos.editar_comite, name='editar_comite'),
    path('proyectos/comites/eliminar/<int:id>/', views_proyectos.eliminar_comite, name='eliminar_comite'),
    path('proyectos/comites/api/<int:id>/', views_proyectos.api_comite, name='api_comite'),
    
    # Proyectos
    path('proyectos/', views_proyectos.proyectos, name='proyectos'),
    path('proyectos/crear/', views_proyectos.crear_proyecto, name='crear_proyecto'),
    path('proyectos/<int:pk>/', views_proyectos.detalle_proyecto, name='detalle_proyecto'),
    path('proyectos/<int:pk>/editar/', views_proyectos.editar_proyecto, name='editar_proyecto'),
    path('proyectos/<int:pk>/eliminar/', views_proyectos.eliminar_proyecto, name='eliminar_proyecto'),
    path('proyectos/api/<int:pk>/', views_proyectos.api_proyecto, name='api_proyecto'),
    
    # Integrantes de Proyectos
    path('proyectos/<int:pk>/asignar-habitante/', views_proyectos.asignar_habitante, name='asignar_habitante_proyecto'),
    path('proyectos/<int:pk>/remover-habitante/<int:habitante_id>/', views_proyectos.remover_habitante, name='remover_habitante_proyecto'),
    path('proyectos/api/buscar-habitantes/', views_proyectos.buscar_habitantes_proyecto, name='buscar_habitantes_proyecto'),
    path('proyectos/api/integrante/<int:integrante_id>/', views_proyectos.api_integrante, name='api_integrante'),
    
    # Dashboard de Proyectos
    path('proyectos/dashboard/', views_proyectos.dashboard_proyectos, name='dashboard_proyectos'),

    # ============================================
    # 🆕 NUEVO: Gestión de actividad Comunitarios
    # ============================================
    
    # Actividades
    path('actividad/', views_actividad.actividad, name='actividad'),
    path('actividad/crear/', views_actividad.crear_actividad, name='crear_actividad'),
    path('actividad/<int:pk>/', views_actividad.detalle_actividad, name='detalle_actividad'),
    path('actividad/<int:pk>/editar/', views_actividad.editar_actividad, name='editar_actividad'),
    path('actividad/<int:pk>/eliminar/', views_actividad.eliminar_actividad, name='eliminar_actividad'),
    path('actividad/api/<int:pk>/', views_actividad.api_actividad, name='api_actividad'),
    
    # Participantes en la Actividad
    path('actividad/<int:pk>/asignar-participante/', views_actividad.asignar_participante, name='asignar_participante_actividad'),
    path('actividad/<int:pk>/remover-participante/<int:habitante_id>/', views_actividad.remover_participante, name='remover_participante_actividad'),
    path('actividad/api/buscar-habitantes/', views_actividad.buscar_habitantes_actividad, name='buscar_habitantes_actividad'),
    path('actividad/api/participante/<int:participante_id>/', views_actividad.api_participante, name='api_participante_actividad'),
    
    # Exportación de las actividades
    path('actividad/<int:pk>/exportar/', views_actividad.exportar_participantes_actividad, name='exportar_participantes_actividad'),
    path('actividad/<int:pk>/exportar-excel/', views_actividad.exportar_participantes_actividad_excel, name='exportar_participantes_actividad_excel'),
    
    # Dashboard de Censos
    path('actividad/dashboard/', views_actividad.dashboard_actividad, name='dashboard_actividad'),
    
    # ReportesDemográficos
    path('documentacion/reportes/panel/', views_comunidad.panel_reportes, name='panel_reportes'),
    # ReporteExcel
    path('documentacion/reporte/excel/<int:reporte_id>/', views_comunidad.exportar_reporte_excel, name='exportar_reporte_excel'),
    
    # ReportePDF
    path('documentacion/reporte/pdf/<int:reporte_id>/', views_comunidad.exportar_reporte_pdf, name='exportar_reporte_pdf'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
