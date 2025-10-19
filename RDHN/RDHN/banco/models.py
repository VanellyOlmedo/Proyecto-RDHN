from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from core.models import Socio, Usuario, CatEstado
from dateutil.relativedelta import relativedelta


# =========================
# CATÁLOGOS
# =========================

class TipoCuenta(models.Model):
    """Tipos de cuentas de ahorro"""
    FIJO = 'FIJO'
    VOLUNTARIO = 'VOLUNTARIO'
    PERSONAL = 'PERSONAL'
    
    TIPOS = [
        (FIJO, 'Ahorro Fijo'),
        (VOLUNTARIO, 'Ahorro Voluntario'),
        (PERSONAL, 'Ahorro Personal (Retirable)'),
    ]
    
    codigo = models.CharField(max_length=20, choices=TIPOS, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(null=True, blank=True)
    tasa_interes_anual = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        default=Decimal('5.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Tasa de interés anual en porcentaje"
    )
    periodicidad_capitalizacion = models.CharField(
        max_length=20,
        choices=[
            ('MENSUAL', 'Mensual'),
            ('TRIMESTRAL', 'Trimestral'),
            ('SEMESTRAL', 'Semestral'),
            ('ANUAL', 'Anual'),
        ],
        default='MENSUAL',
        help_text="Periodicidad con la que se capitaliza el interés"
    )
    monto_minimo = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    es_retirable = models.BooleanField(default=False)
    requiere_deduccion_planilla = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "TIPO_CUENTA"
        verbose_name = "Tipo de Cuenta"
        verbose_name_plural = "Tipos de Cuenta"
        constraints = [
            models.CheckConstraint(
                check=models.Q(tasa_interes_anual__gte=0),
                name="chk_tipo_cuenta_tasa_positiva"
            ),
            models.CheckConstraint(
                check=models.Q(monto_minimo__gte=0),
                name="chk_tipo_cuenta_monto_minimo_positivo"
            ),
        ]
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['activo']),
        ]
    
    def __str__(self):
        return self.nombre


class TipoPrestamo(models.Model):
    """Tipos de préstamos"""
    PERSONAL = 'PERSONAL'
    EMERGENCIA = 'EMERGENCIA'
    
    TIPOS = [
        (PERSONAL, 'Préstamo Personal'),
        (EMERGENCIA, 'Préstamo de Emergencia'),
    ]
    
    codigo = models.CharField(max_length=20, choices=TIPOS, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(null=True, blank=True)
    tasa_interes_anual = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('15.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Tasa de interés anual en porcentaje"
    )
    multiplicador_ahorro = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('3.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Múltiplo del ahorro fijo para préstamo sin garantes"
    )
    plazo_minimo_meses = models.IntegerField(
        default=6,
        validators=[MinValueValidator(1)]
    )
    plazo_maximo_meses = models.IntegerField(
        default=24,
        validators=[MinValueValidator(1)]
    )
    requiere_garantes = models.BooleanField(default=False)
    cantidad_garantes = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "TIPO_PRESTAMO"
        verbose_name = "Tipo de Préstamo"
        verbose_name_plural = "Tipos de Préstamo"
        constraints = [
            models.CheckConstraint(
                check=models.Q(tasa_interes_anual__gte=0),
                name="chk_tipo_prestamo_tasa_positiva"
            ),
            models.CheckConstraint(
                check=models.Q(plazo_minimo_meses__lte=models.F('plazo_maximo_meses')),
                name="chk_tipo_prestamo_plazo_valido"
            ),
            models.CheckConstraint(
                check=models.Q(cantidad_garantes__gte=0),
                name="chk_tipo_prestamo_garantes_no_negativo"
            ),
        ]
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['activo']),
        ]
    
    def __str__(self):
        return self.nombre


# =========================
# CUENTAS DE AHORRO
# =========================

