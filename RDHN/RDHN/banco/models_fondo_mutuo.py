from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from core.models import Socio, Usuario, CatEstado, BitacoraAuditoria
from django.core.exceptions import ValidationError


# =========================
# FONDO MUTUO
# =========================

class FondoMutuo(models.Model):
    """
    Fondo de ayuda mutua por período mensual
    Formato período: YYYYMM (202401, 202402, etc.)
    """
    periodo = models.CharField(
        max_length=6,
        unique=True,
        db_index=True,
        validators=[
            RegexValidator(
                regex=r'^\d{6}$',
                message='El período debe tener formato YYYYMM (ejemplo: 202401)'
            )
        ],
        help_text="Formato: YYYYMM"
    )
    
    # Estado del período
    estado = models.ForeignKey(
        CatEstado,
        on_delete=models.PROTECT,
        related_name='fondos_mutuos',
        limit_choices_to={'dominio': 'FONDO_MUTUO'},
        help_text="ABIERTO/CERRADO"
    )
    
    # Totales del fondo
    total_ingresos = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total de aportes recibidos en el período"
    )
    
    total_egresos = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total de ayudas otorgadas en el período"
    )
    
    saldo_disponible = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Saldo disponible para ayudas"
    )
    
    # Fechas de control
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    fecha_cierre = models.DateField(null=True, blank=True)
    
    # Auditoría
    cerrado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='fondos_cerrados',
        null=True,
        blank=True
    )
    observaciones = models.TextField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "FONDO_MUTUO"
        verbose_name = "Fondo Mutuo"
        verbose_name_plural = "Fondos Mutuos"
        ordering = ['-periodo']
        constraints = [
            models.CheckConstraint(
                check=models.Q(saldo_disponible__gte=0),
                name="chk_fondo_saldo_no_negativo"
            ),
            models.CheckConstraint(
                check=models.Q(fecha_fin__gt=models.F('fecha_inicio')),
                name="chk_fondo_fechas_validas"
            ),
            models.CheckConstraint(
                check=models.Q(
                    saldo_disponible=models.F('total_ingresos') - models.F('total_egresos')
                ),
                name="chk_fondo_saldo_correcto"
            ),
        ]
        indexes = [
            models.Index(fields=['periodo']),
            models.Index(fields=['estado']),
            models.Index(fields=['-fecha_inicio']),
        ]
    
    def __str__(self):
        año = self.periodo[:4]
        mes = self.periodo[4:]
        return f"Fondo Mutuo {mes}/{año}"
    
    def clean(self):
        """Validaciones adicionales"""
        super().clean()
        
        # Validar formato de período
        if len(self.periodo) != 6:
            raise ValidationError({
                'periodo': 'El período debe tener 6 dígitos (YYYYMM)'
            })
        
        try:
            año = int(self.periodo[:4])
            mes = int(self.periodo[4:])
            
            if año < 2000 or año > 2100:
                raise ValidationError({
                    'periodo': 'El año debe estar entre 2000 y 2100'
                })
            
            if mes < 1 or mes > 12:
                raise ValidationError({
                    'periodo': 'El mes debe estar entre 01 y 12'
                })
        except ValueError:
            raise ValidationError({
                'periodo': 'El período debe contener solo dígitos'
            })
    
    def esta_abierto(self):
        """Verifica si el fondo está abierto para operaciones"""
        return self.estado.codigo == 'ABIERTO'
    
    def actualizar_saldo(self):
        """Actualiza el saldo disponible basado en los movimientos"""
        movimientos = self.movimientos.aggregate(
            ingresos=models.Sum('monto', filter=models.Q(origen='INGRESO')),
            egresos=models.Sum('monto', filter=models.Q(origen='EGRESO'))
        )
        
        self.total_ingresos = movimientos['ingresos'] or Decimal('0.00')
        self.total_egresos = movimientos['egresos'] or Decimal('0.00')
        self.saldo_disponible = self.total_ingresos - self.total_egresos
        self.save(update_fields=['total_ingresos', 'total_egresos', 'saldo_disponible', 'actualizado_en'])
    
    @classmethod
    def get_periodo_actual(cls):
        """Obtiene el fondo del período actual (mes actual)"""
        hoy = timezone.now().date()
        periodo = hoy.strftime('%Y%m')
        
        try:
            return cls.objects.get(periodo=periodo)
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def crear_periodo_actual(cls, usuario=None):
        """Crea automáticamente el fondo para el período actual"""
        from dateutil.relativedelta import relativedelta
        
        hoy = timezone.now().date()
        periodo = hoy.strftime('%Y%m')
        
        # Verificar si ya existe
        if cls.objects.filter(periodo=periodo).exists():
            raise ValidationError(f'Ya existe un fondo para el período {periodo}')
        
        # Obtener estado ABIERTO
        try:
            estado_abierto = CatEstado.objects.get(dominio='FONDO_MUTUO', codigo='ABIERTO')
        except CatEstado.DoesNotExist:
            raise ValidationError('No existe el estado ABIERTO para FONDO_MUTUO')
        
        # Calcular fecha inicio y fin del mes
        fecha_inicio = hoy.replace(day=1)
        fecha_fin = (fecha_inicio + relativedelta(months=1)) - relativedelta(days=1)
        
        # Crear el fondo
        fondo = cls.objects.create(
            periodo=periodo,
            estado=estado_abierto,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            observaciones=f"Fondo creado automáticamente para {periodo}"
        )
        
        # Registrar en auditoría
        if usuario:
            BitacoraAuditoria.objects.create(
                usuario=usuario,
                accion='CREAR',
                tabla_afectada='FONDO_MUTUO',
                id_registro=str(fondo.id),
                descripcion=f"Creación de fondo mutuo para período {periodo}"
            )
        
        return fondo


