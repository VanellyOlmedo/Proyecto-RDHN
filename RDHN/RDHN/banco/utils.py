from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import random
import string


def generar_numero_unico(prefijo, modelo, campo='numero_prestamo'):
    """
    Genera un número único para cualquier modelo
    
    Args:
        prefijo: Prefijo del número (CTA, PRE, REC, etc.)
        modelo: Modelo de Django
        campo: Campo donde se almacena el número
    
    Returns:
        str: Número único generado
    """
    año = timezone.now().year
    
    while True:
        numero = random.randint(10000, 99999)
        numero_completo = f"{prefijo}-{año}-{numero}"
        
        # Verificar que no exista
        filtro = {campo: numero_completo}
        if not modelo.objects.filter(**filtro).exists():
            return numero_completo


def enviar_email_notificacion(destinatario, asunto, mensaje, html_mensaje=None):
    """
    Envía un email de notificación
    
    Args:
        destinatario: Email del destinatario
        asunto: Asunto del email
        mensaje: Mensaje en texto plano
        html_mensaje: Mensaje en HTML (opcional)
    
    Returns:
        bool: True si se envió correctamente, False en caso contrario
    """
    try:
        send_mail(
            subject=asunto,
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatario],
            html_message=html_mensaje,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error al enviar email: {str(e)}")
        return False


def calcular_cuota_francesa(capital, tasa_anual, plazo_meses):
    """
    Calcula la cuota mensual usando el sistema francés
    
    Args:
        capital: Monto del préstamo
        tasa_anual: Tasa de interés anual (porcentaje)
        plazo_meses: Plazo en meses
    
    Returns:
        Decimal: Cuota mensual
    """
    P = float(capital)
    r = float(tasa_anual) / 100 / 12  # Tasa mensual
    n = plazo_meses
    
    if r > 0:
        cuota = P * (r * (1 + r)**n) / ((1 + r)**n - 1)
    else:
        cuota = P / n
    
    return Decimal(str(round(cuota, 2)))


def generar_tabla_amortizacion(capital, tasa_anual, plazo_meses, fecha_inicio):
    """
    Genera tabla de amortización completa
    
    Args:
        capital: Monto del préstamo
        tasa_anual: Tasa de interés anual (porcentaje)
        plazo_meses: Plazo en meses
        fecha_inicio: Fecha del primer pago
    
    Returns:
        list: Lista de diccionarios con la tabla de amortización
    """
    cuota_mensual = calcular_cuota_francesa(capital, tasa_anual, plazo_meses)
    
    tabla = []
    saldo = float(capital)
    tasa_mensual = float(tasa_anual) / 100 / 12
    fecha_pago = fecha_inicio
    
    for i in range(1, plazo_meses + 1):
        interes = saldo * tasa_mensual
        capital_pago = float(cuota_mensual) - interes
        saldo -= capital_pago
        
        tabla.append({
            'numero_cuota': i,
            'cuota': round(float(cuota_mensual), 2),
            'capital': round(capital_pago, 2),
            'interes': round(interes, 2),
            'saldo': round(max(saldo, 0), 2),
            'fecha_vencimiento': fecha_pago
        })
        
        # Siguiente mes
        if fecha_pago.month == 12:
            fecha_pago = fecha_pago.replace(year=fecha_pago.year + 1, month=1)
        else:
            fecha_pago = fecha_pago.replace(month=fecha_pago.month + 1)
    
    return tabla


def calcular_mora(monto_cuota, dias_mora, tasa_mora_diaria=Decimal('0.10')):
    """
    Calcula la mora por días de atraso
    
    Args:
        monto_cuota: Monto de la cuota
        dias_mora: Días de atraso
        tasa_mora_diaria: Tasa de mora diaria en porcentaje (default 0.10%)
    
    Returns:
        Decimal: Monto de mora
    """
    mora = monto_cuota * (tasa_mora_diaria / 100) * dias_mora
    return round(mora, 2)


def formatear_moneda(monto):
    """
    Formatea un monto como moneda
    
    Args:
        monto: Monto a formatear
    
    Returns:
        str: Monto formateado (ej: "L. 1,234.56")
    """
    return f"L. {monto:,.2f}"


