from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import (
    TipoCuenta, TipoPrestamo, CuentaAhorro, Transaccion,
    Prestamo, Garante, CuotaPrestamo, PagoPrestamo,
    PeriodoDividendo, Dividendo, Notificacion
)
from core.models import Socio, Usuario, CatEstado
import random


class TipoCuentaForm(forms.ModelForm):
    class Meta:
        model = TipoCuenta
        fields = [
            'codigo', 'nombre', 'descripcion', 'tasa_interes_anual',
            'monto_minimo', 'es_retirable', 'requiere_deduccion_planilla', 'activo'
        ]
        widgets = {
            'codigo': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nombre del tipo de cuenta'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Descripción detallada'
            }),
            'tasa_interes_anual': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0'
            }),
            'monto_minimo': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0'
            }),
        }


class TipoPrestamoForm(forms.ModelForm):
    class Meta:
        model = TipoPrestamo
        fields = [
            'codigo', 'nombre', 'descripcion', 'tasa_interes_anual',
            'multiplicador_ahorro', 'plazo_minimo_meses', 'plazo_maximo_meses',
            'requiere_garantes', 'cantidad_garantes', 'activo'
        ]
        widgets = {
            'codigo': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nombre del tipo de préstamo'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Descripción detallada'
            }),
            'tasa_interes_anual': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0'
            }),
            'multiplicador_ahorro': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0'
            }),
            'plazo_minimo_meses': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1'
            }),
            'plazo_maximo_meses': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1'
            }),
            'cantidad_garantes': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        plazo_min = cleaned_data.get('plazo_minimo_meses')
        plazo_max = cleaned_data.get('plazo_maximo_meses')

        if plazo_min and plazo_max and plazo_min > plazo_max:
            raise ValidationError(
                'El plazo mínimo no puede ser mayor que el plazo máximo'
            )

        return cleaned_data


class CuentaAhorroForm(forms.ModelForm):
    class Meta:
        model = CuentaAhorro
        fields = [
            'socio', 'tipo_cuenta', 'numero_cuenta', 'saldo_actual',
            'monto_deduccion_planilla', 'fecha_apertura', 'fecha_cierre',
            'estado', 'observaciones'
        ]
        widgets = {
            'socio': forms.Select(attrs={
                'class': 'form-select select2-single',
                'data-placeholder': 'Seleccione un socio'
            }),
            'tipo_cuenta': forms.Select(attrs={'class': 'form-select'}),
            'numero_cuenta': forms.TextInput(attrs={
                'class': 'form-input',
                'readonly': 'readonly',
                'style': 'cursor: not-allowed;'
            }),
            'saldo_actual': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'readonly': 'readonly',
                'style': 'cursor: not-allowed;'
            }),
            'monto_deduccion_planilla': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0'
            }),
            'fecha_apertura': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'fecha_cierre': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Generar número de cuenta automático para cuentas nuevas
        if not self.instance.pk:
            self.fields['numero_cuenta'].initial = self.generar_numero_cuenta_unico()
            self.fields['saldo_actual'].initial = Decimal('0.00')
        
        # Filtrar estados por dominio CUENTA_AHORRO
        self.fields['estado'].queryset = CatEstado.objects.filter(
            dominio='CUENTA_AHORRO'
        ).order_by('orden')

    @staticmethod
    def generar_numero_cuenta_unico():
        """Genera un número de cuenta único"""
        while True:
            # Formato: CA-YYYYMMDD-XXXXX
            from django.utils import timezone
            fecha = timezone.now().strftime('%Y%m%d')
            aleatorio = ''.join([str(random.randint(0, 9)) for _ in range(5)])
            numero = f"CA-{fecha}-{aleatorio}"
            
            if not CuentaAhorro.objects.filter(numero_cuenta=numero).exists():
                return numero

    def clean(self):
        cleaned_data = super().clean()
        fecha_apertura = cleaned_data.get('fecha_apertura')
        fecha_cierre = cleaned_data.get('fecha_cierre')

        if fecha_cierre and fecha_apertura and fecha_cierre < fecha_apertura:
            raise ValidationError(
                'La fecha de cierre no puede ser anterior a la fecha de apertura'
            )

        return cleaned_data


