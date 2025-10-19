"""
Comando Django para poblar la base de datos con datos de prueba
Ubicación: core/management/commands/poblar_bd.py
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import random

from core.models import CatEstado, Socio, SocioContacto, Usuario, Rol, UsuarioRol, ExpedienteDigital
from banco.models import (
    TipoCuenta, TipoPrestamo, CuentaAhorro, Transaccion, 
    Prestamo, Garante, CuotaPrestamo, PagoPrestamo,
    PeriodoDividendo, Dividendo, Notificacion
)


class Command(BaseCommand):
    help = 'Pobla la base de datos con datos de prueba realistas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Limpia la base de datos antes de poblar',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Iniciando población de base de datos...'))
        
        if options['limpiar']:
            self.stdout.write(self.style.WARNING('⚠️  Limpiando base de datos...'))
            self.limpiar_bd()
        
        # 1. Crear Estados
        self.stdout.write('📊 Creando estados...')
        self.crear_estados()
        
        # 2. Crear Roles
        self.stdout.write('👥 Creando roles...')
        self.crear_roles()
        
        # 3. Crear Tipos de Cuenta
        self.stdout.write('💰 Creando tipos de cuenta...')
        self.crear_tipos_cuenta()
        
        # 4. Crear Tipos de Préstamo
        self.stdout.write('💳 Creando tipos de préstamo...')
        self.crear_tipos_prestamo()
        
        # 5. Crear Socios
        self.stdout.write('👤 Creando socios...')
        socios = self.crear_socios()
        
        # 6. Crear Usuarios
        self.stdout.write('🔐 Creando usuarios...')
        self.crear_usuarios(socios)
        
        # 7. Crear Cuentas de Ahorro
        self.stdout.write('🏦 Creando cuentas de ahorro...')
        cuentas = self.crear_cuentas_ahorro(socios)
        
        # 8. Crear Transacciones
        self.stdout.write('💸 Creando transacciones...')
        self.crear_transacciones(cuentas)
        
        # 9. Crear Préstamos
        self.stdout.write('📋 Creando préstamos...')
        prestamos = self.crear_prestamos(socios, cuentas)
        
        # 10. Crear Pagos de Préstamos
        self.stdout.write('💵 Creando pagos de préstamos...')
        self.crear_pagos_prestamos(prestamos)
        
        # 11. Crear Dividendos
        self.stdout.write('💰 Creando períodos de dividendos...')
        self.crear_dividendos(socios)
        
        # 12. Crear Notificaciones
        self.stdout.write('📬 Creando notificaciones...')
        self.crear_notificaciones(socios, prestamos)
        
        self.stdout.write(self.style.SUCCESS('✅ ¡Base de datos poblada exitosamente!'))
        self.mostrar_resumen()

    def limpiar_bd(self):
        """Limpia los datos existentes"""
        Notificacion.objects.all().delete()
        Dividendo.objects.all().delete()
        PeriodoDividendo.objects.all().delete()
        PagoPrestamo.objects.all().delete()
        CuotaPrestamo.objects.all().delete()
        Garante.objects.all().delete()
        Prestamo.objects.all().delete()
        Transaccion.objects.all().delete()
        CuentaAhorro.objects.all().delete()
        TipoPrestamo.objects.all().delete()
        TipoCuenta.objects.all().delete()
        UsuarioRol.objects.all().delete()
        Usuario.objects.all().delete()
        ExpedienteDigital.objects.all().delete()
        SocioContacto.objects.all().delete()
        Socio.objects.all().delete()
        Rol.objects.all().delete()
        CatEstado.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('   ✓ Base de datos limpiada'))

    def crear_estados(self):
        """Crea los estados del sistema"""
        estados = [
            # Estados de Socio
            ('SOCIO', 'ACTIVO', 'Activo', False, 1),
            ('SOCIO', 'INACTIVO', 'Inactivo', False, 2),
            ('SOCIO', 'SUSPENDIDO', 'Suspendido', False, 3),
            ('SOCIO', 'RETIRADO', 'Retirado', True, 4),
            
            # Estados de Usuario
            ('USUARIO', 'ACTIVO', 'Activo', False, 1),
            ('USUARIO', 'INACTIVO', 'Inactivo', False, 2),
            ('USUARIO', 'BLOQUEADO', 'Bloqueado', False, 3),
            
            # Estados de Cuenta
            ('CUENTA', 'ACTIVA', 'Activa', False, 1),
            ('CUENTA', 'INACTIVA', 'Inactiva', False, 2),
            ('CUENTA', 'CERRADA', 'Cerrada', True, 3),
        ]
        
        for dominio, codigo, nombre, es_final, orden in estados:
            CatEstado.objects.get_or_create(
                dominio=dominio,
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'es_final': es_final,
                    'orden': orden
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(estados)} estados creados'))

    def crear_roles(self):
        """Crea los roles del sistema"""
        roles = [
            ('Administrador', 'Acceso total al sistema'),
            ('Gerente', 'Gestión de operaciones bancarias'),
            ('Cajero', 'Operaciones de caja y transacciones'),
            ('Auditor', 'Consulta y auditoría de operaciones'),
            ('Socio', 'Acceso básico para socios'),
        ]
        
        for nombre, descripcion in roles:
            Rol.objects.get_or_create(
                nombre_rol=nombre,
                defaults={
                    'descripcion': descripcion,
                    'estado': True
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(roles)} roles creados'))

    def crear_tipos_cuenta(self):
        """Crea los tipos de cuenta"""
        tipos = [
            {
                'codigo': 'FIJO',
                'nombre': 'Ahorro Fijo',
                'descripcion': 'Cuenta de ahorro fijo con deducción de planilla',
                'tasa_interes_anual': Decimal('8.00'),
                'monto_minimo': Decimal('100.00'),
                'es_retirable': False,
                'requiere_deduccion_planilla': True,
            },
            {
                'codigo': 'VOLUNTARIO',
                'nombre': 'Ahorro Voluntario',
                'descripcion': 'Cuenta de ahorro voluntario sin deducción de planilla',
                'tasa_interes_anual': Decimal('5.00'),
                'monto_minimo': Decimal('50.00'),
                'es_retirable': False,
                'requiere_deduccion_planilla': False,
            },
            {
                'codigo': 'PERSONAL',
                'nombre': 'Ahorro Personal (Retirable)',
                'descripcion': 'Cuenta de ahorro personal con retiros permitidos',
                'tasa_interes_anual': Decimal('3.00'),
                'monto_minimo': Decimal('0.00'),
                'es_retirable': True,
                'requiere_deduccion_planilla': False,
            },
        ]
        
        for tipo_data in tipos:
            TipoCuenta.objects.get_or_create(
                codigo=tipo_data['codigo'],
                defaults=tipo_data
            )
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(tipos)} tipos de cuenta creados'))

    def crear_tipos_prestamo(self):
        """Crea los tipos de préstamo"""
        tipos = [
            {
                'codigo': 'PERSONAL',
                'nombre': 'Préstamo Personal',
                'descripcion': 'Préstamo personal para diversos fines',
                'tasa_interes_anual': Decimal('18.00'),
                'multiplicador_ahorro': Decimal('3.00'),
                'plazo_minimo_meses': 6,
                'plazo_maximo_meses': 24,
                'requiere_garantes': True,
                'cantidad_garantes': 2,
            },
            {
                'codigo': 'EMERGENCIA',
                'nombre': 'Préstamo de Emergencia',
                'descripcion': 'Préstamo de emergencia rápido',
                'tasa_interes_anual': Decimal('12.00'),
                'multiplicador_ahorro': Decimal('2.00'),
                'plazo_minimo_meses': 3,
                'plazo_maximo_meses': 12,
                'requiere_garantes': False,
                'cantidad_garantes': 0,
            },
        ]
        
        for tipo_data in tipos:
            TipoPrestamo.objects.get_or_create(
                codigo=tipo_data['codigo'],
                defaults=tipo_data
            )
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(tipos)} tipos de préstamo creados'))

    def crear_socios(self):
        """Crea socios de prueba"""
        estado_activo = CatEstado.objects.get(dominio='SOCIO', codigo='ACTIVO')
        
        socios_data = [
            {
                'numero_socio': 'SOC-001',
                'primer_nombre': 'Juan',
                'segundo_nombre': 'Carlos',
                'primer_apellido': 'López',
                'segundo_apellido': 'Martínez',
                'identidad': '0801-1990-12345',
                'telefono': '9876-5432',
                'email_suffix': '1',
            },
            {
                'numero_socio': 'SOC-002',
                'primer_nombre': 'María',
                'segundo_nombre': 'José',
                'primer_apellido': 'García',
                'segundo_apellido': 'Hernández',
                'identidad': '0801-1992-23456',
                'telefono': '9876-5433',
                'email_suffix': '2',
            },
            {
                'numero_socio': 'SOC-003',
                'primer_nombre': 'Pedro',
                'segundo_nombre': 'Antonio',
                'primer_apellido': 'Rodríguez',
                'segundo_apellido': 'Sánchez',
                'identidad': '0801-1988-34567',
                'telefono': '9876-5434',
                'email_suffix': '3',
            },
            {
                'numero_socio': 'SOC-004',
                'primer_nombre': 'Ana',
                'segundo_nombre': 'Lucía',
                'primer_apellido': 'Martínez',
                'segundo_apellido': 'Gómez',
                'identidad': '0801-1995-45678',
                'telefono': '9876-5435',
                'email_suffix': '4',
            },
            {
                'numero_socio': 'SOC-005',
                'primer_nombre': 'Carlos',
                'segundo_nombre': 'Eduardo',
                'primer_apellido': 'Fernández',
                'segundo_apellido': 'Díaz',
                'identidad': '0801-1987-56789',
                'telefono': '9876-5436',
                'email_suffix': '5',
            },
            {
                'numero_socio': 'SOC-006',
                'primer_nombre': 'Sofía',
                'segundo_nombre': 'Isabel',
                'primer_apellido': 'Ramírez',
                'segundo_apellido': 'Torres',
                'identidad': '0801-1993-67890',
                'telefono': '9876-5437',
                'email_suffix': '6',
            },
            {
                'numero_socio': 'SOC-007',
                'primer_nombre': 'Luis',
                'segundo_nombre': 'Fernando',
                'primer_apellido': 'Morales',
                'segundo_apellido': 'Castro',
                'identidad': '0801-1991-78901',
                'telefono': '9876-5438',
                'email_suffix': '7',
            },
            {
                'numero_socio': 'SOC-008',
                'primer_nombre': 'Carmen',
                'segundo_nombre': 'Rosa',
                'primer_apellido': 'Ruiz',
                'segundo_apellido': 'Ortiz',
                'identidad': '0801-1994-89012',
                'telefono': '9876-5439',
                'email_suffix': '8',
            },
        ]
        
        socios = []
        for i, data in enumerate(socios_data):
            fecha_ingreso = timezone.now().date() - timedelta(days=random.randint(365, 1825))
            
            socio, created = Socio.objects.get_or_create(
                numero_socio=data['numero_socio'],
                defaults={
                    'primer_nombre': data['primer_nombre'],
                    'segundo_nombre': data['segundo_nombre'],
                    'primer_apellido': data['primer_apellido'],
                    'segundo_apellido': data['segundo_apellido'],
                    'identidad': data['identidad'],
                    'direccion': f'Col. Kennedy, Bloque {i+1}, Casa #{random.randint(1, 50)}',
                    'fecha_ingreso': fecha_ingreso,
                    'id_estado': estado_activo,
                }
            )
            
            if created:
                # Crear contactos con formato +numero
                SocioContacto.objects.create(
                    socio=socio,
                    tipo='TELEFONO',
                    valor=data['telefono'],
                    preferido=True,
                    activo=True
                )
                
                SocioContacto.objects.create(
                    socio=socio,
                    tipo='EMAIL',
                    valor=f"testmicorreo2025+{data['email_suffix']}@gmail.com",
                    preferido=True,
                    activo=True
                )
                
                # Crear expediente
                ExpedienteDigital.objects.create(
                    socio=socio,
                    numero_expediente=f"EXP-{data['numero_socio']}",
                    fecha_creacion=fecha_ingreso,
                    observaciones='Expediente generado automáticamente'
                )
            
            socios.append(socio)
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(socios)} socios creados'))
        return socios

    def crear_usuarios(self, socios):
        """Crea usuarios del sistema"""
        estado_activo = CatEstado.objects.get(dominio='USUARIO', codigo='ACTIVO')
        rol_admin = Rol.objects.get(nombre_rol='Administrador')
        rol_gerente = Rol.objects.get(nombre_rol='Gerente')
        rol_cajero = Rol.objects.get(nombre_rol='Cajero')
        rol_socio = Rol.objects.get(nombre_rol='Socio')
        
        # Usuario administrador
        admin, created = Usuario.objects.get_or_create(
            usuario='admin',
            defaults={
                'email': 'testmicorreo2025+admin@gmail.com',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
                'id_estado': estado_activo,
                'requiere_cambio_password': False,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.password_updated_at = timezone.now()
            admin.save()
            admin.roles.add(rol_admin)
        
        # Gerente
        gerente, created = Usuario.objects.get_or_create(
            usuario='gerente',
            defaults={
                'email': 'testmicorreo2025+gerente@gmail.com',
                'is_staff': True,
                'is_active': True,
                'id_estado': estado_activo,
                'requiere_cambio_password': False,
            }
        )
        if created:
            gerente.set_password('gerente123')
            gerente.password_updated_at = timezone.now()
            gerente.save()
            gerente.roles.add(rol_gerente)
        
        # Cajero
        cajero, created = Usuario.objects.get_or_create(
            usuario='cajero',
            defaults={
                'email': 'testmicorreo2025+cajero@gmail.com',
                'is_staff': True,
                'is_active': True,
                'id_estado': estado_activo,
                'requiere_cambio_password': False,
            }
        )
        if created:
            cajero.set_password('cajero123')
            cajero.password_updated_at = timezone.now()
            cajero.save()
            cajero.roles.add(rol_cajero)
        
        # Usuarios para algunos socios
        for i, socio in enumerate(socios[:3]):
            username = f"socio{i+1}"
            usuario, created = Usuario.objects.get_or_create(
                usuario=username,
                defaults={
                    'email': f'testmicorreo2025+socio{i+1}@gmail.com',
                    'socio': socio,
                    'is_active': True,
                    'id_estado': estado_activo,
                    'requiere_cambio_password': True,
                }
            )
            if created:
                usuario.set_password('socio123')
                usuario.password_updated_at = timezone.now()
                usuario.save()
                usuario.roles.add(rol_socio)
        
        self.stdout.write(self.style.SUCCESS('   ✓ Usuarios creados (admin/admin123, gerente/gerente123, cajero/cajero123)'))

    def crear_cuentas_ahorro(self, socios):
        """Crea cuentas de ahorro para los socios"""
        tipo_fijo = TipoCuenta.objects.get(codigo='FIJO')
        tipo_voluntario = TipoCuenta.objects.get(codigo='VOLUNTARIO')
        tipo_personal = TipoCuenta.objects.get(codigo='PERSONAL')
        estado_activa = CatEstado.objects.get(dominio='CUENTA', codigo='ACTIVA')
        
        cuentas = []
        
        for i, socio in enumerate(socios):
            # Cuenta de ahorro fijo
            cuenta_fija, created = CuentaAhorro.objects.get_or_create(
                numero_cuenta=f"FIJO-{1000 + i}",
                defaults={
                    'socio': socio,
                    'tipo_cuenta': tipo_fijo,
                    'saldo_actual': Decimal(random.randint(5000, 50000)),
                    'monto_deduccion_planilla': Decimal(random.choice([500, 1000, 1500, 2000])),
                    'fecha_apertura': socio.fecha_ingreso,
                    'estado': estado_activa,
                }
            )
            cuentas.append(cuenta_fija)
            
            # Cuenta de ahorro voluntario (solo algunos)
            if i % 2 == 0:
                cuenta_vol, created = CuentaAhorro.objects.get_or_create(
                    numero_cuenta=f"VOL-{2000 + i}",
                    defaults={
                        'socio': socio,
                        'tipo_cuenta': tipo_voluntario,
                        'saldo_actual': Decimal(random.randint(1000, 10000)),
                        'fecha_apertura': socio.fecha_ingreso + timedelta(days=30),
                        'estado': estado_activa,
                    }
                )
                cuentas.append(cuenta_vol)
            
            # Cuenta personal (solo algunos)
            if i % 3 == 0:
                cuenta_pers, created = CuentaAhorro.objects.get_or_create(
                    numero_cuenta=f"PERS-{3000 + i}",
                    defaults={
                        'socio': socio,
                        'tipo_cuenta': tipo_personal,
                        'saldo_actual': Decimal(random.randint(500, 5000)),
                        'fecha_apertura': socio.fecha_ingreso + timedelta(days=60),
                        'estado': estado_activa,
                    }
                )
                cuentas.append(cuenta_pers)
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(cuentas)} cuentas de ahorro creadas'))
        return cuentas

    def crear_transacciones(self, cuentas):
        """Crea transacciones de ejemplo"""
        admin = Usuario.objects.get(usuario='admin')
        
        for cuenta in cuentas[:5]:  # Solo primeras 5 cuentas
            # 3-5 transacciones por cuenta
            num_trans = random.randint(3, 5)
            for _ in range(num_trans):
                tipo = random.choice(['DEPOSITO', 'INTERES'])
                monto = Decimal(random.randint(100, 2000))
                fecha = timezone.now() - timedelta(days=random.randint(1, 180))
                
                Transaccion.objects.create(
                    cuenta_ahorro=cuenta,
                    tipo_transaccion=tipo,
                    monto=monto,
                    saldo_anterior=cuenta.saldo_actual - monto,
                    saldo_nuevo=cuenta.saldo_actual,
                    descripcion=f'{tipo.title()} automático',
                    fecha_transaccion=fecha,
                    realizado_por=admin
                )
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ Transacciones creadas'))

    def crear_prestamos(self, socios, cuentas):
        """Crea préstamos de ejemplo"""
        tipo_personal = TipoPrestamo.objects.get(codigo='PERSONAL')
        tipo_emergencia = TipoPrestamo.objects.get(codigo='EMERGENCIA')
        admin = Usuario.objects.get(usuario='admin')
        
        # Crear algunos préstamos
        prestamos_data = [
            {
                'socio': socios[0],
                'tipo': tipo_personal,
                'monto': Decimal('15000.00'),
                'plazo': 12,
                'estado': 'DESEMBOLSADO',
            },
            {
                'socio': socios[1],
                'tipo': tipo_emergencia,
                'monto': Decimal('5000.00'),
                'plazo': 6,
                'estado': 'EN_PAGO',
            },
            {
                'socio': socios[2],
                'tipo': tipo_personal,
                'monto': Decimal('20000.00'),
                'plazo': 18,
                'estado': 'APROBADO',
            },
            {
                'socio': socios[3],
                'tipo': tipo_emergencia,
                'monto': Decimal('3000.00'),
                'plazo': 6,
                'estado': 'SOLICITADO',
            },
            {
                'socio': socios[4],
                'tipo': tipo_personal,
                'monto': Decimal('25000.00'),
                'plazo': 24,
                'estado': 'EN_PAGO',
            },
        ]
        
        prestamos = []
        for i, data in enumerate(prestamos_data):
            fecha_sol = timezone.now().date() - timedelta(days=random.randint(60, 180))
            
            # Determinar fechas según el estado
            if data['estado'] == 'SOLICITADO':
                fecha_aprobacion = None
                fecha_desembolso = None
                fecha_primer_pago = None
                aprobado_por = None
            elif data['estado'] == 'APROBADO':
                fecha_aprobacion = fecha_sol + timedelta(days=3)
                fecha_desembolso = None
                fecha_primer_pago = None
                aprobado_por = admin
            else:  # DESEMBOLSADO o EN_PAGO
                fecha_aprobacion = fecha_sol + timedelta(days=3)
                fecha_desembolso = fecha_sol + timedelta(days=5)
                fecha_primer_pago = fecha_sol + timedelta(days=35)
                aprobado_por = admin
            
            prestamo, created = Prestamo.objects.get_or_create(
                numero_prestamo=f"PREST-{1000 + i}",
                defaults={
                    'socio': data['socio'],
                    'tipo_prestamo': data['tipo'],
                    'monto_solicitado': data['monto'],
                    'monto_aprobado': data['monto'] if data['estado'] != 'SOLICITADO' else None,
                    'tasa_interes': data['tipo'].tasa_interes_anual,
                    'plazo_meses': data['plazo'],
                    'fecha_solicitud': fecha_sol,
                    'fecha_aprobacion': fecha_aprobacion,
                    'fecha_desembolso': fecha_desembolso,
                    'fecha_primer_pago': fecha_primer_pago,
                    'estado': data['estado'],
                    'deducir_por_planilla': True,
                    'numero_planilla': f"PLAN-{1000 + i}",
                    'aprobado_por': aprobado_por,
                }
            )
            
            if created:
                # Solo calcular cuota si está aprobado (no SOLICITADO)
                if data['estado'] not in ['SOLICITADO']:
                    prestamo.calcular_cuota()
                    prestamo.save()
                
                # Solo generar tabla de amortización si tiene fecha de primer pago
                if data['estado'] in ['DESEMBOLSADO', 'EN_PAGO'] and prestamo.fecha_primer_pago:
                    prestamo.generar_tabla_amortizacion()
                
                # Crear garantes si es préstamo personal
                if data['tipo'].requiere_garantes and len(socios) > i + 2:
                    for j in range(data['tipo'].cantidad_garantes):
                        if i + j + 1 < len(socios):
                            Garante.objects.get_or_create(
                                prestamo=prestamo,
                                socio_garante=socios[i + j + 1],
                                defaults={
                                    'fecha_aceptacion': fecha_sol + timedelta(days=1),
                                }
                            )
            
            prestamos.append(prestamo)
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(prestamos_data)} préstamos creados'))
        return prestamos

    def crear_pagos_prestamos(self, prestamos):
        """Crea pagos de préstamos"""
        admin = Usuario.objects.get(usuario='admin')
        contador_pagos = 0
        
        # Solo procesar préstamos EN_PAGO
        for prestamo in prestamos:
            if prestamo.estado == 'EN_PAGO':
                # Pagar algunas cuotas (1-3 cuotas)
                cuotas = prestamo.cuotas.filter(estado='PENDIENTE').order_by('numero_cuota')[:random.randint(1, 3)]
                
                for cuota in cuotas:
                    # Crear pago
                    pago = PagoPrestamo.objects.create(
                        prestamo=prestamo,
                        cuota=cuota,
                        monto_pagado=cuota.monto_cuota,
                        monto_capital=cuota.monto_capital,
                        monto_interes=cuota.monto_interes,
                        monto_mora=Decimal('0.00'),
                        fecha_pago=cuota.fecha_vencimiento - timedelta(days=random.randint(0, 5)),
                        numero_recibo=f"REC-{contador_pagos + 1000}",
                        metodo_pago='PLANILLA',
                        realizado_por=admin
                    )
                    
                    # Actualizar cuota
                    cuota.estado = 'PAGADA'
                    cuota.fecha_pago = pago.fecha_pago
                    cuota.save()
                    
                    # Actualizar saldo pendiente del préstamo
                    prestamo.saldo_pendiente -= cuota.monto_cuota
                    prestamo.save()
                    
                    contador_pagos += 1
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {contador_pagos} pagos de préstamos creados'))

    def crear_dividendos(self, socios):
        """Crea períodos y dividendos"""
        # Crear período del año anterior
        año_anterior = timezone.now().year - 1
        periodo, created = PeriodoDividendo.objects.get_or_create(
            año=año_anterior,
            defaults={
                'fecha_inicio': timezone.datetime(año_anterior, 1, 1).date(),
                'fecha_fin': timezone.datetime(año_anterior, 12, 31).date(),
                'total_intereses_generados': Decimal('50000.00'),
                'total_distribuido': Decimal('45000.00'),
                'fecha_distribucion': timezone.datetime(año_anterior, 12, 31).date(),
                'estado': 'DISTRIBUIDO'
            }
        )
        
        if created:
            # Crear dividendos para algunos socios
            for i, socio in enumerate(socios[:5]):
                # Calcular datos simulados
                saldo_promedio = Decimal(random.randint(10000, 50000))
                cant_prestamos = random.randint(1, 3)
                cumple = cant_prestamos >= 2
                porcentaje = Decimal(random.uniform(5, 15))
                monto = periodo.total_distribuido * (porcentaje / 100)
                
                Dividendo.objects.create(
                    periodo=periodo,
                    socio=socio,
                    saldo_promedio_fijo=saldo_promedio,
                    cantidad_prestamos=cant_prestamos,
                    cumple_requisito=cumple,
                    porcentaje_asignado=porcentaje,
                    monto_dividendo=monto,
                    fecha_acreditacion=periodo.fecha_distribucion,
                    acreditado=True
                )
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ Período de dividendos {año_anterior} creado'))

    def crear_notificaciones(self, socios, prestamos):
        """Crea notificaciones de ejemplo"""
        contador = 0
        
        # Notificaciones para cuotas próximas a vencer
        for prestamo in prestamos:
            if prestamo.estado in ['DESEMBOLSADO', 'EN_PAGO']:
                cuota_proxima = prestamo.cuotas.filter(estado='PENDIENTE').first()
                if cuota_proxima:
                    Notificacion.objects.create(
                        socio=prestamo.socio,
                        tipo='CUOTA_PROXIMA',
                        asunto='Recordatorio: Cuota próxima a vencer',
                        mensaje=f'Su cuota #{cuota_proxima.numero_cuota} del préstamo {prestamo.numero_prestamo} vence el {cuota_proxima.fecha_vencimiento}. Monto: L. {cuota_proxima.monto_cuota}',
                        enviado=False
                    )
                    contador += 1
        
        # Notificación de préstamo aprobado
        for prestamo in prestamos:
            if prestamo.estado == 'APROBADO':
                Notificacion.objects.create(
                    socio=prestamo.socio,
                    tipo='PRESTAMO_APROBADO',
                    asunto='¡Préstamo Aprobado!',
                    mensaje=f'Su préstamo {prestamo.numero_prestamo} por L. {prestamo.monto_aprobado} ha sido aprobado.',
                    enviado=False
                )
                contador += 1
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {contador} notificaciones creadas'))

    def mostrar_resumen(self):
        """Muestra un resumen de los datos creados"""
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN DE DATOS CREADOS'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        self.stdout.write(f"Estados: {CatEstado.objects.count()}")
        self.stdout.write(f"Roles: {Rol.objects.count()}")
        self.stdout.write(f"Socios: {Socio.objects.count()}")
        self.stdout.write(f"Usuarios: {Usuario.objects.count()}")
        self.stdout.write(f"Tipos de Cuenta: {TipoCuenta.objects.count()}")
        self.stdout.write(f"Tipos de Préstamo: {TipoPrestamo.objects.count()}")
        self.stdout.write(f"Cuentas de Ahorro: {CuentaAhorro.objects.count()}")
        self.stdout.write(f"Transacciones: {Transaccion.objects.count()}")
        self.stdout.write(f"Préstamos: {Prestamo.objects.count()}")
        self.stdout.write(f"Garantes: {Garante.objects.count()}")
        self.stdout.write(f"Cuotas: {CuotaPrestamo.objects.count()}")
        self.stdout.write(f"Pagos de Préstamos: {PagoPrestamo.objects.count()}")
        self.stdout.write(f"Períodos de Dividendos: {PeriodoDividendo.objects.count()}")
        self.stdout.write(f"Dividendos: {Dividendo.objects.count()}")
        self.stdout.write(f"Notificaciones: {Notificacion.objects.count()}")
        
        self.stdout.write(self.style.SUCCESS('\n🔑 CREDENCIALES DE ACCESO:'))
        self.stdout.write('   Admin:    usuario: admin    | password: admin123')
        self.stdout.write('   Gerente:  usuario: gerente  | password: gerente123')
        self.stdout.write('   Cajero:   usuario: cajero   | password: cajero123')
        self.stdout.write('   Socios:   usuario: socio1-3 | password: socio123')
        
        self.stdout.write(self.style.SUCCESS('\n📧 Emails usados:'))
        self.stdout.write('   Admin:   testmicorreo2025+admin@gmail.com')
        self.stdout.write('   Gerente: testmicorreo2025+gerente@gmail.com')
        self.stdout.write('   Cajero:  testmicorreo2025+cajero@gmail.com')
        self.stdout.write('   Socios:  testmicorreo2025+1@gmail.com hasta +8@gmail.com')
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))