def validar_capacidad_pago(socio, cuota_nueva):
    """
    Valida si el socio tiene capacidad de pago para una nueva cuota
    
    Args:
        socio: Instancia del socio
        cuota_nueva: Monto de la nueva cuota
    
    Returns:
        dict: {'puede_pagar': bool, 'total_cuotas': Decimal, 'razon': str}
    """
    from .models import Prestamo
    
    # Sumar cuotas actuales
    prestamos_activos = Prestamo.objects.filter(
        socio=socio,
        estado__in=['DESEMBOLSADO', 'EN_PAGO']
    )
    
    total_cuotas_actuales = sum(p.cuota_mensual for p in prestamos_activos if p.cuota_mensual)
    total_con_nueva = total_cuotas_actuales + Decimal(str(cuota_nueva))
    
    # Obtener ahorro mensual del socio
    from .models import CuentaAhorro
    
    ahorro_mensual = CuentaAhorro.objects.filter(
        socio=socio,
        tipo_cuenta__requiere_deduccion_planilla=True,
        fecha_cierre__isnull=True
    ).aggregate(total=models.Sum('monto_deduccion_planilla'))['total'] or Decimal('0.00')
    
    # Regla: Las cuotas totales no deben superar el 40% del ahorro mensual multiplicado por 10
    # (asumiendo que el ahorro es ~10% del salario)
    capacidad_estimada = ahorro_mensual * 10 * Decimal('0.40')
    
    puede_pagar = total_con_nueva <= capacidad_estimada
    
    return {
        'puede_pagar': puede_pagar,
        'total_cuotas': total_con_nueva,
        'capacidad_estimada': capacidad_estimada,
        'razon': 'Capacidad suficiente' if puede_pagar else f'Cuotas totales (L. {total_con_nueva}) exceden capacidad estimada (L. {capacidad_estimada})'
    }


def obtener_tasa_mora_default():
    """Obtiene la tasa de mora por defecto desde settings o retorna 0.10%"""
    return getattr(settings, 'TASA_MORA_DIARIA', Decimal('0.10'))


def generar_reporte_pdf(template_name, context, filename):
    """
    Genera un reporte en PDF (requiere weasyprint o reportlab)
    
    Args:
        template_name: Nombre del template HTML
        context: Contexto para el template
        filename: Nombre del archivo a generar
    
    Returns:
        HttpResponse: Respuesta HTTP con el PDF
    """
    from django.template.loader import render_to_string
    from django.http import HttpResponse
    
    # Aquí integrarías weasyprint o reportlab
    # Por ahora, retornar HTML
    
    html = render_to_string(template_name, context)
    response = HttpResponse(html, content_type='text/html')
    response['Content-Disposition'] = f'attachment; filename="{filename}.html"'
    
    return response


def validar_monto_prestamo(socio, monto_solicitado, tipo_prestamo):
    """
    Valida si el socio puede solicitar el monto del préstamo
    
    Args:
        socio: Instancia del socio
        monto_solicitado: Monto solicitado
        tipo_prestamo: Tipo de préstamo
    
    Returns:
        dict: {'valido': bool, 'monto_maximo': Decimal, 'requiere_garantes': bool, 'mensaje': str}
    """
    from .models import CuentaAhorro
    
    # Buscar cuenta fija
    cuenta_fija = CuentaAhorro.objects.filter(
        socio=socio,
        tipo_cuenta__codigo='FIJO',
        fecha_cierre__isnull=True
    ).first()
    
    if not cuenta_fija:
        return {
            'valido': False,
            'monto_maximo': Decimal('0.00'),
            'requiere_garantes': False,
            'mensaje': 'El socio no tiene cuenta de ahorro fijo'
        }
    
    # Calcular monto máximo sin garantes
    monto_max_sin_garantes = cuenta_fija.saldo_actual * tipo_prestamo.multiplicador_ahorro
    
    if monto_solicitado <= monto_max_sin_garantes:
        return {
            'valido': True,
            'monto_maximo': monto_max_sin_garantes,
            'requiere_garantes': False,
            'mensaje': 'Monto aprobado sin garantes'
        }
    
    # Verificar si el tipo permite garantes
    if not tipo_prestamo.requiere_garantes:
        return {
            'valido': False,
            'monto_maximo': monto_max_sin_garantes,
            'requiere_garantes': False,
            'mensaje': f'Monto máximo sin garantes: L. {monto_max_sin_garantes}'
        }
    
    # Requiere garantes
    return {
        'valido': True,
        'monto_maximo': monto_solicitado,
        'requiere_garantes': True,
        'cantidad_garantes': tipo_prestamo.cantidad_garantes,
        'mensaje': f'Requiere {tipo_prestamo.cantidad_garantes} garantes'
    }


# Constantes útiles
MESES_NOMBRE = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

TRIMESTRES = {
    1: {'inicio': 1, 'fin': 3, 'nombre': 'Primer Trimestre'},
    2: {'inicio': 4, 'fin': 6, 'nombre': 'Segundo Trimestre'},
    3: {'inicio': 7, 'fin': 9, 'nombre': 'Tercer Trimestre'},
    4: {'inicio': 10, 'fin': 12, 'nombre': 'Cuarto Trimestre'}
}