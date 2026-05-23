from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views
from . import views_export
from . import views_comunidad
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
    path('documentacion/', views_comunidad.documentacion, name='documentacion'),
    path('documentacion/constancia/', views_comunidad.generar_constancia, name='generar_constancia'),
    path('documentacion/constancia/descargar/<int:id>/', views_comunidad.descargar_constancia, name='descargar_constancia'),
    path('documentacion/constancia/previa/<int:id>/', views_comunidad.previa_constancia, name='previa_constancia'),
    path('documentacion/acta/', views_comunidad.generar_acta, name='generar_acta'),
    path('documentacion/acta/descargar/<int:id>/', views_comunidad.descargar_acta, name='descargar_acta'),
    path('documentacion/acta/previa/<int:id>/', views_comunidad.previa_acta, name='previa_acta'),
    
    # ============================================
    # Dashboard Comunitario
    # ============================================
    path('dashboard-comunitario/', views_comunidad.dashboard_comunitario, name='dashboard_comunitario'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