class TransaccionForm(forms.ModelForm):
    class Meta:
        model = Transaccion
        fields = [
            'cuenta_ahorro', 'prestamo', 'tipo_transaccion', 'monto',
            'descripcion', 'numero_recibo', 'fecha_transaccion'
        ]
        widgets = {
            'cuenta_ahorro': forms.Select(attrs={
                'class': 'form-select select2-single',
                'data-placeholder': 'Seleccione una cuenta (opcional)'
            }),
            'prestamo': forms.Select(attrs={
                'class': 'form-select select2-single',
                'data-placeholder': 'Seleccione un préstamo (opcional)'
            }),
            'tipo_transaccion': forms.Select(attrs={'class': 'form-select'}),
            'monto': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Descripción de la transacción'
            }),
            'numero_recibo': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Número de recibo (opcional)'
            }),
            'fecha_transaccion': forms.DateTimeInput(attrs={
                'class': 'form-input',
                'type': 'datetime-local'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        cuenta_ahorro = cleaned_data.get('cuenta_ahorro')
        prestamo = cleaned_data.get('prestamo')
        tipo_transaccion = cleaned_data.get('tipo_transaccion')
        monto = cleaned_data.get('monto')

        # Validar que se especifique cuenta O préstamo
        if not cuenta_ahorro and not prestamo:
            raise ValidationError(
                'Debe especificar una cuenta de ahorro o un préstamo'
            )

        if cuenta_ahorro and prestamo:
            raise ValidationError(
                'No puede especificar cuenta de ahorro Y préstamo simultáneamente'
            )

        # Validar retiro contra saldo disponible
        if tipo_transaccion == 'RETIRO' and cuenta_ahorro:
            if monto and cuenta_ahorro.saldo_actual < monto:
                raise ValidationError(
                    f'Saldo insuficiente. Saldo disponible: L. {cuenta_ahorro.saldo_actual}'
                )

        return cleaned_data


class PrestamoForm(forms.ModelForm):
    class Meta:
        model = Prestamo
        fields = [
            'socio', 'tipo_prestamo', 'numero_prestamo', 'monto_solicitado',
            'plazo_meses', 'deducir_por_planilla', 'numero_planilla',
            'constancia_trabajo', 'observaciones'
        ]
        widgets = {
            'socio': forms.Select(attrs={
                'class': 'form-select select2-single',
                'data-placeholder': 'Seleccione un socio'
            }),
            'tipo_prestamo': forms.Select(attrs={'class': 'form-select'}),
            'numero_prestamo': forms.TextInput(attrs={
                'class': 'form-input',
                'readonly': 'readonly',
                'style': 'cursor: not-allowed;'
            }),
            'monto_solicitado': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '1'
            }),
            'plazo_meses': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1'
            }),
            'numero_planilla': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Número de planilla (si aplica)'
            }),
            'constancia_trabajo': forms.FileInput(attrs={
                'class': 'form-input'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['numero_prestamo'].initial = self.generar_numero_prestamo_unico()

    @staticmethod
    def generar_numero_prestamo_unico():
        """Genera un número de préstamo único"""
        while True:
            # Formato: PR-YYYYMMDD-XXXXX
            from django.utils import timezone
            fecha = timezone.now().strftime('%Y%m%d')
            aleatorio = ''.join([str(random.randint(0, 9)) for _ in range(5)])
            numero = f"PR-{fecha}-{aleatorio}"
            
            if not Prestamo.objects.filter(numero_prestamo=numero).exists():
                return numero

    def clean(self):
        cleaned_data = super().clean()
        tipo_prestamo = cleaned_data.get('tipo_prestamo')
        plazo_meses = cleaned_data.get('plazo_meses')

        if tipo_prestamo and plazo_meses:
            if plazo_meses < tipo_prestamo.plazo_minimo_meses:
                raise ValidationError(
                    f'El plazo mínimo para este tipo de préstamo es {tipo_prestamo.plazo_minimo_meses} meses'
                )
            if plazo_meses > tipo_prestamo.plazo_maximo_meses:
                raise ValidationError(
                    f'El plazo máximo para este tipo de préstamo es {tipo_prestamo.plazo_maximo_meses} meses'
                )

        return cleaned_data


class AprobarPrestamoForm(forms.Form):
    """Formulario para aprobar un préstamo"""
    monto_aprobado = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '0.01'
        }),
        label='Monto Aprobado'
    )
    fecha_primer_pago = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        }),
        label='Fecha del Primer Pago'
    )
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 3,
            'placeholder': 'Observaciones sobre la aprobación'
        }),
        label='Observaciones'
    )


