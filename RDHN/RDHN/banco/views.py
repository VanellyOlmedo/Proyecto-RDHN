from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Q
from django.db import transaction
from decimal import Decimal

from .models import (
    TipoCuenta, TipoPrestamo, CuentaAhorro, Transaccion,
    Prestamo, Garante, CuotaPrestamo, PagoPrestamo,
    PeriodoDividendo, Dividendo, Notificacion
)
from .forms import (
    TipoCuentaForm, TipoPrestamoForm, CuentaAhorroForm, TransaccionForm,
    PrestamoForm, AprobarPrestamoForm, RechazarPrestamoForm, GaranteForm,
    PagoPrestamoForm, PeriodoDividendoForm, DividendoForm,
    NotificacionForm, DepositoRetiroForm
)
from core.models import Socio


# ==========================================
# CRUD TIPOS DE CUENTA
# ==========================================

@login_required
def tipos_cuenta_listar(request):
    """Listar tipos de cuenta"""
    tipos = TipoCuenta.objects.all().order_by('-activo', 'nombre')
    return render(request, 'banco/tipos_cuenta/listar.html', {'tipos': tipos})


@login_required
def tipos_cuenta_crear(request):
    """Crear tipo de cuenta"""
    if request.method == 'POST':
        form = TipoCuentaForm(request.POST)
        if form.is_valid():
            tipo = form.save()
            messages.success(request, f'Tipo de cuenta "{tipo.nombre}" creado correctamente')
            return redirect('banco:tipos_cuenta_listar')
    else:
        form = TipoCuentaForm()
    
    return render(request, 'banco/tipos_cuenta/crear.html', {'form': form})


