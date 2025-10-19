from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

Usuario = get_user_model()


class UsuarioBackend(ModelBackend):
    """Backend personalizado para autenticación por usuario o email"""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        try:
            # Permitir login con usuario o email
            user = Usuario.objects.get(
                Q(usuario=username) | Q(email=username)
            )
        except Usuario.DoesNotExist:
            # Ejecutar el hasher por defecto para evitar timing attacks
            Usuario().set_password(password)
            return None
        except Usuario.MultipleObjectsReturned:
            return None
        
        # Verificar si el usuario está activo
        if not user.is_active:
            return None
        
        # Verificar si está bloqueado
        if user.esta_bloqueado:
            return None
        
        # Verificar contraseña
        if user.check_password(password):
            user.registrar_login_exitoso()
            return user
        else:
            user.registrar_intento_fallido()
            return None
    
    def get_user(self, user_id):
        try:
            return Usuario.objects.get(pk=user_id)
        except Usuario.DoesNotExist:
            return None