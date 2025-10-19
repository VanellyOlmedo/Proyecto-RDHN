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


