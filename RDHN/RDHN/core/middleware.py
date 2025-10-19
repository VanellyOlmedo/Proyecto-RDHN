from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone

class PasswordExpirationMiddleware:
    """Middleware para forzar cambio de contraseña expirada"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Rutas que no requieren verificación
            rutas_permitidas = [
                reverse('logout'),
                reverse('cambiar_password'),
            ]
            
            if request.path not in rutas_permitidas:
                if request.user.password_expirado or request.user.requiere_cambio_password:
                    messages.warning(request, 'Debe cambiar su contraseña')
                    return redirect('cambiar_password')
        
        return self.get_response(request)


class SessionSecurityMiddleware:
    """Middleware para seguridad de sesiones"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Verificar inactividad
            ultima_actividad = request.session.get('ultima_actividad')
            if ultima_actividad:
                from datetime import datetime
                tiempo_inactivo = (timezone.now() - datetime.fromisoformat(ultima_actividad)).seconds
                if tiempo_inactivo > 1800:  # 30 minutos
                    from django.contrib.auth import logout
                    logout(request)
                    messages.info(request, 'Sesión cerrada por inactividad')
                    return redirect('login')
            
            # Actualizar última actividad
            request.session['ultima_actividad'] = timezone.now().isoformat()
        
        return self.get_response(request)