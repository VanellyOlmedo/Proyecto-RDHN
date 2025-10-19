from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    TipoCuenta, TipoPrestamo, CuentaAhorro, Transaccion,
    Prestamo, Garante, CuotaPrestamo, PagoPrestamo,
    PeriodoDividendo, Dividendo, Notificacion
)


@admin.register(TipoCuenta)
class TipoCuentaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'tasa_interes_anual', 'monto_minimo', 'es_retirable', 'activo']
    list_filter = ['activo', 'es_retirable', 'requiere_deduccion_planilla']
    search_fields = ['nombre', 'codigo']
    ordering = ['codigo']


@admin.register(TipoPrestamo)
class TipoPrestamoAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 'nombre', 'tasa_interes_anual', 'multiplicador_ahorro',
        'plazo_maximo_meses', 'requiere_garantes', 'activo'
    ]
    list_filter = ['activo', 'requiere_garantes']
    search_fields = ['nombre', 'codigo']
    ordering = ['codigo']


@admin.register(CuentaAhorro)
class CuentaAhorroAdmin(admin.ModelAdmin):
    list_display = [
        'numero_cuenta', 'socio_link', 'tipo_cuenta', 'saldo_actual_formatted',
        'fecha_apertura', 'estado_cuenta'
    ]
    list_filter = ['tipo_cuenta', 'estado', 'fecha_apertura']
    search_fields = ['numero_cuenta', 'socio__numero_socio', 'socio__primer_nombre', 'socio__primer_apellido']
    readonly_fields = ['saldo_actual', 'creado_en', 'actualizado_en']
    date_hierarchy = 'fecha_apertura'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('socio', 'tipo_cuenta', 'numero_cuenta')
        }),
        ('Saldos', {
            'fields': ('saldo_actual', 'monto_deduccion_planilla')
        }),
        ('Fechas', {
            'fields': ('fecha_apertura', 'fecha_cierre')
        }),
        ('Estado y Observaciones', {
            'fields': ('estado', 'observaciones')
        }),
        ('Auditoría', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )
    
    def socio_link(self, obj):
        url = reverse('admin:core_socio_change', args=[obj.socio.id])
        return format_html('<a href="{}">{}</a>', url, obj.socio.nombre_completo)
    socio_link.short_description = 'Socio'
    
    def saldo_actual_formatted(self, obj):
        return format_html('<strong>L. {:,.2f}</strong>', obj.saldo_actual)
    saldo_actual_formatted.short_description = 'Saldo Actual'
    
    def estado_cuenta(self, obj):
        if obj.fecha_cierre:
            return format_html('<span style="color: red;">Cerrada</span>')
        return format_html('<span style="color: green;">Activa</span>')
    estado_cuenta.short_description = 'Estado'


