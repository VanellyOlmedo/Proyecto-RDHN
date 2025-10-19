from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from .serializers import (
    UsuarioSerializer, LoginSerializer, 
    VerificarCodigoSerializer, CambiarPasswordSerializer
)
from .utils import enviar_codigo_2fa

Usuario = get_user_model()


def get_tokens_for_user(user):
    """Genera tokens JWT para un usuario"""
    refresh = RefreshToken.for_user(user)
    
    # Agregar claims personalizados
    refresh['usuario'] = user.usuario
    refresh['email'] = user.email
    refresh['roles'] = [rol.nombre_rol for rol in user.roles_activos()]
    
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    """
    Endpoint de login con JWT
    
    POST /api/auth/login/
    {
        "username": "usuario",
        "password": "contraseña"
    }
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    username = serializer.validated_data['username']
    password = serializer.validated_data['password']
    
    # Autenticar usuario
    user = authenticate(request, username=username, password=password)
    
    if user is None:
        # Registrar intento fallido
        try:
            user = Usuario.objects.get(usuario=username)
            if user.esta_bloqueado:
                return Response({
                    'error': 'Usuario bloqueado',
                    'bloqueado_hasta': user.bloqueado_hasta
                }, status=status.HTTP_403_FORBIDDEN)
            
            user.registrar_intento_fallido()
            return Response({
                'error': 'Credenciales inválidas'
            }, status=status.HTTP_401_UNAUTHORIZED)
        except Usuario.DoesNotExist:
            return Response({
                'error': 'Credenciales inválidas'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Verificar si requiere cambio de password
    if user.requiere_cambio_password or user.password_expirado:
        return Response({
            'requiere_cambio_password': True,
            'user_id': user.id,
            'mensaje': 'Debe cambiar su contraseña antes de continuar'
        }, status=status.HTTP_200_OK)
    
    # Verificar si tiene 2FA habilitado
    if user.two_factor_enabled:
        codigo = user.generar_codigo_2fa()
        
        if enviar_codigo_2fa(user, codigo):
            return Response({
                'requiere_2fa': True,
                'user_id': user.id,
                'email_masked': f"{user.email[:3]}***{user.email[user.email.index('@'):]}"
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Error al enviar código de verificación'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Login exitoso sin 2FA
    user.registrar_login_exitoso()
    tokens = get_tokens_for_user(user)
    
    return Response({
        'tokens': tokens,
        'usuario': UsuarioSerializer(user).data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_verificar_2fa(request):
    """
    Endpoint para verificar código 2FA
    
    POST /api/auth/verificar-2fa/
    {
        "user_id": 1,
        "codigo": "123456"
    }
    """
    serializer = VerificarCodigoSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    user_id = serializer.validated_data['user_id']
    codigo = serializer.validated_data['codigo']
    
    try:
        user = Usuario.objects.get(id=user_id)
    except Usuario.DoesNotExist:
        return Response({
            'error': 'Usuario no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if user.validar_codigo_2fa(codigo):
        user.limpiar_codigo_2fa()
        user.registrar_login_exitoso()
        tokens = get_tokens_for_user(user)
        
        return Response({
            'tokens': tokens,
            'usuario': UsuarioSerializer(user).data
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'error': 'Código incorrecto o expirado'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_reenviar_codigo_2fa(request):
    """
    Endpoint para reenviar código 2FA
    
    POST /api/auth/reenviar-2fa/
    {
        "user_id": 1
    }
    """
    user_id = request.data.get('user_id')
    
    if not user_id:
        return Response({
            'error': 'user_id es requerido'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = Usuario.objects.get(id=user_id)
        codigo = user.generar_codigo_2fa()
        
        if enviar_codigo_2fa(user, codigo):
            return Response({
                'mensaje': 'Código reenviado correctamente'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Error al reenviar código'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Usuario.DoesNotExist:
        return Response({
            'error': 'Usuario no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_cambiar_password(request):
    """
    Endpoint para cambiar contraseña
    
    POST /api/auth/cambiar-password/
    {
        "password_actual": "actual",
        "password_nueva": "nueva",
        "password_confirmar": "nueva"
    }
    """
    serializer = CambiarPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    user = request.user
    password_actual = serializer.validated_data['password_actual']
    password_nueva = serializer.validated_data['password_nueva']
    
    if not user.check_password(password_actual):
        return Response({
            'error': 'La contraseña actual es incorrecta'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if password_actual == password_nueva:
        return Response({
            'error': 'La nueva contraseña debe ser diferente a la actual'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        validate_password(password_nueva, user)
    except ValidationError as e:
        return Response({
            'error': e.messages
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user.set_password(password_nueva)
    user.password_updated_at = timezone.now()
    user.requiere_cambio_password = False
    user.save()
    
    # Generar nuevos tokens
    tokens = get_tokens_for_user(user)
    
    return Response({
        'mensaje': 'Contraseña actualizada correctamente',
        'tokens': tokens
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_refresh_token(request):
    """
    Endpoint para refrescar el token
    
    POST /api/auth/refresh/
    {
        "refresh": "token_refresh"
    }
    """
    from rest_framework_simplejwt.tokens import RefreshToken
    
    refresh_token = request.data.get('refresh')
    
    if not refresh_token:
        return Response({
            'error': 'Token de refresh requerido'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        token = RefreshToken(refresh_token)
        return Response({
            'access': str(token.access_token)
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': 'Token inválido o expirado'
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    """
    Endpoint para logout (blacklist del refresh token)
    
    POST /api/auth/logout/
    {
        "refresh": "token_refresh"
    }
    """
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({
            'mensaje': 'Logout exitoso'
        }, status=status.HTTP_200_OK)
    except Exception:
        return Response({
            'error': 'Token inválido'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_usuario_actual(request):
    """
    Endpoint para obtener información del usuario actual
    
    GET /api/auth/me/
    """
    serializer = UsuarioSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)