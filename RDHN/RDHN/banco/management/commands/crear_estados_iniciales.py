from django.core.management.base import BaseCommand
from core.models import CatEstado


class Command(BaseCommand):
    help = 'Crea los estados iniciales del sistema'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Creando estados iniciales ==='))
        
        estados = [
            # Estados de Socio
            ('SOCIO', 'ACTIVO', 'Activo', False, 1),
            ('SOCIO', 'INACTIVO', 'Inactivo', True, 2),
            ('SOCIO', 'SUSPENDIDO', 'Suspendido', False, 3),
            
            # Estados de Usuario
            ('USUARIO', 'ACTIVO', 'Activo', False, 1),
            ('USUARIO', 'INACTIVO', 'Inactivo', True, 2),
            ('USUARIO', 'BLOQUEADO', 'Bloqueado', False, 3),
            
            # Estados de Cuenta Ahorro
            ('CUENTA_AHORRO', 'ACTIVO', 'Activa', False, 1),
            ('CUENTA_AHORRO', 'INACTIVA', 'Inactiva', False, 2),
            ('CUENTA_AHORRO', 'CERRADA', 'Cerrada', True, 3),
            
            # Estados de Transacción
            ('TRANSACCION', 'PENDIENTE', 'Pendiente', False, 1),
            ('TRANSACCION', 'PROCESADA', 'Procesada', True, 2),
            ('TRANSACCION', 'ANULADA', 'Anulada', True, 3),
            ('TRANSACCION', 'REVERSADA', 'Reversada', True, 4),
            
            # Estados de Fondo Mutuo
            ('FONDO_MUTUO', 'ABIERTO', 'Abierto', False, 1),
            ('FONDO_MUTUO', 'CERRADO', 'Cerrado', True, 2),
            
            # Estados de Solicitud Ayuda
            ('SOLICITUD_AYUDA', 'PENDIENTE', 'Pendiente', False, 1),
            ('SOLICITUD_AYUDA', 'EN_REVISION', 'En Revisión', False, 2),
            ('SOLICITUD_AYUDA', 'APROBADA', 'Aprobada', False, 3),
            ('SOLICITUD_AYUDA', 'RECHAZADA', 'Rechazada', True, 4),
            ('SOLICITUD_AYUDA', 'DESEMBOLSADA', 'Desembolsada', True, 5),
            ('SOLICITUD_AYUDA', 'CANCELADA', 'Cancelada', True, 6),
            
            # Estados de Préstamo
            ('PRESTAMO', 'SOLICITADO', 'Solicitado', False, 1),
            ('PRESTAMO', 'EN_REVISION', 'En Revisión', False, 2),
            ('PRESTAMO', 'APROBADO', 'Aprobado', False, 3),
            ('PRESTAMO', 'RECHAZADO', 'Rechazado', True, 4),
            ('PRESTAMO', 'DESEMBOLSADO', 'Desembolsado', False, 5),
            ('PRESTAMO', 'EN_PAGO', 'En Pago', False, 6),
            ('PRESTAMO', 'PAGADO', 'Pagado', True, 7),
            ('PRESTAMO', 'VENCIDO', 'Vencido', False, 8),
            ('PRESTAMO', 'CANCELADO', 'Cancelado', True, 9),
            
            # Estados de Notificación
            ('NOTIFICACION', 'PENDIENTE', 'Pendiente', False, 1),
            ('NOTIFICACION', 'ENVIADA', 'Enviada', True, 2),
            ('NOTIFICACION', 'FALLIDA', 'Fallida', False, 3),
            ('NOTIFICACION', 'LEIDA', 'Leída', True, 4),
        ]
        
        creados = 0
        for dominio, codigo, nombre, es_final, orden in estados:
            estado, created = CatEstado.objects.get_or_create(
                dominio=dominio,
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'es_final': es_final,
                    'orden': orden
                }
            )
            
            if created:
                creados += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Creado: {dominio}:{codigo}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Total creados: {creados} estados')
        )
