from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Socio, Rol

Usuario = get_user_model()


class UsuarioSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(source='get_full_name', read_only=True)
    roles = serializers.SerializerMethodField()
    
    class Meta:
        model = Usuario
        fields = [
            'id', 'usuario', 'email', 'nombre_completo',
            'is_active', 'roles', 'two_factor_enabled',
            'ultimo_acceso', 'creado_en'
        ]
        read_only_fields = ['id', 'ultimo_acceso', 'creado_en']
    
    def get_roles(self, obj):
        return [rol.nombre_rol for rol in obj.roles_activos()]


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class VerificarCodigoSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
    codigo = serializers.CharField(required=True, max_length=6)


class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(required=True, write_only=True)
    password_nueva = serializers.CharField(required=True, write_only=True)
    password_confirmar = serializers.CharField(required=True, write_only=True)
    
    def validate(self, data):
        if data['password_nueva'] != data['password_confirmar']:
            raise serializers.ValidationError({
                'password_confirmar': 'Las contraseñas no coinciden'
            })
        return data