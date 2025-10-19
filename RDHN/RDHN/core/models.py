from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, F
from django.core.validators import RegexValidator, MinValueValidator


# =========================
# CATÁLOGOS / ESTADOS MEJORADO
# =========================
class CatEstado(models.Model):
    """
    Catálogo unificado de estados por dominio
    Dominios: SOCIO, CUENTA_AHORRO, TRANSACCION, NOTIFICACION, USUARIO, PRESTAMO, FONDO_MUTUO, SOLICITUD_AYUDA
    """
    dominio = models.CharField(max_length=50, db_index=True)
    codigo = models.CharField(max_length=50, db_index=True)
    nombre = models.CharField(max_length=100)
    es_final = models.BooleanField(
        default=False,
        help_text="Indica si es un estado final (no permite más transiciones)"
    )
    orden = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Orden de visualización"
    )
    permite_transicion_a = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='transiciones_desde',
        help_text="Estados a los que puede transicionar"
    )

    class Meta:
        db_table = "CAT_ESTADO"
        unique_together = (("dominio", "codigo"),)
        indexes = [
            models.Index(fields=["dominio", "codigo"]),
            models.Index(fields=["dominio", "orden"]),
        ]
        verbose_name = "Estado"
        verbose_name_plural = "Estados"

    def __str__(self):
        return f"{self.dominio}:{self.codigo} - {self.nombre}"


# =========================
# SOCIOS MEJORADO
# =========================
class Socio(models.Model):
    numero_socio = models.CharField(max_length=20, unique=True, db_index=True)
    
    # Nombres y Apellidos
    primer_nombre = models.CharField(max_length=50)
    segundo_nombre = models.CharField(max_length=50, null=True, blank=True)
    primer_apellido = models.CharField(max_length=50)
    segundo_apellido = models.CharField(max_length=50, null=True, blank=True)
    
    # Identificación única
    identidad = models.CharField(
        max_length=15,  # Sin guiones, solo dígitos
        unique=True,
        db_index=True,
        validators=[
            RegexValidator(
                regex=r'^\d{13}$',
                message='La identidad debe tener exactamente 15 dígitos'
            )
        ]
    )
    
    # Datos de contacto (ahora en tabla relacionada SocioContacto)
    direccion = models.TextField(null=True, blank=True)
    
    # Fechas
    fecha_ingreso = models.DateField()
    fecha_egreso = models.DateField(null=True, blank=True)
    
    # Estado
    id_estado = models.ForeignKey(
        CatEstado,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='socios',
        limit_choices_to={'dominio': 'SOCIO'}
    )
    
    # Auditoría
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        'Usuario',
        on_delete=models.PROTECT,
        related_name='socios_creados',
        null=True,
        blank=True
    )

    class Meta:
        db_table = "SOCIO"
        verbose_name = "Socio"
        verbose_name_plural = "Socios"
        constraints = [
            models.CheckConstraint(
                check=Q(fecha_egreso__isnull=True) | Q(fecha_egreso__gte=F("fecha_ingreso")),
                name="chk_socio_fecha_egreso_ge_ingreso",
            ),
        ]
        indexes = [
            models.Index(fields=["numero_socio"]),
            models.Index(fields=["identidad"]),
            models.Index(fields=["id_estado"]),
            models.Index(fields=["-fecha_ingreso"]),
        ]

    def __str__(self):
        return f"{self.numero_socio} - {self.primer_nombre} {self.primer_apellido}"
    
    @property
    def nombre_completo(self):
        """Retorna el nombre completo del socio"""
        nombres = f"{self.primer_nombre} {self.segundo_nombre or ''}".strip()
        apellidos = f"{self.primer_apellido} {self.segundo_apellido or ''}".strip()
        return f"{nombres} {apellidos}"
    
    @property
    def esta_activo(self):
        """Verifica si el socio está activo"""
        return self.id_estado and self.id_estado.codigo == 'ACTIVO'
    
    @property
    def meses_antiguedad(self):
        """Calcula los meses de antigüedad del socio"""
        from dateutil.relativedelta import relativedelta
        hoy = timezone.now().date()
        fecha_referencia = self.fecha_egreso if self.fecha_egreso else hoy
        delta = relativedelta(fecha_referencia, self.fecha_ingreso)
        return delta.years * 12 + delta.months