class MovimientoFondoMutuo(models.Model):
    """
    Kardex del fondo mutuo - Registro de todos los movimientos
    """
    ORIGEN_CHOICES = [
        ('INGRESO', 'Ingreso/Aporte'),
        ('EGRESO', 'Egreso/Ayuda'),
        ('AJUSTE', 'Ajuste'),
        ('CIERRE', 'Cierre de Período'),
        ('APERTURA', 'Saldo de Apertura'),
    ]
    
    TIPO_APORTE_CHOICES = [
        ('MENSUAL', 'Aporte Mensual'),
        ('EXTRAORDINARIO', 'Aporte Extraordinario'),
        ('DONACION', 'Donación'),
    ]
    
    fondo = models.ForeignKey(
        FondoMutuo,
        on_delete=models.PROTECT,
        related_name='movimientos'
    )
    
    socio = models.ForeignKey(
        Socio,
        on_delete=models.PROTECT,
        related_name='movimientos_fondo',
        null=True,
        blank=True,
        help_text="Socio que realiza el aporte o recibe la ayuda"
    )
    
    origen = models.CharField(
        max_length=20,
        choices=ORIGEN_CHOICES,
        db_index=True
    )
    
    tipo_aporte = models.CharField(
        max_length=20,
        choices=TIPO_APORTE_CHOICES,
        null=True,
        blank=True,
        help_text="Aplica solo para INGRESOS"
    )
    
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Saldos para llevar el kardex
    saldo_anterior = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    saldo_nuevo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    concepto = models.CharField(max_length=200)
    observaciones = models.TextField(null=True, blank=True)
    
    # Referencia a transacción del libro diario
    transaccion = models.ForeignKey(
        'banco.Transaccion',
        on_delete=models.PROTECT,
        related_name='movimientos_fondo',
        null=True,
        blank=True
    )
    
    # Referencia a solicitud de ayuda
    solicitud_ayuda = models.ForeignKey(
        'SolicitudAyudaMutua',
        on_delete=models.PROTECT,
        related_name='movimientos',
        null=True,
        blank=True
    )
    
    numero_movimiento = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Número único del movimiento para comprobante"
    )
    
    fecha_movimiento = models.DateTimeField(default=timezone.now, db_index=True)
    realizado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='movimientos_fondo_realizados'
    )
    
    creado_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "MOVIMIENTO_FONDO_MUTUO"
        verbose_name = "Movimiento de Fondo Mutuo"
        verbose_name_plural = "Movimientos de Fondo Mutuo"
        ordering = ['-fecha_movimiento']
        constraints = [
            models.CheckConstraint(
                check=models.Q(monto__gt=0),
                name="chk_movimiento_monto_positivo"
            ),
            models.CheckConstraint(
                check=models.Q(saldo_anterior__gte=0) & models.Q(saldo_nuevo__gte=0),
                name="chk_movimiento_saldos_no_negativos"
            ),
        ]
        indexes = [
            models.Index(fields=['fondo', '-fecha_movimiento']),
            models.Index(fields=['socio', '-fecha_movimiento']),
            models.Index(fields=['origen', '-fecha_movimiento']),
            models.Index(fields=['numero_movimiento']),
            models.Index(fields=['-fecha_movimiento']),
        ]
    
    def __str__(self):
        return f"{self.numero_movimiento} - {self.origen} - L. {self.monto}"
    
    def clean(self):
        """Validaciones del movimiento"""
        super().clean()
        
        # Si es ingreso, debe tener tipo_aporte
        if self.origen == 'INGRESO' and not self.tipo_aporte:
            raise ValidationError({
                'tipo_aporte': 'Los ingresos deben tener un tipo de aporte'
            })
        
        # Si es ingreso o egreso, debe tener socio
        if self.origen in ['INGRESO', 'EGRESO'] and not self.socio:
            raise ValidationError({
                'socio': 'Los ingresos y egresos deben tener un socio asociado'
            })
    
    @classmethod
    def generar_numero_movimiento(cls):
        """Genera un número único para el movimiento"""
        import random
        while True:
            fecha = timezone.now().strftime('%Y%m%d')
            aleatorio = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            numero = f"FM-{fecha}-{aleatorio}"
            
            if not cls.objects.filter(numero_movimiento=numero).exists():
                return numero


