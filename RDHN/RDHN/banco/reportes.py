from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import (
    CuentaAhorro, Transaccion, Prestamo, PagoPrestamo,
    CuotaPrestamo, PeriodoDividendo
)


class ReportesBanco:
    """Clase para generar reportes del banco"""
    
    @staticmethod
    def balance_general(fecha_inicio=None, fecha_fin=None):
        """Genera el balance general del banco"""
        if not fecha_fin:
            fecha_fin = timezone.now().date()
        if not fecha_inicio:
            fecha_inicio = timezone.now().date().replace(day=1)
        
        # ACTIVOS
        # Total en cuentas de ahorro
        total_ahorros = CuentaAhorro.objects.filter(
            fecha_cierre__isnull=True
        ).aggregate(total=Sum('saldo_actual'))['total'] or Decimal('0.00')
        
        # Préstamos por cobrar (capital pendiente)
        prestamos_cobrar = Prestamo.objects.filter(
            estado__in=['DESEMBOLSADO', 'EN_PAGO']
        ).aggregate(total=Sum('saldo_pendiente'))['total'] or Decimal('0.00')
        
        # PASIVOS
        # Ahorros de socios (obligación)
        pasivo_ahorros = total_ahorros
        
        # PATRIMONIO
        # Intereses generados (capital del banco)
        intereses_generados = PagoPrestamo.objects.filter(
            fecha_pago__range=[fecha_inicio, fecha_fin]
        ).aggregate(total=Sum('monto_interes'))['total'] or Decimal('0.00')
        
        # Mora generada
        mora_generada = PagoPrestamo.objects.filter(
            fecha_pago__range=[fecha_inicio, fecha_fin]
        ).aggregate(total=Sum('monto_mora'))['total'] or Decimal('0.00')
        
        total_activos = total_ahorros + prestamos_cobrar
        total_pasivos = pasivo_ahorros
        patrimonio = intereses_generados + mora_generada
        
        return {
            'activos': {
                'ahorros_caja': total_ahorros,
                'prestamos_cobrar': prestamos_cobrar,
                'total': total_activos
            },
            'pasivos': {
                'obligaciones_socios': pasivo_ahorros,
                'total': total_pasivos
            },
            'patrimonio': {
                'intereses': intereses_generados,
                'mora': mora_generada,
                'total': patrimonio
            },
            'verificacion': total_activos == (total_pasivos + patrimonio)
        }
    
    @staticmethod
    def estado_resultados(fecha_inicio, fecha_fin):
        """Genera estado de resultados (ingresos y gastos)"""
        
        # INGRESOS
        ingresos_intereses = PagoPrestamo.objects.filter(
            fecha_pago__range=[fecha_inicio, fecha_fin]
        ).aggregate(total=Sum('monto_interes'))['total'] or Decimal('0.00')
        
        ingresos_mora = PagoPrestamo.objects.filter(
            fecha_pago__range=[fecha_inicio, fecha_fin]
        ).aggregate(total=Sum('monto_mora'))['total'] or Decimal('0.00')
        
        total_ingresos = ingresos_intereses + ingresos_mora
        
        # GASTOS (si hubiera gastos operativos)
        # Por ahora asumimos que no hay gastos significativos
        total_gastos = Decimal('0.00')
        
        utilidad_neta = total_ingresos - total_gastos
        
        return {
            'ingresos': {
                'intereses': ingresos_intereses,
                'mora': ingresos_mora,
                'total': total_ingresos
            },
            'gastos': {
                'operativos': total_gastos,
                'total': total_gastos
            },
            'utilidad_neta': utilidad_neta
        }
    
    @staticmethod
    def reporte_cartera_prestamos():
        """Reporte de cartera de préstamos"""
        
        # Préstamos por estado
        prestamos_estado = Prestamo.objects.values('estado').annotate(
            cantidad=Count('id'),
            monto_total=Sum('monto_aprobado'),
            saldo_pendiente=Sum('saldo_pendiente')
        )
        
        # Cuotas vencidas
        cuotas_vencidas = CuotaPrestamo.objects.filter(
            estado='VENCIDA'
        ).aggregate(
            cantidad=Count('id'),
            monto_total=Sum('monto_cuota'),
            mora_total=Sum('monto_mora')
        )
        
        # Préstamos por tipo
        prestamos_tipo = Prestamo.objects.values(
            'tipo_prestamo__nombre'
        ).annotate(
            cantidad=Count('id'),
            monto_total=Sum('monto_aprobado')
        )
        
        # Índice de morosidad
        total_cartera = Prestamo.objects.filter(
            estado__in=['DESEMBOLSADO', 'EN_PAGO']
        ).aggregate(total=Sum('saldo_pendiente'))['total'] or Decimal('0.00')
        
        cartera_vencida = CuotaPrestamo.objects.filter(
            estado='VENCIDA'
        ).aggregate(total=Sum('saldo_pendiente'))['total'] or Decimal('0.00')
        
        indice_morosidad = (cartera_vencida / total_cartera * 100) if total_cartera > 0 else 0
        
        return {
            'por_estado': list(prestamos_estado),
            'por_tipo': list(prestamos_tipo),
            'cuotas_vencidas': cuotas_vencidas,
            'cartera_total': total_cartera,
            'cartera_vencida': cartera_vencida,
            'indice_morosidad': round(indice_morosidad, 2)
        }
    
    @staticmethod
    def reporte_ahorros():
        """Reporte de cuentas de ahorro"""
        
        # Ahorros por tipo
        ahorros_tipo = CuentaAhorro.objects.filter(
            fecha_cierre__isnull=True
        ).values('tipo_cuenta__nombre').annotate(
            cantidad=Count('id'),
            saldo_total=Sum('saldo_actual')
        )
        
        # Ahorro promedio
        ahorro_promedio = CuentaAhorro.objects.filter(
            fecha_cierre__isnull=True
        ).aggregate(promedio=Avg('saldo_actual'))['promedio'] or Decimal('0.00')
        
        # Total ahorros
        total_ahorros = CuentaAhorro.objects.filter(
            fecha_cierre__isnull=True
        ).aggregate(total=Sum('saldo_actual'))['total'] or Decimal('0.00')
        
        # Cuentas activas
        cuentas_activas = CuentaAhorro.objects.filter(
            fecha_cierre__isnull=True
        ).count()
        
        return {
            'por_tipo': list(ahorros_tipo),
            'total_ahorros': total_ahorros,
            'ahorro_promedio': ahorro_promedio,
            'cuentas_activas': cuentas_activas
        }
    
    @staticmethod
    def reporte_mensual(año, mes):
        """Reporte mensual completo"""
        fecha_inicio = datetime(año, mes, 1).date()
        if mes == 12:
            fecha_fin = datetime(año + 1, 1, 1).date() - timedelta(days=1)
        else:
            fecha_fin = datetime(año, mes + 1, 1).date() - timedelta(days=1)
        
        # Transacciones del mes
        transacciones = Transaccion.objects.filter(
            fecha_transaccion__range=[fecha_inicio, fecha_fin]
        ).values('tipo_transaccion').annotate(
            cantidad=Count('id'),
            monto_total=Sum('monto')
        )
        
        # Préstamos desembolsados
        prestamos_mes = Prestamo.objects.filter(
            fecha_desembolso__range=[fecha_inicio, fecha_fin]
        ).aggregate(
            cantidad=Count('id'),
            monto_total=Sum('monto_aprobado')
        )
        
        # Pagos recibidos
        pagos_mes = PagoPrestamo.objects.filter(
            fecha_pago__range=[fecha_inicio, fecha_fin]
        ).aggregate(
            cantidad=Count('id'),
            monto_total=Sum('monto_pagado'),
            capital_recuperado=Sum('monto_capital'),
            intereses_cobrados=Sum('monto_interes'),
            mora_cobrada=Sum('monto_mora')
        )
        
        return {
            'periodo': {
                'año': año,
                'mes': mes,
                'inicio': fecha_inicio,
                'fin': fecha_fin
            },
            'transacciones': list(transacciones),
            'prestamos': prestamos_mes,
            'pagos': pagos_mes,
            'balance': ReportesBanco.balance_general(fecha_inicio, fecha_fin),
            'resultados': ReportesBanco.estado_resultados(fecha_inicio, fecha_fin)
        }
    
    @staticmethod
    def reporte_trimestral(año, trimestre):
        """Reporte trimestral"""
        meses_inicio = {1: 1, 2: 4, 3: 7, 4: 10}
        mes_inicio = meses_inicio[trimestre]
        
        fecha_inicio = datetime(año, mes_inicio, 1).date()
        
        if trimestre == 4:
            fecha_fin = datetime(año, 12, 31).date()
        else:
            fecha_fin = datetime(año, mes_inicio + 3, 1).date() - timedelta(days=1)
        
        return {
            'periodo': {
                'año': año,
                'trimestre': trimestre,
                'inicio': fecha_inicio,
                'fin': fecha_fin
            },
            'balance': ReportesBanco.balance_general(fecha_inicio, fecha_fin),
            'resultados': ReportesBanco.estado_resultados(fecha_inicio, fecha_fin),
            'cartera': ReportesBanco.reporte_cartera_prestamos(),
            'ahorros': ReportesBanco.reporte_ahorros()
        }
    
    @staticmethod
    def reporte_anual(año):
        """Reporte anual completo"""
        fecha_inicio = datetime(año, 1, 1).date()
        fecha_fin = datetime(año, 12, 31).date()
        
        # Resumen de dividendos si existe
        try:
            periodo_dividendo = PeriodoDividendo.objects.get(año=año)
            dividendos_info = {
                'total_generado': periodo_dividendo.total_intereses_generados,
                'total_distribuido': periodo_dividendo.total_distribuido,
                'estado': periodo_dividendo.estado,
                'fecha_distribucion': periodo_dividendo.fecha_distribucion
            }
        except PeriodoDividendo.DoesNotExist:
            dividendos_info = None
        
        # Crecimiento de socios
        cuentas_nuevas = CuentaAhorro.objects.filter(
            fecha_apertura__year=año
        ).count()
        
        cuentas_cerradas = CuentaAhorro.objects.filter(
            fecha_cierre__year=año
        ).count()
        
        return {
            'periodo': {
                'año': año,
                'inicio': fecha_inicio,
                'fin': fecha_fin
            },
            'balance': ReportesBanco.balance_general(fecha_inicio, fecha_fin),
            'resultados': ReportesBanco.estado_resultados(fecha_inicio, fecha_fin),
            'cartera': ReportesBanco.reporte_cartera_prestamos(),
            'ahorros': ReportesBanco.reporte_ahorros(),
            'dividendos': dividendos_info,
            'crecimiento': {
                'cuentas_nuevas': cuentas_nuevas,
                'cuentas_cerradas': cuentas_cerradas,
                'crecimiento_neto': cuentas_nuevas - cuentas_cerradas
            }
        }
    
    @staticmethod
    def reporte_socio(socio):
        """Reporte individual de un socio"""
        
        # Cuentas del socio
        cuentas = CuentaAhorro.objects.filter(
            socio=socio,
            fecha_cierre__isnull=True
        ).values('tipo_cuenta__nombre', 'numero_cuenta', 'saldo_actual')
        
        total_ahorros = sum(c['saldo_actual'] for c in cuentas)
        
        # Préstamos del socio
        prestamos = Prestamo.objects.filter(socio=socio).values(
            'numero_prestamo', 'estado', 'monto_aprobado',
            'saldo_pendiente', 'cuota_mensual'
        )
        
        # Historial de pagos
        pagos_realizados = PagoPrestamo.objects.filter(
            prestamo__socio=socio
        ).aggregate(
            total_pagado=Sum('monto_pagado'),
            cantidad_pagos=Count('id')
        )
        
        # Dividendos recibidos
        dividendos = PeriodoDividendo.objects.filter(
            dividendos__socio=socio,
            estado='DISTRIBUIDO'
        ).values(
            'año',
            dividendos__monto_dividendo=Sum('dividendos__monto_dividendo')
        )
        
        return {
            'socio': {
                'numero': socio.numero_socio,
                'nombre': socio.nombre_completo,
                'identidad': socio.identidad
            },
            'cuentas': list(cuentas),
            'total_ahorros': total_ahorros,
            'prestamos': list(prestamos),
            'historial_pagos': pagos_realizados,
            'dividendos': list(dividendos)
        }