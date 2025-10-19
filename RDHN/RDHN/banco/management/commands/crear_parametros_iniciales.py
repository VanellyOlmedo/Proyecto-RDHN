from django.core.management.base import BaseCommand
from core.models import ParametroSistema


class Command(BaseCommand):
    help = 'Crea los parámetros iniciales del sistema'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Creando parámetros iniciales ==='))
        
        parametros = [
            # Parámetros del Fondo Mutuo
            ('FONDO_MUTUO', 'MONTO_MINIMO_APORTE', 'DECIMAL', '50.00', 'GLOBAL', 
             'Monto mínimo para aportar al fondo mutuo'),
            ('FONDO_MUTUO', 'MONTO_MAXIMO_AYUDA', 'DECIMAL', '5000.00', 'GLOBAL',
             'Monto máximo de ayuda que se puede otorgar'),
            ('FONDO_MUTUO', 'MESES_ANTIGUEDAD_MINIMA', 'INT', '6', 'GLOBAL',
             'Meses mínimos de antigüedad para solicitar ayuda'),
            
            # Parámetros de Notificaciones
            ('NOTIFICACIONES', 'MAX_REINTENTOS', 'INT', '3', 'GLOBAL',
             'Número máximo de reintentos para enviar notificaciones'),
            ('NOTIFICACIONES', 'MINUTOS_ESPERA_REINTENTO', 'INT', '15', 'GLOBAL',
             'Minutos de espera entre reintentos'),
            
            # Parámetros de Seguridad
            ('SEGURIDAD', 'MAX_INTENTOS_LOGIN', 'INT', '5', 'GLOBAL',
             'Intentos máximos de login antes de bloquear'),
            ('SEGURIDAD', 'MINUTOS_BLOQUEO', 'INT', '30', 'GLOBAL',
             'Minutos de bloqueo tras superar intentos'),
            ('SEGURIDAD', 'DIAS_EXPIRACION_PASSWORD', 'INT', '90', 'GLOBAL',
             'Días hasta que expire la contraseña'),
            
            # Parámetros de Cuentas
            ('CUENTAS', 'DIAS_MAX_REVERSO', 'INT', '30', 'GLOBAL',
             'Días máximos para reversar una transacción'),
        ]
        
        creados = 0
        for modulo, nombre, tipo_dato, valor, scope, descripcion in parametros:
            param, created = ParametroSistema.objects.get_or_create(
                modulo=modulo,
                nombre_parametro=nombre,
                scope=scope,
                defaults={
                    'tipo_dato': tipo_dato,
                    'valor': valor,
                    'descripcion': descripcion,
                    'activo': True
                }
            )
            
            if created:
                creados += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Creado: {modulo}.{nombre}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Total creados: {creados} parámetros')
        )