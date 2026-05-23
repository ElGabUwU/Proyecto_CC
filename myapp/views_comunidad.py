"""
Vistas para la gestión comunitaria del Consejo Comunal.
ARQUITECTURA NUEVA: Vista unificada maestro-detalle para Familias y Habitantes.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
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
import json
from datetime import datetime, timedelta
import csv

from .models import (
    Familia, Habitante, IngresoComunal, EgresoComunal, 
    ConstanciaResidencia, ActaReunion
)
from .forms import (
    FamiliaForm, HabitanteForm, IngresoComunalForm, 
    EgresoComunalForm, ConstanciaResidenciaForm, ActaReunionForm
)
from .decorators import admin_required, vocero_finanzas_required, vocero_secretaria_required
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

@login_required
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

@login_required
def familia_unificada(request, familia_id=None):
    """
    Vista Detalle: Renderiza la interfaz unificada de registro y edición masiva.
    """
    # Evitar bloqueos de acceso si eres el administrador del sistema
    es_autorizado = request.user.is_superuser or request.user.is_staff or getattr(request.user, 'role', None) in ['admin', 'vocero_secretaria']
    if not es_autorizado:
        messages.error(request, "No tienes permisos para acceder a esta sección.")
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

@login_required
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


@login_required
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

@login_required
def finanzas(request):
    """
    Vista principal del dashboard financiero.
    """
    # Obtener fechas para filtro
    fecha_inicio_str = request.GET.get('fecha_inicio', '')
    fecha_fin_str = request.GET.get('fecha_fin', '')
    
    # Fechas por defecto (últimos 30 días)
    fecha_fin = timezone.now().date()
    fecha_inicio = fecha_fin - timedelta(days=30)
    
    if fecha_inicio_str:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    if fecha_fin_str:
        try:
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Calcular totales generales
    total_ingresos = IngresoComunal.objects.aggregate(Sum('monto'))['monto__sum'] or 0
    total_egresos = EgresoComunal.objects.aggregate(Sum('monto'))['monto__sum'] or 0
    saldo_actual = total_ingresos - total_egresos
    
    # Calcular totales del período
    ingresos_periodo = IngresoComunal.objects.filter(
        fecha__range=[fecha_inicio, fecha_fin]
    ).aggregate(Sum('monto'))['monto__sum'] or 0
    
    egresos_periodo = EgresoComunal.objects.filter(
        fecha__range=[fecha_inicio, fecha_fin]
    ).aggregate(Sum('monto'))['monto__sum'] or 0
    
    saldo_periodo = ingresos_periodo - egresos_periodo
    
    # Obtener movimientos del período
    ingresos = IngresoComunal.objects.filter(
        fecha__range=[fecha_inicio, fecha_fin]
    ).order_by('-fecha', '-fecha_registro')[:50]
    
    egresos = EgresoComunal.objects.filter(
        fecha__range=[fecha_inicio, fecha_fin]
    ).order_by('-fecha', '-fecha_registro')[:50]
    
    # Preparar movimientos combinados para reporte
    movimientos_periodo = []
    for ingreso in ingresos:
        movimientos_periodo.append({
            'fecha': ingreso.fecha,
            'tipo': 'ingreso',
            'concepto': ingreso.concepto,
            'monto': ingreso.monto,
            'responsable': ingreso.responsable,
        })
    
    for egreso in egresos:
        movimientos_periodo.append({
            'fecha': egreso.fecha,
            'tipo': 'egreso',
            'concepto': egreso.concepto,
            'monto': egreso.monto,
            'responsable': egreso.responsable,
        })
    
    # Ordenar movimientos por fecha
    movimientos_periodo.sort(key=lambda x: x['fecha'], reverse=True)
    
    context = {
        'saldo_actual': saldo_actual,
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
        'total_ingresos_periodo': ingresos_periodo,
        'total_egresos_periodo': egresos_periodo,
        'saldo_periodo': saldo_periodo,
        'ingresos': ingresos,
        'egresos': egresos,
        'movimientos_periodo': movimientos_periodo,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'ingreso_form': IngresoComunalForm(user=request.user),
        'egreso_form': EgresoComunalForm(user=request.user),
    }
    
    return render(request, 'finanzas.html', context)


@login_required
@vocero_finanzas_required
def crear_ingreso(request):
    """
    Vista para crear un nuevo ingreso.
    """
    if request.method == 'POST':
        form = IngresoComunalForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            ingreso = form.save()
            messages.success(request, f'Ingreso de Bs. {ingreso.monto} registrado exitosamente.')
            return redirect('finanzas')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = IngresoComunalForm(user=request.user)
    
    context = {'form': form}
    return render(request, 'finanzas.html', context)


@login_required
@vocero_finanzas_required
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


@login_required
@vocero_finanzas_required
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


@login_required
@vocero_finanzas_required
def crear_egreso(request):
    """
    Vista para crear un nuevo egreso.
    """
    if request.method == 'POST':
        form = EgresoComunalForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            egreso = form.save()
            messages.success(request, f'Egreso de Bs. {egreso.monto} registrado exitosamente.')
            return redirect('finanzas')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = EgresoComunalForm(user=request.user)
    
    context = {'form': form}
    return render(request, 'finanzas.html', context)


@login_required
@vocero_finanzas_required
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


@login_required
@vocero_finanzas_required
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


@login_required
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
    }
    
    return JsonResponse(data)


@login_required
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
    }
    
    return JsonResponse(data)


@login_required
def exportar_finanzas(request):
    """
    Vista para exportar datos financieros a CSV.
    """
    # Obtener parámetros de filtro
    fecha_inicio_str = request.GET.get('fecha_inicio', '')
    fecha_fin_str = request.GET.get('fecha_fin', '')
    
    # Crear respuesta CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="finanzas_comunales.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Fecha', 'Tipo', 'Concepto', 'Monto (Bs.)', 'Responsable', 'Beneficiario', 'Observaciones'])
    
    # Obtener ingresos
    ingresos = IngresoComunal.objects.all()
    if fecha_inicio_str and fecha_fin_str:
        ingresos = ingresos.filter(fecha__range=[fecha_inicio_str, fecha_fin_str])
    
    for ingreso in ingresos:
        writer.writerow([
            ingreso.fecha.strftime('%d/%m/%Y'),
            'INGRESO',
            ingreso.concepto,
            ingreso.monto,
            ingreso.responsable.get_full_name(),
            '',
            ingreso.observaciones or ''
        ])
    
    # Obtener egresos
    egresos = EgresoComunal.objects.all()
    if fecha_inicio_str and fecha_fin_str:
        egresos = egresos.filter(fecha__range=[fecha_inicio_str, fecha_fin_str])
    
    for egreso in egresos:
        writer.writerow([
            egreso.fecha.strftime('%d/%m/%Y'),
            'EGRESO',
            egreso.concepto,
            egreso.monto,
            egreso.responsable.get_full_name(),
            egreso.beneficiario or '',
            egreso.observaciones or ''
        ])
    
    return response


# ============================================
# Vistas para Documentación
# ============================================

@login_required
def documentacion(request):
    """
    Vista principal para la generación de documentos.
    """
    # Obtener familias para constancias
    familias = Familia.objects.filter(is_deleted=False)
    
    # Obtener constancias recientes
    constancias_recientes = ConstanciaResidencia.objects.all().order_by('-fecha_generacion')[:10]
    
    # Obtener actas recientes
    actas_recientes = ActaReunion.objects.all().order_by('-fecha_reunion')[:10]
    
    context = {
        'familias': familias,
        'constancias_recientes': constancias_recientes,
        'actas_recientes': actas_recientes,
        'constancia_form': ConstanciaResidenciaForm(user=request.user),
        'acta_form': ActaReunionForm(user=request.user),
    }
    
    return render(request, 'documentacion.html', context)


@login_required
@vocero_secretaria_required
def generar_constancia(request):
    """
    Vista para generar una constancia de residencia.
    """
    if request.method == 'POST':
        form = ConstanciaResidenciaForm(request.POST, user=request.user)
        if form.is_valid():
            constancia = form.save()
            messages.success(request, f'Constancia para {constancia.familia.jefe_familia.name} generada exitosamente.')
            
            # TODO: Generar PDF y adjuntar al modelo
            # constancia.archivo_pdf = generar_pdf_constancia(constancia)
            # constancia.save()
            
            return redirect('documentacion')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = ConstanciaResidenciaForm(user=request.user)
    
    context = {'form': form}
    return render(request, 'documentacion.html', context)


@login_required
@vocero_secretaria_required
def generar_acta(request):
    """
    Vista para generar un acta de reunión.
    """
    if request.method == 'POST':
        form = ActaReunionForm(request.POST, user=request.user)
        if form.is_valid():
            acta = form.save()
            messages.success(request, f'Acta "{acta.titulo}" generada exitosamente.')
            
            # TODO: Generar PDF y adjuntar al modelo
            # acta.archivo_pdf = generar_pdf_acta(acta)
            # acta.save()
            
            return redirect('documentacion')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = ActaReunionForm(user=request.user)
    
    context = {'form': form}
    return render(request, 'documentacion.html', context)


@login_required
@require_GET
def descargar_constancia(request, id):
    """
    Vista para descargar una constancia en PDF.
    """
    constancia = get_object_or_404(ConstanciaResidencia, id=id)
    
    # TODO: Implementar generación y descarga de PDF
    # response = HttpResponse(constancia.archivo_pdf.read(), content_type='application/pdf')
    # response['Content-Disposition'] = f'attachment; filename="constancia_{constancia.id}.pdf"'
    # return response
    
    messages.warning(request, 'Generación de PDF no implementada aún.')
    return redirect('documentacion')


@login_required
@require_GET
def descargar_acta(request, id):
    """
    Vista para descargar un acta en PDF.
    """
    acta = get_object_or_404(ActaReunion, id=id)
    
    # TODO: Implementar generación y descarga de PDF
    # response = HttpResponse(acta.archivo_pdf.read(), content_type='application/pdf')
    # response['Content-Disposition'] = f'attachment; filename="acta_{acta.id}.pdf"'
    # return response
    
    messages.warning(request, 'Generación de PDF no implementada aún.')
    return redirect('documentacion')


@login_required
@require_GET
def previa_constancia(request, id):
    """
    API para obtener previsualización de una constancia en JSON.
    """
    constancia = get_object_or_404(ConstanciaResidencia, id=id)
    
    data = {
        'id': constancia.id,
        'familia': f"{constancia.familia.jefe_familia.name} {constancia.familia.jefe_familia.surname}",
        'fecha': constancia.fecha_documento.strftime('%d/%m/%Y'),
        'finalidad': constancia.finalidad,
        'contenido': constancia.contenido,
    }
    
    return JsonResponse(data)


@login_required
@require_GET
def previa_acta(request, id):
    """
    API para obtener previsualización de un acta en JSON.
    """
    acta = get_object_or_404(ActaReunion, id=id)
    
    data = {
        'id': acta.id,
        'titulo': acta.titulo,
        'fecha_reunion': acta.fecha_reunion.strftime('%d/%m/%Y %H:%M'),
        'lugar': acta.lugar,
        'asistentes_count': acta.asistentes_count(),
        'contenido': acta.contenido,
    }
    
    return JsonResponse(data)


# ============================================
# Vistas para Dashboard Comunitario
# ============================================

@login_required
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