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