class CuentaAhorro(models.Model):
    """Cuenta de ahorro del socio"""
    socio = models.ForeignKey(Socio, on_delete=models.PROTECT, related_name='cuentas_ahorro')
    tipo_cuenta = models.ForeignKey(TipoCuenta, on_delete=models.PROTECT)
    numero_cuenta = models.CharField(max_length=20, unique=True, db_index=True)
    
    saldo_actual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Para ahorros fijos por planilla
    monto_deduccion_planilla = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Monto a deducir de planilla mensualmente"
    )
    
    fecha_apertura = models.DateField(default=timezone.now)
    fecha_cierre = models.DateField(null=True, blank=True)
    
    estado = models.ForeignKey(
        CatEstado,
        on_delete=models.PROTECT,
        related_name='cuentas_ahorro',
        limit_choices_to={'dominio': 'CUENTA_AHORRO'}
    )
    
    observaciones = models.TextField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    # Campos de auditoría
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='cuentas_creadas',
        null=True,
        blank=True
    )
    actualizado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='cuentas_actualizadas',
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = "CUENTA_AHORRO"
        verbose_name = "Cuenta de Ahorro"
        verbose_name_plural = "Cuentas de Ahorro"
        constraints = [
            # Una sola cuenta activa por tipo y socio
            models.UniqueConstraint(
                fields=['socio', 'tipo_cuenta'],
                condition=models.Q(fecha_cierre__isnull=True),
                name='uq_cuenta_activa_por_tipo_socio'
            ),
            models.CheckConstraint(
                check=models.Q(saldo_actual__gte=0),
                name="chk_cuenta_saldo_no_negativo"
            ),
            models.CheckConstraint(
                check=(
                    models.Q(fecha_cierre__isnull=True) | 
                    models.Q(fecha_cierre__gte=models.F('fecha_apertura'))
                ),
                name="chk_cuenta_fecha_cierre_valida"
            ),
        ]
        indexes = [
            models.Index(fields=['socio', 'tipo_cuenta']),
            models.Index(fields=['numero_cuenta']),
            models.Index(fields=['estado', 'fecha_cierre']),
            models.Index(fields=['-creado_en']),
        ]
    
    def __str__(self):
        return f"{self.numero_cuenta} - {self.socio.nombre_completo} ({self.tipo_cuenta.nombre})"
    
    def depositar(self, monto, descripcion="Depósito", usuario=None):
        """Realiza un depósito en la cuenta - DEBE EJECUTARSE EN TRANSACCIÓN"""
        monto = Decimal(str(monto))
        if monto <= 0:
            raise ValueError("El monto debe ser mayor a cero")
        
        saldo_anterior = self.saldo_actual
        self.saldo_actual += monto
        self.actualizado_por = usuario
        self.save(update_fields=['saldo_actual', 'actualizado_en', 'actualizado_por'])
        
        # Registrar transacción
        Transaccion.objects.create(
            cuenta_ahorro=self,
            tipo_transaccion='DEPOSITO',
            monto=monto,
            saldo_anterior=saldo_anterior,
            saldo_nuevo=self.saldo_actual,
            descripcion=descripcion,
            realizado_por=usuario
        )
        
        return self.saldo_actual
    
    def retirar(self, monto, descripcion="Retiro", usuario=None):
        """Realiza un retiro de la cuenta - DEBE EJECUTARSE EN TRANSACCIÓN"""
        monto = Decimal(str(monto))
        
        if monto <= 0:
            raise ValueError("El monto debe ser mayor a cero")
        
        if not self.tipo_cuenta.es_retirable and not self.fecha_cierre:
            raise ValueError("Esta cuenta no permite retiros")
        
        if self.saldo_actual < monto:
            raise ValueError(
                f"Saldo insuficiente. Disponible: L. {self.saldo_actual}"
            )
        
        saldo_anterior = self.saldo_actual
        self.saldo_actual -= monto
        self.actualizado_por = usuario
        self.save(update_fields=['saldo_actual', 'actualizado_en', 'actualizado_por'])
        
        # Registrar transacción
        Transaccion.objects.create(
            cuenta_ahorro=self,
            tipo_transaccion='RETIRO',
            monto=monto,
            saldo_anterior=saldo_anterior,
            saldo_nuevo=self.saldo_actual,
            descripcion=descripcion,
            realizado_por=usuario
        )
        
        return self.saldo_actual
    
    def calcular_interes(self, fecha_calculo=None):
        """Calcula el interés generado según la tasa y periodicidad"""
        if not fecha_calculo:
            fecha_calculo = timezone.now().date()
        
        # Implementar cálculo de interés según periodicidad
        pass


# =========================
# TRANSACCIONES
# =========================

class Transaccion(models.Model):
    """Libro de transacciones del banco"""
    TIPO_CHOICES = [
        ('DEPOSITO', 'Depósito'),
        ('RETIRO', 'Retiro'),
        ('INTERES', 'Interés Generado'),
        ('PAGO_PRESTAMO', 'Pago de Préstamo'),
        ('DESEMBOLSO_PRESTAMO', 'Desembolso de Préstamo'),
        ('DIVIDENDO', 'Dividendo'),
        ('AJUSTE', 'Ajuste'),
        ('REVERSO', 'Reverso'),
    ]
    
    cuenta_ahorro = models.ForeignKey(
        CuentaAhorro,
        on_delete=models.PROTECT,
        related_name='transacciones',
        null=True,
        blank=True
    )
    prestamo = models.ForeignKey(
        'Prestamo',
        on_delete=models.PROTECT,
        related_name='transacciones',
        null=True,
        blank=True
    )
    
    tipo_transaccion = models.CharField(max_length=20, choices=TIPO_CHOICES, db_index=True)
    monto = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    saldo_anterior = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    saldo_nuevo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    descripcion = models.TextField()
    numero_recibo = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    
    # Estado de la transacción
    estado = models.ForeignKey(
        CatEstado,
        on_delete=models.PROTECT,
        related_name='transacciones',
        limit_choices_to={'dominio': 'TRANSACCION'},
        null=True,
        blank=True
    )
    
    # Referencia a transacción reversada
    transaccion_reversada = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        related_name='reversos',
        null=True,
        blank=True
    )
    
    fecha_transaccion = models.DateTimeField(default=timezone.now, db_index=True)
    realizado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='transacciones_realizadas',
        null=True,
        blank=True
    )
    
    creado_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "TRANSACCION"
        verbose_name = "Transacción"
        verbose_name_plural = "Transacciones"
        ordering = ['-fecha_transaccion']
        constraints = [
            # XOR: Debe tener cuenta_ahorro O prestamo, pero no ambos
            models.CheckConstraint(
                check=(
                    models.Q(cuenta_ahorro__isnull=False, prestamo__isnull=True) |
                    models.Q(cuenta_ahorro__isnull=True, prestamo__isnull=False)
                ),
                name="chk_transaccion_origen_xor"
            ),
            models.CheckConstraint(
                check=models.Q(monto__gt=0),
                name="chk_transaccion_monto_positivo"
            ),
            # Saldo nuevo no puede ser negativo para cuentas
            models.CheckConstraint(
                check=(
                    models.Q(cuenta_ahorro__isnull=True) |
                    models.Q(saldo_nuevo__gte=0)
                ),
                name="chk_transaccion_saldo_no_negativo"
            ),
        ]
        indexes = [
            models.Index(fields=['cuenta_ahorro', '-fecha_transaccion']),
            models.Index(fields=['prestamo', '-fecha_transaccion']),
            models.Index(fields=['tipo_transaccion', '-fecha_transaccion']),
            models.Index(fields=['estado', '-fecha_transaccion']),
            models.Index(fields=['numero_recibo']),
            models.Index(fields=['-fecha_transaccion']),
        ]
    
    def __str__(self):
        return f"{self.tipo_transaccion} - L. {self.monto} - {self.fecha_transaccion.strftime('%d/%m/%Y')}"


# =========================
# PRÉSTAMOS
# =========================

