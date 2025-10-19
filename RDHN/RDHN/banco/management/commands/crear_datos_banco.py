from django.core.management.base import BaseCommand
from banco.models import TipoCuenta, TipoPrestamo
from core.models import CatEstado
from decimal import Decimal


class Command(BaseCommand):
    help = 'Crea datos iniciales para el sistema bancario'

    def handle(self, *args, **options):
        self.stdout.write('Creando datos iniciales del banco...')
        
        # Crear estados para cuentas
        estados_cuenta = [
            {'dominio': 'CUENTA', 'codigo': 'ACTIVA', 'nombre': 'Activa', 'es_final': False},
            {'dominio': 'CUENTA', 'codigo': 'INACTIVA', 'nombre': 'Inactiva', 'es_final': False},
            {'dominio': 'CUENTA', 'codigo': 'CERRADA', 'nombre': 'Cerrada', 'es_final': True},
        ]
        
        for estado in estados_cuenta:
            CatEstado.objects.get_or_create(**estado)
        
        self.stdout.write(self.style.SUCCESS('✓ Estados de cuenta creados'))
        
        # Crear tipos de cuenta
        tipos_cuenta = [
            {
                'codigo': 'FIJO',
                'nombre': 'Ahorro Fijo',
                'descripcion': 'Cuenta de ahorro fijo con deducción de planilla',
                'tasa_interes_anual': Decimal('5.00'),
                'monto_minimo': Decimal('25.00'),
                'es_retirable': False,
                'requiere_deduccion_planilla': True,
                'activo': True
            },
            {
                'codigo': 'VOLUNTARIO',
                'nombre': 'Ahorro Voluntario',
                'descripcion': 'Cuenta de ahorro voluntario sin monto mínimo',
                'tasa_interes_anual': Decimal('3.00'),
                'monto_minimo': Decimal('0.00'),
                'es_retirable': False,
                'requiere_deduccion_planilla': False,
                'activo': True
            },
            {
                'codigo': 'PERSONAL',
                'nombre': 'Ahorro Personal (Retirable)',
                'descripcion': 'Cuenta de ahorro personal con retiros libres',
                'tasa_interes_anual': Decimal('2.00'),
                'monto_minimo': Decimal('0.00'),
                'es_retirable': True,
                'requiere_deduccion_planilla': False,
                'activo': True
            },
        ]
        
        for tipo in tipos_cuenta:
            TipoCuenta.objects.get_or_create(
                codigo=tipo['codigo'],
                defaults=tipo
            )
        
        self.stdout.write(self.style.SUCCESS('✓ Tipos de cuenta creados'))
        
        # Crear tipos de préstamo
        tipos_prestamo = [
            {
                'codigo': 'PERSONAL',
                'nombre': 'Préstamo Personal',
                'descripcion': 'Préstamo personal estándar basado en ahorro fijo',
                'tasa_interes_anual': Decimal('15.00'),
                'multiplicador_ahorro': Decimal('3.00'),
                'plazo_minimo_meses': 6,
                'plazo_maximo_meses': 24,
                'requiere_garantes': False,
                'cantidad_garantes': 0,
                'activo': True
            },
            {
                'codigo': 'EMERGENCIA',
                'nombre': 'Préstamo de Emergencia',
                'descripcion': 'Préstamo especial para emergencias con garantes',
                'tasa_interes_anual': Decimal('18.00'),
                'multiplicador_ahorro': Decimal('5.00'),
                'plazo_minimo_meses': 12,
                'plazo_maximo_meses': 60,
                'requiere_garantes': True,
                'cantidad_garantes': 2,
                'activo': True
            },
        ]
        
        for tipo in tipos_prestamo:
            TipoPrestamo.objects.get_or_create(
                codigo=tipo['codigo'],
                defaults=tipo
            )
        
        self.stdout.write(self.style.SUCCESS('✓ Tipos de préstamo creados'))
        
        self.stdout.write(
            self.style.SUCCESS('\n¡Datos iniciales creados exitosamente!')
        )