@admin.register(Transaccion)
class TransaccionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'fecha_transaccion', 'tipo_transaccion', 'monto_formatted',
        'cuenta_ahorro', 'prestamo_link', 'realizado_por'
    ]
    list_filter = ['tipo_transaccion', 'fecha_transaccion']
    search_fields = ['descripcion', 'numero_recibo']
    readonly_fields = ['creado_en']
    date_hierarchy = 'fecha_transaccion'
    
    def monto_formatted(self, obj):
        color = 'green' if obj.tipo_transaccion in ['DEPOSITO', 'INTERES', 'DIVIDENDO'] else 'red'
        return format_html('<span style="color: {};">L. {:,.2f}</span>', color, obj.monto)
    monto_formatted.short_description = 'Monto'
    
    def prestamo_link(self, obj):
        if obj.prestamo:
            url = reverse('admin:banco_prestamo_change', args=[obj.prestamo.id])
            return format_html('<a href="{}">{}</a>', url, obj.prestamo.numero_prestamo)
        return '-'
    prestamo_link.short_description = 'Préstamo'


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = [
        'numero_prestamo', 'socio_link', 'tipo_prestamo', 'monto_aprobado_formatted',
        'saldo_pendiente_formatted', 'cuota_mensual_formatted', 'estado_badge',
        'fecha_solicitud'
    ]
    list_filter = ['estado', 'tipo_prestamo', 'fecha_solicitud', 'deducir_por_planilla']
    search_fields = [
        'numero_prestamo', 'socio__numero_socio', 
        'socio__primer_nombre', 'socio__primer_apellido'
    ]
    readonly_fields = [
        'numero_prestamo', 'cuota_mensual', 'total_a_pagar', 
        'saldo_pendiente', 'creado_en', 'actualizado_en'
    ]
    date_hierarchy = 'fecha_solicitud'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('socio', 'tipo_prestamo', 'numero_prestamo')
        }),
        ('Montos', {
            'fields': (
                'monto_solicitado', 'monto_aprobado', 'tasa_interes',
                'plazo_meses', 'cuota_mensual', 'total_a_pagar', 'saldo_pendiente'
            )
        }),
        ('Fechas', {
            'fields': (
                'fecha_solicitud', 'fecha_aprobacion', 'fecha_desembolso', 'fecha_primer_pago'
            )
        }),
        ('Planilla', {
            'fields': ('deducir_por_planilla', 'numero_planilla', 'constancia_trabajo')
        }),
        ('Estado y Aprobación', {
            'fields': ('estado', 'aprobado_por', 'observaciones')
        }),
        ('Auditoría', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )
    
    def socio_link(self, obj):
        url = reverse('admin:core_socio_change', args=[obj.socio.id])
        return format_html('<a href="{}">{}</a>', url, obj.socio.nombre_completo)
    socio_link.short_description = 'Socio'
    
    def monto_aprobado_formatted(self, obj):
        if obj.monto_aprobado:
            return format_html('<strong>L. {:,.2f}</strong>', obj.monto_aprobado)
        return '-'
    monto_aprobado_formatted.short_description = 'Monto Aprobado'
    
    def saldo_pendiente_formatted(self, obj):
        if obj.saldo_pendiente > 0:
            return format_html('<span style="color: red;">L. {:,.2f}</span>', obj.saldo_pendiente)
        return format_html('<span style="color: green;">L. 0.00</span>')
    saldo_pendiente_formatted.short_description = 'Saldo Pendiente'
    
    def cuota_mensual_formatted(self, obj):
        if obj.cuota_mensual:
            return format_html('L. {:,.2f}', obj.cuota_mensual)
        return '-'
    cuota_mensual_formatted.short_description = 'Cuota Mensual'
    
    def estado_badge(self, obj):
        colores = {
            'SOLICITADO': 'orange',
            'EN_REVISION': 'blue',
            'APROBADO': 'green',
            'RECHAZADO': 'red',
            'DESEMBOLSADO': 'purple',
            'EN_PAGO': 'teal',
            'PAGADO': 'darkgreen',
            'VENCIDO': 'darkred',
            'CANCELADO': 'gray'
        }
        color = colores.get(obj.estado, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'


class GaranteInline(admin.TabularInline):
    model = Garante
    extra = 0
    fields = ['socio_garante', 'fecha_aceptacion', 'activo']
    readonly_fields = ['fecha_aceptacion']


class CuotaPrestamoInline(admin.TabularInline):
    model = CuotaPrestamo
    extra = 0
    fields = [
        'numero_cuota', 'monto_cuota', 'fecha_vencimiento',
        'fecha_pago', 'estado', 'dias_mora', 'monto_mora'
    ]
    readonly_fields = ['dias_mora', 'monto_mora']
    can_delete = False


@admin.register(CuotaPrestamo)
class CuotaPrestamoAdmin(admin.ModelAdmin):
    list_display = [
        'prestamo_link', 'numero_cuota', 'monto_cuota_formatted',
        'fecha_vencimiento', 'fecha_pago', 'estado_badge', 'mora_formatted'
    ]
    list_filter = ['estado', 'fecha_vencimiento']
    search_fields = ['prestamo__numero_prestamo']
    readonly_fields = ['dias_mora', 'monto_mora']
    
    def prestamo_link(self, obj):
        url = reverse('admin:banco_prestamo_change', args=[obj.prestamo.id])
        return format_html('<a href="{}">{}</a>', url, obj.prestamo.numero_prestamo)
    prestamo_link.short_description = 'Préstamo'
    
    def monto_cuota_formatted(self, obj):
        return format_html('L. {:,.2f}', obj.monto_cuota)
    monto_cuota_formatted.short_description = 'Monto'
    
    def estado_badge(self, obj):
        colores = {
            'PENDIENTE': 'orange',
            'PAGADA': 'green',
            'VENCIDA': 'red',
            'PAGADA_TARDE': 'blue'
        }
        color = colores.get(obj.estado, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def mora_formatted(self, obj):
        if obj.monto_mora > 0:
            return format_html(
                '<span style="color: red;">L. {:,.2f} ({} días)</span>',
                obj.monto_mora, obj.dias_mora
            )
        return '-'
    mora_formatted.short_description = 'Mora'


@admin.register(PagoPrestamo)
class PagoPrestamoAdmin(admin.ModelAdmin):
    list_display = [
        'numero_recibo', 'prestamo_link', 'monto_pagado_formatted',
        'fecha_pago', 'metodo_pago', 'realizado_por'
    ]
    list_filter = ['metodo_pago', 'fecha_pago']
    search_fields = ['numero_recibo', 'prestamo__numero_prestamo']
    readonly_fields = ['numero_recibo', 'creado_en']
    date_hierarchy = 'fecha_pago'
    
    def prestamo_link(self, obj):
        url = reverse('admin:banco_prestamo_change', args=[obj.prestamo.id])
        return format_html('<a href="{}">{}</a>', url, obj.prestamo.numero_prestamo)
    prestamo_link.short_description = 'Préstamo'
    
    def monto_pagado_formatted(self, obj):
        return format_html('<strong style="color: green;">L. {:,.2f}</strong>', obj.monto_pagado)
    monto_pagado_formatted.short_description = 'Monto Pagado'


@admin.register(PeriodoDividendo)
class PeriodoDividendoAdmin(admin.ModelAdmin):
    list_display = [
        'año', 'total_intereses_formatted', 'total_distribuido_formatted',
        'fecha_distribucion', 'estado_badge'
    ]
    list_filter = ['estado', 'año']
    readonly_fields = ['total_intereses_generados', 'total_distribuido']
    
    def total_intereses_formatted(self, obj):
        return format_html('L. {:,.2f}', obj.total_intereses_generados)
    total_intereses_formatted.short_description = 'Intereses Generados'
    
    def total_distribuido_formatted(self, obj):
        return format_html('L. {:,.2f}', obj.total_distribuido)
    total_distribuido_formatted.short_description = 'Total Distribuido'
    
    def estado_badge(self, obj):
        colores = {
            'ABIERTO': 'blue',
            'CERRADO': 'orange',
            'DISTRIBUIDO': 'green'
        }
        color = colores.get(obj.estado, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.estado
        )
    estado_badge.short_description = 'Estado'


@admin.register(Dividendo)
class DividendoAdmin(admin.ModelAdmin):
    list_display = [
        'periodo', 'socio_link', 'saldo_promedio_formatted',
        'cantidad_prestamos', 'cumple_requisito_badge',
        'monto_dividendo_formatted', 'acreditado_badge'
    ]
    list_filter = ['periodo', 'cumple_requisito', 'acreditado']
    search_fields = ['socio__numero_socio', 'socio__primer_nombre', 'socio__primer_apellido']
    readonly_fields = ['creado_en']
    
    def socio_link(self, obj):
        url = reverse('admin:core_socio_change', args=[obj.socio.id])
        return format_html('<a href="{}">{}</a>', url, obj.socio.nombre_completo)
    socio_link.short_description = 'Socio'
    
    def saldo_promedio_formatted(self, obj):
        return format_html('L. {:,.2f}', obj.saldo_promedio_fijo)
    saldo_promedio_formatted.short_description = 'Saldo Promedio'
    
    def cumple_requisito_badge(self, obj):
        if obj.cumple_requisito:
            return format_html('<span style="color: green;">✓ Sí</span>')
        return format_html('<span style="color: red;">✗ No</span>')
    cumple_requisito_badge.short_description = 'Cumple Requisito'
    
    def monto_dividendo_formatted(self, obj):
        return format_html('<strong style="color: green;">L. {:,.2f}</strong>', obj.monto_dividendo)
    monto_dividendo_formatted.short_description = 'Monto Dividendo'
    
    def acreditado_badge(self, obj):
        if obj.acreditado:
            return format_html('<span style="color: green;">✓ Acreditado</span>')
        return format_html('<span style="color: orange;">Pendiente</span>')
    acreditado_badge.short_description = 'Estado'


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'socio', 'tipo', 'asunto', 'enviado_badge', 'fecha_envio', 'creado_en'
    ]
    list_filter = ['tipo', 'enviado', 'fecha_envio']
    search_fields = ['asunto', 'mensaje', 'socio__numero_socio']
    readonly_fields = ['creado_en']
    date_hierarchy = 'creado_en'
    
    def enviado_badge(self, obj):
        if obj.enviado:
            return format_html('<span style="color: green;">✓ Enviado</span>')
        return format_html('<span style="color: orange;">Pendiente</span>')
    enviado_badge.short_description = 'Estado'