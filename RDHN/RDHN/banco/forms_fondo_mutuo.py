from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models_fondo_mutuo import FondoMutuo, MovimientoFondoMutuo, SolicitudAyudaMutua
from core.models import Socio


class FondoMutuoForm(forms.ModelForm):
    class Meta:
        model = FondoMutuo
        fields = ['periodo', 'fecha_inicio', 'fecha_fin', 'estado', 'observaciones']
        widgets = {
            'periodo': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'YYYYMM (Ej: 202401)',
                'pattern': '[0-9]{6}',
                'maxlength': '6'
            }),
            'fecha_inicio': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'fecha_fin': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Observaciones del período'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar estados por dominio FONDO_MUTUO
        from core.models import CatEstado
        self.fields['estado'].queryset = CatEstado.objects.filter(
            dominio='FONDO_MUTUO'
        ).order_by('orden')


class AporteFondoMutuoForm(forms.Form):
    """Formulario para registrar aportes al fondo mutuo"""
    
    socio = forms.ModelChoiceField(
        queryset=Socio.objects.filter(
            id_estado__dominio='SOCIO',
            id_estado__codigo='ACTIVO'
        ).order_by('numero_socio'),
        widget=forms.Select(attrs={
            'class': 'form-select select2-single',
            'data-placeholder': 'Buscar socio por nombre o número'
        }),
        label='Socio',
        help_text='Socio que realiza el aporte'
    )
    
    tipo_aporte = forms.ChoiceField(
        choices=MovimientoFondoMutuo.TIPO_APORTE_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-radio'
        }),
        initial='MENSUAL',
        label='Tipo de Aporte'
    )
    
    monto = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '0.01',
            'placeholder': '0.00',
            'min': '0.01'
        }),
        label='Monto del Aporte'
    )
    
    concepto = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Concepto del aporte (opcional)'
        }),
        label='Concepto'
    )
    
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 3,
            'placeholder': 'Observaciones adicionales (opcional)'
        }),
        label='Observaciones'
    )
    
    def clean_socio(self):
        """Validar que el socio esté activo"""
        socio = self.cleaned_data.get('socio')
        if socio and not socio.esta_activo:
            raise ValidationError('El socio debe estar ACTIVO para aportar al fondo')
        return socio


