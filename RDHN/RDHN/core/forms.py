from django import forms
from .models import CatEstado, Socio, SocioContacto, ExpedienteDigital, Rol, Usuario, UsuarioRol
from django.contrib.auth.password_validation import validate_password
import random

class CatEstadoForm(forms.ModelForm):
    class Meta:
        model = CatEstado
        fields = ['dominio', 'codigo', 'nombre', 'es_final', 'orden']
        widgets = {
            'dominio': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: SOCIO'}),
            'codigo': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: ACTIVO'}),
            'nombre': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: Activo'}),
            'orden': forms.NumberInput(attrs={'class': 'form-input'}),
        }


class SocioForm(forms.ModelForm):
    class Meta:
        model = Socio
        fields = [
            'numero_socio', 'identidad', 'primer_nombre', 'segundo_nombre',
            'primer_apellido', 'segundo_apellido', 'direccion', 
            'fecha_ingreso', 'fecha_egreso', 'id_estado'
        ]
        widgets = {
            'numero_socio': forms.TextInput(attrs={
                'class': 'form-input',
                'readonly': 'readonly',
                'style': 'cursor: not-allowed;'
            }),
            'identidad': forms.TextInput(attrs={
                'class': 'form-input identidad-input',
                'placeholder': '0801-1990-12345',
                'maxlength': '15'  # 13 dígitos + 2 guiones
            }),
            'primer_nombre': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Primer nombre'
            }),
            'segundo_nombre': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Segundo nombre (opcional)'
            }),
            'primer_apellido': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Primer apellido'
            }),
            'segundo_apellido': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Segundo apellido (opcional)'
            }),
            'direccion': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Dirección completa'
            }),
            'fecha_ingreso': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'fecha_egreso': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'id_estado': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si es un nuevo socio, generar número automático
        if not self.instance.pk:
            self.fields['numero_socio'].initial = self.generar_numero_socio_unico()

        if self.instance.pk and self.instance.identidad:
            identidad = self.instance.identidad.replace('-', '')
            if len(identidad) == 13:
                self.initial['identidad'] = f"{identidad[:4]}-{identidad[4:8]}-{identidad[8:]}"

    def clean_identidad(self):
        """Limpia la identidad removiendo los guiones antes de guardar"""
        identidad = self.cleaned_data.get('identidad', '')
        # Remover guiones y espacios
        identidad_limpia = identidad.replace('-', '').replace(' ', '')
        
        # Validar que sean 13 dígitos
        if identidad_limpia and not identidad_limpia.isdigit():
            raise forms.ValidationError('La identidad debe contener solo números.')
        
        if identidad_limpia and len(identidad_limpia) != 13:
            raise forms.ValidationError('La identidad debe tener 13 dígitos.')
        
        return identidad_limpia
    
    @staticmethod
    def generar_numero_socio_unico():
        """Genera un número de socio único de 20 dígitos"""
        while True:
            # Generar número aleatorio de 20 dígitos
            numero = ''.join([str(random.randint(0, 9)) for _ in range(20)])
            
            # Verificar si ya existe
            if not Socio.objects.filter(numero_socio=numero).exists():
                return numero


class SocioContactoForm(forms.ModelForm):
    class Meta:
        model = SocioContacto
        fields = ['tipo', 'valor', 'preferido', 'activo']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'valor': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Valor del contacto'}),
        }


class ExpedienteDigitalForm(forms.ModelForm):
    class Meta:
        model = ExpedienteDigital
        fields = ['socio', 'numero_expediente', 'fecha_creacion', 'observaciones']
        widgets = {
            'socio': forms.Select(attrs={'class': 'form-select'}),
            'numero_expediente': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Número de expediente'}),
            'fecha_creacion': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
        }


class RolForm(forms.ModelForm):
    class Meta:
        model = Rol
        fields = ['nombre_rol', 'descripcion', 'estado']
        widgets = {
            'nombre_rol': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nombre del rol'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }


class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input', 
            'placeholder': 'Contraseña (dejar en blanco para temporal)'
        }),
        help_text='Dejar en blanco para usar contraseña temporal'
    )
    
    class Meta:
        model = Usuario
        fields = [
            'socio', 'usuario', 'email', 'password',
            'password_expira_dias', 'is_active', 'is_staff', 'roles'
        ]
        exclude = [
            'ultimo_acceso', 'intentos_fallidos', 'bloqueado_hasta', 
            'requiere_cambio_password', 'id_estado', 'token_recuperacion', 'token_expira'
        ]
        widgets = {
            'socio': forms.Select(attrs={
                'class': 'form-select select2-single',
                'data-placeholder': 'Seleccione un socio (opcional)'
            }),
            'usuario': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': 'Nombre de usuario'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input', 
                'placeholder': 'correo@ejemplo.com'
            }),
            'password_expira_dias': forms.NumberInput(attrs={'class': 'form-input'}),
            'roles': forms.SelectMultiple(attrs={
                'class': 'form-select select2-multiple',
                'data-placeholder': 'Selecciona uno o más roles'
            }),
        }


class AsignarRolesForm(forms.Form):
    roles = forms.ModelMultipleChoiceField(
        queryset=Rol.objects.filter(estado=True),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )