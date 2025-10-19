from django.core.mail import send_mail
from django.conf import settings

def enviar_codigo_2fa(usuario, codigo):
    """Envía el código 2FA por email"""
    asunto = 'Código de Verificación - RDHN'
    
    mensaje = f"""
Hola {usuario.get_full_name()},

Tu código de verificación es: {codigo}

Este código expirará en 10 minutos.

Si no solicitaste este código, ignora este mensaje.

Saludos,
Red de Desarrollo Sostenible de Honduras
    """
    
    try:
        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [usuario.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error enviando email: {e}")
        return False