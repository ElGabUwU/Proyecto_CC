"""
Vistas para la gestión de proyectos comunitarios del Consejo Comunal.
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
from django.views import View
from django.utils.decorators import method_decorator
import json
from datetime import datetime, timedelta

from .models import (
    Comite, Proyecto, ProyectoIntegrante, Habitante, Person
)
from .forms import (
    ComiteForm, ProyectoForm, AsignarHabitanteForm
)
from .decorators import admin_required


# ============================================
# Vistas para Comités
# ============================================

@login_required
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
    
    # Ordenar por nombre
    comites_list = comites_list.order_by('nombre')
    
    # Paginación
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


@login_required
@admin_required
def crear_comite(request):
    """
    Vista para crear un nuevo comité.
    """
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


@login_required
@admin_required
def editar_comite(request, id):
    """
    Vista para editar un comité existente.
    """
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
    
    context = {
        'form': form,
        'comite': comite,
    }
    return render(request, 'comites.html', context)


@login_required
@admin_required
@require_POST
def eliminar_comite(request, id):
    """
    Vista para eliminar (soft delete) un comité.
    """
    comite = get_object_or_404(Comite, id=id, is_deleted=False)
    
    # Verificar si tiene proyectos activos
    proyectos_activos = comite.proyectos.filter(is_deleted=False).count()
    if proyectos_activos > 0:
        messages.error(
            request, 
            f'No se puede eliminar el comité porque tiene {proyectos_activos} proyecto(s) asociado(s).'
        )
        return redirect('comites')
    
    comite.delete()  # Soft delete
    messages.success(request, f'Comité "{comite.nombre}" eliminado exitosamente.')
    return redirect('comites')


@login_required
@require_GET
def api_comite(request, id):
    """
    API para obtener datos de un comité en formato JSON (para AJAX).
    """
    comite = get_object_or_404(Comite, id=id, is_deleted=False)
    
    data = {
        'id': comite.id,
        'nombre': comite.nombre,
        'tipo_comite': comite.tipo_comite,
        'tipo_comite_display': comite.get_tipo_comite_display(),
        'descripcion': comite.descripcion or '',
        'vocero_principal': comite.vocero_principal.id if comite.vocero_principal else None,
        'vocero_principal_nombre': f"{comite.vocero_principal.name} {comite.vocero_principal.surname}" if comite.vocero_principal else '',
        'activo': comite.activo,
        'proyectos_count': comite.cantidad_proyectos_activos(),
    }
    
    return JsonResponse(data)


# ============================================
# Vistas para Proyectos
# ============================================

@login_required
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
    
    # Anotar cantidad de integrantes
    proyectos_list = proyectos_list.annotate(
        num_integrantes=Count('integrantes')
    )
    
    # Ordenar por fecha de creación (más recientes primero)
    proyectos_list = proyectos_list.order_by('-fecha_creacion')
    
    # Paginación
    paginator = Paginator(proyectos_list, 15)
    page_number = request.GET.get('page')
    proyectos_page = paginator.get_page(page_number)
    
    # Obtener todos los comités para el filtro
    comites = Comite.objects.filter(is_deleted=False, activo=True).order_by('nombre')

    conteos = proyectos_list.aggregate(
        planificacion=Count('pk', filter=Q(estatus='planificacion')),
        ejecucion=Count('pk', filter=Q(estatus='ejecucion')),
        finalizados=Count('pk', filter=Q(estatus='finalizados')),
        cancelados=Count('pk', filter=Q(estatus='cancelados')),
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
        'count_finalizados': conteos['finalizados'],
        'count_cancelados': conteos['cancelados'],
    }
    
    return render(request, 'proyectos/proyecto_list.html', context)


@login_required
@admin_required
def crear_proyecto(request):
    """
    Vista para crear un nuevo proyecto.
    """
    if request.method == 'POST':
        form = ProyectoForm(request.POST, user=request.user)
        if form.is_valid():
            proyecto = form.save()
            messages.success(request, f'Proyecto "{proyecto.nombre}" creado exitosamente.')
            return redirect('proyectos')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = ProyectoForm(user=request.user)
    
    context = {'form': form}
    return render(request, 'proyectos/proyecto_list.html', context)


@login_required
def detalle_proyecto(request, pk):
    """
    Vista para ver el detalle completo de un proyecto.
    Incluye el listado de integrantes asignados.
    """
    proyecto = get_object_or_404(
        Proyecto.objects.filter(is_deleted=False).prefetch_related(
            'integrantes__habitante__persona',
            'integrantes__habitante__familia'
        ).select_related('comite', 'creado_por'),
        pk=pk
    )
    
    # Obtener integrantes ordenados por rol
    integrantes = proyecto.integrantes.all()
    
    # Agrupar integrantes por rol
    integrantes_por_rol = {}
    for integrante in integrantes:
        rol = integrante.get_rol_display()
        if rol not in integrantes_por_rol:
            integrantes_por_rol[rol] = []
        integrantes_por_rol[rol].append(integrante)
    
    context = {
        'proyecto': proyecto,
        'integrantes': integrantes,
        'integrantes_por_rol': integrantes_por_rol,
        'asignar_form': AsignarHabitanteForm(proyecto=proyecto),
    }
    
    return render(request, 'proyectos/proyecto_detail.html', context)


@login_required
@admin_required
def editar_proyecto(request, pk):
    """
    Vista para editar un proyecto existente.
    """
    proyecto = get_object_or_404(Proyecto, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        form = ProyectoForm(request.POST, instance=proyecto, user=request.user)
        if form.is_valid():
            proyecto = form.save()
            messages.success(request, f'Proyecto "{proyecto.nombre}" actualizado exitosamente.')
            return redirect('detalle_proyecto', pk=proyecto.pk)
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = ProyectoForm(instance=proyecto, user=request.user)
    
    context = {
        'form': form,
        'proyecto': proyecto,
    }
    return render(request, 'proyectos/proyecto_form.html', context)


@login_required
@admin_required
@require_POST
def eliminar_proyecto(request, pk):
    """
    Vista para eliminar (soft delete) un proyecto.
    """
    proyecto = get_object_or_404(Proyecto, pk=pk, is_deleted=False)
    
    nombre = proyecto.nombre
    proyecto.delete()  # Soft delete
    
    messages.success(request, f'Proyecto "{nombre}" eliminado exitosamente.')
    return redirect('proyectos')


@login_required
@require_GET
def api_proyecto(request, pk):
    """
    API para obtener datos de un proyecto en formato JSON (para AJAX).
    """
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

@login_required
def buscar_habitantes_proyecto(request):
    """
    API para buscar habitantes para asignar a un proyecto.
    Busca por nombre, apellido o número de documento.
    """
    query = request.GET.get('q', '')
    proyecto_id = request.GET.get('proyecto_id', '')
    
    if len(query) < 2:
        return JsonResponse({'habitantes': []})
    
    # Buscar habitantes no eliminados
    habitantes = Habitante.objects.filter(
        is_deleted=False
    ).filter(
        Q(persona__name__icontains=query) |
        Q(persona__surname__icontains=query) |
        Q(persona__document_number__icontains=query)
    ).select_related('persona', 'familia').order_by('persona__name')[:20]
    
    # Si hay proyecto, excluir los ya asignados
    if proyecto_id:
        asignados = ProyectoIntegrante.objects.filter(
            proyecto_id=proyecto_id
        ).values_list('habitante_id', flat=True)
        habitantes = habitantes.exclude(id__in=asignados)
    
    resultados = []
    for h in habitantes:
        resultados.append({
            'id': h.id,
            'nombre': f"{h.persona.name} {h.persona.surname}",
            'documento': h.persona.document_number,
            'telefono': h.persona.telephone_number or '',
            'familia': f"{h.familia.jefe_familia.name} {h.familia.jefe_familia.surname}",
            'parentesco': h.get_parentesco_jefe_display(),
        })
    
    return JsonResponse({'habitantes': resultados})


@login_required
@admin_required
def asignar_habitante(request, pk):
    """
    Vista para asignar un habitante a un proyecto.
    """
    proyecto = get_object_or_404(Proyecto, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        form = AsignarHabitanteForm(request.POST, proyecto=proyecto)
        if form.is_valid():
            integrante = form.save()
            messages.success(
                request, 
                f'{integrante.habitante.persona.name} {integrante.habitante.persona.surname} '
                f'asignado como {integrante.get_rol_display()} al proyecto.'
            )
            return redirect('detalle_proyecto', pk=proyecto.pk)
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = AsignarHabitanteForm(proyecto=proyecto)
    
    context = {
        'form': form,
        'proyecto': proyecto,
    }
    return render(request, 'proyectos/proyecto_detail.html', context)


@login_required
@admin_required
@require_POST
def remover_habitante(request, pk, habitante_id):
    """
    Vista para remover un habitante de un proyecto.
    """
    proyecto = get_object_or_404(Proyecto, pk=pk, is_deleted=False)
    
    try:
        integrante = ProyectoIntegrante.objects.get(
            proyecto=proyecto,
            habitante_id=habitante_id
        )
        nombre = f"{integrante.habitante.persona.name} {integrante.habitante.persona.surname}"
        integrante.delete()
        messages.success(request, f'{nombre} removido del proyecto exitosamente.')
    except ProyectoIntegrante.DoesNotExist:
        messages.error(request, 'El integrante no está asignado a este proyecto.')
    
    return redirect('detalle_proyecto', pk=proyecto.pk)


@login_required
@require_GET
def api_integrante(request, integrante_id):
    """
    API para obtener datos de un integrante en formato JSON (para AJAX).
    """
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

@login_required
def dashboard_proyectos(request):
    """
    Vista del dashboard de proyectos con estadísticas.
    """
    # Estadísticas generales
    total_proyectos = Proyecto.objects.filter(is_deleted=False).count()
    
    # Proyectos por estatus
    por_estatus = Proyecto.objects.filter(is_deleted=False).values('estatus').annotate(
        count=Count('id')
    ).order_by('estatus')
    
    # Proyectos por comité
    por_comite = Comite.objects.filter(is_deleted=False).annotate(
        num_proyectos=Count('proyectos', filter=Q(proyectos__is_deleted=False))
    ).order_by('-num_proyectos')[:10]
    
    # Proyectos en ejecución
    en_ejecucion = Proyecto.objects.filter(
        is_deleted=False, 
        estatus='ejecucion'
    ).select_related('comite').order_by('fecha_inicio')[:10]
    
    # Presupuesto total estimado
    presupuesto_total = Proyecto.objects.filter(
        is_deleted=False
    ).aggregate(
        total=Sum('monto_estimado')
    )['total'] or 0
    
    # Proyectos próximos a vencer (fecha_fin en los próximos 30 días)
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
