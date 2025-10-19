"""
Servicios del sistema bancario - Equivalente a Stored Procedures
Implementa la lógica de negocio crítica con transacciones atómicas
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from .models import CuentaAhorro, Transaccion 
from .models_fondo_mutuo import FondoMutuo, MovimientoFondoMutuo
from core.models import BitacoraAuditoria


class TransaccionService:
    """
    Servicio para manejar transacciones del libro diario
    Equivalente a sp_post_transaccion
    """
    
    @staticmethod
    @transaction.atomic
    def post_transaccion(
        tipo_transaccion,
        monto,
        descripcion,
        usuario,
        cuenta_ahorro=None,
        prestamo=None,
        fondo_mutuo=None,
        numero_recibo=None
    ):
        """
        Registra una transacción en el libro diario y actualiza saldos
        
        Args:
            tipo_transaccion: DEPOSITO, RETIRO, INTERES, PAGO_PRESTAMO, etc.
            monto: Monto de la transacción
            descripcion: Descripción detallada
            usuario: Usuario que realiza la transacción
            cuenta_ahorro: Cuenta de ahorro relacionada (opcional)
            prestamo: Préstamo relacionado (opcional)
            fondo_mutuo: Fondo mutuo relacionado (opcional)
            numero_recibo: Número de recibo (opcional)
        
        Returns:
            Transaccion: La transacción creada
        """
        
        # Validar que se especifique al menos un origen
        if not any([cuenta_ahorro, prestamo, fondo_mutuo]):
            raise ValidationError(
                'Debe especificar al menos: cuenta_ahorro, prestamo o fondo_mutuo'
            )
        
        # Validar XOR para cuenta_ahorro y prestamo
        if cuenta_ahorro and prestamo:
            raise ValidationError(
                'No puede especificar cuenta_ahorro Y prestamo simultáneamente'
            )
        
        # Validar monto positivo
        monto = Decimal(str(monto))
        if monto <= 0:
            raise ValidationError('El monto debe ser mayor a cero')
        
        # Obtener saldos anteriores según el tipo
        saldo_anterior = None
        saldo_nuevo = None
        
        if cuenta_ahorro:
            saldo_anterior = cuenta_ahorro.saldo_actual
            
            # Validar retiros
            if tipo_transaccion == 'RETIRO':
                if not cuenta_ahorro.tipo_cuenta.es_retirable:
                    raise ValidationError(
                        'Esta cuenta no permite retiros'
                    )
                if saldo_anterior < monto:
                    raise ValidationError(
                        f'Saldo insuficiente. Disponible: L. {saldo_anterior}'
                    )
                saldo_nuevo = saldo_anterior - monto
            elif tipo_transaccion == 'DEPOSITO':
                saldo_nuevo = saldo_anterior + monto
            
            # Actualizar saldo de la cuenta
            if saldo_nuevo is not None:
                cuenta_ahorro.saldo_actual = saldo_nuevo
                cuenta_ahorro.save(update_fields=['saldo_actual', 'actualizado_en'])
        
        # Crear la transacción
        transaccion = Transaccion.objects.create(
            cuenta_ahorro=cuenta_ahorro,
            prestamo=prestamo,
            tipo_transaccion=tipo_transaccion,
            monto=monto,
            saldo_anterior=saldo_anterior,
            saldo_nuevo=saldo_nuevo,
            descripcion=descripcion,
            numero_recibo=numero_recibo,
            realizado_por=usuario
        )
        
        # Registrar en bitácora
        BitacoraAuditoria.objects.create(
            usuario=usuario,
            accion='CREAR',
            tabla_afectada='TRANSACCION',
            id_registro=str(transaccion.id),
            descripcion=f"Transacción {tipo_transaccion} por L. {monto}",
            datos_nuevos={
                'tipo': tipo_transaccion,
                'monto': str(monto),
                'numero_recibo': numero_recibo
            }
        )
        
        return transaccion
    
    @staticmethod
    @transaction.atomic
    def reversar_transaccion(transaccion_id, motivo, usuario):
        """
        Reversa una transacción y restaura saldos
        Equivalente a sp_reverso_transaccion
        
        Args:
            transaccion_id: ID de la transacción a reversar
            motivo: Motivo del reverso
            usuario: Usuario que realiza el reverso
        
        Returns:
            Transaccion: La transacción de reverso creada
        """
        
        # Obtener transacción original
        try:
            transaccion_original = Transaccion.objects.select_for_update().get(
                id=transaccion_id
            )
        except Transaccion.DoesNotExist:
            raise ValidationError('Transacción no encontrada')
        
        # Validar que no esté ya reversada
        if transaccion_original.estado and transaccion_original.estado.codigo == 'REVERSADA':
            raise ValidationError('Esta transacción ya fue reversada')
        
        # Validar que no sea muy antigua (ejemplo: máximo 30 días)
        dias_transcurridos = (timezone.now() - transaccion_original.fecha_transaccion).days
        if dias_transcurridos > 30:
            raise ValidationError(
                'No se pueden reversar transacciones con más de 30 días de antigüedad'
            )
        
        # Crear transacción de reverso
        if transaccion_original.cuenta_ahorro:
            cuenta = transaccion_original.cuenta_ahorro
            saldo_anterior = cuenta.saldo_actual
            
            # Revertir el saldo
            if transaccion_original.tipo_transaccion == 'DEPOSITO':
                # Si fue depósito, ahora restamos
                saldo_nuevo = saldo_anterior - transaccion_original.monto
                tipo_reverso = 'RETIRO'
            elif transaccion_original.tipo_transaccion == 'RETIRO':
                # Si fue retiro, ahora sumamos
                saldo_nuevo = saldo_anterior + transaccion_original.monto
                tipo_reverso = 'DEPOSITO'
            else:
                raise ValidationError(
                    f'No se puede reversar transacción de tipo {transaccion_original.tipo_transaccion}'
                )
            
            # Validar que el saldo no quede negativo
            if saldo_nuevo < 0:
                raise ValidationError(
                    'No se puede reversar: el saldo quedaría negativo'
                )
            
            # Actualizar saldo
            cuenta.saldo_actual = saldo_nuevo
            cuenta.save(update_fields=['saldo_actual', 'actualizado_en'])
            
            # Crear transacción de reverso
            transaccion_reverso = Transaccion.objects.create(
                cuenta_ahorro=cuenta,
                tipo_transaccion='REVERSO',
                monto=transaccion_original.monto,
                saldo_anterior=saldo_anterior,
                saldo_nuevo=saldo_nuevo,
                descripcion=f"REVERSO de transacción {transaccion_original.id}. Motivo: {motivo}",
                transaccion_reversada=transaccion_original,
                realizado_por=usuario
            )
            
            # Marcar transacción original como reversada
            from core.models import CatEstado
            try:
                estado_reversada = CatEstado.objects.get(
                    dominio='TRANSACCION', 
                    codigo='REVERSADA'
                )
                transaccion_original.estado = estado_reversada
                transaccion_original.save(update_fields=['estado'])
            except CatEstado.DoesNotExist:
                pass
            
            # Registrar en bitácora
            BitacoraAuditoria.objects.create(
                usuario=usuario,
                accion='REVERSAR',
                tabla_afectada='TRANSACCION',
                id_registro=str(transaccion_original.id),
                descripcion=f"Reverso de transacción. Motivo: {motivo}",
                datos_anteriores={
                    'monto': str(transaccion_original.monto),
                    'tipo': transaccion_original.tipo_transaccion
                }
            )
            
            return transaccion_reverso
        
        else:
            raise ValidationError('Solo se pueden reversar transacciones de cuentas de ahorro')


class CuentaAhorroService:
    """
    Servicio para operaciones de cuentas de ahorro
    """
    
    @staticmethod
    @transaction.atomic
    def apertura_cuenta(socio, tipo_cuenta, usuario, monto_inicial=None):
        """
        Abre una nueva cuenta de ahorro
        Equivalente a sp_apertura_ahorro
        
        Args:
            socio: Socio titular de la cuenta
            tipo_cuenta: Tipo de cuenta a abrir
            usuario: Usuario que realiza la apertura
            monto_inicial: Depósito inicial (opcional)
        
        Returns:
            CuentaAhorro: La cuenta creada
        """
        
        # Validar que el socio esté activo
        if not socio.esta_activo:
            raise ValidationError('El socio debe estar ACTIVO para abrir una cuenta')
        
        # Validar monto mínimo si se especifica
        if monto_inicial and monto_inicial < tipo_cuenta.monto_minimo:
            raise ValidationError(
                f'El monto mínimo de apertura es L. {tipo_cuenta.monto_minimo}'
            )
        
        # Obtener estado ACTIVO
        from core.models import CatEstado
        try:
            estado_activo = CatEstado.objects.get(
                dominio='CUENTA_AHORRO',
                codigo='ACTIVO'
            )
        except CatEstado.DoesNotExist:
            raise ValidationError('No existe el estado ACTIVO para cuentas')
        
        # Generar número de cuenta
        numero_cuenta = CuentaAhorro.generar_numero_cuenta()
        
        # Crear la cuenta
        cuenta = CuentaAhorro.objects.create(
            socio=socio,
            tipo_cuenta=tipo_cuenta,
            numero_cuenta=numero_cuenta,
            saldo_actual=monto_inicial or Decimal('0.00'),
            fecha_apertura=timezone.now().date(),
            estado=estado_activo,
            creado_por=usuario
        )
        
        # Si hay depósito inicial, registrar transacción
        if monto_inicial and monto_inicial > 0:
            Transaccion.objects.create(
                cuenta_ahorro=cuenta,
                tipo_transaccion='DEPOSITO',
                monto=monto_inicial,
                saldo_anterior=Decimal('0.00'),
                saldo_nuevo=monto_inicial,
                descripcion=f"Depósito de apertura - Cuenta {numero_cuenta}",
                realizado_por=usuario
            )
        
        # Registrar en bitácora
        BitacoraAuditoria.objects.create(
            usuario=usuario,
            accion='CREAR',
            tabla_afectada='CUENTA_AHORRO',
            id_registro=str(cuenta.id),
            descripcion=f"Apertura de cuenta {numero_cuenta} para {socio.nombre_completo}",
            datos_nuevos={
                'numero_cuenta': numero_cuenta,
                'tipo_cuenta': tipo_cuenta.nombre,
                'monto_inicial': str(monto_inicial) if monto_inicial else '0.00'
            }
        )
        
        return cuenta
    
    @staticmethod
    @transaction.atomic
    def cierre_cuenta(cuenta_id, usuario, motivo=None):
        """
        Cierra una cuenta de ahorro
        Equivalente a sp_cierre_ahorro
        
        Args:
            cuenta_id: ID de la cuenta a cerrar
            usuario: Usuario que realiza el cierre
            motivo: Motivo del cierre
        
        Returns:
            CuentaAhorro: La cuenta cerrada
        """
        
        # Obtener cuenta con lock
        try:
            cuenta = CuentaAhorro.objects.select_for_update().get(id=cuenta_id)
        except CuentaAhorro.DoesNotExist:
            raise ValidationError('Cuenta no encontrada')
        
        # Validar que tenga saldo cero
        if cuenta.saldo_actual != Decimal('0.00'):
            raise ValidationError(
                f'La cuenta debe tener saldo cero para cerrar. Saldo actual: L. {cuenta.saldo_actual}'
            )
        
        # Validar que no esté ya cerrada
        if cuenta.fecha_cierre:
            raise ValidationError('La cuenta ya está cerrada')
        
        # Obtener estado CERRADA
        from core.models import CatEstado
        try:
            estado_cerrada = CatEstado.objects.get(
                dominio='CUENTA_AHORRO',
                codigo='CERRADA'
            )
            cuenta.estado = estado_cerrada
        except CatEstado.DoesNotExist:
            pass
        
        # Cerrar la cuenta
        cuenta.fecha_cierre = timezone.now().date()
        if motivo:
            cuenta.observaciones = (cuenta.observaciones or '') + f"\nCierre: {motivo}"
        cuenta.save()
        
        # Registrar en bitácora
        BitacoraAuditoria.objects.create(
            usuario=usuario,
            accion='EDITAR',
            tabla_afectada='CUENTA_AHORRO',
            id_registro=str(cuenta.id),
            descripcion=f"Cierre de cuenta {cuenta.numero_cuenta}. Motivo: {motivo or 'No especificado'}",
        )
        
        return cuenta


class FondoMutuoService:
    """
    Servicio para operaciones del Fondo Mutuo
    """
    
    @staticmethod
    @transaction.atomic
    def registrar_aporte(
        socio,
        monto,
        tipo_aporte,
        usuario,
        fondo=None,
        concepto=None,
        observaciones=None
    ):
        """
        Registra un aporte al fondo mutuo
        
        Args:
            socio: Socio que realiza el aporte
            monto: Monto del aporte
            tipo_aporte: MENSUAL, EXTRAORDINARIO, DONACION
            usuario: Usuario que registra el aporte
            fondo: Fondo específico (opcional, por defecto usa el período actual)
            concepto: Concepto del aporte (opcional)
            observaciones: Observaciones adicionales
        
        Returns:
            MovimientoFondoMutuo: El movimiento creado
        """
        
        # Validar que el socio esté activo
        if not socio.esta_activo:
            raise ValidationError('El socio debe estar ACTIVO para aportar')
        
        # Obtener o validar fondo
        if not fondo:
            fondo = FondoMutuo.get_periodo_actual()
            if not fondo:
                # Intentar crear el fondo del período actual
                fondo = FondoMutuo.crear_periodo_actual(usuario)
        
        # Validar que el fondo esté abierto
        if not fondo.esta_abierto():
            raise ValidationError(
                f'El fondo del período {fondo.periodo} está cerrado. No se aceptan aportes.'
            )
        
        # Validar monto positivo
        monto = Decimal(str(monto))
        if monto <= 0:
            raise ValidationError('El monto debe ser mayor a cero')
        
        # Validar monto mínimo si aplica
        from core.models import ParametroSistema
        try:
            param = ParametroSistema.objects.get(
                modulo='FONDO_MUTUO',
                nombre_parametro='MONTO_MINIMO_APORTE',
                activo=True
            )
            monto_minimo = param.get_valor()
            if monto < monto_minimo:
                raise ValidationError(
                    f'El monto mínimo de aporte es L. {monto_minimo}'
                )
        except ParametroSistema.DoesNotExist:
            pass
        
        # Calcular saldos
        saldo_anterior = fondo.saldo_disponible
        saldo_nuevo = saldo_anterior + monto
        
        # Generar concepto si no se especifica
        if not concepto:
            concepto = f"Aporte {tipo_aporte.lower()} de {socio.nombre_completo}"
        
        # Crear movimiento
        movimiento = MovimientoFondoMutuo.objects.create(
            fondo=fondo,
            socio=socio,
            origen='INGRESO',
            tipo_aporte=tipo_aporte,
            monto=monto,
            saldo_anterior=saldo_anterior,
            saldo_nuevo=saldo_nuevo,
            concepto=concepto,
            observaciones=observaciones,
            numero_movimiento=MovimientoFondoMutuo.generar_numero_movimiento(),
            realizado_por=usuario
        )
        
        # Actualizar totales del fondo
        fondo.actualizar_saldo()
        
        # Registrar en bitácora
        BitacoraAuditoria.objects.create(
            usuario=usuario,
            accion='CREAR',
            tabla_afectada='MOVIMIENTO_FONDO_MUTUO',
            id_registro=str(movimiento.id),
            descripcion=f"Aporte de L. {monto} al fondo período {fondo.periodo}",
            datos_nuevos={
                'socio': socio.nombre_completo,
                'monto': str(monto),
                'tipo_aporte': tipo_aporte,
                'numero_movimiento': movimiento.numero_movimiento
            }
        )
        
        return movimiento
    
    @staticmethod
    @transaction.atomic
    def cerrar_periodo(fondo_id, usuario, observaciones=None):
        """
        Cierra un período del fondo mutuo
        Equivalente a sp_cerrar_periodo_fondo_mutuo
        
        Args:
            fondo_id: ID del fondo a cerrar
            usuario: Usuario que cierra el período
            observaciones: Observaciones del cierre
        
        Returns:
            FondoMutuo: El fondo cerrado
        """
        
        # Obtener fondo con lock
        try:
            fondo = FondoMutuo.objects.select_for_update().get(id=fondo_id)
        except FondoMutuo.DoesNotExist:
            raise ValidationError('Fondo no encontrado')
        
        # Validar que esté abierto
        if not fondo.esta_abierto():
            raise ValidationError('El fondo ya está cerrado')
        
        # Validar que no haya solicitudes pendientes
        solicitudes_pendientes = fondo.solicitudes.filter(
            estado__in=['PENDIENTE', 'EN_REVISION']
        ).count()
        
        if solicitudes_pendientes > 0:
            raise ValidationError(
                f'No se puede cerrar el período. Hay {solicitudes_pendientes} '
                'solicitudes pendientes de resolver.'
            )
        
        # Obtener estado CERRADO
        from core.models import CatEstado
        try:
            estado_cerrado = CatEstado.objects.get(
                dominio='FONDO_MUTUO',
                codigo='CERRADO'
            )
            fondo.estado = estado_cerrado
        except CatEstado.DoesNotExist:
            raise ValidationError('No existe el estado CERRADO para fondos mutuos')
        
        # Actualizar saldos finales
        fondo.actualizar_saldo()
        
        # Registrar movimiento de cierre
        MovimientoFondoMutuo.objects.create(
            fondo=fondo,
            socio=None,
            origen='CIERRE',
            monto=fondo.saldo_disponible,
            saldo_anterior=fondo.saldo_disponible,
            saldo_nuevo=fondo.saldo_disponible,
            concepto=f"Cierre de período {fondo.periodo}",
            observaciones=observaciones,
            numero_movimiento=MovimientoFondoMutuo.generar_numero_movimiento(),
            realizado_por=usuario
        )
        
        # Cerrar el fondo
        fondo.fecha_cierre = timezone.now().date()
        fondo.cerrado_por = usuario
        if observaciones:
            fondo.observaciones = (fondo.observaciones or '') + f"\n{observaciones}"
        fondo.save()
        
        # Registrar en bitácora
        BitacoraAuditoria.objects.create(
            usuario=usuario,
            accion='EDITAR',
            tabla_afectada='FONDO_MUTUO',
            id_registro=str(fondo.id),
            descripcion=f"Cierre de período {fondo.periodo}. Saldo final: L. {fondo.saldo_disponible}",
            datos_nuevos={
                'total_ingresos': str(fondo.total_ingresos),
                'total_egresos': str(fondo.total_egresos),
                'saldo_disponible': str(fondo.saldo_disponible)
            }
        )
        
        return fondo


# Método auxiliar para generar número de cuenta
def generar_numero_cuenta_unico():
    """Genera un número de cuenta único"""
    import random
    while True:
        fecha = timezone.now().strftime('%Y%m%d')
        aleatorio = ''.join([str(random.randint(0, 9)) for _ in range(5)])
        numero = f"CA-{fecha}-{aleatorio}"
        
        if not CuentaAhorro.objects.filter(numero_cuenta=numero).exists():
            return numero

# Agregar método al modelo
CuentaAhorro.generar_numero_cuenta = staticmethod(generar_numero_cuenta_unico)