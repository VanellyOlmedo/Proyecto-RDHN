from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Q, Count
from django.db import transaction
from django.http import JsonResponse
from django.core.paginator import Paginator

from .models_fondo_mutuo import FondoMutuo, MovimientoFondoMutuo, SolicitudAyudaMutua
from .forms_fondo_mutuo import (
    FondoMutuoForm, AporteFondoMutuoForm, SolicitudAyudaForm,
    AprobarSolicitudForm, RechazarSolicitudForm, CerrarPeriodoForm,
    BusquedaMovimientosForm, BusquedaSolicitudesForm
)
from .services import FondoMutuoService


# ==========================================
# DASHBOARD DEL FONDO MUTUO
# ==========================================

@login_required
def fondo_mutuo_dashboard(request):
    """Dashboard principal del fondo mutuo"""
    
    # Obtener período actual
    periodo_actual = FondoMutuo.get_periodo_actual()
    
    # Estadísticas generales
    if periodo_actual:
        stats_periodo = {
            'total_ingresos': periodo_actual.total_ingresos,
            'total_egresos': periodo_actual.total_egresos,
            'saldo_disponible': periodo_actual.saldo_disponible,
            'total_aportes': periodo_actual.movimientos.filter(origen='INGRESO').count(),
            'total_ayudas': periodo_actual.movimientos.filter(origen='EGRESO').count(),
        }
        
        # Solicitudes pendientes
        solicitudes_pendientes = periodo_actual.solicitudes.filter(
            estado__in=['PENDIENTE', 'EN_REVISION']
        ).count()
    else:
        stats_periodo = None
        solicitudes_pendientes = 0
    
    # Últimos movimientos
    ultimos_movimientos = MovimientoFondoMutuo.objects.select_related(
        'fondo', 'socio', 'realizado_por'
    ).order_by('-fecha_movimiento')[:10]
    
    # Estadísticas históricas
    stats_historicas = FondoMutuo.objects.aggregate(
        total_acumulado=Sum('saldo_disponible'),
        total_fondos=Count('id')
    )
    
    context = {
        'periodo_actual': periodo_actual,
        'stats_periodo': stats_periodo,
        'solicitudes_pendientes': solicitudes_pendientes,
        'ultimos_movimientos': ultimos_movimientos,
        'stats_historicas': stats_historicas,
    }
    
    return render(request, 'banco/fondo_mutuo/dashboard.html', context)


# ==========================================
# CRUD FONDOS MUTUOS (PERÍODOS)
# ==========================================

@login_required
def fondos_listar(request):
    """Listar todos los períodos del fondo mutuo"""
    fondos = FondoMutuo.objects.select_related('estado', 'cerrado_por').order_by('-periodo')
    
    return render(request, 'banco/fondo_mutuo/fondos_listar.html', {
        'fondos': fondos
    })


@login_required
def fondos_crear(request):
    """Crear un nuevo período del fondo mutuo"""
    if request.method == 'POST':
        form = FondoMutuoForm(request.POST)
        if form.is_valid():
            fondo = form.save()
            messages.success(
                request,
                f'Fondo mutuo para el período {fondo.periodo} creado exitosamente'
            )
            return redirect('banco:fondos_detalle', pk=fondo.pk)
    else:
        form = FondoMutuoForm()
    
    return render(request, 'banco/fondo_mutuo/fondos_crear.html', {'form': form})


@login_required
def fondos_crear_actual(request):
    """Crear automáticamente el fondo para el período actual"""
    try:
        fondo = FondoMutuo.crear_periodo_actual(request.user)
        messages.success(
            request,
            f'Fondo mutuo para el período {fondo.periodo} creado exitosamente'
        )
        return redirect('banco:fondos_detalle', pk=fondo.pk)
    except Exception as e:
        messages.error(request, f'Error al crear el fondo: {str(e)}')
        return redirect('banco:fondos_listar')


