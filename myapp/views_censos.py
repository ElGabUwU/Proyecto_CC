"""
Vistas para la gestión de censos comunitarios del Consejo Comunal.
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
import csv

from .models import (
    Censo, CensoParticipante, Habitante, Person
)
from .forms import (
    CensoForm, AsignarParticipanteForm
)
from .decorators import admin_required


# ============================================
# Vistas para Censos
# ============================================

@login_required
def censos(request):
    """
    Vista para listar y buscar censos comunitarios.
    """
    query = request.GET.get('q', '')
    estatus = request.GET.get('estatus', '')
    categoria = request.GET.get('categoria', '')
    
    censos_list = Censo.objects.filter(is_deleted=False).select_related('creado_por')
    
    if query:
        censos_list = censos_list.filter(
            Q(nombre_censo__icontains=query) |
            Q(descripcion__icontains=query)
        )
    
    if estatus:
        censos_list = censos_list.filter(estatus=estatus)
    
    if categoria:
        censos_list = censos_list.filter(categoria_enfoque=categoria)
    
    # Anotar cantidad de participantes
    censos_list = censos_list.annotate(
        num_participantes=Count('participantes')
    )
    
    # Ordenar por fecha de creación (más recientes primero)
    censos_list = censos_list.order_by('-fecha_creacion')
    
    # Paginación
    paginator = Paginator(censos_list, 15)
    page_number = request.GET.get('page')
    censos_page = paginator.get_page(page_number)

    conteos = censos_list.aggregate(
        activo=Count('pk', filter=Q(estatus='activo')),
        cerrado=Count('pk', filter=Q(estatus='cerrado')),
        archivado=Count('pk', filter=Q(estatus='archivado')),
    )
    
    context = {
        'censos': censos_page,
        'query': query,
        'estatus': estatus,
        'categoria': categoria,
        'censo_form': CensoForm(user=request.user),
        'estatus_choices': Censo.ESTATUS_CHOICES,
        'categoria_choices': Censo.CATEGORIA_ENFOQUE_CHOICES,
        'count_activo': conteos['activo'],
        'count_cerrado': conteos['cerrado'],
        'count_archivado': conteos['archivado'],
    }
    
    return render(request, 'censos/censo_list.html', context)


@login_required
@admin_required
def crear_censo(request):
    """
    Vista para crear un nuevo censo.
    """
    if request.method == 'POST':
        form = CensoForm(request.POST, user=request.user)
        if form.is_valid():
            censo = form.save()
            messages.success(request, f'Censo "{censo.nombre_censo}" creado exitosamente.')
            return redirect('censos')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = CensoForm(user=request.user)
    
    context = {'form': form}
    return render(request, 'censos/censo_list.html', context)


@login_required
def detalle_censo(request, pk):
    """
    Vista para ver el detalle completo de un censo.
    Incluye el listado de participantes registrados.
    """
    censo = get_object_or_404(
        Censo.objects.filter(is_deleted=False).prefetch_related(
            'participantes_censo__habitante__persona',
            'participantes_censo__habitante__familia'
        ).select_related('creado_por'),
        pk=pk
    )
    
    # Obtener participantes ordenados por fecha de registro
    participantes = censo.participantes_censo.all()
    
    # Estadísticas por categoría (familia, género, etc.)
    stats_genero = {}
    stats_familias = {}
    
    for p in participantes:
        # Estadísticas por género
        genero = p.habitante.persona.gender
        genero_display = 'Masculino' if genero == 'M' else 'Femenino' if genero == 'F' else 'No especificado'
        stats_genero[genero_display] = stats_genero.get(genero_display, 0) + 1
        
        # Estadísticas por familia
        familia_nombre = f"{p.habitante.familia.jefe_familia.name} {p.habitante.familia.jefe_familia.surname}"
        stats_familias[familia_nombre] = stats_familias.get(familia_nombre, 0) + 1
    
    context = {
        'censo': censo,
        'participantes': participantes,
        'asignar_form': AsignarParticipanteForm(censo=censo),
        'stats_genero': stats_genero,
        'stats_familias': stats_familias,
    }
    
    return render(request, 'censos/censo_detail.html', context)


@login_required
@admin_required
def editar_censo(request, pk):
    """
    Vista para editar un censo existente.
    """
    censo = get_object_or_404(Censo, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        form = CensoForm(request.POST, instance=censo, user=request.user)
        if form.is_valid():
            censo = form.save()
            messages.success(request, f'Censo "{censo.nombre_censo}" actualizado exitosamente.')
            return redirect('detalle_censo', pk=censo.pk)
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = CensoForm(instance=censo, user=request.user)
    
    context = {
        'form': form,
        'censo': censo,
    }
    return render(request, 'censos/censo_form.html', context)


@login_required
@admin_required
@require_POST
def eliminar_censo(request, pk):
    """
    Vista para eliminar (soft delete) un censo.
    """
    censo = get_object_or_404(Censo, pk=pk, is_deleted=False)
    
    nombre = censo.nombre_censo
    censo.delete()  # Soft delete
    
    messages.success(request, f'Censo "{nombre}" eliminado exitosamente.')
    return redirect('censos')


@login_required
@require_GET
def api_censo(request, pk):
    """
    API para obtener datos de un censo en formato JSON (para AJAX).
    """
    censo = get_object_or_404(Censo, pk=pk, is_deleted=False)
    
    data = {
        'id': censo.id,
        'nombre_censo': censo.nombre_censo,
        'fecha_inicio': censo.fecha_inicio.strftime('%Y-%m-%d'),
        'fecha_fin': censo.fecha_fin.strftime('%Y-%m-%d') if censo.fecha_fin else '',
        'descripcion': censo.descripcion,
        'categoria_enfoque': censo.categoria_enfoque,
        'categoria_enfoque_display': censo.get_categoria_enfoque_display(),
        'estatus': censo.estatus,
        'estatus_display': censo.get_estatus_display(),
        'fecha_creacion': censo.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
        'creado_por': censo.creado_por.username if censo.creado_por else '',
        'participantes_count': censo.cantidad_participantes(),
    }
    
    return JsonResponse(data)


# ============================================
# Vistas para Gestión de Participantes
# ============================================

@login_required
def buscar_habitantes_censo(request):
    """
    API para buscar habitantes para registrar en un censo.
    Busca por nombre, apellido o número de documento.
    """
    query = request.GET.get('q', '')
    censo_id = request.GET.get('censo_id', '')
    
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
    
    # Si hay censo, excluir los ya registrados
    if censo_id:
        registrados = CensoParticipante.objects.filter(
            censo_id=censo_id
        ).values_list('habitante_id', flat=True)
        habitantes = habitantes.exclude(id__in=registrados)
    
    resultados = []
    for h in habitantes:
        resultados.append({
            'id': h.id,
            'nombre': f"{h.persona.name} {h.persona.surname}",
            'documento': h.persona.document_number,
            'telefono': h.persona.telephone_number or '',
            'familia': f"{h.familia.jefe_familia.name} {h.familia.jefe_familia.surname}",
            'parentesco': h.get_parentesco_jefe_display(),
            'genero': h.persona.get_gender_display(),
        })
    
    return JsonResponse({'habitantes': resultados})


@login_required
@admin_required
def asignar_participante(request, pk):
    """
    Vista para registrar un habitante en un censo.
    """
    censo = get_object_or_404(Censo, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        form = AsignarParticipanteForm(request.POST, censo=censo)
        if form.is_valid():
            participante = form.save()
            messages.success(
                request, 
                f'{participante.habitante.persona.name} {participante.habitante.persona.surname} '
                f'registrado exitosamente en el censo.'
            )
            return redirect('detalle_censo', pk=censo.pk)
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = AsignarParticipanteForm(censo=censo)
    
    context = {
        'form': form,
        'censo': censo,
    }
    return render(request, 'censos/censo_detail.html', context)


@login_required
@admin_required
@require_POST
def remover_participante(request, pk, habitante_id):
    """
    Vista para remover un habitante de un censo.
    """
    censo = get_object_or_404(Censo, pk=pk, is_deleted=False)
    
    try:
        participante = CensoParticipante.objects.get(
            censo=censo,
            habitante_id=habitante_id
        )
        nombre = f"{participante.habitante.persona.name} {participante.habitante.persona.surname}"
        participante.delete()
        messages.success(request, f'{nombre} removido del censo exitosamente.')
    except CensoParticipante.DoesNotExist:
        messages.error(request, 'El habitante no está registrado en este censo.')
    
    return redirect('detalle_censo', pk=censo.pk)


@login_required
@require_GET
def api_participante(request, participante_id):
    """
    API para obtener datos de un participante en formato JSON (para AJAX).
    """
    participante = get_object_or_404(CensoParticipante, id=participante_id)
    
    data = {
        'id': participante.id,
        'censo': participante.censo.id,
        'censo_nombre': participante.censo.nombre_censo,
        'habitante': participante.habitante.id,
        'habitante_nombre': participante.nombre_habitante,
        'habitante_documento': participante.documento_habitante,
        'fecha_registro': participante.fecha_registro.strftime('%d/%m/%Y %H:%M'),
        'observaciones': participante.observaciones or '',
    }
    
    return JsonResponse(data)


# ============================================
# Vistas para Exportación
# ============================================

@login_required
def exportar_participantes_censo(request, pk):
    """
    Vista para exportar la lista de participantes de un censo a CSV.
    """
    censo = get_object_or_404(Censo, pk=pk, is_deleted=False)
    
    participantes = CensoParticipante.objects.filter(
        censo=censo
    ).select_related(
        'habitante__persona',
        'habitante__familia'
    ).order_by('habitante__persona__name')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="censo_{censo.id}_{datetime.now().strftime("%Y%m%d")}.csv"'
    
    # Delimitador ; para Excel en español
    writer = csv.writer(response, delimiter=';', quoting=csv.QUOTE_NONNUMERIC)
    writer.writerow([
        'N°', 'Cédula', 'Nombre Completo', 'Teléfono', 'Email',
        'Género', 'Familia', 'Parentesco', 'Fecha Registro', 'Observaciones'
    ])
    
    for i, p in enumerate(participantes, 1):
        writer.writerow([
            i,
            p.habitante.persona.document_number,
            f"{p.habitante.persona.name} {p.habitante.persona.surname}",
            p.habitante.persona.telelephone_number or '',
            p.habitante.persona.email or '',
            p.habitante.persona.get_gender_display(),
            f"{p.habitante.familia.jefe_familia.name} {p.habitante.familia.jefe_familia.surname}",
            p.habitante.get_parentesco_jefe_display(),
            p.fecha_registro.strftime('%d/%m/%Y %H:%M'),
            p.observaciones or '',
        ])
    
    return response


# ============================================
# Vistas para Dashboard de Censos
# ============================================

@login_required
def dashboard_censos(request):
    """
    Vista del dashboard de censos con estadísticas.
    """
    # Estadísticas generales
    total_censos = Censo.objects.filter(is_deleted=False).count()
    
    # Censos por estatus
    por_estatus = Censo.objects.filter(is_deleted=False).values('estatus').annotate(
        count=Count('id')
    ).order_by('estatus')
    
    # Censos por categoría
    por_categoria = Censo.objects.filter(is_deleted=False).values('categoria_enfoque').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Censos activos
    activos = Censo.objects.filter(
        is_deleted=False, 
        estatus='activo'
    ).annotate(
        num_participantes=Count('participantes')
    ).order_by('-fecha_creacion')[:10]
    
    # Total de participaciones
    total_participaciones = CensoParticipante.objects.count()
    
    # Últimos censos creados
    ultimos_censos = Censo.objects.filter(is_deleted=False).order_by('-fecha_creacion')[:5]
    
    # Censos próximos a cerrar (fecha_fin en los próximos 7 días)
    hoy = timezone.now().date()
    en_7_dias = hoy + timedelta(days=7)
    proximos_cerrar = Censo.objects.filter(
        is_deleted=False,
        estatus='activo',
        fecha_fin__range=[hoy, en_7_dias]
    ).order_by('fecha_fin')[:5]
    
    context = {
        'total_censos': total_censos,
        'por_estatus': por_estatus,
        'por_categoria': por_categoria,
        'activos': activos,
        'total_participaciones': total_participaciones,
        'ultimos_censos': ultimos_censos,
        'proximos_cerrar': proximos_cerrar,
    }
    
    return render(request, 'censos/dashboard_censos.html', context)
