from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views
from . import views_export
from . import views_comunidad
from . import views_proyectos
from . import views_censos
from .views import PersonApiView, DocenteApiView
from .views import change_password

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('welcome/', views.welcome, name='welcome'),

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
    
    # # ============================================
    # # Habitantes (Vistas independientes para gestión individual)
    # # ============================================
    # path('habitantes/', views_comunidad.habitantes, name='habitantes'),
    # path('habitantes/detalle/<int:id>/', views_comunidad.detalle_habitante, name='detalle_habitante'),
    
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
    # Procesamiento de Formularios (POST)
    path('comunidad/documentacion/constancia/generar/', views_comunidad.generar_constancia, name='generar_constancia'),
    path('comunidad/documentacion/acta/generar/', views_comunidad.generar_acta, name='generar_acta'),
    # Descarga e Impresión de PDFs Reales
    path('comunidad/documentacion/constancia/descargar/<int:id>/', views_comunidad.descargar_constancia, name='descargar_constancia'),
    path('comunidad/documentacion/acta/descargar/<int:id>/', views_comunidad.descargar_acta, name='descargar_acta'),
    # APIs JSON para las previsualizaciones interactivas de SweetAlert2
    path('documentacion/constancia/previa/<int:id>/', views_comunidad.previa_constancia, name='previa_constancia'),
    path('documentacion/acta/previa/<int:id>/', views_comunidad.previa_acta, name='previa_acta'),
    
    # ============================================
    # Dashboard Comunitario
    # ============================================
    path('dashboard-comunitario/', views_comunidad.dashboard_comunitario, name='dashboard_comunitario'),

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
    # 🆕 NUEVO: Gestión de Censos Comunitarios
    # ============================================
    
    # Censos
    path('censos/', views_censos.censos, name='censos'),
    path('censos/crear/', views_censos.crear_censo, name='crear_censo'),
    path('censos/<int:pk>/', views_censos.detalle_censo, name='detalle_censo'),
    path('censos/<int:pk>/editar/', views_censos.editar_censo, name='editar_censo'),
    path('censos/<int:pk>/eliminar/', views_censos.eliminar_censo, name='eliminar_censo'),
    path('censos/api/<int:pk>/', views_censos.api_censo, name='api_censo'),
    
    # Participantes de Censos
    path('censos/<int:pk>/asignar-participante/', views_censos.asignar_participante, name='asignar_participante_censo'),
    path('censos/<int:pk>/remover-participante/<int:habitante_id>/', views_censos.remover_participante, name='remover_participante_censo'),
    path('censos/api/buscar-habitantes/', views_censos.buscar_habitantes_censo, name='buscar_habitantes_censo'),
    path('censos/api/participante/<int:participante_id>/', views_censos.api_participante, name='api_participante_censo'),
    
    # Exportación de Censos
    path('censos/<int:pk>/exportar/', views_censos.exportar_participantes_censo, name='exportar_participantes_censo'),
    
    # Dashboard de Censos
    path('censos/dashboard/', views_censos.dashboard_censos, name='dashboard_censos'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