@login_required
def fondos_detalle(request, pk):
    """Detalle de un período del fondo mutuo"""
    fondo = get_object_or_404(
        FondoMutuo.objects.select_related('estado', 'cerrado_por'),
        pk=pk
    )
    
    # Movimientos del período
    movimientos = fondo.movimientos.select_related(
        'socio', 'realizado_por'
    ).order_by('-fecha_movimiento')[:50]
    
    # Solicitudes del período
    solicitudes = fondo.solicitudes.select_related(
        'socio', 'revisado_por'
    ).order_by('-fecha_solicitud')
    
    # Estadísticas
    stats = {
        'total_aportantes': fondo.movimientos.filter(
            origen='INGRESO'
        ).values('socio').distinct().count(),
        'total_ayudas_otorgadas': fondo.movimientos.filter(
            origen='EGRESO'
        ).count(),
        'solicitudes_pendientes': solicitudes.filter(
            estado__in=['PENDIENTE', 'EN_REVISION']
        ).count(),
        'solicitudes_aprobadas': solicitudes.filter(estado='APROBADA').count(),
        'solicitudes_rechazadas': solicitudes.filter(estado='RECHAZADA').count(),
    }
    
    context = {
        'fondo': fondo,
        'movimientos': movimientos,
        'solicitudes': solicitudes,
        'stats': stats,
    }
    
    return render(request, 'banco/fondo_mutuo/fondos_detalle.html', context)


@login_required
def fondos_cerrar(request, pk):
    """Cerrar un período del fondo mutuo"""
    fondo = get_object_or_404(FondoMutuo, pk=pk)
    
    if not fondo.esta_abierto():
        messages.error(request, 'Este período ya está cerrado')
        return redirect('banco:fondos_detalle', pk=pk)
    
    if request.method == 'POST':
        form = CerrarPeriodoForm(request.POST)
        if form.is_valid():
            try:
                FondoMutuoService.cerrar_periodo(
                    fondo_id=fondo.id,
                    usuario=request.user,
                    observaciones=form.cleaned_data.get('observaciones')
                )
                messages.success(
                    request,
                    f'Período {fondo.periodo} cerrado exitosamente. '
                    f'Saldo final: L. {fondo.saldo_disponible}'
                )
                return redirect('banco:fondos_detalle', pk=pk)
            except Exception as e:
                messages.error(request, f'Error al cerrar el período: {str(e)}')
    else:
        form = CerrarPeriodoForm()
    
    return render(request, 'banco/fondo_mutuo/fondos_cerrar.html', {
        'form': form,
        'fondo': fondo
    })


# ==========================================
# APORTES AL FONDO MUTUO
# ==========================================

@login_required
def aportes_crear(request):
    """Registrar un nuevo aporte al fondo mutuo"""
    if request.method == 'POST':
        form = AporteFondoMutuoForm(request.POST)
        if form.is_valid():
            try:
                movimiento = FondoMutuoService.registrar_aporte(
                    socio=form.cleaned_data['socio'],
                    monto=form.cleaned_data['monto'],
                    tipo_aporte=form.cleaned_data['tipo_aporte'],
                    usuario=request.user,
                    concepto=form.cleaned_data.get('concepto'),
                    observaciones=form.cleaned_data.get('observaciones')
                )
                
                messages.success(
                    request,
                    f'Aporte de L. {movimiento.monto} registrado exitosamente. '
                    f'Comprobante: {movimiento.numero_movimiento}'
                )
                
                # Redirigir al comprobante
                return redirect('banco:movimientos_detalle', pk=movimiento.pk)
            except Exception as e:
                messages.error(request, f'Error al registrar el aporte: {str(e)}')
    else:
        form = AporteFondoMutuoForm()
    
    # Obtener período actual para mostrar info
    periodo_actual = FondoMutuo.get_periodo_actual()
    
    return render(request, 'banco/fondo_mutuo/aportes_crear.html', {
        'form': form,
        'periodo_actual': periodo_actual
    })


