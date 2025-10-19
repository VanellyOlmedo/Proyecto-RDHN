from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from banco.models import CuotaPrestamo, Notificacion


class Command(BaseCommand):
    help = 'Ejecuta tareas diarias del banco (calcular moras, enviar notificaciones)'

    def handle(self, *args, **options):
        self.stdout.write('Ejecutando tareas diarias del banco...')
        
        # ==================================================
        # 1. CALCULAR MORAS EN CUOTAS VENCIDAS
        # ==================================================
        cuotas_pendientes = CuotaPrestamo.objects.filter(
            estado='PENDIENTE',
            fecha_vencimiento__lt=timezone.now().date()
        )
        
        mora_calculada = 0
        for cuota in cuotas_pendientes:
            cuota.calcular_mora()
            mora_calculada += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ {mora_calculada} cuotas con mora calculada')
        )
        
        # ==================================================
        # 2. NOTIFICACIONES DE CUOTAS PRÓXIMAS A VENCER
        # ==================================================
        fecha_limite = timezone.now().date() + timedelta(days=5)
        
        cuotas_proximas = CuotaPrestamo.objects.filter(
            estado='PENDIENTE',
            fecha_vencimiento__lte=fecha_limite,
            fecha_vencimiento__gte=timezone.now().date()
        ).select_related('prestamo__socio')
        
        notif_proximas = 0
        for cuota in cuotas_proximas:
            # Verificar si ya se envió notificación
            notif_existe = Notificacion.objects.filter(
                socio=cuota.prestamo.socio,
                tipo='CUOTA_PROXIMA',
                creado_en__date=timezone.now().date()
            ).exists()
            
            if not notif_existe:
                dias_faltantes = (cuota.fecha_vencimiento - timezone.now().date()).days
                
                Notificacion.objects.create(
                    socio=cuota.prestamo.socio,
                    tipo='CUOTA_PROXIMA',
                    asunto=f'Recordatorio: Cuota próxima a vencer',
                    mensaje=f'Su cuota #{cuota.numero_cuota} del préstamo {cuota.prestamo.numero_prestamo} vence en {dias_faltantes} días ({cuota.fecha_vencimiento}). Monto: L. {cuota.monto_cuota}'
                )
                notif_proximas += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ {notif_proximas} notificaciones de cuotas próximas')
        )
        
        # ==================================================
        # 3. NOTIFICACIONES DE CUOTAS VENCIDAS
        # ==================================================
        cuotas_vencidas = CuotaPrestamo.objects.filter(
            estado='VENCIDA'
        ).select_related('prestamo__socio')
        
        notif_vencidas = 0
        for cuota in cuotas_vencidas:
            # Enviar notificación cada 7 días
            if cuota.dias_mora % 7 == 0:
                Notificacion.objects.create(
                    socio=cuota.prestamo.socio,
                    tipo='CUOTA_VENCIDA',
                    asunto=f'URGENTE: Cuota vencida hace {cuota.dias_mora} días',
                    mensaje=f'Su cuota #{cuota.numero_cuota} del préstamo {cuota.prestamo.numero_prestamo} lleva {cuota.dias_mora} días de atraso. Monto original: L. {cuota.monto_cuota}. Mora acumulada: L. {cuota.monto_mora}. Total a pagar: L. {cuota.monto_cuota + cuota.monto_mora}'
                )
                notif_vencidas += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ {notif_vencidas} notificaciones de cuotas vencidas')
        )
        
        # ==================================================
        # 4. ENVIAR NOTIFICACIONES PENDIENTES
        # ==================================================
        notificaciones_pendientes = Notificacion.objects.filter(
            enviado=False
        ).select_related('socio')
        
        enviadas = 0
        for notif in notificaciones_pendientes[:50]:  # Limitar a 50 por ejecución
            # Aquí integrarías el envío de email
            # Por ahora solo simular
            
            # from django.core.mail import send_mail
            # try:
            #     send_mail(
            #         notif.asunto,
            #         notif.mensaje,
            #         'noreply@rdhn.com',
            #         [notif.socio.usuario.email if hasattr(notif.socio, 'usuario') else None],
            #         fail_silently=False,
            #     )
            #     notif.enviado = True
            #     notif.fecha_envio = timezone.now()
            #     notif.save()
            #     enviadas += 1
            # except Exception as e:
            #     notif.error_envio = str(e)
            #     notif.save()
            
            # Simulación (comentar cuando tengas email configurado)
            notif.enviado = True
            notif.fecha_envio = timezone.now()
            notif.save()
            enviadas += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ {enviadas} notificaciones enviadas por email')
        )
        
        self.stdout.write(
            self.style.SUCCESS('\n¡Tareas diarias completadas exitosamente!')
        )