@login_required
def tipos_cuenta_editar(request, pk):
    """Editar tipo de cuenta"""
    tipo = get_object_or_404(TipoCuenta, pk=pk)
    
    if request.method == 'POST':
        form = TipoCuentaForm(request.POST, instance=tipo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tipo de cuenta actualizado correctamente')
            return redirect('banco:tipos_cuenta_listar')
    else:
        form = TipoCuentaForm(instance=tipo)
    
    return render(request, 'banco/tipos_cuenta/editar.html', {'form': form, 'tipo': tipo})


@login_required
def tipos_cuenta_eliminar(request, pk):
    """Eliminar tipo de cuenta"""
    tipo = get_object_or_404(TipoCuenta, pk=pk)
    
    if request.method == 'POST':
        try:
            nombre = tipo.nombre
            tipo.delete()
            messages.success(request, f'Tipo de cuenta "{nombre}" eliminado correctamente')
        except Exception as e:
            messages.error(request, f'No se puede eliminar el tipo de cuenta: {str(e)}')
    
    return redirect('banco:tipos_cuenta_listar')


# ==========================================
# CRUD TIPOS DE PRÉSTAMO
# ==========================================

@login_required
def tipos_prestamo_listar(request):
    """Listar tipos de préstamo"""
    tipos = TipoPrestamo.objects.all().order_by('-activo', 'nombre')
    return render(request, 'banco/tipos_prestamo/listar.html', {'tipos': tipos})


@login_required
def tipos_prestamo_crear(request):
    """Crear tipo de préstamo"""
    if request.method == 'POST':
        form = TipoPrestamoForm(request.POST)
        if form.is_valid():
            tipo = form.save()
            messages.success(request, f'Tipo de préstamo "{tipo.nombre}" creado correctamente')
            return redirect('banco:tipos_prestamo_listar')
    else:
        form = TipoPrestamoForm()
    
    return render(request, 'banco/tipos_prestamo/crear.html', {'form': form})


@login_required
def tipos_prestamo_editar(request, pk):
    """Editar tipo de préstamo"""
    tipo = get_object_or_404(TipoPrestamo, pk=pk)
    
    if request.method == 'POST':
        form = TipoPrestamoForm(request.POST, instance=tipo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tipo de préstamo actualizado correctamente')
            return redirect('banco:tipos_prestamo_listar')
    else:
        form = TipoPrestamoForm(instance=tipo)
    
    return render(request, 'banco/tipos_prestamo/editar.html', {'form': form, 'tipo': tipo})


@login_required
def tipos_prestamo_eliminar(request, pk):
    """Eliminar tipo de préstamo"""
    tipo = get_object_or_404(TipoPrestamo, pk=pk)
    
    if request.method == 'POST':
        try:
            nombre = tipo.nombre
            tipo.delete()
            messages.success(request, f'Tipo de préstamo "{nombre}" eliminado correctamente')
        except Exception as e:
            messages.error(request, f'No se puede eliminar el tipo de préstamo: {str(e)}')
    
    return redirect('banco:tipos_prestamo_listar')


# ==========================================
# CRUD CUENTAS DE AHORRO
# ==========================================

@login_required
def cuentas_listar(request):
    """Listar cuentas de ahorro"""
    cuentas = CuentaAhorro.objects.all().select_related(
        'socio', 'tipo_cuenta', 'estado'
    ).order_by('-creado_en')
    
    # Filtros opcionales
    socio_id = request.GET.get('socio')
    tipo_id = request.GET.get('tipo')
    estado_id = request.GET.get('estado')
    
    if socio_id:
        cuentas = cuentas.filter(socio_id=socio_id)
    if tipo_id:
        cuentas = cuentas.filter(tipo_cuenta_id=tipo_id)
    if estado_id:
        cuentas = cuentas.filter(estado_id=estado_id)
    
    context = {
        'cuentas': cuentas,
        'socios': Socio.objects.all(),
        'tipos': TipoCuenta.objects.filter(activo=True),
    }
    return render(request, 'banco/cuentas/listar.html', context)


@login_required
def cuentas_crear(request):
    """Crear cuenta de ahorro"""
    if request.method == 'POST':
        form = CuentaAhorroForm(request.POST)
        if form.is_valid():
            cuenta = form.save()
            messages.success(
                request,
                f'Cuenta {cuenta.numero_cuenta} creada exitosamente para {cuenta.socio.nombre_completo}'
            )
            return redirect('banco:cuentas_listar')
    else:
        form = CuentaAhorroForm()
    
    return render(request, 'banco/cuentas/crear.html', {'form': form})


@login_required
def cuentas_detalle(request, pk):
    """Detalle de cuenta de ahorro"""
    cuenta = get_object_or_404(
        CuentaAhorro.objects.select_related('socio', 'tipo_cuenta', 'estado'),
        pk=pk
    )
    
    # Últimas transacciones
    transacciones = cuenta.transacciones.all().order_by('-fecha_transaccion')[:20]
    
    context = {
        'cuenta': cuenta,
        'transacciones': transacciones,
    }
    return render(request, 'banco/cuentas/detalle.html', context)


@login_required
def cuentas_editar(request, pk):
    """Editar cuenta de ahorro"""
    cuenta = get_object_or_404(CuentaAhorro, pk=pk)
    
    if request.method == 'POST':
        form = CuentaAhorroForm(request.POST, instance=cuenta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cuenta actualizada correctamente')
            return redirect('banco:cuentas_detalle', pk=cuenta.pk)
    else:
        form = CuentaAhorroForm(instance=cuenta)
    
    return render(request, 'banco/cuentas/editar.html', {'form': form, 'cuenta': cuenta})


@login_required
def cuentas_eliminar(request, pk):
    """Eliminar cuenta de ahorro"""
    cuenta = get_object_or_404(CuentaAhorro, pk=pk)
    
    if request.method == 'POST':
        try:
            if cuenta.saldo_actual > 0:
                messages.error(
                    request,
                    'No se puede eliminar una cuenta con saldo pendiente'
                )
            else:
                numero = cuenta.numero_cuenta
                cuenta.delete()
                messages.success(request, f'Cuenta {numero} eliminada correctamente')
                return redirect('banco:cuentas_listar')
        except Exception as e:
            messages.error(request, f'No se puede eliminar la cuenta: {str(e)}')
    
    return redirect('banco:cuentas_detalle', pk=pk)


@login_required
def cuentas_depositar(request, pk):
    """Realizar depósito en cuenta"""
    cuenta = get_object_or_404(CuentaAhorro, pk=pk)
    
    if request.method == 'POST':
        form = DepositoRetiroForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    monto = form.cleaned_data['monto']
                    descripcion = form.cleaned_data['descripcion']
                    
                    cuenta.depositar(
                        monto=monto,
                        descripcion=descripcion,
                        usuario=request.user
                    )
                    
                    messages.success(
                        request,
                        f'Depósito de L. {monto} realizado exitosamente. Nuevo saldo: L. {cuenta.saldo_actual}'
                    )
                    return redirect('banco:cuentas_detalle', pk=cuenta.pk)
            except Exception as e:
                messages.error(request, f'Error al realizar el depósito: {str(e)}')
    else:
        form = DepositoRetiroForm()
    
    return render(request, 'banco/cuentas/depositar.html', {
        'form': form,
        'cuenta': cuenta
    })


@login_required
def cuentas_retirar(request, pk):
    """Realizar retiro de cuenta"""
    cuenta = get_object_or_404(CuentaAhorro, pk=pk)
    
    if request.method == 'POST':
        form = DepositoRetiroForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    monto = form.cleaned_data['monto']
                    descripcion = form.cleaned_data['descripcion']
                    
                    cuenta.retirar(
                        monto=monto,
                        descripcion=descripcion,
                        usuario=request.user
                    )
                    
                    messages.success(
                        request,
                        f'Retiro de L. {monto} realizado exitosamente. Nuevo saldo: L. {cuenta.saldo_actual}'
                    )
                    return redirect('banco:cuentas_detalle', pk=cuenta.pk)
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Error al realizar el retiro: {str(e)}')
    else:
        form = DepositoRetiroForm()
    
    return render(request, 'banco/cuentas/retirar.html', {
        'form': form,
        'cuenta': cuenta
    })


# ==========================================
# CRUD TRANSACCIONES
# ==========================================

@login_required
def transacciones_listar(request):
    """Listar transacciones"""
    transacciones = Transaccion.objects.all().select_related(
        'cuenta_ahorro__socio', 'prestamo__socio', 'realizado_por'
    ).order_by('-fecha_transaccion')[:100]
    
    # Filtros
    tipo = request.GET.get('tipo')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    if tipo:
        transacciones = transacciones.filter(tipo_transaccion=tipo)
    if fecha_desde:
        transacciones = transacciones.filter(fecha_transaccion__date__gte=fecha_desde)
    if fecha_hasta:
        transacciones = transacciones.filter(fecha_transaccion__date__lte=fecha_hasta)
    
    return render(request, 'banco/transacciones/listar.html', {
        'transacciones': transacciones
    })


@login_required
def transacciones_detalle(request, pk):
    """Detalle de transacción"""
    transaccion = get_object_or_404(Transaccion, pk=pk)
    return render(request, 'banco/transacciones/detalle.html', {
        'transaccion': transaccion
    })


# ==========================================
# CRUD PRÉSTAMOS
# ==========================================

@login_required
def prestamos_listar(request):
    """Listar préstamos"""
    prestamos = Prestamo.objects.all().select_related(
        'socio', 'tipo_prestamo', 'aprobado_por'
    ).order_by('-fecha_solicitud')
    
    # Filtros
    estado = request.GET.get('estado')
    socio_id = request.GET.get('socio')
    
    if estado:
        prestamos = prestamos.filter(estado=estado)
    if socio_id:
        prestamos = prestamos.filter(socio_id=socio_id)
    
    context = {
        'prestamos': prestamos,
        'socios': Socio.objects.all(),
    }
    return render(request, 'banco/prestamos/listar.html', context)


@login_required
def prestamos_crear(request):
    """Crear solicitud de préstamo"""
    if request.method == 'POST':
        form = PrestamoForm(request.POST, request.FILES)
        if form.is_valid():
            prestamo = form.save(commit=False)
            prestamo.tasa_interes = prestamo.tipo_prestamo.tasa_interes_anual
            prestamo.save()
            
            messages.success(
                request,
                f'Préstamo {prestamo.numero_prestamo} solicitado exitosamente'
            )
            return redirect('banco:prestamos_detalle', pk=prestamo.pk)
    else:
        form = PrestamoForm()
    
    return render(request, 'banco/prestamos/crear.html', {'form': form})


@login_required
def prestamos_detalle(request, pk):
    """Detalle de préstamo"""
    prestamo = get_object_or_404(
        Prestamo.objects.select_related('socio', 'tipo_prestamo', 'aprobado_por'),
        pk=pk
    )
    
    cuotas = prestamo.cuotas.all().order_by('numero_cuota')
    garantes = prestamo.garantes.filter(activo=True).select_related('socio_garante')
    pagos = prestamo.pagos.all().order_by('-fecha_pago')[:10]
    
    context = {
        'prestamo': prestamo,
        'cuotas': cuotas,
        'garantes': garantes,
        'pagos': pagos,
    }
    return render(request, 'banco/prestamos/detalle.html', context)


@login_required
def prestamos_editar(request, pk):
    """Editar préstamo"""
    prestamo = get_object_or_404(Prestamo, pk=pk)
    
    # Solo se pueden editar préstamos en estado SOLICITADO
    if prestamo.estado not in ['SOLICITADO', 'EN_REVISION']:
        messages.error(request, 'Solo se pueden editar préstamos en estado Solicitado o En Revisión')
        return redirect('banco:prestamos_detalle', pk=pk)
    
    if request.method == 'POST':
        form = PrestamoForm(request.POST, request.FILES, instance=prestamo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Préstamo actualizado correctamente')
            return redirect('banco:prestamos_detalle', pk=prestamo.pk)
    else:
        form = PrestamoForm(instance=prestamo)
    
    return render(request, 'banco/prestamos/editar.html', {
        'form': form,
        'prestamo': prestamo
    })


@login_required
def prestamos_aprobar(request, pk):
    """Aprobar préstamo"""
    prestamo = get_object_or_404(Prestamo, pk=pk)
    
    if prestamo.estado not in ['SOLICITADO', 'EN_REVISION']:
        messages.error(request, 'Este préstamo no puede ser aprobado en su estado actual')
        return redirect('banco:prestamos_detalle', pk=pk)
    
    if request.method == 'POST':
        form = AprobarPrestamoForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    prestamo.monto_aprobado = form.cleaned_data['monto_aprobado']
                    prestamo.fecha_primer_pago = form.cleaned_data['fecha_primer_pago']
                    prestamo.fecha_aprobacion = timezone.now().date()
                    prestamo.estado = 'APROBADO'
                    prestamo.aprobado_por = request.user
                    
                    if form.cleaned_data.get('observaciones'):
                        prestamo.observaciones = (
                            prestamo.observaciones or ''
                        ) + f"\n\nAprobación: {form.cleaned_data['observaciones']}"
                    
                    # Calcular cuota y generar tabla de amortización
                    prestamo.calcular_cuota()
                    prestamo.save()
                    
                    prestamo.generar_tabla_amortizacion()
                    
                    messages.success(
                        request,
                        f'Préstamo aprobado por L. {prestamo.monto_aprobado}. '
                        f'Cuota mensual: L. {prestamo.cuota_mensual}'
                    )
                    return redirect('banco:prestamos_detalle', pk=prestamo.pk)
            except Exception as e:
                messages.error(request, f'Error al aprobar el préstamo: {str(e)}')
    else:
        form = AprobarPrestamoForm(initial={
            'monto_aprobado': prestamo.monto_solicitado,
            'fecha_primer_pago': timezone.now().date()
        })
    
    return render(request, 'banco/prestamos/aprobar.html', {
        'form': form,
        'prestamo': prestamo
    })


@login_required
def prestamos_rechazar(request, pk):
    """Rechazar préstamo"""
    prestamo = get_object_or_404(Prestamo, pk=pk)
    
    if prestamo.estado not in ['SOLICITADO', 'EN_REVISION']:
        messages.error(request, 'Este préstamo no puede ser rechazado en su estado actual')
        return redirect('banco:prestamos_detalle', pk=pk)
    
    if request.method == 'POST':
        form = RechazarPrestamoForm(request.POST)
        if form.is_valid():
            prestamo.estado = 'RECHAZADO'
            prestamo.observaciones = (
                prestamo.observaciones or ''
            ) + f"\n\nRechazo: {form.cleaned_data['motivo_rechazo']}"
            prestamo.save()
            
            messages.success(request, 'Préstamo rechazado')
            return redirect('banco:prestamos_detalle', pk=prestamo.pk)
    else:
        form = RechazarPrestamoForm()
    
    return render(request, 'banco/prestamos/rechazar.html', {
        'form': form,
        'prestamo': prestamo
    })


@login_required
def prestamos_desembolsar(request, pk):
    """Desembolsar préstamo aprobado"""
    prestamo = get_object_or_404(Prestamo, pk=pk)

    if prestamo.estado != 'APROBADO':
        messages.error(request, 'Solo se pueden desembolsar préstamos aprobados')
        return redirect('banco:prestamos_detalle', pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                prestamo.fecha_desembolso = timezone.now().date()
                prestamo.estado = 'DESEMBOLSADO'
                prestamo.save()
                
                # Registrar transacción de desembolso
                Transaccion.objects.create(
                    prestamo=prestamo,
                    tipo_transaccion='DESEMBOLSO_PRESTAMO',
                    monto=prestamo.monto_aprobado,
                    descripcion=f'Desembolso del préstamo {prestamo.numero_prestamo}',
                    realizado_por=request.user
                )
                
                messages.success(
                    request,
                    f'Préstamo desembolsado por L. {prestamo.monto_aprobado}'
                )
                return redirect('banco:prestamos_detalle', pk=prestamo.pk)
        except Exception as e:
            messages.error(request, f'Error al desembolsar el préstamo: {str(e)}')
    
    return render(request, 'banco/prestamos/desembolsar.html', {
        'prestamo': prestamo
    })


@login_required
def prestamos_eliminar(request, pk):
    """Eliminar préstamo"""
    prestamo = get_object_or_404(Prestamo, pk=pk)
    
    # Solo se pueden eliminar préstamos no desembolsados
    if prestamo.estado not in ['SOLICITADO', 'EN_REVISION', 'RECHAZADO']:
        messages.error(
            request,
            'No se pueden eliminar préstamos aprobados o desembolsados'
        )
        return redirect('banco:prestamos_detalle', pk=pk)
    
    if request.method == 'POST':
        try:
            numero = prestamo.numero_prestamo
            prestamo.delete()
            messages.success(request, f'Préstamo {numero} eliminado correctamente')
            return redirect('banco:prestamos_listar')
        except Exception as e:
            messages.error(request, f'No se puede eliminar el préstamo: {str(e)}')
    
    return redirect('banco:prestamos_detalle', pk=pk)


# ==========================================
# GARANTES
# ==========================================

@login_required
def garantes_agregar(request, prestamo_pk):
    """Agregar garante a un préstamo"""
    prestamo = get_object_or_404(Prestamo, pk=prestamo_pk)
    
    # Verificar que el préstamo requiera garantes
    if not prestamo.tipo_prestamo.requiere_garantes:
        messages.error(request, 'Este tipo de préstamo no requiere garantes')
        return redirect('banco:prestamos_detalle', pk=prestamo.pk)
    
    # Verificar cantidad de garantes
    garantes_actuales = prestamo.garantes.filter(activo=True).count()
    if garantes_actuales >= prestamo.tipo_prestamo.cantidad_garantes:
        messages.error(
            request,
            f'Ya se alcanzó el máximo de {prestamo.tipo_prestamo.cantidad_garantes} garantes'
        )
        return redirect('banco:prestamos_detalle', pk=prestamo.pk)
    
    if request.method == 'POST':
        form = GaranteForm(request.POST, request.FILES, prestamo=prestamo)
        if form.is_valid():
            garante = form.save(commit=False)
            garante.prestamo = prestamo
            garante.save()
            
            messages.success(
                request,
                f'Garante {garante.socio_garante.nombre_completo} agregado correctamente'
            )
            return redirect('banco:prestamos_detalle', pk=prestamo.pk)
    else:
        form = GaranteForm(prestamo=prestamo)
    
    return render(request, 'banco/garantes/agregar.html', {
        'form': form,
        'prestamo': prestamo
    })


@login_required
def garantes_eliminar(request, prestamo_pk, pk):
    """Eliminar garante de un préstamo"""
    garante = get_object_or_404(Garante, pk=pk, prestamo_id=prestamo_pk)
    
    if request.method == 'POST':
        garante.activo = False
        garante.save()
        messages.success(request, 'Garante removido correctamente')
    
    return redirect('banco:prestamos_detalle', pk=prestamo_pk)


# ==========================================
# PAGOS DE PRÉSTAMOS
# ==========================================

@login_required
def pagos_crear(request, prestamo_pk):
    """Registrar pago de préstamo"""
    prestamo = get_object_or_404(Prestamo, pk=prestamo_pk)
    
    if prestamo.estado not in ['DESEMBOLSADO', 'EN_PAGO']:
        messages.error(request, 'Este préstamo no acepta pagos en su estado actual')
        return redirect('banco:prestamos_detalle', pk=prestamo.pk)
    
    if request.method == 'POST':
        form = PagoPrestamoForm(request.POST, prestamo=prestamo)
        if form.is_valid():
            try:
                with transaction.atomic():
                    pago = form.save(commit=False)
                    pago.prestamo = prestamo
                    pago.realizado_por = request.user
                    
                    # Si se especificó una cuota, distribuir el pago
                    if pago.cuota:
                        cuota = pago.cuota
                        
                        # Calcular mora si aplica
                        if cuota.estado == 'VENCIDA':
                            cuota.calcular_mora()
                        
                        total_cuota = (
                            cuota.monto_cuota + cuota.monto_mora
                        )
                        
                        if pago.monto_pagado >= total_cuota:
                            # Pago completo
                            pago.monto_capital = cuota.monto_capital
                            pago.monto_interes = cuota.monto_interes
                            pago.monto_mora = cuota.monto_mora
                            
                            cuota.fecha_pago = pago.fecha_pago
                            cuota.estado = (
                                'PAGADA' if cuota.dias_mora == 0 else 'PAGADA_TARDE'
                            )
                            cuota.save()
                        else:
                            # Pago parcial
                            pago.monto_mora = min(pago.monto_pagado, cuota.monto_mora)
                            restante = pago.monto_pagado - pago.monto_mora
                            
                            proporcion_interes = (
                                cuota.monto_interes / cuota.monto_cuota
                            )
                            pago.monto_interes = restante * proporcion_interes
                            pago.monto_capital = restante - pago.monto_interes
                    
                    pago.save()
                    
                    # Actualizar saldo del préstamo
                    prestamo.saldo_pendiente -= pago.monto_pagado
                    if prestamo.saldo_pendiente <= 0:
                        prestamo.estado = 'PAGADO'
                    elif prestamo.estado == 'DESEMBOLSADO':
                        prestamo.estado = 'EN_PAGO'
                    prestamo.save()
                    
                    # Registrar transacción
                    Transaccion.objects.create(
                        prestamo=prestamo,
                        tipo_transaccion='PAGO_PRESTAMO',
                        monto=pago.monto_pagado,
                        descripcion=f'Pago de préstamo - Recibo {pago.numero_recibo}',
                        numero_recibo=pago.numero_recibo,
                        realizado_por=request.user
                    )
                    
                    messages.success(
                        request,
                        f'Pago de L. {pago.monto_pagado} registrado correctamente'
                    )
                    return redirect('banco:prestamos_detalle', pk=prestamo.pk)
            except Exception as e:
                messages.error(request, f'Error al registrar el pago: {str(e)}')
    else:
        form = PagoPrestamoForm(prestamo=prestamo)
    
    return render(request, 'banco/pagos/crear.html', {
        'form': form,
        'prestamo': prestamo
    })


@login_required
def pagos_detalle(request, pk):
    """Detalle de un pago"""
    pago = get_object_or_404(
        PagoPrestamo.objects.select_related('prestamo', 'cuota', 'realizado_por'),
        pk=pk
    )
    return render(request, 'banco/pagos/detalle.html', {'pago': pago})


# ==========================================
# DIVIDENDOS
# ==========================================

@login_required
def periodos_listar(request):
    """Listar períodos de dividendos"""
    periodos = PeriodoDividendo.objects.all().order_by('-año')
    return render(request, 'banco/dividendos/periodos_listar.html', {
        'periodos': periodos
    })


@login_required
def periodos_crear(request):
    """Crear período de dividendos"""
    if request.method == 'POST':
        form = PeriodoDividendoForm(request.POST)
        if form.is_valid():
            periodo = form.save()
            messages.success(request, f'Período {periodo.año} creado correctamente')
            return redirect('banco:periodos_listar')
    else:
        form = PeriodoDividendoForm()
    
    return render(request, 'banco/dividendos/periodos_crear.html', {'form': form})


@login_required
def dividendos_listar(request, periodo_pk):
    """Listar dividendos de un período"""
    periodo = get_object_or_404(PeriodoDividendo, pk=periodo_pk)
    dividendos = periodo.dividendos.all().select_related('socio').order_by(
        '-monto_dividendo'
    )
    
    return render(request, 'banco/dividendos/listar.html', {
        'periodo': periodo,
        'dividendos': dividendos
    })


# ==========================================
# NOTIFICACIONES
# ==========================================

@login_required
def notificaciones_listar(request):
    """Listar notificaciones"""
    notificaciones = Notificacion.objects.all().select_related(
        'socio'
    ).order_by('-creado_en')[:100]
    
    # Filtros
    tipo = request.GET.get('tipo')
    enviado = request.GET.get('enviado')
    
    if tipo:
        notificaciones = notificaciones.filter(tipo=tipo)
    if enviado:
        notificaciones = notificaciones.filter(
            enviado=(enviado == 'true')
        )
    
    return render(request, 'banco/notificaciones/listar.html', {
        'notificaciones': notificaciones
    })


@login_required
def notificaciones_crear(request):
    """Crear notificación"""
    if request.method == 'POST':
        form = NotificacionForm(request.POST)
        if form.is_valid():
            notificacion = form.save()
            messages.success(request, 'Notificación creada correctamente')
            return redirect('banco:notificaciones_listar')
    else:
        form = NotificacionForm()
    
    return render(request, 'banco/notificaciones/crear.html', {'form': form})


@login_required
def notificaciones_detalle(request, pk):
    """Detalle de notificación"""
    notificacion = get_object_or_404(Notificacion, pk=pk)
    return render(request, 'banco/notificaciones/detalle.html', {
        'notificacion': notificacion
    })