# ==========================================
# MOVIMIENTOS DEL FONDO
# ==========================================

@login_required
def movimientos_listar(request):
    """Listar todos los movimientos del fondo mutuo con filtros"""
    movimientos = MovimientoFondoMutuo.objects.select_related(
        'fondo', 'socio', 'realizado_por', 'solicitud_ayuda'
    ).order_by('-fecha_movimiento')
    
    # Aplicar filtros
    form = BusquedaMovimientosForm(request.GET)
    if form.is_valid():
        if form.cleaned_data.get('periodo'):
            movimientos = movimientos.filter(fondo__periodo=form.cleaned_data['periodo'])
        
        if form.cleaned_data.get('socio'):
            movimientos = movimientos.filter(socio=form.cleaned_data['socio'])
        
        if form.cleaned_data.get('origen'):
            movimientos = movimientos.filter(origen=form.cleaned_data['origen'])
        
        if form.cleaned_data.get('fecha_desde'):
            movimientos = movimientos.filter(
                fecha_movimiento__date__gte=form.cleaned_data['fecha_desde']
            )
        
        if form.cleaned_data.get('fecha_hasta'):
            movimientos = movimientos.filter(
                fecha_movimiento__date__lte=form.cleaned_data['fecha_hasta']
            )
    
    # Paginación
    paginator = Paginator(movimientos, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Totales de la página actual
    totales = movimientos.aggregate(
        total_ingresos=Sum('monto', filter=Q(origen='INGRESO')),
        total_egresos=Sum('monto', filter=Q(origen='EGRESO'))
    )
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'totales': totales,
    }
    
    return render(request, 'banco/fondo_mutuo/movimientos_listar.html', context)


@login_required
def movimientos_detalle(request, pk):
    """Detalle de un movimiento (comprobante)"""
    movimiento = get_object_or_404(
        MovimientoFondoMutuo.objects.select_related(
            'fondo', 'socio', 'realizado_por', 'solicitud_ayuda'
        ),
        pk=pk
    )
    
    return render(request, 'banco/fondo_mutuo/movimientos_detalle.html', {
        'movimiento': movimiento
    })


@login_required
def movimientos_imprimir(request, pk):
    """Generar comprobante imprimible de un movimiento"""
    movimiento = get_object_or_404(MovimientoFondoMutuo, pk=pk)
    
    return render(request, 'banco/fondo_mutuo/movimientos_imprimir.html', {
        'movimiento': movimiento
    }, content_type='text/html')


# ==========================================
# SOLICITUDES DE AYUDA MUTUA
# ==========================================

@login_required
def solicitudes_listar(request):
    """Listar todas las solicitudes de ayuda"""
    solicitudes = SolicitudAyudaMutua.objects.select_related(
        'socio', 'fondo', 'revisado_por', 'creado_por'
    ).order_by('-fecha_solicitud')
    
    # Aplicar filtros
    form = BusquedaSolicitudesForm(request.GET)
    if form.is_valid():
        if form.cleaned_data.get('estado'):
            solicitudes = solicitudes.filter(estado=form.cleaned_data['estado'])
        
        if form.cleaned_data.get('tipo_ayuda'):
            solicitudes = solicitudes.filter(tipo_ayuda=form.cleaned_data['tipo_ayuda'])
        
        if form.cleaned_data.get('socio'):
            solicitudes = solicitudes.filter(socio=form.cleaned_data['socio'])
        
        if form.cleaned_data.get('fecha_desde'):
            solicitudes = solicitudes.filter(
                fecha_solicitud__gte=form.cleaned_data['fecha_desde']
            )
        
        if form.cleaned_data.get('fecha_hasta'):
            solicitudes = solicitudes.filter(
                fecha_solicitud__lte=form.cleaned_data['fecha_hasta']
            )
    
    # Paginación
    paginator = Paginator(solicitudes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
    }
    
    return render(request, 'banco/fondo_mutuo/solicitudes_listar.html', context)