class Prestamo(models.Model):
    """Préstamo otorgado a un socio"""
    ESTADO_CHOICES = [
        ('SOLICITADO', 'Solicitado'),
        ('EN_REVISION', 'En Revisión'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
        ('DESEMBOLSADO', 'Desembolsado'),
        ('EN_PAGO', 'En Pago'),
        ('PAGADO', 'Pagado'),
        ('VENCIDO', 'Vencido'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    socio = models.ForeignKey(Socio, on_delete=models.PROTECT, related_name='prestamos')
    tipo_prestamo = models.ForeignKey(TipoPrestamo, on_delete=models.PROTECT)
    numero_prestamo = models.CharField(max_length=20, unique=True, db_index=True)
    
    monto_solicitado = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    monto_aprobado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    tasa_interes = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Tasa de interés anual"
    )
    
    plazo_meses = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Plazo en meses"
    )
    cuota_mensual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    total_a_pagar = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    saldo_pendiente = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    fecha_solicitud = models.DateField(default=timezone.now)
    fecha_aprobacion = models.DateField(null=True, blank=True)
    fecha_desembolso = models.DateField(null=True, blank=True)
    fecha_primer_pago = models.DateField(null=True, blank=True)
    
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES, 
        default='SOLICITADO',
        db_index=True
    )
    
    # Deducción de planilla
    deducir_por_planilla = models.BooleanField(default=False)
    numero_planilla = models.CharField(max_length=50, null=True, blank=True)
    constancia_trabajo = models.FileField(
        upload_to='prestamos/constancias/',
        null=True,
        blank=True
    )
    
    observaciones = models.TextField(null=True, blank=True)
    
    aprobado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='prestamos_aprobados',
        null=True,
        blank=True
    )
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "PRESTAMO"
        verbose_name = "Préstamo"
        verbose_name_plural = "Préstamos"
        ordering = ['-fecha_solicitud']
        constraints = [
            models.CheckConstraint(
                check=models.Q(monto_solicitado__gt=0),
                name="chk_prestamo_monto_solicitado_positivo"
            ),
            models.CheckConstraint(
                check=(
                    models.Q(monto_aprobado__isnull=True) |
                    models.Q(monto_aprobado__gt=0)
                ),
                name="chk_prestamo_monto_aprobado_positivo"
            ),
            models.CheckConstraint(
                check=models.Q(plazo_meses__gte=1),
                name="chk_prestamo_plazo_minimo"
            ),
            models.CheckConstraint(
                check=models.Q(saldo_pendiente__gte=0),
                name="chk_prestamo_saldo_no_negativo"
            ),
            models.CheckConstraint(
                check=(
                    models.Q(fecha_aprobacion__isnull=True) |
                    models.Q(fecha_aprobacion__gte=models.F('fecha_solicitud'))
                ),
                name="chk_prestamo_fecha_aprobacion_valida"
            ),
        ]
        indexes = [
            models.Index(fields=['socio', 'estado']),
            models.Index(fields=['numero_prestamo']),
            models.Index(fields=['estado', '-fecha_solicitud']),
            models.Index(fields=['-fecha_solicitud']),
        ]
    
    def __str__(self):
        return f"{self.numero_prestamo} - {self.socio.nombre_completo} - L. {self.monto_solicitado}"
    
    def calcular_cuota(self):
        """Calcula la cuota mensual usando sistema francés"""
        if self.monto_aprobado and self.tasa_interes and self.plazo_meses:
            P = float(self.monto_aprobado)
            r = float(self.tasa_interes) / 100 / 12  # Tasa mensual
            n = self.plazo_meses
            
            if r > 0:
                cuota = P * (r * (1 + r)**n) / ((1 + r)**n - 1)
            else:
                cuota = P / n
            
            self.cuota_mensual = Decimal(str(round(cuota, 2)))
            self.total_a_pagar = self.cuota_mensual * n
            self.saldo_pendiente = self.total_a_pagar
    
    def generar_tabla_amortizacion(self):
        """Genera la tabla de amortización del préstamo"""
        if not self.cuota_mensual:
            self.calcular_cuota()
        
        if not self.fecha_primer_pago:
            raise ValueError(
                f"No se puede generar tabla de amortización para préstamo {self.numero_prestamo}: "
                "fecha_primer_pago es requerida"
            )
        
        # Eliminar cuotas existentes
        self.cuotas.all().delete()
        
        saldo = float(self.monto_aprobado)
        tasa_mensual = float(self.tasa_interes) / 100 / 12
        fecha_pago = self.fecha_primer_pago
        
        for i in range(1, self.plazo_meses + 1):
            interes = saldo * tasa_mensual
            capital = float(self.cuota_mensual) - interes
            saldo -= capital
            
            CuotaPrestamo.objects.create(
                prestamo=self,
                numero_cuota=i,
                monto_cuota=self.cuota_mensual,
                monto_capital=Decimal(str(round(capital, 2))),
                monto_interes=Decimal(str(round(interes, 2))),
                saldo_pendiente=Decimal(str(round(max(saldo, 0), 2))),
                fecha_vencimiento=fecha_pago
            )
            
            # Siguiente mes
            fecha_pago = fecha_pago + relativedelta(months=1)


