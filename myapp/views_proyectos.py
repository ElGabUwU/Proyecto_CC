"""
Vistas para la gestión de proyectos comunitarios del Consejo Comunal.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction
from django.views import View
from django.utils.decorators import method_decorator
import json
from datetime import datetime, timedelta

from .models import (
    Comite, Proyecto, ProyectoIntegrante, Habitante
)
from .forms import (
    ComiteForm, ProyectoForm, AsignarHabitanteForm
)
from .decorators import admin_required


# ============================================
# Vistas para Comités
# ============================================

def comites(request):
    """
    Vista para listar y gestionar comités.
    """
    query = request.GET.get('q', '')
    tipo = request.GET.get('tipo', '')
    
    comites_list = Comite.objects.filter(is_deleted=False)
    
    if query:
        comites_list = comites_list.filter(
            Q(nombre__icontains=query) |
            Q(descripcion__icontains=query)
        )
    
    if tipo:
        comites_list = comites_list.filter(tipo_comite=tipo)
    
    comites_list = comites_list.order_by('nombre')
    
    paginator = Paginator(comites_list, 15)
    page_number = request.GET.get('page')
    comites_page = paginator.get_page(page_number)
    
    context = {
        'comites': comites_page,
        'query': query,
        'tipo': tipo,
        'comite_form': ComiteForm(),
        'tipos_comite': Comite.TIPO_COMITE_CHOICES,
    }
    
    return render(request, 'comites.html', context)


def crear_comite(request):
    if request.method == 'POST':
        form = ComiteForm(request.POST)
        if form.is_valid():
            comite = form.save()
            messages.success(request, f'Comité "{comite.nombre}" creado exitosamente.')
            return redirect('comites')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = ComiteForm()
    
    context = {'form': form}
    return render(request, 'comites.html', context)


def editar_comite(request, id):
    comite = get_object_or_404(Comite, id=id, is_deleted=False)
    
    if request.method == 'POST':
        form = ComiteForm(request.POST, instance=comite)
        if form.is_valid():
            comite = form.save()
            messages.success(request, f'Comité "{comite.nombre}" actualizado exitosamente.')
            return redirect('comites')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = ComiteForm(instance=comite)
    
    context = {'form': form, 'comite': comite}
    return render(request, 'comites.html', context)


@require_POST
def eliminar_comite(request, id):
    comite = get_object_or_404(Comite, id=id, is_deleted=False)
    
    proyectos_activos = comite.proyectos.filter(is_deleted=False).count()
    if proyectos_activos > 0:
        messages.error(request, f'No se puede eliminar el comité porque tiene {proyectos_activos} proyecto(s) asociado(s).')
        return redirect('comites')
    
    comite.delete()
    messages.success(request, f'Comité "{comite.nombre}" eliminado exitosamente.')
    return redirect('comites')


@require_GET
def api_comite(request, id):
    comite = get_object_or_404(Comite, id=id, is_deleted=False)
    
    # ✅ CORRECCIÓN: Acceder directamente a nombre/apellido del Habitante
    vocero_nombre = f"{comite.vocero_principal.nombre} {comite.vocero_principal.apellido}" if comite.vocero_principal else ''
    
    data = {
        'id': comite.id,
        'nombre': comite.nombre,
        'tipo_comite': comite.tipo_comite,
        'tipo_comite_display': comite.get_tipo_comite_display(),
        'descripcion': comite.descripcion or '',
        'vocero_principal': comite.vocero_principal.id if comite.vocero_principal else None,
        'vocero_principal_nombre': vocero_nombre,
        'activo': comite.activo,
        'proyectos_count': comite.cantidad_proyectos_activos(),
    }
    
    return JsonResponse(data)


# ============================================
# Vistas para Proyectos
# ============================================

def proyectos(request):
    """
    Vista para listar y buscar proyectos comunitarios.
    """
    query = request.GET.get('q', '')
    estatus = request.GET.get('estatus', '')
    comite_id = request.GET.get('comite', '')
    
    proyectos_list = Proyecto.objects.filter(is_deleted=False).select_related('comite')
    
    if query:
        proyectos_list = proyectos_list.filter(
            Q(nombre__icontains=query) |
            Q(descripcion__icontains=query) |
            Q(comite__nombre__icontains=query)
        )
    
    if estatus:
        proyectos_list = proyectos_list.filter(estatus=estatus)
    
    if comite_id:
        proyectos_list = proyectos_list.filter(comite_id=comite_id)
    
    proyectos_list = proyectos_list.annotate(num_integrantes=Count('integrantes'))
    proyectos_list = proyectos_list.order_by('-fecha_creacion')
    
    paginator = Paginator(proyectos_list, 15)
    page_number = request.GET.get('page')
    proyectos_page = paginator.get_page(page_number)
    
    comites = Comite.objects.filter(is_deleted=False, activo=True).order_by('nombre')

    # ✅ CORRECCIÓN: Usar valores SINGULARES para coincidir con ESTATUS_CHOICES del modelo
    conteos = proyectos_list.aggregate(
        planificacion=Count('pk', filter=Q(estatus='planificacion')),
        ejecucion=Count('pk', filter=Q(estatus='ejecucion')),
        finalizado=Count('pk', filter=Q(estatus='finalizado')),
        cancelado=Count('pk', filter=Q(estatus='cancelado')),
    )
    
    context = {
        'proyectos': proyectos_page,
        'comites': comites,
        'query': query,
        'estatus': estatus,
        'comite_id': comite_id,
        'proyecto_form': ProyectoForm(user=request.user),
        'estatus_choices': Proyecto.ESTATUS_CHOICES,
        'count_planificacion': conteos['planificacion'],
        'count_ejecucion': conteos['ejecucion'],
        'count_finalizado': conteos['finalizado'],   # ✅ Clave corregida
        'count_cancelado': conteos['cancelado'],     # ✅ Clave corregida
    }
    
    return render(request, 'proyectos/proyecto_list.html', context)


def crear_proyecto(request):
    if request.method == 'POST':
        form = ProyectoForm(request.POST, user=request.user)
        if form.is_valid():
            proyecto = form.save()
            messages.success(request, f'Proyecto "{proyecto.nombre}" creado exitosamente.')
            # Si es una petición AJAX, devolver respuesta JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Proyecto "{proyecto.nombre}" creado exitosamente.',
                    'redirect_url': str(reverse('detalle_proyecto', kwargs={'pk': proyecto.pk}))
                })
            return redirect('proyectos')
        else:
            # Si es una petición AJAX, devolver los errores del formulario en JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {}
                for field, error_list in form.errors.items():
                    field_label = form.fields[field].label if field in form.fields else field
                    errors[field] = [str(e) for e in error_list]
                return JsonResponse({
                    'success': False,
                    'errors': errors,
                    'message': 'Por favor corrija los errores en el formulario.'
                }, status=400)
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = ProyectoForm(user=request.user)
    
    context = {'form': form}
    return render(request, 'proyectos/proyecto_list.html', context)


def detalle_proyecto(request, pk):
    proyecto = get_object_or_404(
        Proyecto.objects.filter(is_deleted=False).prefetch_related(
            'integrantes__habitante',          # ✅ Eliminada referencia a __persona
            'integrantes__habitante__familia'
        ).select_related('comite', 'creado_por'),
        pk=pk
    )
    
    integrantes = proyecto.integrantes.all()
    integrantes_por_rol = {}
    for integrante in integrantes:
        rol = integrante.get_rol_display()
        integrantes_por_rol.setdefault(rol, []).append(integrante)
    
    context = {
        'proyecto': proyecto,
        'integrantes': integrantes,
        'integrantes_por_rol': integrantes_por_rol,
        'asignar_form': AsignarHabitanteForm(proyecto=proyecto),
    }
    
    return render(request, 'proyectos/proyecto_detail.html', context)


def editar_proyecto(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        form = ProyectoForm(request.POST, instance=proyecto, user=request.user)
        if form.is_valid():
            proyecto = form.save()
            messages.success(request, f'Proyecto "{proyecto.nombre}" actualizado exitosamente.')
            # Si es una petición AJAX, devolver respuesta JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Proyecto "{proyecto.nombre}" actualizado exitosamente.',
                    'redirect_url': str(reverse('detalle_proyecto', kwargs={'pk': proyecto.pk}))
                })
            return redirect('detalle_proyecto', pk=proyecto.pk)
        else:
            # Si es una petición AJAX, devolver los errores del formulario en JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {}
                for field, error_list in form.errors.items():
                    field_label = form.fields[field].label if field in form.fields else field
                    errors[field] = [str(e) for e in error_list]
                return JsonResponse({
                    'success': False,
                    'errors': errors,
                    'message': 'Por favor corrija los errores en el formulario.'
                }, status=400)
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = ProyectoForm(instance=proyecto, user=request.user)
    
    context = {'form': form, 'proyecto': proyecto}
    return render(request, 'proyectos/proyecto_form.html', context)


@require_POST
def eliminar_proyecto(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, is_deleted=False)
    nombre = proyecto.nombre
    proyecto.delete()
    messages.success(request, f'Proyecto "{nombre}" eliminado exitosamente.')
    return redirect('proyectos')


@require_GET
def api_proyecto(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, is_deleted=False)
    
    data = {
        'id': proyecto.id,
        'nombre': proyecto.nombre,
        'fecha_inicio': proyecto.fecha_inicio.strftime('%Y-%m-%d'),
        'fecha_fin': proyecto.fecha_fin.strftime('%Y-%m-%d') if proyecto.fecha_fin else '',
        'descripcion': proyecto.descripcion,
        'monto_estimado': str(proyecto.monto_estimado),
        'estatus': proyecto.estatus,
        'estatus_display': proyecto.get_estatus_display(),
        'comite': proyecto.comite.id,
        'comite_nombre': proyecto.comite.nombre,
        'fecha_creacion': proyecto.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
        'creado_por': proyecto.creado_por.username if proyecto.creado_por else '',
        'integrantes_count': proyecto.cantidad_integrantes(),
    }
    
    return JsonResponse(data)


# ============================================
# Vistas para Gestión de Integrantes
# ============================================

def buscar_habitantes_proyecto(request):
    query = request.GET.get('q', '')
    proyecto_id = request.GET.get('proyecto_id', '')
    
    if len(query) < 2:
        return JsonResponse({'habitantes': []})
    
    # ✅ CORRECCIÓN: Filtrar por campos directos del modelo Habitante
    habitantes = Habitante.objects.filter(
        is_deleted=False
    ).filter(
        Q(nombre__icontains=query) |
        Q(apellido__icontains=query) |
        Q(cedula__icontains=query)
    ).select_related('familia').order_by('nombre')
    
    if proyecto_id:
        asignados = ProyectoIntegrante.objects.filter(proyecto_id=proyecto_id).values_list('habitante_id', flat=True)
        habitantes = habitantes.exclude(id__in=asignados)
    
    habitantes = habitantes[:20]  # Aplicar el slice al final, después de todos los filtros
    
    resultados = []
    for h in habitantes:
        jefe = h.familia.jefe_familia
        familia_nombre = f"{jefe.nombre} {jefe.apellido}" if jefe else "Sin definir"
        
        resultados.append({
            'id': h.id,
            'nombre': f"{h.nombre} {h.apellido}",
            'documento': h.cedula,
            'telefono': getattr(h, 'telefono', ''),  # Manejo seguro si el campo no existe
            'familia': familia_nombre,
            # ✅ CORRECCIÓN: Adaptado al campo actual es_jefe_familia
            'parentesco': "Jefe de Familia" if h.es_jefe_familia else "Miembro",
        })
    
    return JsonResponse({'habitantes': resultados})


def asignar_habitante(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        form = AsignarHabitanteForm(request.POST, proyecto=proyecto)
        if form.is_valid():
            integrante = form.save()
            # ✅ CORRECCIÓN: Nombres directos del habitante
            nombre_completo = f"{integrante.habitante.nombre} {integrante.habitante.apellido}"
            messages.success(request, f'{nombre_completo} asignado como {integrante.get_rol_display()} al proyecto.')
            return redirect('detalle_proyecto', pk=proyecto.pk)
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = AsignarHabitanteForm(proyecto=proyecto)
    
    return render(request, 'proyectos/proyecto_detail.html', {'form': form, 'proyecto': proyecto})


@require_POST
def remover_habitante(request, pk, habitante_id):
    proyecto = get_object_or_404(Proyecto, pk=pk, is_deleted=False)
    
    try:
        integrante = ProyectoIntegrante.objects.get(proyecto=proyecto, habitante_id=habitante_id)
        nombre_completo = f"{integrante.habitante.nombre} {integrante.habitante.apellido}"
        integrante.delete()
        messages.success(request, f'{nombre_completo} removido del proyecto exitosamente.')
    except ProyectoIntegrante.DoesNotExist:
        messages.error(request, 'El integrante no está asignado a este proyecto.')
    
    return redirect('detalle_proyecto', pk=proyecto.pk)


@require_GET
def api_integrante(request, integrante_id):
    integrante = get_object_or_404(ProyectoIntegrante, id=integrante_id)
    
    data = {
        'id': integrante.id,
        'proyecto': integrante.proyecto.id,
        'proyecto_nombre': integrante.proyecto.nombre,
        'habitante': integrante.habitante.id,
        'habitante_nombre': integrante.nombre_habitante,
        'habitante_documento': integrante.documento_habitante,
        'rol': integrante.rol,
        'rol_display': integrante.get_rol_display(),
        'fecha_asignacion': integrante.fecha_asignacion.strftime('%d/%m/%Y'),
        'observaciones': integrante.observaciones or '',
    }
    
    return JsonResponse(data)


# ============================================
# Vistas para Dashboard de Proyectos
# ============================================

def dashboard_proyectos(request):
    total_proyectos = Proyecto.objects.filter(is_deleted=False).count()
    
    por_estatus = Proyecto.objects.filter(is_deleted=False).values('estatus').annotate(
        count=Count('id')
    ).order_by('estatus')
    
    por_comite = Comite.objects.filter(is_deleted=False).annotate(
        num_proyectos=Count('proyectos', filter=Q(proyectos__is_deleted=False))
    ).order_by('-num_proyectos')[:10]
    
    en_ejecucion = Proyecto.objects.filter(
        is_deleted=False, 
        estatus='ejecucion'
    ).select_related('comite').order_by('fecha_inicio')[:10]
    
    presupuesto_total = Proyecto.objects.filter(is_deleted=False).aggregate(total=Sum('monto_estimado'))['total'] or 0
    
    hoy = timezone.now().date()
    en_30_dias = hoy + timedelta(days=30)
    proximos_vencer = Proyecto.objects.filter(
        is_deleted=False,
        estatus__in=['planificacion', 'ejecucion'],
        fecha_fin__range=[hoy, en_30_dias]
    ).select_related('comite').order_by('fecha_fin')[:5]
    
    context = {
        'total_proyectos': total_proyectos,
        'por_estatus': por_estatus,
        'por_comite': por_comite,
        'en_ejecucion': en_ejecucion,
        'presupuesto_total': presupuesto_total,
        'proximos_vencer': proximos_vencer,
    }
    
    return render(request, 'proyectos/dashboard_proyectos.html', context)