"""
Vistas para la gestión comunitaria del Consejo Comunal.
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
import json
from datetime import datetime, timedelta
import csv

from .models import (
    Familia, Habitante, IngresoComunal, EgresoComunal, 
    ConstanciaResidencia, ActaReunion, Person, User
)
from .forms import (
    FamiliaForm, HabitanteForm, IngresoComunalForm, 
    EgresoComunalForm, ConstanciaResidenciaForm, ActaReunionForm
)
from .decorators import admin_required, vocero_finanzas_required, vocero_secretaria_required

# ============================================
# Vistas para Familias
# ============================================

@login_required
def familias(request):
    """
    Vista para listar y buscar familias.
    """
    query = request.GET.get('q', '')
    campo = request.GET.get('campo', 'todos')
    
    familias_list = Familia.objects.filter(is_deleted=False)
    
    if query:
        if campo == 'todos' or campo == 'jefe_familia__name':
            familias_list = familias_list.filter(
                Q(jefe_familia__name__icontains=query) |
                Q(jefe_familia__surname__icontains=query)
            )
        elif campo == 'direccion':
            familias_list = familias_list.filter(direccion__icontains=query)
        elif campo == 'telefono_contacto':
            familias_list = familias_list.filter(telefono_contacto__icontains=query)
        elif campo == 'numero_vivienda':
            familias_list = familias_list.filter(numero_vivienda__icontains=query)
    
    # Ordenar por fecha de registro (más recientes primero)
    familias_list = familias_list.order_by('-fecha_registro')
    
    # Paginación
    paginator = Paginator(familias_list, 20)  # 20 familias por página
    page_number = request.GET.get('page')
    familias_page = paginator.get_page(page_number)
    
    context = {
        'familias': familias_page,
        'query': query,
        'campo': campo,
        'familia_form': FamiliaForm(),
    }
    
    return render(request, 'familias.html', context)


@login_required
@admin_required
def crear_familia(request):
    """
    Vista para crear una nueva familia.
    """
    if request.method == 'POST':
        form = FamiliaForm(request.POST)
        if form.is_valid():
            familia = form.save()
            messages.success(request, f'Familia {familia.jefe_familia.name} creada exitosamente.')
            return redirect('familias')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = FamiliaForm()
    
    context = {'form': form}
    return render(request, 'familias.html', context)


@login_required
@admin_required
def editar_familia(request, id):
    """
    Vista para editar una familia existente.
    """
    familia = get_object_or_404(Familia, id=id, is_deleted=False)
    
    if request.method == 'POST':
        form = FamiliaForm(request.POST, instance=familia)
        if form.is_valid():
            familia = form.save()
            messages.success(request, f'Familia {familia.jefe_familia.name} actualizada exitosamente.')
            return redirect('familias')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = FamiliaForm(instance=familia)
    
    context = {
        'form': form,
        'familia': familia,
        'person_to_edit': familia.jefe_familia,
    }
    return render(request, 'familias.html', context)


@login_required
@admin_required
@require_POST
def eliminar_familia(request, id):
    """
    Vista para eliminar (soft delete) una familia.
    """
    familia = get_object_or_404(Familia, id=id, is_deleted=False)
    
    # Verificar que no tenga habitantes antes de eliminar
    if familia.habitante_set.exists():
        messages.error(request, 'No se puede eliminar la familia porque tiene habitantes registrados.')
        return redirect('familias')
    
    familia.delete()  # Soft delete
    messages.success(request, f'Familia {familia.jefe_familia.name} eliminada exitosamente.')
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
# Vistas para Habitantes
# ============================================

@login_required
def habitantes(request):
    """
    Vista para listar y buscar habitantes.
    """
    query = request.GET.get('q', '')
    familia_id = request.GET.get('familia', '')
    
    habitantes_list = Habitante.objects.filter(is_deleted=False)
    
    if query:
        habitantes_list = habitantes_list.filter(
            Q(name__icontains=query) |
            Q(surname__icontains=query) |
            Q(document_number__icontains=query) |
            Q(telephone_number__icontains=query)
        )
    
    if familia_id and familia_id != 'todos':
        habitantes_list = habitantes_list.filter(familia_id=familia_id)
    
    # Obtener todas las familias para el filtro
    familias = Familia.objects.filter(is_deleted=False)
    
    # Paginación
    paginator = Paginator(habitantes_list, 25)  # 25 habitantes por página
    page_number = request.GET.get('page')
    habitantes_page = paginator.get_page(page_number)
    
    context = {
        'habitantes': habitantes_page,
        'familias': familias,
        'query': query,
        'familia_id': familia_id,
        'habitante_form': HabitanteForm(),
    }
    
    return render(request, 'habitantes.html', context)


@login_required
@admin_required
def crear_habitante(request):
    """
    Vista para crear un nuevo habitante.
    """
    if request.method == 'POST':
        form = HabitanteForm(request.POST)
        if form.is_valid():
            habitante = form.save()
            messages.success(request, f'Habitante {habitante.name} {habitante.surname} creado exitosamente.')
            return redirect('habitantes')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = HabitanteForm()
    
    context = {'form': form}
    return render(request, 'habitantes.html', context)


@login_required
@admin_required
def editar_habitante(request, id):
    """
    Vista para editar un habitante existente.
    """
    habitante = get_object_or_404(Habitante, id=id, is_deleted=False)
    
    if request.method == 'POST':
        form = HabitanteForm(request.POST, instance=habitante)
        if form.is_valid():
            habitante = form.save()
            messages.success(request, f'Habitante {habitante.name} {habitante.surname} actualizado exitosamente.')
            return redirect('habitantes')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = HabitanteForm(instance=habitante)
    
    context = {
        'form': form,
        'habitante': habitante,
    }
    return render(request, 'habitantes.html', context)


@login_required
@admin_required
@require_POST
def eliminar_habitante(request, id):
    """
    Vista para eliminar (soft delete) un habitante.
    """
    habitante = get_object_or_404(Habitante, id=id, is_deleted=False)
    
    # Si es jefe de familia, no permitir eliminación
    if habitante.parentesco_jefe == 'Jefe':
        messages.error(request, 'No se puede eliminar al jefe de familia. Elimine la familia completa.')
        return redirect('habitantes')
    
    habitante.delete()  # Soft delete
    messages.success(request, f'Habitante {habitante.name} {habitante.surname} eliminado exitosamente.')
    return redirect('habitantes')


@login_required
@require_GET
def api_habitante(request, id):
    """
    API para obtener datos de un habitante en formato JSON (para AJAX).
    """
    habitante = get_object_or_404(Habitante, id=id, is_deleted=False)
    
    data = {
        'id': habitante.id,
        'persona': habitante.persona.id,
        'type_document': habitante.persona.type_document,
        'document_number': habitante.persona.document_number,
        'name': habitante.persona.name,
        'surname': habitante.persona.surname,
        'telephone_number': habitante.persona.telephone_number or '',
        'email': habitante.persona.email or '',
        'date_of_birth': habitante.persona.date_of_birth.strftime('%Y-%m-%d') if habitante.persona.date_of_birth else '',
        'gender': habitante.persona.gender,
        'pais_origen': habitante.persona.pais_origen or '',
        'familia': habitante.familia.id,
        'parentesco_jefe': habitante.parentesco_jefe,
        'nivel_educativo': habitante.nivel_educativo or '',
        'ocupacion': habitante.ocupacion or '',
        'ingresos_mensuales': str(habitante.ingresos_mensuales) if habitante.ingresos_mensuales else '',
        'condiciones_salud': habitante.condiciones_salud or '',
    }
    
    return JsonResponse(data)


@login_required
def habitantes_familia(request, familia_id):
    """
    Vista para listar habitantes de una familia específica.
    """
    familia = get_object_or_404(Familia, id=familia_id, is_deleted=False)
    habitantes = Habitante.objects.filter(familia=familia, is_deleted=False)
    
    context = {
        'familia': familia,
        'habitantes': habitantes,
    }
    
    return render(request, 'habitantes_familia.html', context)


@login_required
def detalle_habitante(request, id):
    """
    Vista para ver el detalle completo de un habitante.
    """
    habitante = get_object_or_404(Habitante, id=id, is_deleted=False)
    
    context = {
        'habitante': habitante,
    }
    
    return render(request, 'detalle_habitante.html', context)


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