class Garante(models.Model):
    """Garantes solidarios de un préstamo"""
    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name='garantes')
    socio_garante = models.ForeignKey(
        Socio,
        on_delete=models.PROTECT,
        related_name='prestamos_garantizados'
    )
    
    fecha_aceptacion = models.DateField(default=timezone.now)
    documento_garante = models.FileField(
        upload_to='prestamos/garantes/',
        null=True,
        blank=True
    )
    
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "GARANTE"
        verbose_name = "Garante"
        verbose_name_plural = "Garantes"
        unique_together = [['prestamo', 'socio_garante']]
        indexes = [
            models.Index(fields=['prestamo', 'activo']),
            models.Index(fields=['socio_garante', 'activo']),
        ]
    
    def __str__(self):
        return f"{self.socio_garante.nombre_completo} - Préstamo {self.prestamo.numero_prestamo}"


class CuotaPrestamo(models.Model):
    """Cuotas del préstamo (tabla de amortización)"""
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('PAGADA', 'Pagada'),
        ('VENCIDA', 'Vencida'),
        ('PAGADA_TARDE', 'Pagada con Retraso'),
    ]
    
    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name='cuotas')
    numero_cuota = models.IntegerField(validators=[MinValueValidator(1)])
    
    monto_cuota = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    monto_capital = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    monto_interes = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    monto_mora = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    saldo_pendiente = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    fecha_vencimiento = models.DateField(db_index=True)
    fecha_pago = models.DateField(null=True, blank=True)
    dias_mora = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES, 
        default='PENDIENTE',
        db_index=True
    )
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "CUOTA_PRESTAMO"
        verbose_name = "Cuota de Préstamo"
        verbose_name_plural = "Cuotas de Préstamos"
        ordering = ['prestamo', 'numero_cuota']
        unique_together = [['prestamo', 'numero_cuota']]
        constraints = [
            models.CheckConstraint(
                check=models.Q(monto_cuota__gte=0),
                name="chk_cuota_monto_no_negativo"
            ),
            models.CheckConstraint(
                check=models.Q(dias_mora__gte=0),
                name="chk_cuota_dias_mora_no_negativo"
            ),
        ]
        indexes = [
            models.Index(fields=['prestamo', 'estado']),
            models.Index(fields=['estado', 'fecha_vencimiento']),
            models.Index(fields=['fecha_vencimiento']),
        ]
    
    def __str__(self):
        return f"Cuota {self.numero_cuota} - {self.prestamo.numero_prestamo}"
    
    def calcular_mora(self, tasa_mora_diaria=Decimal('0.10')):
        """Calcula la mora si la cuota está vencida"""
        if self.estado == 'PENDIENTE' and self.fecha_vencimiento < timezone.now().date():
            self.dias_mora = (timezone.now().date() - self.fecha_vencimiento).days
            self.monto_mora = self.monto_cuota * (tasa_mora_diaria / 100) * self.dias_mora
            self.estado = 'VENCIDA'
            self.save(update_fields=['dias_mora', 'monto_mora', 'estado', 'actualizado_en'])