class SolicitudAyudaForm(forms.ModelForm):
    class Meta:
        model = SolicitudAyudaMutua
        fields = [
            'socio', 'tipo_ayuda', 'monto_solicitado',
            'justificacion', 'documento_soporte'
        ]
        widgets = {
            'socio': forms.Select(attrs={
                'class': 'form-select select2-single',
                'data-placeholder': 'Seleccione el socio'
            }),
            'tipo_ayuda': forms.Select(attrs={
                'class': 'form-select'
            }),
            'monto_solicitado': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'justificacion': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 5,
                'placeholder': 'Explique detalladamente el motivo de su solicitud...'
            }),
            'documento_soporte': forms.FileInput(attrs={
                'class': 'form-input',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar solo socios activos con más de 6 meses
        self.fields['socio'].queryset = Socio.objects.filter(
            id_estado__dominio='SOCIO',
            id_estado__codigo='ACTIVO'
        ).order_by('numero_socio')
        
        # Si es una nueva solicitud, asignar número automáticamente
        if not self.instance.pk:
            self.instance.numero_solicitud = SolicitudAyudaMutua.generar_numero_solicitud()
    
    def clean(self):
        cleaned_data = super().clean()
        socio = cleaned_data.get('socio')
        
        if socio:
            # Validar antigüedad
            if socio.meses_antiguedad < 6:
                raise ValidationError({
                    'socio': f'El socio debe tener al menos 6 meses de antigüedad. '
                            f'Antigüedad actual: {socio.meses_antiguedad} meses'
                })
            
            # Validar que no tenga solicitudes pendientes
            solicitudes_pendientes = SolicitudAyudaMutua.objects.filter(
                socio=socio,
                estado__in=['PENDIENTE', 'EN_REVISION', 'APROBADA']
            ).exists()
            
            if solicitudes_pendientes:
                raise ValidationError({
                    'socio': 'Este socio ya tiene una solicitud de ayuda pendiente'
                })
        
        return cleaned_data


class AprobarSolicitudForm(forms.Form):
    """Formulario para aprobar una solicitud de ayuda"""
    
    monto_aprobado = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '0.01',
            'min': '0.01'
        }),
        label='Monto a Aprobar'
    )
    
    comentarios = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 4,
            'placeholder': 'Comentarios sobre la aprobación (opcional)'
        }),
        label='Comentarios'
    )
    
    def __init__(self, *args, solicitud=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.solicitud = solicitud
        
        if solicitud:
            # Pre-llenar con el monto solicitado
            self.fields['monto_aprobado'].initial = solicitud.monto_solicitado
    
    def clean_monto_aprobado(self):
        """Validar que haya saldo disponible"""
        monto = self.cleaned_data.get('monto_aprobado')
        
        if self.solicitud:
            if self.solicitud.fondo.saldo_disponible < monto:
                raise ValidationError(
                    f'Saldo insuficiente en el fondo. '
                    f'Disponible: L. {self.solicitud.fondo.saldo_disponible}'
                )
        
        return monto


class RechazarSolicitudForm(forms.Form):
    """Formulario para rechazar una solicitud de ayuda"""
    
    motivo_rechazo = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 4,
            'placeholder': 'Explique el motivo del rechazo...'
        }),
        label='Motivo del Rechazo'
    )


class CerrarPeriodoForm(forms.Form):
    """Formulario para cerrar un período del fondo mutuo"""
    
    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 4,
            'placeholder': 'Observaciones del cierre (opcional)'
        }),
        label='Observaciones'
    )
    
    confirmar = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        }),
        label='Confirmo que deseo cerrar este período del fondo mutuo',
        help_text='Una vez cerrado, no se podrán realizar más aportes ni aprobar solicitudes'
    )


class BusquedaMovimientosForm(forms.Form):
    """Formulario para filtrar movimientos del fondo"""
    
    periodo = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Período'
    )
    
    socio = forms.ModelChoiceField(
        required=False,
        queryset=Socio.objects.all().order_by('numero_socio'),
        widget=forms.Select(attrs={
            'class': 'form-select select2-single',
            'data-placeholder': 'Todos los socios'
        }),
        label='Socio'
    )
    
    origen = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos')] + list(MovimientoFondoMutuo.ORIGEN_CHOICES),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Tipo de Movimiento'
    )
    
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        }),
        label='Desde'
    )
    
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        }),
        label='Hasta'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Llenar opciones de período con los fondos existentes
        periodos = FondoMutuo.objects.values_list('periodo', flat=True).order_by('-periodo')
        self.fields['periodo'].choices = [('', 'Todos los períodos')] + [
            (p, f"{p[4:6]}/{p[:4]}") for p in periodos
        ]


class BusquedaSolicitudesForm(forms.Form):
    """Formulario para filtrar solicitudes de ayuda"""
    
    estado = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos los estados')] + list(SolicitudAyudaMutua.ESTADO_CHOICES),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Estado'
    )
    
    tipo_ayuda = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos los tipos')] + list(SolicitudAyudaMutua.TIPO_AYUDA_CHOICES),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Tipo de Ayuda'
    )
    
    socio = forms.ModelChoiceField(
        required=False,
        queryset=Socio.objects.all().order_by('numero_socio'),
        widget=forms.Select(attrs={
            'class': 'form-select select2-single',
            'data-placeholder': 'Todos los socios'
        }),
        label='Socio'
    )
    
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        }),
        label='Desde'
    )
    
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        }),
        label='Hasta'
    )