class SocioContacto(models.Model):
    """Tabla de contactos del socio (mejora: múltiples contactos por tipo)"""
    class Tipo(models.TextChoices):
        TELEFONO = "TELEFONO", "Teléfono"
        CELULAR = "CELULAR", "Celular"
        EMAIL = "EMAIL", "Email"
        DIRECCION = "DIRECCION", "Dirección"

    socio = models.ForeignKey(Socio, on_delete=models.CASCADE, related_name="contactos")
    tipo = models.CharField(max_length=20, choices=Tipo.choices, db_index=True)
    valor = models.CharField(max_length=255)
    preferido = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "SOCIO_CONTACTO"
        verbose_name = "Contacto de Socio"
        verbose_name_plural = "Contactos de Socios"
        constraints = [
            # Solo un preferido por tipo y socio
            models.UniqueConstraint(
                fields=["socio", "tipo"],
                condition=Q(preferido=True, activo=True),
                name="uq_contacto_preferido_por_tipo",
            ),
        ]
        indexes = [
            models.Index(fields=['socio', 'tipo', 'activo']),
            models.Index(fields=['tipo', 'preferido']),
        ]

    def __str__(self):
        pref = " (preferido)" if self.preferido else ""
        return f"{self.socio} - {self.tipo}: {self.valor}{pref}"


class ExpedienteDigital(models.Model):
    # 1:1 con socio
    socio = models.OneToOneField(Socio, on_delete=models.CASCADE, related_name="expediente")
    numero_expediente = models.CharField(max_length=20, unique=True)
    fecha_creacion = models.DateField()
    observaciones = models.TextField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "EXPEDIENTE_DIGITAL"
        verbose_name = "Expediente Digital"
        verbose_name_plural = "Expedientes Digitales"

    def __str__(self):
        return f"Expediente {self.numero_expediente} — {self.socio}"


# =========================
# ROLES
# =========================
class Rol(models.Model):
    nombre_rol = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    estado = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ROLES"
        verbose_name = "Rol"
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.nombre_rol