class RechazarPrestamoForm(forms.Form):
    """Formulario para rechazar un préstamo"""
    motivo_rechazo = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 4,
            'placeholder': 'Explique el motivo del rechazo'
        }),
        label='Motivo del Rechazo'
    )


class GaranteForm(forms.ModelForm):
    class Meta:
        model = Garante
        fields = ['socio_garante', 'fecha_aceptacion', 'documento_garante', 'activo']
        widgets = {
            'socio_garante': forms.Select(attrs={
                'class': 'form-select select2-single',
                'data-placeholder': 'Seleccione un socio garante'
            }),
            'fecha_aceptacion': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'documento_garante': forms.FileInput(attrs={
                'class': 'form-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.prestamo = kwargs.pop('prestamo', None)
        super().__init__(*args, **kwargs)
        
        if self.prestamo:
            # Excluir al solicitante del préstamo y garantes ya asignados
            garantes_existentes = self.prestamo.garantes.values_list(
                'socio_garante_id', flat=True
            )
            self.fields['socio_garante'].queryset = Socio.objects.exclude(
                id=self.prestamo.socio_id
            ).exclude(id__in=garantes_existentes)


class PagoPrestamoForm(forms.ModelForm):
    class Meta:
        model = PagoPrestamo
        fields = [
            'cuota', 'monto_pagado', 'fecha_pago', 'numero_recibo',
            'metodo_pago', 'observaciones'
        ]
        widgets = {
            'cuota': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'Seleccione una cuota (opcional)'
            }),
            'monto_pagado': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01'
            }),
            'fecha_pago': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'numero_recibo': forms.TextInput(attrs={
                'class': 'form-input',
                'readonly': 'readonly',
                'style': 'cursor: not-allowed;'
            }),
            'metodo_pago': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3
            }),
        }

    def __init__(self, *args, **kwargs):
        self.prestamo = kwargs.pop('prestamo', None)
        super().__init__(*args, **kwargs)
        
        if not self.instance.pk:
            self.fields['numero_recibo'].initial = self.generar_numero_recibo_unico()
        
        if self.prestamo:
            # Mostrar solo cuotas pendientes o vencidas
            self.fields['cuota'].queryset = self.prestamo.cuotas.filter(
                estado__in=['PENDIENTE', 'VENCIDA']
            ).order_by('numero_cuota')

    @staticmethod
    def generar_numero_recibo_unico():
        """Genera un número de recibo único"""
        while True:
            from django.utils import timezone
            fecha = timezone.now().strftime('%Y%m%d')
            aleatorio = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            numero = f"REC-{fecha}-{aleatorio}"
            
            if not PagoPrestamo.objects.filter(numero_recibo=numero).exists():
                return numero


class PeriodoDividendoForm(forms.ModelForm):
    class Meta:
        model = PeriodoDividendo
        fields = [
            'año', 'fecha_inicio', 'fecha_fin', 'total_intereses_generados',
            'total_distribuido', 'fecha_distribucion', 'estado'
        ]
        widgets = {
            'año': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '2000',
                'max': '2100'
            }),
            'fecha_inicio': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'fecha_fin': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'total_intereses_generados': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'readonly': 'readonly'
            }),
            'total_distribuido': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'readonly': 'readonly'
            }),
            'fecha_distribucion': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')