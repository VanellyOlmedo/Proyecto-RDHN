from django.core.management.base import BaseCommand
from django.db.models import Sum, Q
from decimal import Decimal
from banco.models import CuentaAhorro, Transaccion


class Command(BaseCommand):
    help = 'Concilia los saldos de las cuentas con las transacciones (Job Diario)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Iniciando conciliación de saldos ==='))
        
        cuentas = CuentaAhorro.objects.all()
        errores = []
        
        for cuenta in cuentas:
            # Calcular saldo según transacciones
            transacciones = cuenta.transacciones.aggregate(
                depositos=Sum('monto', filter=Q(tipo_transaccion='DEPOSITO')),
                retiros=Sum('monto', filter=Q(tipo_transaccion='RETIRO'))
            )
            
            depositos = transacciones['depositos'] or Decimal('0.00')
            retiros = transacciones['retiros'] or Decimal('0.00')
            saldo_calculado = depositos - retiros
            
            # Comparar con saldo actual
            diferencia = cuenta.saldo_actual - saldo_calculado
            
            if diferencia != 0:
                errores.append({
                    'cuenta': cuenta.numero_cuenta,
                    'socio': cuenta.socio.nombre_completo,
                    'saldo_actual': cuenta.saldo_actual,
                    'saldo_calculado': saldo_calculado,
                    'diferencia': diferencia
                })
                
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ Diferencia en cuenta {cuenta.numero_cuenta}: '
                        f'L. {diferencia}'
                    )
                )
        
        if not errores:
            self.stdout.write(
                self.style.SUCCESS('✅ Todos los saldos están correctos')
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Se encontraron {len(errores)} cuentas con diferencias'
                )
            )
            
            # TODO: Enviar reporte por email a administradores
            
        self.stdout.write(self.style.SUCCESS('=== Conciliación completada ==='))


# ========================================================
# banco/management/commands/detectar_cuotas_vencidas.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from banco.models import CuotaPrestamo, Notificacion


class Command(BaseCommand):
    help = 'Detecta cuotas vencidas y genera alertas (Job Diario)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Detectando cuotas vencidas ==='))
        
        hoy = timezone.now().date()
        
        # Buscar cuotas pendientes vencidas
        cuotas_vencidas = CuotaPrestamo.objects.filter(
            estado='PENDIENTE',
            fecha_vencimiento__lt=hoy
        ).select_related('prestamo__socio')
        
        cuotas_actualizadas = 0
        notificaciones_creadas = 0
        
        for cuota in cuotas_vencidas:
            # Calcular mora
            cuota.calcular_mora()
            cuotas_actualizadas += 1
            
            # Crear notificación para el socio
            Notificacion.objects.get_or_create(
                socio=cuota.prestamo.socio,
                tipo='CUOTA_VENCIDA',
                defaults={
                    'asunto': f'Cuota {cuota.numero_cuota} vencida',
                    'mensaje': (
                        f'Su cuota #{cuota.numero_cuota} del préstamo '
                        f'{cuota.prestamo.numero_prestamo} está vencida. '
                        f'Monto: L. {cuota.monto_cuota + cuota.monto_mora} '
                        f'(incluye mora de L. {cuota.monto_mora})'
                    )
                }
            )
            notificaciones_creadas += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ {cuotas_actualizadas} cuotas marcadas como vencidas'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ {notificaciones_creadas} notificaciones creadas'
            )
        )


# ========================================================
# banco/management/commands/alertar_cuotas_proximas.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from banco.models import CuotaPrestamo, Notificacion


class Command(BaseCommand):
    help = 'Alerta sobre cuotas próximas a vencer (Job Diario)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=5,
            help='Días de anticipación para alertar (default: 5)'
        )

    def handle(self, *args, **options):
        dias = options['dias']
        self.stdout.write(
            self.style.SUCCESS(
                f'=== Alertando cuotas que vencen en {dias} días ==='
            )
        )
        
        hoy = timezone.now().date()
        fecha_limite = hoy + timedelta(days=dias)
        
        # Buscar cuotas pendientes que vencen pronto
        cuotas_proximas = CuotaPrestamo.objects.filter(
            estado='PENDIENTE',
            fecha_vencimiento__gte=hoy,
            fecha_vencimiento__lte=fecha_limite
        ).select_related('prestamo__socio')
        
        notificaciones_creadas = 0
        
        for cuota in cuotas_proximas:
            dias_restantes = (cuota.fecha_vencimiento - hoy).days
            
            # Crear notificación
            _, created = Notificacion.objects.get_or_create(
                socio=cuota.prestamo.socio,
                tipo='CUOTA_PROXIMA',
                defaults={
                    'asunto': f'Cuota {cuota.numero_cuota} próxima a vencer',
                    'mensaje': (
                        f'Su cuota #{cuota.numero_cuota} del préstamo '
                        f'{cuota.prestamo.numero_prestamo} vence en {dias_restantes} días. '
                        f'Fecha de vencimiento: {cuota.fecha_vencimiento}. '
                        f'Monto: L. {cuota.monto_cuota}'
                    )
                }
            )
            
            if created:
                notificaciones_creadas += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ {notificaciones_creadas} notificaciones creadas'
            )
        )


