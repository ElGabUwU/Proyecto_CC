"""
Vistas para la gestión comunitaria del Consejo Comunal.
ARQUITECTURA NUEVA: Vista unificada maestro-detalle para Familias y Habitantes.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator
from django.conf import settings
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import json
from datetime import date, datetime, timedelta
import os
import base64
import io
from xhtml2pdf import pisa
import csv

from .models import (
    Familia, Habitante, IngresoComunal, EgresoComunal, 
    ConstanciaResidencia, ActaReunion, ReporteDemografico
)
from .forms import (
    FamiliaForm, HabitanteForm, IngresoComunalForm, 
    EgresoComunalForm, ConstanciaResidenciaForm, ActaReunionForm,
    BuenaConductaForm, ConstanciaFallecidoForm
)
from .decorators import admin_required
from .serializers import (
    FamiliaListSerializer, FamiliaDetalleSerializer, 
    FamiliaConHabitantesSerializer, HabitanteSerializer
)


# ============================================
# API REST para Familias (Maestro-Detalle)
# ============================================

@method_decorator(csrf_exempt, name='dispatch')
class FamiliaAPIView(View):
    """
    API REST para gestión de Familias con Habitantes (Maestro-Detalle).
    
    GET /api/familias/ - Lista todas las familias
    POST /api/familias/ - Crea familia con habitantes
    GET /api/familias/{id}/ - Obtiene familia con habitantes
    PUT /api/familias/{id}/ - Actualiza familia y habitantes
    DELETE /api/familias/{id}/ - Soft delete de familia
    """
    
    def get(self, request, familia_id=None):
        """Obtiene lista de familias o detalle de una familia."""
        if familia_id:
            # Obtener detalle de una familia
            try:
                familia = Familia.objects.get(pk=familia_id, is_deleted=False)
                serializer = FamiliaDetalleSerializer(familia)
                return JsonResponse(serializer.data, safe=False, status=200)
            except Familia.DoesNotExist:
                return JsonResponse(
                    {'error': 'Familia no encontrada'}, 
                    status=404
                )
        else:
            # Listar todas las familias
            familias = Familia.objects.filter(is_deleted=False).order_by('-fecha_registro')
            
            # Filtros de búsqueda
            query = request.GET.get('q', '')
            if query:
                familias = familias.filter(
                    Q(nombre_familia__icontains=query) |
                    Q(direccion__icontains=query) |
                    Q(vivienda__icontains=query) |
                    Q(catastro__icontains=query)
                )
            
            # Paginación
            page = int(request.GET.get('page', 1))
            per_page = int(request.GET.get('per_page', 20))
            paginator = Paginator(familias, per_page)
            familias_page = paginator.get_page(page)
            
            serializer = FamiliaListSerializer(familias_page, many=True)
            
            return JsonResponse({
                'results': serializer.data,
                'count': paginator.count,
                'page': page,
                'total_pages': paginator.num_pages
            }, safe=False, status=200)
    
    def post(self, request, familia_id=None):
        """Crea una nueva familia con habitantes."""
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {'error': 'Datos JSON inválidos'}, 
                status=400
            )
        
        serializer = FamiliaConHabitantesSerializer(data=data)
        
        if serializer.is_valid():
            try:
                familia = serializer.save()
                return JsonResponse(
                    FamiliaDetalleSerializer(familia).data,
                    status=201
                )
            except Exception as e:
                return JsonResponse(
                    {'error': str(e)}, 
                    status=500
                )
        else:
            return JsonResponse(
                {'errors': serializer.errors}, 
                status=400
            )
    
    def put(self, request, familia_id=None):
        """Actualiza una familia existente y sus habitantes."""
        if not familia_id:
            return JsonResponse(
                {'error': 'ID de familia requerido'}, 
                status=400
            )
        
        try:
            familia = Familia.objects.get(pk=familia_id, is_deleted=False)
        except Familia.DoesNotExist:
            return JsonResponse(
                {'error': 'Familia no encontrada'}, 
                status=404
            )
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {'error': 'Datos JSON inválidos'}, 
                status=400
            )
        
        serializer = FamiliaConHabitantesSerializer(
            familia, 
            data=data, 
            partial=False
        )
        
        if serializer.is_valid():
            try:
                familia = serializer.save()
                return JsonResponse(
                    FamiliaDetalleSerializer(familia).data,
                    status=200
                )
            except Exception as e:
                return JsonResponse(
                    {'error': str(e)}, 
                    status=500
                )
        else:
            return JsonResponse(
                {'errors': serializer.errors}, 
                status=400
            )
    
    def delete(self, request, familia_id=None):
        """Elimina (soft delete) una familia y sus habitantes."""
        if not familia_id:
            return JsonResponse(
                {'error': 'ID de familia requerido'}, 
                status=400
            )
        
        try:
            familia = Familia.objects.get(pk=familia_id, is_deleted=False)
        except Familia.DoesNotExist:
            return JsonResponse(
                {'error': 'Familia no encontrada'}, 
                status=404
            )
        
        # Soft delete de la familia y sus habitantes
        with transaction.atomic():
            familia.is_deleted = True
            familia.save()
            familia.habitantes.filter(is_deleted=False).update(is_deleted=True)
        
        return JsonResponse(
            {'message': f'Familia {familia.nombre_familia} eliminada correctamente'},
            status=200
        )


# ============================================
# Vistas de Template para Familias (Nueva Arquitectura)
# ============================================
from .serializers import HabitanteSerializer

def familias(request):
    """
    Vista Maestro: Muestra el listado de todas las familias con sus habitantes precargados.
    """
    query = request.GET.get('q', '')
    
    # Prefetch_related optimiza la consulta en Postgres trayendo los habitantes de un solo golpe
    familias_list = Familia.objects.filter(is_deleted=False).prefetch_related('habitantes')
    
    if query:
        familias_list = familias_list.filter(
            Q(nombre_familia__icontains=query) |
            Q(direccion__icontains=query) |
            Q(vivienda__icontains=query) |
            Q(catastro__icontains=query) |
            Q(habitantes__nombre__icontains=query) |
            Q(habitantes__apellido__icontains=query) |
            Q(habitantes__cedula__icontains=query)
        ).distinct()
    
    familias_list = familias_list.order_by('-fecha_registro')
    
    paginator = Paginator(familias_list, 15)  # 15 familias por página
    page_number = request.GET.get('page')
    familias_page = paginator.get_page(page_number)
    
    context = {
        'familias': familias_page,
        'query': query,
    }
    return render(request, 'familias.html', context)

def familia_unificada(request, familia_id=None):
    """
    Vista Detalle: Renderiza la interfaz unificada de registro y edición masiva.
    """
    # Solo administradores pueden acceder
    es_autorizado = request.user.is_superuser or request.user.is_staff or getattr(request.user, 'role', None) == 'admin'
    if not es_autorizado:
        messages.error(request, "No tienes permisos para acceder a esta sección. Solo administradores pueden acceder.")
        return redirect('welcome')

    familia = None
    habitantes_json = "[]"
    
    if familia_id:
        familia = get_object_or_404(Familia, pk=familia_id, is_deleted=False)
        # Convertir los habitantes existentes a JSON de manera segura para manipularlos en el frontend
        habitantes_qs = familia.habitantes.filter(is_deleted=False)
        habitantes_json = json.dumps(HabitanteSerializer(habitantes_qs, many=True).data)
    
    context = {
        'familia': familia,
        'habitantes_json': habitantes_json,
        'is_edit': familia_id is not None
    }
    return render(request, 'familia_unificada.html', context)


@require_POST
def eliminar_familia(request, id):
    """
    Soft delete unificado para resguardar la integridad del censo comunal.
    """
    familia = get_object_or_404(Familia, id=id, is_deleted=False)
    
    with transaction.atomic():
        familia.is_deleted = True
        familia.save()
        # Al eliminar la familia, se marcan automáticamente como dados de baja sus habitantes
        familia.habitantes.filter(is_deleted=False).update(is_deleted=True)
        
    messages.success(request, f'Familia {familia.nombre_familia} y sus integrantes eliminados correctamente.')
    return redirect('familias')

# ============================================
# Vistas para Habitantes (Lista y Detalle)
# ============================================


def habitantes(request):
    # 
    # Vista de listado general de habitantes.
    # Adaptada al modelo unificado (sin tabla Person).
    # 
    query = request.GET.get('q', '')
    familia_id = request.GET.get('familia', '')
    
    # Optimización con select_related para traer datos de la familia en una sola query
    habitantes_list = Habitante.objects.filter(is_deleted=False).select_related('familia')
    
    if query:
        habitantes_list = habitantes_list.filter(
            Q(nombre__icontains=query) |
            Q(apellido__icontains=query) |
            Q(cedula__icontains=query)
        )
        
    if familia_id:
        habitantes_list = habitantes_list.filter(familia_id=familia_id)
        
    habitantes_list = habitantes_list.order_by('apellido', 'nombre')
    
    paginator = Paginator(habitantes_list, 20)
    page_number = request.GET.get('page')
    habitantes_page = paginator.get_page(page_number)
    
    context = {
        'habitantes': habitantes_page,
        'familias': Familia.objects.filter(is_deleted=False).order_by('nombre_familia'),
        'query': query,
        'familia_filter': familia_id,
    }
    return render(request, 'habitantes.html', context)


def detalle_habitante(request, id):
    """
    Vista de detalle de un habitante individual.
    """
    habitante = get_object_or_404(Habitante, id=id, is_deleted=False)
    
    context = {
        'habitante': habitante,
    }
    return render(request, 'detalle_habitante.html', context)


@require_GET
def api_familia(request, id):
    """
    API para obtener datos de una familia en formato JSON (para AJAX).
    """
    familia = get_object_or_404(Familia, id=id, is_deleted=False)
    
    data = {
        'id': familia.id,
        'jefe_familia': familia.jefe_familia.id,
        'direccion': familia.direccion,
        'numero_vivienda': familia.numero_vivienda or '',
        'telefono_contacto': familia.telefono_contacto,
        'observaciones': familia.observaciones or '',
    }
    
    return JsonResponse(data)

# ============================================
# Vistas para Finanzas
# ============================================

def finanzas(request):
    # Obtener fechas para filtro
    fecha_inicio_str = request.GET.get('fecha_inicio', '')
    fecha_fin_str = request.GET.get('fecha_fin', '')
    
    fecha_fin = timezone.now().date()
    fecha_inicio = fecha_fin - timedelta(days=30)
    
    if fecha_inicio_str:
        try: fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        except ValueError: pass
    if fecha_fin_str:
        try: fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        except ValueError: pass
    
    # 🔹 TOTALES GENERALES (sin filtro)
    total_ingresos = IngresoComunal.objects.aggregate(Sum('monto'))['monto__sum'] or 0
    total_egresos = EgresoComunal.objects.aggregate(Sum('monto'))['monto__sum'] or 0
    saldo_actual = total_ingresos - total_egresos
    
    # 🔹 QUERYSETS COMPLETOS FILTRADOS (para reporte y totales del período)
    ingresos_qs = IngresoComunal.objects.filter(fecha__range=[fecha_inicio, fecha_fin])
    egresos_qs = EgresoComunal.objects.filter(fecha__range=[fecha_inicio, fecha_fin])
    
    ingresos_periodo = ingresos_qs.aggregate(Sum('monto'))['monto__sum'] or 0
    egresos_periodo = egresos_qs.aggregate(Sum('monto'))['monto__sum'] or 0
    saldo_periodo = ingresos_periodo - egresos_periodo
    
    # 🔹 DATOS PARA PESTAÑAS (limitados a 50 para rendimiento)
    ingresos_tab = ingresos_qs.order_by('-fecha', '-fecha_registro')[:50]
    egresos_tab = egresos_qs.order_by('-fecha', '-fecha_registro')[:50]
    
    # 🔹 DATOS PARA REPORTE (SIN límite, usa todo el queryset filtrado)
    movimientos_periodo = []
    for ing in ingresos_qs.order_by('fecha'):
        movimientos_periodo.append({
            'fecha': ing.fecha, 'tipo': 'ingreso', 'concepto': ing.concepto,
            'monto': ing.monto, 'responsable': ing.responsable
        })
    for eg in egresos_qs.order_by('fecha'):
        movimientos_periodo.append({
            'fecha': eg.fecha, 'tipo': 'egreso', 'concepto': eg.concepto,
            'monto': eg.monto, 'responsable': eg.responsable
        })
    movimientos_periodo.sort(key=lambda x: x['fecha'], reverse=True)
    
    context = {
        'saldo_actual': saldo_actual, 'total_ingresos': total_ingresos, 'total_egresos': total_egresos,
        'total_ingresos_periodo': ingresos_periodo, 'total_egresos_periodo': egresos_periodo,
        'saldo_periodo': saldo_periodo,
        'ingresos': ingresos_tab,       # 👈 Solo para pestañas
        'egresos': egresos_tab,         # 👈 Solo para pestañas
        'movimientos_periodo': movimientos_periodo, # 👈 Para reporte completo
        'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin,
        'ingreso_form': IngresoComunalForm(user=request.user),
        'egreso_form': EgresoComunalForm(user=request.user),
    }
    return render(request, 'finanzas.html', context)


def crear_ingreso(request):
    if request.method == 'POST':
        form = IngresoComunalForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            ingreso = form.save()
            # Si es AJAX, devolvemos JSON exitoso
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Ingreso de Bs. {ingreso.monto} registrado exitosamente.'
                })
            messages.success(request, f'Ingreso de Bs. {ingreso.monto} registrado exitosamente.')
            return redirect('finanzas')
        else:
            # Si falla y es AJAX, capturamos el diccionario de errores con sus códigos específicos
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errores_dict = {}
                for campo, lista_errores in form.errors.get_json_data().items():
                    # Tomamos solo el texto del primer error de cada campo
                    errores_dict[campo] = lista_errores[0]['message']
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
            
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = IngresoComunalForm(user=request.user)
    
    # Este bloque solo se ejecutará en solicitudes GET comunes
    from .models import IngresoComunal
    context = {
        'form': form,
        'ingresos': IngresoComunal.objects.filter(is_deleted=False).order_by('-fecha_ingreso')
    }
    return render(request, 'finanzas.html', context)


def editar_ingreso(request, id):
    """
    Vista para editar un ingreso existente.
    """
    ingreso = get_object_or_404(IngresoComunal, id=id)
    
    if request.method == 'POST':
        form = IngresoComunalForm(request.POST, request.FILES, instance=ingreso, user=request.user)
        if form.is_valid():
            ingreso = form.save()
            messages.success(request, f'Ingreso de Bs. {ingreso.monto} actualizado exitosamente.')
            return redirect('finanzas')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = IngresoComunalForm(instance=ingreso, user=request.user)
    
    context = {
        'form': form,
        'ingreso': ingreso,
    }
    return render(request, 'finanzas.html', context)


@require_POST
def eliminar_ingreso(request, id):
    """
    Vista para eliminar un ingreso.
    """
    ingreso = get_object_or_404(IngresoComunal, id=id)
    monto = ingreso.monto
    ingreso.delete()
    
    messages.success(request, f'Ingreso de Bs. {monto} eliminado exitosamente.')
    return redirect('finanzas')

def crear_egreso(request):
    """
    Vista optimizada para AJAX: Registra egresos y especifica 
    los errores sin alterar el historial.
    """
    if request.method == 'POST':
        form = EgresoComunalForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            egreso = form.save()
            
            # Si es una petición asíncrona (AJAX)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Egreso de Bs. {egreso.monto} registrado exitosamente.'
                }, status=200)
                
            messages.success(request, f'Egreso de Bs. {egreso.monto} registrado exitosamente.')
            return redirect('finanzas')
        else:
            # Si falla y es AJAX, extraemos los mensajes del diccionario de forma limpia
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errores_dict = {}
                for campo, lista_errores in form.errors.get_json_data().items():
                    # Extraemos el primer texto de error para simplificar la lectura en JS
                    errores_dict[campo] = lista_errores[0]['message']
                
                return JsonResponse({
                    'success': False,
                    'errors': errores_dict
                }, status=400)
            
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = EgresoComunalForm(user=request.user)
    
    # Flujo de respaldo para peticiones GET convencionales
    context = {
        'form_egreso': form,
        'egresos': EgresoComunal.objects.filter(is_deleted=False).order_by('-fecha')
    }
    return render(request, 'finanzas.html', context)


def editar_egreso(request, id):
    """
    Vista para editar un egreso existente.
    """
    egreso = get_object_or_404(EgresoComunal, id=id)
    
    if request.method == 'POST':
        form = EgresoComunalForm(request.POST, request.FILES, instance=egreso, user=request.user)
        if form.is_valid():
            egreso = form.save()
            messages.success(request, f'Egreso de Bs. {egreso.monto} actualizado exitosamente.')
            return redirect('finanzas')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = EgresoComunalForm(instance=egreso, user=request.user)
    
    context = {
        'form': form,
        'egreso': egreso,
    }
    return render(request, 'finanzas.html', context)


@require_POST
def eliminar_egreso(request, id):
    """
    Vista para eliminar un egreso.
    """
    egreso = get_object_or_404(EgresoComunal, id=id)
    monto = egreso.monto
    egreso.delete()
    
    messages.success(request, f'Egreso de Bs. {monto} eliminado exitosamente.')
    return redirect('finanzas')


@require_GET
def api_ingreso(request, id):
    """
    API para obtener datos de un ingreso en formato JSON (para AJAX).
    """
    ingreso = get_object_or_404(IngresoComunal, id=id)
    
    data = {
        'id': ingreso.id,
        'fecha': ingreso.fecha.strftime('%Y-%m-%d'),
        'tipo_ingreso': ingreso.tipo_ingreso,
        'concepto': ingreso.concepto,
        'monto': str(ingreso.monto),
        'observaciones': ingreso.observaciones or '',
        'soporte_digital_nombre': ingreso.soporte_digital.name if ingreso.soporte_digital else None,
    }
    
    return JsonResponse(data)


@require_GET
def api_egreso(request, id):
    """
    API para obtener datos de un egreso en formato JSON (para AJAX).
    """
    egreso = get_object_or_404(EgresoComunal, id=id)
    
    data = {
        'id': egreso.id,
        'fecha': egreso.fecha.strftime('%Y-%m-%d'),
        'tipo_egreso': egreso.tipo_egreso,
        'concepto': egreso.concepto,
        'monto': str(egreso.monto),
        'beneficiario': egreso.beneficiario or '',
        'observaciones': egreso.observaciones or '',
        'soporte_nombre': egreso.soporte.name if egreso.soporte else None,
    }
    
    return JsonResponse(data)


def exportar_finanzas(request):
    fecha_inicio_str = request.GET.get('fecha_inicio', '')
    fecha_fin_str = request.GET.get('fecha_fin', '')
    
    # Parseo seguro de fechas
    fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date() if fecha_inicio_str else None
    fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date() if fecha_fin_str else None
    
    ingresos_qs = IngresoComunal.objects.all().order_by('fecha')
    egresos_qs = EgresoComunal.objects.all().order_by('fecha')
    
    if fecha_inicio and fecha_fin:
        ingresos_qs = ingresos_qs.filter(fecha__range=[fecha_inicio, fecha_fin])
        egresos_qs = egresos_qs.filter(fecha__range=[fecha_inicio, fecha_fin])
    elif fecha_inicio:
        ingresos_qs = ingresos_qs.filter(fecha__gte=fecha_inicio)
        egresos_qs = egresos_qs.filter(fecha__gte=fecha_inicio)
    elif fecha_fin:
        ingresos_qs = ingresos_qs.filter(fecha__lte=fecha_fin)
        egresos_qs = egresos_qs.filter(fecha__lte=fecha_fin)
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="finanzas_{datetime.now().strftime("%Y%m%d")}.csv"'
    
    # 👇 DELIMITADOR ; para que Excel en español abra las columnas correctamente
    writer = csv.writer(response, delimiter=';', quoting=csv.QUOTE_NONNUMERIC)
    writer.writerow(['Fecha', 'Tipo', 'Concepto', 'Monto (Bs.)', 'Responsable', 'Beneficiario', 'Observaciones'])
    
    for ing in ingresos_qs:
        writer.writerow([
            ing.fecha.strftime('%d/%m/%Y'), 'INGRESO', ing.concepto,
            f"{ing.monto:.2f}", ing.responsable.get_full_name() or ing.responsable.username,
            '', ing.observaciones or ''
        ])
    for eg in egresos_qs:
        writer.writerow([
            eg.fecha.strftime('%d/%m/%Y'), 'EGRESO', eg.concepto,
            f"{eg.monto:.2f}", eg.responsable.get_full_name() or eg.responsable.username,
            eg.beneficiario or '', eg.observaciones or ''
        ])
    return response


# ============================================
# Vistas para Documentación
# ============================================

# # Nota: Conserva o ajusta tus decoradores de permisos según los manejes en tu app
# def vocero_secretaria_required(view_func):
#     return view_func  # Si usas @admin_required, puedes dejarlo pasar para la beta

def documentacion(request):
    """
    Vista principal para la gestión de documentación y actas.
    """
    # 💡 CORRECCIÓN: Cambiado .ordering() por .order_by()
    familias = Familia.objects.filter(is_deleted=False).order_by('nombre_familia')
    
    constancias_recientes = ConstanciaResidencia.objects.all().order_by('-fecha_generacion')[:10]
    actas_recientes = ActaReunion.objects.all().order_by('-fecha_reunion')[:10]
    
    context = {
        'familias': familias,
        'constancias_recientes': constancias_recientes,
        'actas_recientes': actas_recientes,
        'constancia_form': ConstanciaResidenciaForm(user=request.user),
        'acta_form': ActaReunionForm(user=request.user),
        'buena_conducta_form': BuenaConductaForm(user=request.user),
        'fallecido_form': ConstanciaFallecidoForm(user=request.user),
    }
    return render(request, 'documentacion.html', context)


def generar_constancia(request):
    """
    Vista optimizada para AJAX: Procesa la constancia, retorna JSON de éxito 
    para actualizar la tabla histórica sin abrir pestañas automáticas.
    """
    if request.method == 'POST':
        form = ConstanciaResidenciaForm(request.POST, user=request.user)
        
        if form.is_valid():
            constancia = form.save()
            nombre_ciudadano = f"{constancia.habitante.nombre} {constancia.habitante.apellido}"
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'La constancia de residencia para <strong>{nombre_ciudadano}</strong> se ha generado con éxito y se ha añadido al historial.'
                }, status=200)
                
            messages.success(request, f'¡Excelente! La constancia de residencia para <strong>{nombre_ciudadano}</strong> se ha generado con éxito.')
            return redirect('documentacion')
            
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errores_dict = {}
                for campo, lista_errores in form.errors.get_json_data().items():
                    errores_dict[campo] = lista_errores[0]['message']
                
                return JsonResponse({
                    'success': False,
                    'errors': errores_dict
                }, status=400)
                
            messages.error(request, 'Por favor, verifique los datos del formulario de constancia.')
            return redirect('documentacion')
            
    return redirect('documentacion')

def generar_buena_conducta(request):
    if request.method == 'POST':
        form = BuenaConductaForm(request.POST, user=request.user)
        if form.is_valid():
            habitante = form.cleaned_data.get('habitante')
            familia = habitante.familia
            tiempo_residencia = form.cleaned_data.get('tiempo_residencia')
            organismo_destino = form.cleaned_data.get('organismo_destino')
            
            logo_base64 = ""
            ruta_logo = os.path.join(settings.BASE_DIR, 'static', 'assets', 'images', 'CC_Logo.png')
            if os.path.exists(ruta_logo):
                with open(ruta_logo, "rb") as image_file:
                    logo_base64 = base64.b64encode(image_file.read()).decode('utf-8')
            
            context = {
                'habitante': habitante,
                'familia': familia,
                'tiempo_residencia': tiempo_residencia,
                'organismo_destino': organismo_destino,
                'fecha_emision': date.today(),
                'logo_pdf': logo_base64,
            }
            html_string = render_to_string('reportes/buena_conducta_pdf.html', context)
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Carta_Buena_Conducta_{habitante.cedula}.pdf"'
            pisa_status = pisa.CreatePDF(src=html_string, dest=response, encoding='utf-8')
            if not pisa_status.err:
                return response
            messages.error(request, "Error técnico al compilar el PDF de Buena Conducta.")
            return redirect('documentacion')
        else:
            errores = "<br>".join([f"• <b>{form.fields[campo].label}:</b> {msg[0]}" for campo, msg in form.errors.items()])
            messages.error(request, f"Errores en el formulario de Buena Conducta:<br>{errores}")
            return redirect('documentacion')
    return redirect('documentacion')

def generar_post_mortem(request):
    if request.method == 'POST':
        form = ConstanciaFallecidoForm(request.POST, user=request.user)
        if form.is_valid():
            fallecido = form.cleaned_data.get('habitante')
            familia = fallecido.familia
            fecha_deceso = form.cleaned_data.get('fecha_deceso')
            solicitante_defuncion = form.cleaned_data.get('solicitante_defuncion')
            solicitante_cedula = form.cleaned_data.get('solicitante_cedula')
            relacion_parentesco = form.cleaned_data.get('relacion_parentesco')
            
            logo_base64 = ""
            ruta_logo = os.path.join(settings.BASE_DIR, 'static', 'assets', 'images', 'CC_Logo.png')
            if os.path.exists(ruta_logo):
                with open(ruta_logo, "rb") as image_file:
                    logo_base64 = base64.b64encode(image_file.read()).decode('utf-8')
            
            context = {
                'fallecido': fallecido,
                'familia': familia,
                'fecha_fallecimiento': fecha_deceso,
                'solicitante_nombre': solicitante_defuncion,
                'solicitante_cedula': solicitante_cedula,
                'relacion_parentesco': relacion_parentesco,
                'fecha_emision': date.today(),
                'logo_pdf': logo_base64,
            }
            html_string = render_to_string('reportes/post_mortem_pdf.html', context)
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Constancia_PostMortem_{fallecido.cedula}.pdf"'
            pisa_status = pisa.CreatePDF(src=html_string, dest=response, encoding='utf-8')
            if not pisa_status.err:
                return response
            messages.error(request, "Error técnico al compilar el PDF Post-Mortem.")
            return redirect('documentacion')
        else:
            errores = "<br>".join([f"• <b>{form.fields[campo].label}:</b> {msg[0]}" for campo, msg in form.errors.items()])
            messages.error(request, f"Errores en el formulario Post-Mortem:<br>{errores}")
            return redirect('documentacion')
    return redirect('documentacion')

@transaction.atomic
def generar_acta(request):
    if request.method == 'POST':
        # Pasamos el usuario explícitamente al formulario
        form = ActaReunionForm(request.POST, user=request.user)
        if form.is_valid():
            acta = form.save()
            messages.success(request, f'Acta "{acta.titulo}" creada con éxito de forma tradicional.')
            return redirect('documentacion') # Redirecciona a la vista principal del módulo
        else:
            messages.error(request, 'Hubo errores al validar el formulario del Acta.')
    return redirect('documentacion')

def descargar_constancia(request, id):
    try:
        # 1. Recuperamos la constancia e inspeccionamos sus relaciones
        constancia = ConstanciaResidencia.objects.get(id=id)
        habitante = constancia.habitante
        familia_obj = getattr(habitante, 'familia', None)
        
        # 2. Reconstruimos el contexto inyectando el logo convertido
        context = {
            'constancia': constancia,
            'motivo': constancia.finalidad,
            'solicitante': habitante,   
            'familia': familia_obj,     
            'fecha_emision': constancia.fecha_documento,
            'logo_pdf': obtener_logo_base64(), # 👈 Inyección Base64
        }
        
        # 3. Renderizamos el HTML corregido a cadena de texto
        html = render_to_string('residence.html', context)
        
        # 4. Generamos el flujo de respuesta limpia
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Constancia_Residencia_{id}.pdf"'
        
        # 5. Compilación sin depender de link_callback para imágenes
        pdf = pisa.CreatePDF(
            src=html,
            dest=response,
            encoding='utf-8'
        )
        
        if not pdf.err:
            return response
            
        return HttpResponse('Error interno al compilar la estructura del PDF.', status=500)
        
    except ConstanciaResidencia.DoesNotExist:
        return HttpResponse('La constancia especificada no existe en la base de datos.', status=404)
    
@require_GET
def descargar_acta(request, id):
    # 1. Recuperamos el acta de la base de datos
    acta = get_object_or_404(ActaReunion, id=id)
    
    # 2. Contexto limpio incluyendo el logo institucional
    context = {
        'acta': acta,
        'logo_pdf': obtener_logo_base64(), # 👈 Inyección Base64
    }
    html = render_to_string('acta_reunion.html', context)
    
    # 3. Preparar la respuesta HTTP tipo PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Acta_Asamblea_{acta.id}.pdf"'
    
    # 4. Compilamos el binario de forma directa y segura
    pdf = pisa.CreatePDF(
        src=html,
        dest=response,
        encoding='utf-8'
    )
    
    # 5. Si no hubo errores, retornamos el archivo binario descargable
    if not pdf.err:
        return response
    
    return HttpResponse('Error al estructurar los elementos del PDF de la Asamblea.', status=500)


# ============================================
# Vistas para Dashboard Comunitario
# ============================================

def dashboard_comunitario(request):
    """
    Vista del dashboard principal de la comunidad.
    """
    # Estadísticas generales
    total_familias = Familia.objects.filter(is_deleted=False).count()
    total_habitantes = Habitante.objects.filter(is_deleted=False).count()
    
    # Estadísticas financieras
    total_ingresos = IngresoComunal.objects.aggregate(Sum('monto'))['monto__sum'] or 0
    total_egresos = EgresoComunal.objects.aggregate(Sum('monto'))['monto__sum'] or 0
    saldo_actual = total_ingresos - total_egresos
    
    # Últimos movimientos financieros
    ultimos_ingresos = IngresoComunal.objects.all().order_by('-fecha', '-fecha_registro')[:5]
    ultimos_egresos = EgresoComunal.objects.all().order_by('-fecha', '-fecha_registro')[:5]
    
    # Últimas familias registradas
    ultimas_familias = Familia.objects.filter(is_deleted=False).order_by('-fecha_registro')[:5]
    
    # Últimos documentos generados
    ultimas_constancias = ConstanciaResidencia.objects.all().order_by('-fecha_generacion')[:3]
    ultimas_actas = ActaReunion.objects.all().order_by('-fecha_reunion')[:3]
    
    context = {
        'total_familias': total_familias,
        'total_habitantes': total_habitantes,
        'saldo_actual': saldo_actual,
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
        'ultimos_ingresos': ultimos_ingresos,
        'ultimos_egresos': ultimos_egresos,
        'ultimas_familias': ultimas_familias,
        'ultimas_constancias': ultimas_constancias,
        'ultimas_actas': ultimas_actas,
    }
    
    return render(request, 'dashboard_comunitario.html', context)


# ============================================
# Funciones de utilidad
# ============================================

def calcular_saldo_comunal():
    """
    Calcula el saldo actual de la caja comunal.
    """
    total_ingresos = IngresoComunal.objects.aggregate(Sum('monto'))['monto__sum'] or 0
    total_egresos = EgresoComunal.objects.aggregate(Sum('monto'))['monto__sum'] or 0
    return total_ingresos - total_egresos


def obtener_estadisticas_comunidad():
    """
    Obtiene estadísticas generales de la comunidad.
    """
    return {
        'familias': Familia.objects.filter(is_deleted=False).count(),
        'habitantes': Habitante.objects.filter(is_deleted=False).count(),
        'ingresos_mes': IngresoComunal.objects.filter(
            fecha__month=timezone.now().month,
            fecha__year=timezone.now().year
        ).aggregate(Sum('monto'))['monto__sum'] or 0,
        'egresos_mes': EgresoComunal.objects.filter(
            fecha__month=timezone.now().month,
            fecha__year=timezone.now().year
        ).aggregate(Sum('monto'))['monto__sum'] or 0,
    }

def obtener_logo_base64():
    """
    Función auxiliar unificada para leer el logo institucional
    y retornarlo listo en formato Base64 para cualquier PDF.
    """
    logo_base64 = ""
    # Apuntamos directamente a la ruta real dentro de tus estáticos
    ruta_logo = os.path.join(settings.STATICFILES_DIRS[0], 'assets', 'images', 'CC_Logo.png')
    
    if os.path.exists(ruta_logo):
        with open(ruta_logo, "rb") as image_file:
            logo_base64 = base64.b64encode(image_file.read()).decode('utf-8')
    else:
        print(f"⚠️ ALERTA EN ACTAS/CONSTANCIAS: No se encontró el logo en: {ruta_logo}")
        
    return logo_base64

# --------------------------------------------------------------
# ---------------- Funciones ReporteDemográfico ----------------
# --------------------------------------------------------------

def panel_reportes(request):
    """
    Vista controladora principal para el módulo de Reportes Demográficos.
    Muestra el formulario de filtrado y el listado de reportes generados.
    """
    if request.method == 'POST':
        # Capturamos los datos del formulario de la interfaz
        titulo = request.POST.get('titulo_reporte')
        genero = request.POST.get('filtro_genero')
        edad = request.POST.get('filtro_edad')
        
        if titulo:
            # Creamos el registro de configuración en la Base de Datos
            nuevo_reporte = ReporteDemografico.objects.create(
                titulo_reporte=titulo,
                filtro_genero=genero,
                filtro_edad=edad,
                solicitado_por=request.user
            )
            messages.success(request, f"Filtro '{titulo}' creado con éxito. Ya puedes descargar los reportes.")
            return redirect('panel_reportes')
        else:
            messages.error(request, "Debe indicarle un título descriptivo al reporte.")

    # Recuperamos todos los reportes creados para listarlos en una tabla analítica
    reportes = ReporteDemografico.objects.all()
    
    context = {
        'reportes': reportes,
    }
    # Este es el template asociado al controlador:
    return render(request, 'reportes/panel_reportes.html', context)

def obtener_habitantes_filtrados(reporte):
    # Condición base: Solo habitantes activos (no eliminados)
    queryset = Habitante.objects.filter(is_deleted=False)
    hoy = date.today()

    # 1. Evaluación de la condición de Género
    if reporte.filtro_genero != 'TODOS':
        queryset = queryset.filter(genero=reporte.filtro_genero)

    # 2. Evaluación de las condiciones complejas de Edad
    if reporte.filtro_edad == 'MENOR_12':
        # Nacidos hace menos de 12 años
        fecha_limite = hoy - timedelta(days=12*365.25)
        queryset = queryset.filter(fecha_nacimiento__gt=fecha_limite)
        
    elif reporte.filtro_edad == 'MENOR_16':
        # Nacidos hace menos de 16 años
        fecha_limite = hoy - timedelta(days=16*365.25)
        queryset = queryset.filter(fecha_nacimiento__gt=fecha_limite)
        
    elif reporte.filtro_edad == 'TERCERA_EDAD':
        # Nacidos hace 60 años o más
        fecha_limite = hoy - timedelta(days=60*365.25)
        queryset = queryset.filter(fecha_nacimiento__lte=fecha_limite)

    # 3. Optimización de Query para incluir las Familias asociadas sin hacer consultas lentas
    if reporte.incluir_datos_familia:
        queryset = queryset.select_related('familia')

    return queryset

def obtener_habitantes_filtrados(reporte):
    """
    Función auxiliar para aplicar los filtros del reporte sobre 
    la tabla de habitantes reales registrados en el sistema.
    """
    # 1. Traemos todos los habitantes activos en el sistema que tengan un grupo familiar
    # Usamos select_related('familia') para traer la dirección y el nombre de la familia en una sola consulta SQL (JOIN)
    queryset = Habitante.objects.filter(is_deleted=False).select_related('familia')

    # 2. Evaluamos y aplicamos el Filtro de Género
    if reporte.filtro_genero != 'TODOS':
        queryset = queryset.filter(genero=reporte.filtro_genero)

    # 3. Evaluamos y aplicamos el Filtro de Edad (Calculando según la fecha de nacimiento)
    hoy = date.today()
    habitantes_finales = []

    for habitante in queryset:
        if habitante.fecha_nacimiento:
            # Cálculo estricto de la edad del habitante
            edad = hoy.year - habitante.fecha_nacimiento.year - (
                (hoy.month, hoy.day) < (habitante.fecha_nacimiento.month, habitante.fecha_nacimiento.day)
            )
            
            # Validamos si cumple con la segmentación seleccionada en el panel
            cumple_edad = False
            if reporte.filtro_edad == 'TODOS':
                cumple_edad = True
            elif reporte.filtro_edad == 'MENOR_12' and edad < 12:
                cumple_edad = True
            elif reporte.filtro_edad == 'MENOR_16' and edad < 16:
                cumple_edad = True
            elif reporte.filtro_edad == 'TERCERA_EDAD' and edad >= 60:
                cumple_edad = True

            # Si cumple la condición de edad, lo preparamos para el reporte
            if cumple_edad:
                habitantes_finales.append({
                    'objeto': habitante,
                    'edad': edad
                })
                
    return habitantes_finales

def exportar_reporte_excel(request, reporte_id):
    """
    Genera un archivo Excel profesional (.xlsx) en memoria RAM con los 
    habitantes clasificados según los parámetros del reporte demográfico.
    """
    # 1. Recuperamos la configuración del reporte solicitado
    reporte = get_object_or_404(ReporteDemografico, id=reporte_id)
    habitantes = obtener_habitantes_filtrados(reporte)
    
    # 2. Inicializamos el libro de openpyxl
    wb = Workbook()
    ws = wb.active
    ws.title = "Datos Demográficos"
    
    # Habilitar líneas de cuadrícula visibles
    ws.views.sheetView[0].showGridLines = True
    
    # 3. Definición de Estilos Institucionales (Azul y Gris)
    fuente_titulo = Font(name='Arial', size=14, bold=True, color='0F2027')
    fuente_subtitulo = Font(name='Arial', size=10, italic=True, color='555555')
    fuente_cabecera = Font(name='Arial', size=11, bold=True, color='FFFFFF')
    fuente_datos = Font(name='Arial', size=10)
    
    fill_cabecera = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
    fill_cebra = PatternFill(start_color='F2F4F7', end_color='F2F4F7', fill_type='solid')
    
    borde_delgado = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC')
    )
    
    # 4. Construcción del Encabezado del Formato
    ws['A1'] = "CONSEJO COMUNAL MANUEL PULIDO MÉNDEZ"
    ws['A1'].font = fuente_titulo
    ws['A2'] = f"REPORTE: {reporte.titulo_reporte.upper()}"
    ws['A2'].font = Font(name='Arial', size=12, bold=True, color='1F4E78')
    
    # Detalle de las condiciones aplicadas
    resumen_filtros = f"Filtros aplicados: Género: {reporte.get_filtro_genero_display()} | Rango: {reporte.get_filtro_edad_display()}"
    ws['A3'] = resumen_filtros
    ws['A3'].font = fuente_subtitulo
    ws['A4'] = f"Fecha de exportación: {date.today().strftime('%d/%m/%Y')} | Total registros: {len(habitantes)}"
    ws['A4'].font = fuente_subtitulo
    
    # Espacio en blanco
    ws.append([]) 
    
    # 5. Cabecera de la Tabla de Datos
    columnas = ['N°', 'Cédula', 'Apellidos y Nombres', 'Edad', 'Género', '¿Es Jefe?', 'Grupo Familiar', 'Dirección de Vivienda']
    ws.append(columnas)
    
    fila_cabecera = 6
    for col_num, columna in enumerate(columnas, 1):
        celda = ws.cell(row=fila_cabecera, column=col_num)
        celda.font = fuente_cabecera
        celda.fill = fill_cabecera
        celda.alignment = Alignment(horizontal='center', vertical='center')
        celda.border = borde_delgado
    
    # 6. Llenado Lógico de los Registros Filtrados
    hoy = date.today()
    for indice, item in enumerate(habitantes, start=1):
        # Extraemos el objeto habitante real y la edad precalculada del diccionario
        h = item['objeto']
        edad = item['edad']
        
        nombre_completo = f"{h.apellido}, {h.nombre}"
        es_jefe_txt = "SÍ" if h.es_jefe_familia else "NO"
        
        # Acceso seguro a la relación de la familia mapeada en la Base de Datos
        familia_txt = h.familia.nombre_familia if h.familia else "SIN REGISTRO"
        direccion_txt = h.familia.direccion if h.familia else "No asignada"
        
        fila_datos = [
            indice,
            f"{h.tipo_cedula}-{h.cedula}",
            nombre_completo,
            edad, # 👈 Usamos la edad exacta calculada por la función auxiliar
            h.get_genero_display(),
            es_jefe_txt,
            familia_txt,    # 👈 Ahora sí se rellenará con el censo del sistema
            direccion_txt   # 👈 Ahora sí se rellenará con la dirección real
        ]
        
        ws.append(fila_datos)
        num_fila_actual = ws.max_row
        
        # Aplicamos estilos a las celdas de datos para que se vea limpio
        for col_num in range(1, len(fila_datos) + 1):
            celda = ws.cell(row=num_fila_actual, column=col_num)
            celda.font = fuente_datos
            celda.border = borde_delgado
            
            # Formato cebra intercalado para lectura ágil
            if indice % 2 == 0:
                celda.fill = fill_cebra
                
            # Alineación específica según el tipo de dato
            if col_num in [1, 2, 4, 5, 6]:
                celda.alignment = Alignment(horizontal='center')
            else:
                celda.alignment = Alignment(horizontal='left')

    # 7. Autoajuste automático del ancho de las columnas
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            # Ignoramos las primeras filas de títulos para que no ensanchen de más la columna A
            if cell.row < 6:
                continue
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # Ajustes manuales mínimos para columnas largas
    ws.column_dimensions['C'].width = 30  # Nombre
    ws.column_dimensions['H'].width = 40  # Dirección

    # 8. Guardado en Buffer RAM y respuesta HTTP directa de descarga
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="Reporte_Demografico_{reporte.id}.xlsx"'
    
    return response

def exportar_reporte_pdf(request, reporte_id):
    """
    Genera un listado demográfico profesional en formato PDF en tiempo real,
    inyectando el logo institucional en formato Base64 directamente en la memoria RAM.
    """
    # 1. Recuperamos la configuración del reporte y su lista de habitantes filtrados
    reporte = get_object_or_404(ReporteDemografico, id=reporte_id)
    habitantes = obtener_habitantes_filtrados(reporte)
    
    # =========================================================================
    # PROCESAMIENTO DEL LOGO EN BASE64 (Evita colapsos de rutas locales)
    # =========================================================================
    logo_base64 = ""
    # Construimos la ruta física buscando en tu carpeta de archivos estáticos configurada
    # Usamos 'assets/images/aguila.png' (Asegúrate de que la extensión coincida: .png o .jpg)
    ruta_logo = os.path.join(settings.STATICFILES_DIRS[0], 'assets', 'images', 'CC_logo.png')
    
    if os.path.exists(ruta_logo):
        with open(ruta_logo, "rb") as image_file:
            # Leemos los bytes del archivo y los transformamos en un string UTF-8 plano
            logo_base64 = base64.b64encode(image_file.read()).decode('utf-8')
    else:
        # Respaldo impreso en la consola de Django por si escribiste mal el nombre o la extensión
        print(f"⚠️ ADVERTENCIA: No se encontró el logo en la ruta física: {ruta_logo}")
    # =========================================================================

    # 2. Construimos el contexto directo para la plantilla incluyendo el logo codificado
    hoy = date.today()
    context = {
        'reporte': reporte,
        'habitantes': habitantes,
        'total_registros': len(habitantes),
        'fecha_actual': hoy,
        'logo_pdf': logo_base64,  # 👈 Pasamos la cadena Base64 al HTML
    }
    
    # 3. Renderizamos el HTML como un String ordinario
    html_string = render_to_string('reportes/reporte_demografico_pdf.html', context)
    
    # 4. Creamos el objeto de respuesta HTTP configurado como PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Reporte_Demografico_{reporte.id}.pdf"'
    
    # 5. Compilamos el PDF directamente (Ya no dependemos críticamente de link_callback para la imagen)
    pdf = pisa.CreatePDF(
        src=html_string,
        dest=response,
        encoding='utf-8'
        # Puedes quitar o comentar la línea de link_callback si ya no manejas otros recursos externos
    )
    
    # 6. Si no hay errores lógicos visuales, el navegador inicia la descarga nativa
    if not pdf.err:
        return response
        
    return HttpResponse('Error al compilar la matriz del reporte demográfico en PDF.', status=500)