class SolicitudAyudaMutua(models.Model):
    """
    Solicitudes de ayuda del fondo mutuo
    """
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_REVISION', 'En Revisión'),
        ('APROBADA', 'Aprobada'),
        ('RECHAZADA', 'Rechazada'),
        ('DESEMBOLSADA', 'Desembolsada'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    TIPO_AYUDA_CHOICES = [
        ('EMERGENCIA_MEDICA', 'Emergencia Médica'),
        ('FALLECIMIENTO', 'Fallecimiento de Familiar'),
        ('CALAMIDAD', 'Calamidad Doméstica'),
        ('OTRA', 'Otra'),
    ]
    
    socio = models.ForeignKey(
        Socio,
        on_delete=models.PROTECT,
        related_name='solicitudes_ayuda'
    )
    
    fondo = models.ForeignKey(
        FondoMutuo,
        on_delete=models.PROTECT,
        related_name='solicitudes',
        help_text="Fondo del período en que se solicita"
    )
    
    numero_solicitud = models.CharField(
        max_length=20,
        unique=True,
        db_index=True
    )
    
    tipo_ayuda = models.CharField(
        max_length=30,
        choices=TIPO_AYUDA_CHOICES,
        db_index=True
    )
    
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
    
    justificacion = models.TextField(
        help_text="Explique detalladamente el motivo de la solicitud"
    )
    
    # Documentos de soporte
    documento_soporte = models.FileField(
        upload_to='solicitudes_ayuda/documentos/',
        null=True,
        blank=True,
        help_text="Documento que respalde la solicitud (recibo médico, acta de defunción, etc.)"
    )
    
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        db_index=True
    )
    
    # Fechas
    fecha_solicitud = models.DateField(default=timezone.now)
    fecha_revision = models.DateField(null=True, blank=True)
    fecha_desembolso = models.DateField(null=True, blank=True)
    
    # Aprobación/Rechazo
    revisado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='solicitudes_revisadas',
        null=True,
        blank=True
    )
    
    comentarios_revision = models.TextField(
        null=True,
        blank=True,
        help_text="Comentarios del supervisor sobre la decisión"
    )
    
    motivo_rechazo = models.TextField(
        null=True,
        blank=True
    )
    
    # Auditoría
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='solicitudes_ayuda_creadas',
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = "SOLICITUD_AYUDA_MUTUA"
        verbose_name = "Solicitud de Ayuda Mutua"
        verbose_name_plural = "Solicitudes de Ayuda Mutua"
        ordering = ['-fecha_solicitud']
        constraints = [
            models.CheckConstraint(
                check=models.Q(monto_solicitado__gt=0),
                name="chk_solicitud_monto_positivo"
            ),
            models.CheckConstraint(
                check=(
                    models.Q(monto_aprobado__isnull=True) |
                    models.Q(monto_aprobado__gt=0)
                ),
                name="chk_solicitud_monto_aprobado_positivo"
            ),
        ]
        indexes = [
            models.Index(fields=['socio', '-fecha_solicitud']),
            models.Index(fields=['fondo', 'estado']),
            models.Index(fields=['estado', '-fecha_solicitud']),
            models.Index(fields=['numero_solicitud']),
            models.Index(fields=['-fecha_solicitud']),
        ]
    
    def __str__(self):
        return f"{self.numero_solicitud} - {self.socio.nombre_completo} - L. {self.monto_solicitado}"
    
    def clean(self):
        """Validaciones de la solicitud"""
        super().clean()
        
        # Validar que el socio esté activo
        if not self.socio.esta_activo:
            raise ValidationError({
                'socio': 'El socio debe estar ACTIVO para solicitar ayuda'
            })
        
        # Validar antigüedad mínima (6 meses)
        if self.socio.meses_antiguedad < 6:
            raise ValidationError({
                'socio': f'El socio debe tener al menos 6 meses de antigüedad. '
                        f'Antigüedad actual: {self.socio.meses_antiguedad} meses'
            })
        
        # Validar que el fondo esté abierto
        if not self.fondo.esta_abierto():
            raise ValidationError({
                'fondo': 'El fondo debe estar ABIERTO para aceptar solicitudes'
            })
        
        # Validar límite máximo según parámetros
        from core.models import ParametroSistema
        try:
            param = ParametroSistema.objects.get(
                modulo='FONDO_MUTUO',
                nombre_parametro='MONTO_MAXIMO_AYUDA',
                activo=True
            )
            monto_maximo = param.get_valor()
            
            if self.monto_solicitado > monto_maximo:
                raise ValidationError({
                    'monto_solicitado': f'El monto máximo de ayuda es L. {monto_maximo}'
                })
        except ParametroSistema.DoesNotExist:
            pass  # Si no existe el parámetro, no se valida
    
    @classmethod
    def generar_numero_solicitud(cls):
        """Genera un número único para la solicitud"""
        import random
        while True:
            fecha = timezone.now().strftime('%Y%m%d')
            aleatorio = ''.join([str(random.randint(0, 9)) for _ in range(5)])
            numero = f"SA-{fecha}-{aleatorio}"
            
            if not cls.objects.filter(numero_solicitud=numero).exists():
                return numero
    
    def aprobar(self, monto_aprobado, usuario, comentarios=None):
        """Aprueba la solicitud y genera el egreso del fondo"""
        from django.db import transaction
        
        if self.estado not in ['PENDIENTE', 'EN_REVISION']:
            raise ValidationError('Solo se pueden aprobar solicitudes PENDIENTES o EN_REVISION')
        
        # Validar que haya saldo disponible
        if self.fondo.saldo_disponible < monto_aprobado:
            raise ValidationError(
                f'Saldo insuficiente en el fondo. Disponible: L. {self.fondo.saldo_disponible}'
            )
        
        with transaction.atomic():
            # Actualizar solicitud
            self.estado = 'APROBADA'
            self.monto_aprobado = monto_aprobado
            self.fecha_revision = timezone.now().date()
            self.revisado_por = usuario
            self.comentarios_revision = comentarios
            self.save()
            
            # Registrar movimiento de egreso
            saldo_anterior = self.fondo.saldo_disponible
            saldo_nuevo = saldo_anterior - monto_aprobado
            
            movimiento = MovimientoFondoMutuo.objects.create(
                fondo=self.fondo,
                socio=self.socio,
                origen='EGRESO',
                monto=monto_aprobado,
                saldo_anterior=saldo_anterior,
                saldo_nuevo=saldo_nuevo,
                concepto=f"Ayuda mutua aprobada - {self.get_tipo_ayuda_display()}",
                observaciones=f"Solicitud {self.numero_solicitud}",
                solicitud_ayuda=self,
                numero_movimiento=MovimientoFondoMutuo.generar_numero_movimiento(),
                realizado_por=usuario
            )
            
            # Actualizar saldo del fondo
            self.fondo.actualizar_saldo()
            
            # Registrar en auditoría
            BitacoraAuditoria.objects.create(
                usuario=usuario,
                accion='APROBAR',
                tabla_afectada='SOLICITUD_AYUDA_MUTUA',
                id_registro=str(self.id),
                descripcion=f"Aprobación de solicitud {self.numero_solicitud} por L. {monto_aprobado}"
            )
            
            return movimiento
    
    def rechazar(self, motivo, usuario):
        """Rechaza la solicitud"""
        if self.estado not in ['PENDIENTE', 'EN_REVISION']:
            raise ValidationError('Solo se pueden rechazar solicitudes PENDIENTES o EN_REVISION')
        
        self.estado = 'RECHAZADA'
        self.fecha_revision = timezone.now().date()
        self.revisado_por = usuario
        self.motivo_rechazo = motivo
        self.save()
        
        # Registrar en auditoría
        BitacoraAuditoria.objects.create(
            usuario=usuario,
            accion='RECHAZAR',
            tabla_afectada='SOLICITUD_AYUDA_MUTUA',
            id_registro=str(self.id),
            descripcion=f"Rechazo de solicitud {self.numero_solicitud}. Motivo: {motivo}"
        )