class PagoPrestamo(models.Model):
    """Registro de pagos realizados a préstamos"""
    prestamo = models.ForeignKey(Prestamo, on_delete=models.PROTECT, related_name='pagos')
    cuota = models.ForeignKey(
        CuotaPrestamo,
        on_delete=models.PROTECT,
        related_name='pagos',
        null=True,
        blank=True
    )
    
    monto_pagado = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    monto_capital = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    monto_interes = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    monto_mora = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    fecha_pago = models.DateField(default=timezone.now, db_index=True)
    numero_recibo = models.CharField(max_length=20, unique=True, db_index=True)
    
    metodo_pago = models.CharField(
        max_length=20,
        choices=[
            ('EFECTIVO', 'Efectivo'),
            ('TRANSFERENCIA', 'Transferencia'),
            ('PLANILLA', 'Deducción de Planilla'),
            ('CHEQUE', 'Cheque'),
        ],
        default='EFECTIVO'
    )
    
    observaciones = models.TextField(null=True, blank=True)
    realizado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='pagos_prestamos_procesados'
    )
    
    creado_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "PAGO_PRESTAMO"
        verbose_name = "Pago de Préstamo"
        verbose_name_plural = "Pagos de Préstamos"
        ordering = ['-fecha_pago']
        constraints = [
            models.CheckConstraint(
                check=models.Q(monto_pagado__gt=0),
                name="chk_pago_monto_positivo"
            ),
            models.CheckConstraint(
                check=(
                    models.Q(monto_capital__gte=0) &
                    models.Q(monto_interes__gte=0) &
                    models.Q(monto_mora__gte=0)
                ),
                name="chk_pago_componentes_no_negativos"
            ),
        ]
        indexes = [
            models.Index(fields=['prestamo', '-fecha_pago']),
            models.Index(fields=['numero_recibo']),
            models.Index(fields=['-fecha_pago']),
        ]
    
    def __str__(self):
        return f"Pago {self.numero_recibo} - L. {self.monto_pagado}"


# =========================
# DIVIDENDOS
# =========================

class PeriodoDividendo(models.Model):
    """Período de cálculo de dividendos"""
    año = models.IntegerField(
        unique=True,
        validators=[MinValueValidator(2000), MaxValueValidator(2100)]
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    
    total_intereses_generados = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    total_distribuido = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    fecha_distribucion = models.DateField(null=True, blank=True)
    estado = models.CharField(
        max_length=20,
        choices=[
            ('ABIERTO', 'Abierto'),
            ('CERRADO', 'Cerrado'),
            ('DISTRIBUIDO', 'Distribuido'),
        ],
        default='ABIERTO',
        db_index=True
    )
    
    cerrado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='periodos_cerrados',
        null=True,
        blank=True
    )
    fecha_cierre = models.DateField(null=True, blank=True)
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "PERIODO_DIVIDENDO"
        verbose_name = "Período de Dividendo"
        verbose_name_plural = "Períodos de Dividendos"
        ordering = ['-año']
        constraints = [
            models.CheckConstraint(
                check=models.Q(fecha_fin__gt=models.F('fecha_inicio')),
                name="chk_periodo_fechas_validas"
            ),
            models.CheckConstraint(
                check=models.Q(total_distribuido__lte=models.F('total_intereses_generados')),
                name="chk_periodo_distribucion_valida"
            ),
        ]
        indexes = [
            models.Index(fields=['año']),
            models.Index(fields=['estado']),
        ]
    
    def __str__(self):
        return f"Dividendos {self.año}"


