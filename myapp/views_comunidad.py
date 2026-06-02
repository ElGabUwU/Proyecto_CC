"""
Vistas para la gestión comunitaria del Consejo Comunal.
ARQUITECTURA NUEVA: Vista unificada maestro-detalle para Familias y Habitantes.
"""
from django.contrib.auth.decorators import login_required
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
import json
from datetime import datetime, timedelta
import io
from xhtml2pdf import pisa
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

# ============================================
# Vistas para Habitantes (Lista y Detalle)
# ============================================

@login_required
def habitantes(request):
    """
    Vista de listado general de habitantes.
    Adaptada al modelo unificado (sin tabla Person).
    """
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


@login_required
def detalle_habitante(request, id):
    """
    Vista de detalle de un habitante individual.
    """
    habitante = get_object_or_404(Habitante, id=id, is_deleted=False)
    
    context = {
        'habitante': habitante,
    }
    return render(request, 'detalle_habitante.html', context)


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
        'soporte_digital_nombre': ingreso.soporte_digital.name if ingreso.soporte_digital else None,
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
        'soporte_nombre': egreso.soporte.name if egreso.soporte else None,
    }
    
    return JsonResponse(data)


@login_required
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

# Nota: Conserva o ajusta tus decoradores de permisos según los manejes en tu app
def vocero_secretaria_required(view_func):
    return view_func  # Si usas @login_required, puedes dejarlo pasar para la beta

@login_required
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
    }
    return render(request, 'documentacion.html', context)


@login_required
def generar_constancia(request):
    """
    Vista que procesa el formulario enviado desde el HTML de manera síncrona.
    """
    if request.method == 'POST':
        form = ConstanciaResidenciaForm(request.POST, user=request.user)
        
        if form.is_valid():
            # Aquí se guarda correctamente en PostgreSQL
            constancia = form.save()
            
            # 💡 CORRECCIÓN AQUÍ: Navegamos correctamente a través del habitante para buscar la familia
            familia_objeto = constancia.habitante.familia if hasattr(constancia.habitante, 'familia') else None
            
            if familia_objeto:
                # Buscamos el jefe de hogar de forma segura dentro de la relación inversa de habitantes
                jefe = familia_objeto.habitantes.filter(es_jefe_familia=True, is_deleted=False).first()
            else:
                jefe = None
            
            # Extraemos el nombre completo del ciudadano solicitante
            nombre_ciudadano = f"{constancia.habitante.nombre} {constancia.habitante.apellido}"
            
            messages.success(
                request, 
                f'¡Excelente! La constancia de residencia para <strong>{nombre_ciudadano}</strong> se ha generado con éxito.'
            )
            return redirect('documentacion')
        else:
            print("Errores en validación de constancia:", form.errors)
            messages.error(request, 'Por favor, verifique los datos del formulario de constancia.')
            
    return redirect('documentacion')


@login_required
@transaction.atomic
def generar_acta(request):
    """
    Vista para procesar la creación de actas de asambleas.
    """
    if request.method == 'POST':
        form = ActaReunionForm(request.POST, user=request.user)
        if form.is_valid():
            acta = form.save()
            messages.success(request, f'Acta "{acta.titulo}" asentada dinámicamente en Postgres.')
            return redirect('documentacion')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario del acta.')
    return redirect('documentacion')


@login_required
@require_GET
def descargar_constancia(request, id):
    constancia = get_object_or_404(ConstanciaResidencia, id=id)
    solicitante = constancia.habitante
    
    # 🆕 BLINDAJE CRÍTICO
    familia = getattr(solicitante, 'familia', None)
    
    if familia is not None:
        jefe = familia.habitantes.filter(es_jefe_familia=True, is_deleted=False).first()
        if not jefe:
            jefe = familia.habitantes.filter(is_deleted=False).first()
    else:
        jefe = solicitante  # Si no hay familia, el jefe por defecto es el mismo solicitante
        
    context = {
        'constancia': constancia,
        'solicitante': solicitante,
        'familia': familia,
        'jefe': jefe,
        'tiempo': 'VARIOS AÑOS',
        'motivo': constancia.finalidad,
        'fecha_emision': constancia.fecha_documento,
    }
    
    html_string = render_to_string('residence.html', context)
    
    result = io.BytesIO()
    pisa_status = pisa.pisaDocument(io.BytesIO(html_string.encode("UTF-8")), result)
    
    if not pisa_status.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        cedula_pdf = jefe.cedula if jefe else constancia.id
        response['Content-Disposition'] = f'inline; filename="Constancia_{cedula_pdf}.pdf"'
        return response
        
    messages.error(request, 'Ocurrió un error técnico al compilar el PDF de la constancia.')
    return redirect('documentacion')

@login_required
@require_GET
def descargar_acta(request, id):
    """
    Descarga el PDF formal del acta de reunión.
    """
    acta = get_object_or_404(ActaReunion, id=id)
    
    # Renderizamos usando el HTML estructurado guardado dinámicamente por tu formulario
    html_string = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="padding: 40px; font-family: Arial, sans-serif; color: #334155;">
        {acta.contenido_formateado if hasattr(acta, 'contenido_formateado') else acta.contenido}
    </body>
    </html>
    """
    
    result = io.BytesIO()
    pisa_status = pisa.pisaDocument(io.BytesIO(html_string.encode("UTF-8")), result)
    
    if not pisa_status.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Acta_Asamblea_{acta.id}.pdf"'
        return response
        
    messages.error(request, 'No se pudo exportar el acta seleccionada.')
    return redirect('documentacion')


@login_required
def previa_constancia(request, constancia_id):
    try:
        constancia = ConstanciaResidencia.objects.get(id=constancia_id)
        habitante = constancia.habitante
        
        # 🆕 BLINDAJE CRÍTICO: Verificamos si realmente existe la relación antes de pedir atributos
        familia_obj = getattr(habitante, 'familia', None)
        
        if familia_obj is not None:
            nombre_familia = familia_obj.nombre_familia
        else:
            nombre_familia = "SIN GRUPO FAMILIAR REGISTRADO"
            
        data = {
            'id': constancia.id,
            'familia': nombre_familia,
            'solicitante': f"{habitante.nombre} {habitante.apellido}",
            'fecha': constancia.fecha_documento.strftime('%d/%m/%Y'),
            'finalidad': constancia.finalidad,
            'contenido': constancia.contenido
        }
        return JsonResponse(data)
    except ConstanciaResidencia.DoesNotExist:
        return JsonResponse({'error': 'La constancia no existe'}, status=404)


@login_required
@require_GET
def previa_acta(request, id):
    """
    API JSON para la previsualización interactiva de actas de asambleas.
    """
    acta = get_object_or_404(ActaReunion, id=id)
    
    # Controlamos si el conteo es un método o propiedad del modelo
    try:
        count = acta.asistentes_count()
    except TypeError:
        count = acta.asistentes_count
        
    data = {
        'id': acta.id,
        'titulo': acta.titulo,
        'fecha_reunion': acta.fecha_reunion.strftime('%d/%m/%Y %H:%M'),
        'lugar': acta.lugar,
        'asistentes_count': count,
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