@login_required
def solicitudes_pendientes(request):
    """Dashboard de solicitudes pendientes de revisión (para supervisores)"""
    solicitudes_pendientes = SolicitudAyudaMutua.objects.select_related(
        'socio', 'fondo', 'creado_por'
    ).filter(
        estado__in=['PENDIENTE', 'EN_REVISION']
    ).order_by('fecha_solicitud')
    
    return render(request, 'banco/fondo_mutuo/solicitudes_pendientes.html', {
        'solicitudes': solicitudes_pendientes
    })


@login_required
def solicitudes_crear(request):
    """Crear una nueva solicitud de ayuda"""
    if request.method == 'POST':
        form = SolicitudAyudaForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Obtener período actual
                fondo = FondoMutuo.get_periodo_actual()
                if not fondo:
                    messages.error(
                        request,
                        'No existe un fondo abierto para el período actual'
                    )
                    return redirect('banco:fondos_listar')
                
                solicitud = form.save(commit=False)
                solicitud.fondo = fondo
                solicitud.creado_por = request.user
                solicitud.save()
                
                messages.success(
                    request,
                    f'Solicitud {solicitud.numero_solicitud} creada exitosamente. '
                    'Será revisada por un supervisor.'
                )
                return redirect('banco:solicitudes_detalle', pk=solicitud.pk)
            except Exception as e:
                messages.error(request, f'Error al crear la solicitud: {str(e)}')
    else:
        form = SolicitudAyudaForm()
    
    # Info del fondo actual
    periodo_actual = FondoMutuo.get_periodo_actual()
    
    return render(request, 'banco/fondo_mutuo/solicitudes_crear.html', {
        'form': form,
        'periodo_actual': periodo_actual
    })


@login_required
def solicitudes_detalle(request, pk):
    """Detalle de una solicitud de ayuda"""
    solicitud = get_object_or_404(
        SolicitudAyudaMutua.objects.select_related(
            'socio', 'fondo', 'revisado_por', 'creado_por'
        ),
        pk=pk
    )
    
    # Movimientos relacionados
    movimientos = solicitud.movimientos.all().order_by('-fecha_movimiento')
    
    context = {
        'solicitud': solicitud,
        'movimientos': movimientos,
    }
    
    return render(request, 'banco/fondo_mutuo/solicitudes_detalle.html', context)


@login_required
def solicitudes_aprobar(request, pk):
    """Aprobar una solicitud de ayuda"""
    solicitud = get_object_or_404(SolicitudAyudaMutua, pk=pk)
    
    if solicitud.estado not in ['PENDIENTE', 'EN_REVISION']:
        messages.error(request, 'Esta solicitud no puede ser aprobada en su estado actual')
        return redirect('banco:solicitudes_detalle', pk=pk)
    
    if request.method == 'POST':
        form = AprobarSolicitudForm(request.POST, solicitud=solicitud)
        if form.is_valid():
            try:
                movimiento = solicitud.aprobar(
                    monto_aprobado=form.cleaned_data['monto_aprobado'],
                    usuario=request.user,
                    comentarios=form.cleaned_data.get('comentarios')
                )
                
                messages.success(
                    request,
                    f'Solicitud aprobada por L. {form.cleaned_data["monto_aprobado"]}. '
                    f'Comprobante: {movimiento.numero_movimiento}'
                )
                
                # TODO: Enviar notificación al socio
                
                return redirect('banco:solicitudes_detalle', pk=pk)
            except Exception as e:
                messages.error(request, f'Error al aprobar la solicitud: {str(e)}')
    else:
        form = AprobarSolicitudForm(solicitud=solicitud)
    
    return render(request, 'banco/fondo_mutuo/solicitudes_aprobar.html', {
        'form': form,
        'solicitud': solicitud
    })