class Dividendo(models.Model):
    """Dividendos distribuidos a socios"""
    periodo = models.ForeignKey(
        PeriodoDividendo, 
        on_delete=models.PROTECT, 
        related_name='dividendos'
    )
    socio = models.ForeignKey(Socio, on_delete=models.PROTECT, related_name='dividendos')
    
    saldo_promedio_fijo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Saldo promedio en cuenta fija durante el período"
    )
    
    cantidad_prestamos = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Cantidad de préstamos activos durante el año"
    )
    
    cumple_requisito = models.BooleanField(
        default=False,
        help_text="¿Cumplió con mínimo 2 préstamos?"
    )
    
    porcentaje_asignado = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="% del total de dividendos"
    )
    
    monto_dividendo = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    fecha_acreditacion = models.DateField(null=True, blank=True)
    acreditado = models.BooleanField(default=False)
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "DIVIDENDO"
        verbose_name = "Dividendo"
        verbose_name_plural = "Dividendos"
        unique_together = [['periodo', 'socio']]
        constraints = [
            models.CheckConstraint(
                check=models.Q(monto_dividendo__gte=0),
                name="chk_dividendo_monto_no_negativo"
            ),
            models.CheckConstraint(
                check=models.Q(cantidad_prestamos__gte=0),
                name="chk_dividendo_prestamos_no_negativo"
            ),
        ]
        indexes = [
            models.Index(fields=['periodo', 'socio']),
            models.Index(fields=['acreditado']),
        ]
    
    def __str__(self):
        return f"{self.socio.nombre_completo} - {self.periodo.año} - L. {self.monto_dividendo}"


# =========================
# NOTIFICACIONES
# =========================

class Notificacion(models.Model):
    """Notificaciones enviadas a socios"""
    TIPO_CHOICES = [
        ('CUOTA_PROXIMA', 'Cuota Próxima a Vencer'),
        ('CUOTA_VENCIDA', 'Cuota Vencida'),
        ('DEPOSITO', 'Depósito Realizado'),
        ('RETIRO', 'Retiro Realizado'),
        ('PAGO_PRESTAMO', 'Pago de Préstamo'),
        ('PRESTAMO_APROBADO', 'Préstamo Aprobado'),
        ('PRESTAMO_RECHAZADO', 'Préstamo Rechazado'),
        ('DIVIDENDO', 'Dividendo Acreditado'),
        ('ALERTA', 'Alerta General'),
    ]
    
    CANAL_CHOICES = [
        ('EMAIL', 'Email'),
        ('SMS', 'SMS'),
        ('NOTIFICACION_APP', 'Notificación en App'),
        ('WHATSAPP', 'WhatsApp'),
    ]
    
    PRIORIDAD_CHOICES = [
        ('BAJA', 'Baja'),
        ('NORMAL', 'Normal'),
        ('ALTA', 'Alta'),
        ('URGENTE', 'Urgente'),
    ]
    
    socio = models.ForeignKey(Socio, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, db_index=True)
    canal = models.CharField(
        max_length=20, 
        choices=CANAL_CHOICES, 
        default='EMAIL',
        db_index=True
    )
    prioridad = models.CharField(
        max_length=10,
        choices=PRIORIDAD_CHOICES,
        default='NORMAL',
        db_index=True
    )
    
    asunto = models.CharField(max_length=200)
    mensaje = models.TextField()
    
    estado = models.ForeignKey(
        CatEstado,
        on_delete=models.PROTECT,
        related_name='notificaciones',
        limit_choices_to={'dominio': 'NOTIFICACION'},
        null=True,
        blank=True
    )
    
    enviado = models.BooleanField(default=False, db_index=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    intentos = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    ultimo_error = models.TextField(null=True, blank=True)
    programada_para = models.DateTimeField(null=True, blank=True, db_index=True)
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "NOTIFICACION"
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ['-creado_en']
        constraints = [
            models.CheckConstraint(
                check=models.Q(intentos__gte=0) & models.Q(intentos__lte=10),
                name="chk_notificacion_intentos_validos"
            ),
        ]
        indexes = [
            models.Index(fields=['socio', '-creado_en']),
            models.Index(fields=['estado', 'programada_para']),
            models.Index(fields=['enviado', 'programada_para']),
            models.Index(fields=['tipo', '-creado_en']),
            models.Index(fields=['-creado_en']),
        ]
    
    def __str__(self):
        return f"{self.tipo} - {self.socio.nombre_completo}"
    

