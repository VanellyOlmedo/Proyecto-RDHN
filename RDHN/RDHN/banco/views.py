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