# =========================
# USUARIOS - AUTENTICACIÓN MEJORADO
# =========================
class UsuarioManager(BaseUserManager):
    """Manager personalizado para el modelo Usuario"""
    
    def create_user(self, usuario, email, password=None, **extra_fields):
        """Crea y guarda un usuario regular"""
        if not email:
            raise ValueError('El usuario debe tener un email')
        if not usuario:
            raise ValueError('El usuario debe tener un nombre de usuario')
        
        email = self.normalize_email(email)
        user = self.model(usuario=usuario, email=email, **extra_fields)
        
        if password is None:
            password = 'TemporalPass'
            user.requiere_cambio_password = True
        
        user.set_password(password)
        user.password_updated_at = timezone.now()
        user.save(using=self._db)
        return user
    
    def create_superuser(self, usuario, email, password=None, **extra_fields):
        """Crea y guarda un superusuario"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('requiere_cambio_password', False)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser debe tener is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser debe tener is_superuser=True')
        
        return self.create_user(usuario, email, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Modelo de usuario personalizado - MEJORADO"""
    
    # Relación con Socio
    socio = models.OneToOneField(
        Socio, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name="usuario"
    )
    
    # Campos de autenticación
    usuario = models.CharField(
        max_length=50, 
        unique=True, 
        db_index=True,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9_]{4,}$',
                message='Usuario debe tener al menos 4 caracteres alfanuméricos o guión bajo'
            )
        ]
    )
    email = models.EmailField(max_length=100, unique=True, db_index=True)
    
    # Seguridad de contraseña - MEJORADO
    password_updated_at = models.DateTimeField(null=True, blank=True)
    password_expira_dias = models.IntegerField(
        default=90, 
        help_text="Días hasta que expire la contraseña",
        validators=[MinValueValidator(0)]
    )
    
    # Control de acceso - MEJORADO
    ultimo_acceso = models.DateTimeField(null=True, blank=True)
    intentos_fallidos = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    bloqueado_hasta = models.DateTimeField(null=True, blank=True, db_index=True)
    requiere_cambio_password = models.BooleanField(default=True)
    
    # Estado - MEJORADO
    id_estado = models.ForeignKey(
        CatEstado, 
        null=True, 
        blank=True, 
        on_delete=models.PROTECT,
        related_name='usuarios',
        limit_choices_to={'dominio': 'USUARIO'}
    )
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    is_staff = models.BooleanField(default=False, verbose_name="Es staff")
    
    # Tokens de recuperación
    token_recuperacion = models.CharField(max_length=100, null=True, blank=True)
    token_expira = models.DateTimeField(null=True, blank=True)
    
    # Auditoría
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    # Relaciones Many-to-Many
    roles = models.ManyToManyField(
        Rol,
        through='UsuarioRol',
        through_fields=('usuario', 'rol'),
        related_name='usuarios',
        blank=True
    )
    
    # Sobrescribir campos heredados de PermissionsMixin
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='grupos',
        blank=True,
        help_text='Los grupos a los que pertenece este usuario.',
        related_name='usuarios_custom',
        related_query_name='usuario_custom',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='permisos de usuario',
        blank=True,
        help_text='Permisos específicos para este usuario.',
        related_name='usuarios_custom',
        related_query_name='usuario_custom',
    )
    
    # 2FA
    two_factor_enabled = models.BooleanField(default=True, verbose_name="2FA Habilitado")
    two_factor_code = models.CharField(max_length=6, null=True, blank=True)
    two_factor_code_expira = models.DateTimeField(null=True, blank=True)
    
    # Configuración del modelo de usuario
    USERNAME_FIELD = 'usuario'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['email']
    
    objects = UsuarioManager()
    
    class Meta:
        db_table = "USUARIOS"
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        constraints = [
            models.CheckConstraint(
                check=Q(intentos_fallidos__gte=0),
                name="chk_intentos_no_negativo",
            ),
        ]
        indexes = [
            models.Index(fields=['usuario']),
            models.Index(fields=['email']),
            models.Index(fields=['is_active', 'is_staff']),
            models.Index(fields=['bloqueado_hasta']),
            models.Index(fields=['id_estado']),
        ]
    
    def generar_codigo_2fa(self):
        """Genera un código 2FA de 6 dígitos"""
        import random
        codigo = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        self.two_factor_code = codigo
        self.two_factor_code_expira = timezone.now() + timedelta(minutes=10)
        self.save(update_fields=['two_factor_code', 'two_factor_code_expira'])
        return codigo
    
    def validar_codigo_2fa(self, codigo):
        """Valida el código 2FA"""
        if not self.two_factor_code or not self.two_factor_code_expira:
            return False
        if self.two_factor_code_expira < timezone.now():
            return False
        return self.two_factor_code == codigo
    
    def limpiar_codigo_2fa(self):
        """Limpia el código 2FA después de usarlo"""
        self.two_factor_code = None
        self.two_factor_code_expira = None
        self.save(update_fields=['two_factor_code', 'two_factor_code_expira'])

    def __str__(self):
        return self.usuario
    
    def get_full_name(self):
        """Retorna el nombre completo del usuario"""
        if self.socio:
            return self.socio.nombre_completo
        return self.usuario
    
    def get_short_name(self):
        """Retorna el nombre corto del usuario"""
        if self.socio:
            return self.socio.primer_nombre
        return self.usuario
    
    @property
    def esta_bloqueado(self):
        """Verifica si el usuario está bloqueado"""
        if self.bloqueado_hasta and self.bloqueado_hasta > timezone.now():
            return True
        return False
    
    @property
    def password_expirado(self):
        """Verifica si la contraseña ha expirado"""
        if not self.password_updated_at:
            return True
        dias_transcurridos = (timezone.now() - self.password_updated_at).days
        return dias_transcurridos > self.password_expira_dias
    
    def bloquear_usuario(self, minutos=30):
        """Bloquea el usuario por X minutos"""
        self.bloqueado_hasta = timezone.now() + timedelta(minutes=minutos)
        self.save(update_fields=['bloqueado_hasta'])
    
    def desbloquear_usuario(self):
        """Desbloquea el usuario"""
        self.bloqueado_hasta = None
        self.intentos_fallidos = 0
        self.save(update_fields=['bloqueado_hasta', 'intentos_fallidos'])
    
    def registrar_intento_fallido(self, max_intentos=5):
        """Registra un intento fallido de login"""
        self.intentos_fallidos += 1
        if self.intentos_fallidos >= max_intentos:
            self.bloquear_usuario()
        else:
            self.save(update_fields=['intentos_fallidos'])
    
    def registrar_login_exitoso(self):
        """Registra un login exitoso"""
        self.ultimo_acceso = timezone.now()
        self.intentos_fallidos = 0
        self.save(update_fields=['ultimo_acceso', 'intentos_fallidos'])
    
    def generar_token_recuperacion(self):
        """Genera un token para recuperación de contraseña"""
        import secrets
        self.token_recuperacion = secrets.token_urlsafe(32)
        self.token_expira = timezone.now() + timedelta(hours=2)
        self.save(update_fields=['token_recuperacion', 'token_expira'])
        return self.token_recuperacion
    
    def validar_token_recuperacion(self, token):
        """Valida el token de recuperación"""
        if not self.token_recuperacion or not self.token_expira:
            return False
        if self.token_expira < timezone.now():
            return False
        return self.token_recuperacion == token
    
    def tiene_rol(self, nombre_rol):
        """Verifica si el usuario tiene un rol específico"""
        return self.roles.filter(nombre_rol=nombre_rol, estado=True).exists()
    
    def roles_activos(self):
        """Retorna los roles activos del usuario"""
        return self.roles.filter(estado=True)