# ========================================================
# banco/management/commands/procesar_notificaciones.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from banco.models import Notificacion
from core.models import ParametroSistema


class Command(BaseCommand):
    help = 'Procesa y envía notificaciones pendientes (Job cada 15 minutos)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Procesando notificaciones ==='))
        
        # Obtener notificaciones pendientes
        notificaciones = Notificacion.objects.filter(
            enviado=False,
            programada_para__lte=timezone.now()
        ).select_related('socio')[:100]  # Procesar máximo 100 por ejecución
        
        enviadas = 0
        fallidas = 0
        
        # Obtener parámetro de reintentos máximos
        try:
            param = ParametroSistema.objects.get(
                modulo='NOTIFICACIONES',
                nombre_parametro='MAX_REINTENTOS',
                activo=True
            )
            max_reintentos = param.get_valor()
        except ParametroSistema.DoesNotExist:
            max_reintentos = 3
        
        for notif in notificaciones:
            # Verificar si ya superó el máximo de intentos
            if notif.intentos >= max_reintentos:
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ Notificación {notif.id} superó máximo de intentos'
                    )
                )
                continue
            
            # Incrementar intentos
            notif.intentos += 1
            
            try:
                # TODO: Implementar envío real según canal
                # Por ahora solo simulamos
                exito = self._enviar_notificacion(notif)
                
                if exito:
                    notif.enviado = True
                    notif.fecha_envio = timezone.now()
                    notif.save()
                    enviadas += 1
                else:
                    notif.ultimo_error = "Error simulado"
                    notif.save()
                    fallidas += 1
                    
            except Exception as e:
                notif.ultimo_error = str(e)
                notif.save()
                fallidas += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ Error en notificación {notif.id}: {str(e)}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ {enviadas} notificaciones enviadas')
        )
        if fallidas > 0:
            self.stdout.write(
                self.style.WARNING(f'⚠️  {fallidas} notificaciones fallidas')
            )
    
    def _enviar_notificacion(self, notif):
        """Simula el envío de una notificación"""
        # TODO: Implementar envío real por email/SMS/WhatsApp
        # según el canal especificado
        
        if notif.canal == 'EMAIL':
            # Enviar por email
            pass
        elif notif.canal == 'SMS':
            # Enviar por SMS
            pass
        
        return True  # Simular éxito


# ========================================================
# banco/management/commands/crear_periodo_fondo_mutuo.py

from django.core.management.base import BaseCommand
from banco.models import FondoMutuo


class Command(BaseCommand):
    help = 'Crea automáticamente el período del fondo mutuo (Job mensual - día 1)'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('=== Creando período del fondo mutuo ===')
        )
        
        try:
            # Intentar crear el fondo del período actual
            fondo = FondoMutuo.crear_periodo_actual()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Fondo mutuo para período {fondo.periodo} creado'
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'   Fecha inicio: {fondo.fecha_inicio}'
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'   Fecha fin: {fondo.fecha_fin}'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {str(e)}')
            )


# ========================================================
# banco/management/commands/desbloquear_usuarios.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Usuario


class Command(BaseCommand):
    help = 'Desbloquea usuarios cuyo tiempo de bloqueo ha expirado (Job cada hora)'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('=== Desbloqueando usuarios ===')
        )
        
        # Buscar usuarios bloqueados cuyo tiempo expiró
        usuarios_bloqueados = Usuario.objects.filter(
            bloqueado_hasta__isnull=False,
            bloqueado_hasta__lt=timezone.now()
        )
        
        desbloqueados = 0
        
        for usuario in usuarios_bloqueados:
            usuario.desbloquear_usuario()
            desbloqueados += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Usuario {usuario.usuario} desbloqueado')
            )
        
        if desbloqueados == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ No hay usuarios para desbloquear')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Total: {desbloqueados} usuarios desbloqueados'
                )
            )


# ========================================================
# CONFIGURACIÓN DE CRON JOBS
# ========================================================

"""
Para configurar estos jobs, puedes usar:

1. **Django-cron** o **Celery Beat** (recomendado para producción)

2. **Crontab del sistema** (Linux):

# /etc/crontab o crontab -e

# Conciliación diaria a las 11:00 PM
0 23 * * * cd /ruta/proyecto && python manage.py conciliar_saldos

# Detectar cuotas vencidas diariamente a las 6:00 AM
0 6 * * * cd /ruta/proyecto && python manage.py detectar_cuotas_vencidas

# Alertar cuotas próximas diariamente a las 8:00 AM
0 8 * * * cd /ruta/proyecto && python manage.py alertar_cuotas_proximas --dias=5

# Procesar notificaciones cada 15 minutos
*/15 * * * * cd /ruta/proyecto && python manage.py procesar_notificaciones

# Crear período fondo mutuo el día 1 de cada mes a las 00:01
1 0 1 * * cd /ruta/proyecto && python manage.py crear_periodo_fondo_mutuo

# Desbloquear usuarios cada hora
0 * * * * cd /ruta/proyecto && python manage.py desbloquear_usuarios

3. **Django-Q o Huey** (alternativas más ligeras que Celery)

4. **APScheduler** para desarrollo/testing
"""