@login_required
def solicitudes_rechazar(request, pk):
    """Rechazar una solicitud de ayuda"""
    solicitud = get_object_or_404(SolicitudAyudaMutua, pk=pk)
    
    if solicitud.estado not in ['PENDIENTE', 'EN_REVISION']:
        messages.error(request, 'Esta solicitud no puede ser rechazada en su estado actual')
        return redirect('banco:solicitudes_detalle', pk=pk)
    
    if request.method == 'POST':
        form = RechazarSolicitudForm(request.POST)
        if form.is_valid():
            try:
                solicitud.rechazar(
                    motivo=form.cleaned_data['motivo_rechazo'],
                    usuario=request.user
                )
                
                messages.success(request, 'Solicitud rechazada')
                
                # TODO: Enviar notificación al socio
                
                return redirect('banco:solicitudes_detalle', pk=pk)
            except Exception as e:
                messages.error(request, f'Error al rechazar la solicitud: {str(e)}')
    else:
        form = RechazarSolicitudForm()
    
    return render(request, 'banco/fondo_mutuo/solicitudes_rechazar.html', {
        'form': form,
        'solicitud': solicitud
    })


# ==========================================
# REPORTES Y ESTADÍSTICAS
# ==========================================

@login_required
def reportes_kardex(request):
    """Reporte de kardex del fondo mutuo"""
    periodo = request.GET.get('periodo')
    
    if periodo:
        fondo = get_object_or_404(FondoMutuo, periodo=periodo)
        movimientos = fondo.movimientos.select_related(
            'socio', 'realizado_por'
        ).order_by('fecha_movimiento')
    else:
        fondo = FondoMutuo.get_periodo_actual()
        if fondo:
            movimientos = fondo.movimientos.select_related(
                'socio', 'realizado_por'
            ).order_by('fecha_movimiento')
        else:
            movimientos = MovimientoFondoMutuo.objects.none()
    
    # Totales
    totales = movimientos.aggregate(
        total_ingresos=Sum('monto', filter=Q(origen='INGRESO')),
        total_egresos=Sum('monto', filter=Q(origen='EGRESO'))
    )
    
    context = {
        'fondo': fondo,
        'movimientos': movimientos,
        'totales': totales,
        'periodos': FondoMutuo.objects.values_list('periodo', flat=True).order_by('-periodo')
    }
    
    return render(request, 'banco/fondo_mutuo/reportes_kardex.html', context)


# ==========================================
# API ENDPOINTS (AJAX)
# ==========================================

@login_required
def api_periodo_actual(request):
    """API para obtener información del período actual"""
    periodo = FondoMutuo.get_periodo_actual()
    
    if periodo:
        data = {
            'exists': True,
            'periodo': periodo.periodo,
            'estado': periodo.estado.nombre if periodo.estado else None,
            'saldo_disponible': str(periodo.saldo_disponible),
            'total_ingresos': str(periodo.total_ingresos),
            'total_egresos': str(periodo.total_egresos),
            'esta_abierto': periodo.esta_abierto()
        }
    else:
        data = {
            'exists': False,
            'message': 'No existe un fondo para el período actual'
        }
    
    return JsonResponse(data)


@login_required
def api_socio_info(request):
    """API para obtener información de un socio para validación"""
    socio_id = request.GET.get('socio_id')
    
    if not socio_id:
        return JsonResponse({'error': 'Socio no especificado'}, status=400)
    
    try:
        from core.models import Socio
        socio = Socio.objects.get(id=socio_id)
        
        data = {
            'nombre_completo': socio.nombre_completo,
            'numero_socio': socio.numero_socio,
            'esta_activo': socio.esta_activo,
            'meses_antiguedad': socio.meses_antiguedad,
            'cumple_antiguedad': socio.meses_antiguedad >= 6,
            'solicitudes_pendientes': SolicitudAyudaMutua.objects.filter(
                socio=socio,
                estado__in=['PENDIENTE', 'EN_REVISION', 'APROBADA']
            ).count()
        }
        
        return JsonResponse(data)
    except Socio.DoesNotExist:
        return JsonResponse({'error': 'Socio no encontrado'}, status=404)