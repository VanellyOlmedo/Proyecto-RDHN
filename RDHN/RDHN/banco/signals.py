"""
Signals para el módulo bancario
Implementan actualizaciones automáticas y auditoría
"""

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import (
    
    CuentaAhorro, Transaccion
)
from .models_fondo_mutuo import FondoMutuo, MovimientoFondoMutuo, SolicitudAyudaMutua
from core.models import BitacoraAuditoria


# =========================
# SIGNALS DEL FONDO MUTUO
# =========================

@receiver(post_save, sender=MovimientoFondoMutuo)
def actualizar_totales_fondo(sender, instance, created, **kwargs):
    """
    Actualiza los totales del fondo cuando se crea un movimiento
    Equivalente a un trigger AFTER INSERT
    """
    if created:
        # Actualizar saldo del fondo
        instance.fondo.actualizar_saldo()


@receiver(post_save, sender=SolicitudAyudaMutua)
def notificar_cambio_estado_solicitud(sender, instance, created, **kwargs):
    """
    Envía notificación cuando cambia el estado de una solicitud
    """
    if not created:
        # Si la solicitud fue aprobada o rechazada, notificar al socio
        if instance.estado in ['APROBADA', 'RECHAZADA']:
            # TODO: Implementar envío de notificación
            # Por ahora solo registramos en auditoría
            pass


# =========================
# SIGNALS DE AUDITORÍA
# =========================

@receiver(post_save, sender=Transaccion)
def auditar_transaccion(sender, instance, created, **kwargs):
    """
    Registra en bitácora las transacciones importantes
    """
    if created and instance.tipo_transaccion in ['DEPOSITO', 'RETIRO', 'REVERSO']:
        BitacoraAuditoria.objects.create(
            usuario=instance.realizado_por,
            accion='CREAR',
            tabla_afectada='TRANSACCION',
            id_registro=str(instance.id),
            descripcion=f"Transacción {instance.tipo_transaccion} por L. {instance.monto}",
            datos_nuevos={
                'tipo': instance.tipo_transaccion,
                'monto': str(instance.monto),
                'cuenta': instance.cuenta_ahorro.numero_cuenta if instance.cuenta_ahorro else None
            }
        )


@receiver(post_save, sender=CuentaAhorro)
def auditar_cuenta_ahorro(sender, instance, created, **kwargs):
    """
    Registra apertura y cambios importantes de cuentas
    """
    if created:
        BitacoraAuditoria.objects.create(
            usuario=instance.creado_por,
            accion='CREAR',
            tabla_afectada='CUENTA_AHORRO',
            id_registro=str(instance.id),
            descripcion=f"Apertura de cuenta {instance.numero_cuenta}",
            datos_nuevos={
                'numero_cuenta': instance.numero_cuenta,
                'tipo': instance.tipo_cuenta.nombre,
                'socio': instance.socio.nombre_completo
            }
        )


# =========================
# VALIDACIONES PRE-SAVE
# =========================

@receiver(pre_save, sender=CuentaAhorro)
def validar_saldo_no_negativo(sender, instance, **kwargs):
    """
    Valida que el saldo nunca sea negativo antes de guardar
    """
    if instance.saldo_actual < 0:
        raise ValueError('El saldo de la cuenta no puede ser negativo')


@receiver(pre_save, sender=FondoMutuo)
def validar_saldo_fondo_no_negativo(sender, instance, **kwargs):
    """
    Valida que el saldo del fondo nunca sea negativo
    """
    if instance.saldo_disponible < 0:
        raise ValueError('El saldo del fondo no puede ser negativo')


# =========================
# SIGNALS DE NOTIFICACIÓN
# =========================

@receiver(post_save, sender=SolicitudAyudaMutua)
def notificar_nueva_solicitud(sender, instance, created, **kwargs):
    """
    Notifica a los supervisores cuando se crea una nueva solicitud
    """
    if created:
        # TODO: Implementar notificación a supervisores
        # Puede ser por email o notificación interna
        pass


@receiver(post_save, sender=MovimientoFondoMutuo)
def notificar_aporte_registrado(sender, instance, created, **kwargs):
    """
    Notifica al socio cuando se registra su aporte
    """
    if created and instance.origen == 'INGRESO':
        # TODO: Implementar notificación al socio
        # Enviar comprobante de aporte
        pass