class UsuarioRol(models.Model):
    """Tabla intermedia para la relación Usuario-Rol"""
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='usuario_roles'
    )
    rol = models.ForeignKey(
        Rol,
        on_delete=models.CASCADE,
        related_name='rol_usuarios'
    )
    fecha_asignacion = models.DateField(null=True)
    fecha_revocacion = models.DateField(null=True, blank=True)
    estado = models.BooleanField(default=True)
    asignado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="asignaciones_realizadas", 
        null=True, 
        blank=True
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "USUARIO_ROL"
        verbose_name = "Usuario-Rol"
        verbose_name_plural = "Usuarios-Roles"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "rol"],
                name="uq_usuario_rol_unico"
            ),
        ]
        indexes = [
            models.Index(fields=['usuario', 'estado']),
            models.Index(fields=['rol', 'estado']),
        ]

    def __str__(self):
        return f"{self.usuario} -> {self.rol}"


# =========================
# PARÁMETROS DEL SISTEMA - NUEVO
# =========================
class ParametroSistema(models.Model):
    """Parámetros configurables del sistema"""
    TIPO_DATO_CHOICES = [
        ('STRING', 'Texto'),
        ('INT', 'Entero'),
        ('DECIMAL', 'Decimal'),
        ('BOOL', 'Booleano'),
        ('JSON', 'JSON'),
    ]
    
    SCOPE_CHOICES = [
        ('GLOBAL', 'Global'),
        ('SOCIO', 'Por Socio'),
        ('MODULO', 'Por Módulo'),
    ]
    
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default='GLOBAL')
    modulo = models.CharField(max_length=50, db_index=True)
    nombre_parametro = models.CharField(max_length=100)
    tipo_dato = models.CharField(max_length=10, choices=TIPO_DATO_CHOICES, default='STRING')
    valor = models.TextField()
    descripcion = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='parametros_actualizados',
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = "PARAMETROS_SISTEMA"
        verbose_name = "Parámetro del Sistema"
        verbose_name_plural = "Parámetros del Sistema"
        unique_together = [['scope', 'nombre_parametro', 'modulo']]
        indexes = [
            models.Index(fields=['modulo', 'nombre_parametro']),
            models.Index(fields=['scope', 'activo']),
        ]
    
    def __str__(self):
        return f"{self.modulo}.{self.nombre_parametro}"
    
    def get_valor(self):
        """Retorna el valor parseado según el tipo de dato"""
        if self.tipo_dato == 'INT':
            return int(self.valor)
        elif self.tipo_dato == 'DECIMAL':
            from decimal import Decimal
            return Decimal(self.valor)
        elif self.tipo_dato == 'BOOL':
            return self.valor.lower() in ('true', '1', 'si', 'yes')
        elif self.tipo_dato == 'JSON':
            import json
            return json.loads(self.valor)
        return self.valor


# =========================
# BITÁCORA DE AUDITORÍA - NUEVO
# =========================
class BitacoraAuditoria(models.Model):
    """Registro de auditoría de todas las operaciones críticas"""
    ACCION_CHOICES = [
        ('CREAR', 'Crear'),
        ('EDITAR', 'Editar'),
        ('ELIMINAR', 'Eliminar'),
        ('APROBAR', 'Aprobar'),
        ('RECHAZAR', 'Rechazar'),
        ('REVERSAR', 'Reversar'),
        ('LOGIN', 'Inicio de Sesión'),
        ('LOGOUT', 'Cierre de Sesión'),
        ('CAMBIO_PASSWORD', 'Cambio de Contraseña'),
    ]
    
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='acciones_auditoria',
        null=True,
        blank=True
    )
    accion = models.CharField(max_length=50, choices=ACCION_CHOICES, db_index=True)
    tabla_afectada = models.CharField(max_length=100, db_index=True)
    id_registro = models.CharField(max_length=50, db_index=True)
    descripcion = models.TextField()
    datos_anteriores = models.JSONField(null=True, blank=True)
    datos_nuevos = models.JSONField(null=True, blank=True)
    
    # Información de la petición
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    request_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    
    fecha_hora = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = "BITACORA_AUDITORIA"
        verbose_name = "Bitácora de Auditoría"
        verbose_name_plural = "Bitácoras de Auditoría"
        ordering = ['-fecha_hora']
        indexes = [
            models.Index(fields=['tabla_afectada', 'id_registro']),
            models.Index(fields=['usuario', '-fecha_hora']),
            models.Index(fields=['accion', '-fecha_hora']),
            models.Index(fields=['-fecha_hora']),
        ]
    
    def __str__(self):
        return f"{self.accion} - {self.tabla_afectada} - {self.fecha_hora}"