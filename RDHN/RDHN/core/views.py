# core/views.py

from datetime import timedelta
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import CatEstado, Socio, SocioContacto, ExpedienteDigital, Rol, UsuarioRol
from .forms import (
    CatEstadoForm, SocioForm, SocioContactoForm, 
    ExpedienteDigitalForm, RolForm, UsuarioForm, AsignarRolesForm
)

Usuario = get_user_model()


# ==========================================
# AUTENTICACIÓN
# ==========================================

def home(request):
    """Vista principal"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    return redirect('core:login')


from .utils import enviar_codigo_2fa

def login_view(request):
    """Vista de login"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        if not username or not password:
            messages.error(request, 'Por favor ingrese usuario y contraseña')
            return render(request, 'core/auth/login.html')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Verificar si requiere cambio de password
            if user.requiere_cambio_password or user.password_expirado:
                # Login temporal para cambiar password
                login(request, user)
                messages.warning(
                    request, 
                    'Debe cambiar su contraseña temporal antes de continuar'
                )
                return redirect('core:cambiar_password')
            
            # Si 2FA está habilitado, generar y enviar código
            if user.two_factor_enabled:
                codigo = user.generar_codigo_2fa()
                
                if enviar_codigo_2fa(user, codigo):
                    # Guardar user_id en sesión (sin hacer login completo aún)
                    request.session['pending_2fa_user_id'] = user.id
                    request.session['pending_2fa_timestamp'] = timezone.now().isoformat()
                    
                    messages.info(
                        request, 
                        f'Se ha enviado un código de verificación a {user.email}'
                    )
                    return redirect('core:verificar_2fa')
                else:
                    messages.error(
                        request, 
                        'Error al enviar el código de verificación. Intente nuevamente.'
                    )
                    return render(request, 'core/auth/login.html')
            else:
                # Si 2FA no está habilitado, login directo
                login(request, user)
                user.registrar_login_exitoso()
                messages.success(request, f'Bienvenido {user.get_full_name()}')
                return redirect('core:dashboard')
        else:
            try:
                user = Usuario.objects.get(Q(usuario=username) | Q(email=username))
                if user.esta_bloqueado:
                    messages.error(
                        request, 
                        f'Usuario bloqueado. Intente nuevamente después de {user.bloqueado_hasta.strftime("%H:%M")}'
                    )
                else:
                    user.registrar_intento_fallido()
                    messages.error(request, 'Contraseña incorrecta')
            except Usuario.DoesNotExist:
                messages.error(request, 'Usuario no encontrado')
    
    return render(request, 'core/auth/login.html')


def verificar_2fa_view(request):
    """Vista para verificar el código 2FA"""
    # Verificar que hay un usuario pendiente de 2FA
    user_id = request.session.get('pending_2fa_user_id')
    timestamp = request.session.get('pending_2fa_timestamp')
    
    if not user_id or not timestamp:
        messages.error(request, 'Sesión expirada. Por favor inicie sesión nuevamente.')
        return redirect('core:login')
    
    # Verificar que no haya pasado más de 15 minutos
    timestamp_dt = timezone.datetime.fromisoformat(timestamp)
    if timezone.now() - timestamp_dt > timedelta(minutes=15):
        del request.session['pending_2fa_user_id']
        del request.session['pending_2fa_timestamp']
        messages.error(request, 'Sesión expirada. Por favor inicie sesión nuevamente.')
        return redirect('core:login')
    
    try:
        user = Usuario.objects.get(id=user_id)
    except Usuario.DoesNotExist:
        messages.error(request, 'Usuario no encontrado.')
        return redirect('core:login')
    
    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip()
        
        if not codigo:
            messages.error(request, 'Por favor ingrese el código de verificación')
            return render(request, 'core/auth/verificar_2fa.html')
        
        if user.validar_codigo_2fa(codigo):
            # Código correcto - completar login
            user.limpiar_codigo_2fa()
            user.registrar_login_exitoso()
            
            # Limpiar sesión temporal
            del request.session['pending_2fa_user_id']
            del request.session['pending_2fa_timestamp']
            
            # Login completo
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'Bienvenido {user.get_full_name()}')
            return redirect('core:dashboard')
        else:
            messages.error(request, 'Código incorrecto o expirado')
    
    return render(request, 'core/auth/verificar_2fa.html', {
        'email_masked': f"{user.email[:3]}***{user.email[user.email.index('@'):]}"
    })


def reenviar_codigo_2fa_view(request):
    """Vista para reenviar el código 2FA"""
    user_id = request.session.get('pending_2fa_user_id')
    
    if not user_id:
        messages.error(request, 'Sesión expirada. Por favor inicie sesión nuevamente.')
        return redirect('core:login')
    
    try:
        user = Usuario.objects.get(id=user_id)
        codigo = user.generar_codigo_2fa()
        
        if enviar_codigo_2fa(user, codigo):
            messages.success(request, 'Se ha reenviado el código de verificación')
        else:
            messages.error(request, 'Error al reenviar el código. Intente nuevamente.')
    except Usuario.DoesNotExist:
        messages.error(request, 'Usuario no encontrado.')
        return redirect('core:login')
    
    return redirect('core:verificar_2fa')

@login_required
def logout_view(request):
    """Vista de logout"""
    logout(request)
    messages.info(request, 'Sesión cerrada correctamente')
    return redirect('core:login')


@login_required
def cambiar_password_view(request):
    """Vista para cambiar contraseña"""
    if not request.user.requiere_cambio_password and not request.user.password_expirado:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        password_actual = request.POST.get('password_actual', '')
        password_nueva = request.POST.get('password_nueva', '')
        password_confirmar = request.POST.get('password_confirmar', '')
        
        if not request.user.check_password(password_actual):
            messages.error(request, 'La contraseña actual es incorrecta')
            return render(request, 'core/auth/cambiar_password.html')
        
        if password_actual == password_nueva:
            messages.error(request, 'La nueva contraseña debe ser diferente a la actual')
            return render(request, 'core/auth/cambiar_password.html')
        
        if password_nueva != password_confirmar:
            messages.error(request, 'Las contraseñas nuevas no coinciden')
            return render(request, 'core/auth/cambiar_password.html')
        
        try:
            validate_password(password_nueva, request.user)
        except ValidationError as e:
            for error in e.messages:
                messages.error(request, error)
            return render(request, 'core/auth/cambiar_password.html')
        
        request.user.set_password(password_nueva)
        request.user.password_updated_at = timezone.now()
        request.user.requiere_cambio_password = False
        request.user.save()
        
        update_session_auth_hash(request, request.user)
        
        messages.success(request, 'Contraseña actualizada correctamente')
        return redirect('core:dashboard')
    
    return render(request, 'core/auth/cambiar_password.html')


def recuperar_password_view(request):
    """Vista para solicitar recuperación de contraseña"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, 'Por favor ingrese su email')
            return render(request, 'core/auth/recuperar_password.html')
        
        try:
            user = Usuario.objects.get(email=email)
            token = user.generar_token_recuperacion()
            
            messages.success(
                request, 
                f'Se ha generado un token de recuperación. Token: {token}'
            )
        except Usuario.DoesNotExist:
            messages.success(
                request, 
                'Si el email existe, recibirá un enlace de recuperación'
            )
        
        return redirect('core:login')
    
    return render(request, 'core/auth/recuperar_password.html')


def restablecer_password_view(request, token):
    """Vista para restablecer contraseña con token"""
    try:
        user = Usuario.objects.get(token_recuperacion=token)
        
        if not user.token_expira or user.token_expira < timezone.now():
            messages.error(request, 'El enlace ha expirado')
            return redirect('core:recuperar_password')
        
        if request.method == 'POST':
            password_nueva = request.POST.get('password_nueva', '')
            password_confirmar = request.POST.get('password_confirmar', '')
            
            if password_nueva != password_confirmar:
                messages.error(request, 'Las contraseñas no coinciden')
                return render(request, 'core/auth/restablecer_password.html', {'token': token})
            
            try:
                validate_password(password_nueva, user)
            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)
                return render(request, 'core/auth/restablecer_password.html', {'token': token})
            
            user.set_password(password_nueva)
            user.password_updated_at = timezone.now()
            user.token_recuperacion = None
            user.token_expira = None
            user.requiere_cambio_password = False
            user.save()
            
            messages.success(request, 'Contraseña restablecida correctamente')
            return redirect('core:login')
        
        return render(request, 'core/auth/restablecer_password.html', {'token': token})
    
    except Usuario.DoesNotExist:
        messages.error(request, 'Token inválido')
        return redirect('core:login')


@login_required
def dashboard_view(request):
    """Vista del dashboard"""
    context = {
        'total_socios': Socio.objects.count(),
        'total_usuarios': Usuario.objects.count(),
        'total_roles': Rol.objects.filter(estado=True).count(),
        'total_expedientes': ExpedienteDigital.objects.count(),
    }
    return render(request, 'core/dashboard.html', context)


# ==========================================
# CRUD ESTADOS
# ==========================================

@login_required
def estados_listar(request):
    """Listar estados"""
    estados = CatEstado.objects.all().order_by('dominio', 'orden', 'codigo')
    return render(request, 'core/estados/listar.html', {'estados': estados})


@login_required
def estados_crear(request):
    """Crear estado"""
    if request.method == 'POST':
        form = CatEstadoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Estado creado correctamente')
            return redirect('core:estados_listar')
    else:
        form = CatEstadoForm()
    
    return render(request, 'core/estados/crear.html', {'form': form})


@login_required
def estados_editar(request, pk):
    """Editar estado"""
    estado = get_object_or_404(CatEstado, pk=pk)
    
    if request.method == 'POST':
        form = CatEstadoForm(request.POST, instance=estado)
        if form.is_valid():
            form.save()
            messages.success(request, 'Estado actualizado correctamente')
            return redirect('core:estados_listar')
    else:
        form = CatEstadoForm(instance=estado)
    
    return render(request, 'core/estados/editar.html', {'form': form, 'estado': estado})


@login_required
def estados_eliminar(request, pk):
    """Eliminar estado"""
    estado = get_object_or_404(CatEstado, pk=pk)
    
    if request.method == 'POST':
        try:
            estado.delete()
            messages.success(request, 'Estado eliminado correctamente')
        except Exception as e:
            messages.error(request, f'No se puede eliminar el estado: {str(e)}')
    
    return redirect('core:estados_listar')


# ==========================================
# CRUD SOCIOS
# ==========================================

@login_required
def socios_listar(request):
    """Listar socios"""
    socios = Socio.objects.all().select_related('id_estado').order_by('-creado_en')
    return render(request, 'core/socios/listar.html', {'socios': socios})


@login_required
def socios_crear(request):
    if request.method == 'POST':
        form = SocioForm(request.POST)
        if form.is_valid():
            socio = form.save()
            messages.success(request, f'Socio {socio.numero_socio} creado exitosamente.')
            return redirect('core:socios_listar')
    else:
        form = SocioForm()
    
    return render(request, 'core/socios/crear.html', {'form': form})


@login_required
def socios_detalle(request, pk):
    """Detalle del socio"""
    socio = get_object_or_404(Socio, pk=pk)
    contactos = socio.contactos.filter(activo=True)
    
    try:
        expediente = socio.expediente
    except ExpedienteDigital.DoesNotExist:
        expediente = None
    
    context = {
        'socio': socio,
        'contactos': contactos,
        'expediente': expediente,
    }
    return render(request, 'core/socios/detalle.html', context)


@login_required
def socios_editar(request, pk):
    socio = get_object_or_404(Socio, pk=pk)
    
    if request.method == 'POST':
        form = SocioForm(request.POST, instance=socio)
        if form.is_valid():
            form.save()
            messages.success(request, f'Socio {socio.numero_socio} actualizado exitosamente.')
            return redirect('core:socios_listar')
    else:
        form = SocioForm(instance=socio)
    
    return render(request, 'core/socios/editar.html', {
        'form': form,
        'socio': socio
    })


@login_required
def socios_eliminar(request, pk):
    """Eliminar socio"""
    socio = get_object_or_404(Socio, pk=pk)
    
    if request.method == 'POST':
        try:
            nombre = socio.nombre_completo
            socio.delete()
            messages.success(request, f'Socio {nombre} eliminado correctamente')
        except Exception as e:
            messages.error(request, f'No se puede eliminar el socio: {str(e)}')
    
    return redirect('core:socios_listar')


# ==========================================
# CRUD CONTACTOS DE SOCIOS
# ==========================================

@login_required
def contactos_crear(request, socio_pk):
    """Crear contacto para un socio"""
    socio = get_object_or_404(Socio, pk=socio_pk)
    
    if request.method == 'POST':
        form = SocioContactoForm(request.POST)
        if form.is_valid():
            contacto = form.save(commit=False)
            contacto.socio = socio
            contacto.save()
            messages.success(request, 'Contacto agregado correctamente')
            return redirect('core:socios_detalle', pk=socio.pk)
    else:
        form = SocioContactoForm()
    
    return render(request, 'core/socios/contacto_form.html', {
        'form': form, 
        'socio': socio,
        'accion': 'Crear'
    })


@login_required
def contactos_editar(request, socio_pk, pk):
    """Editar contacto de un socio"""
    socio = get_object_or_404(Socio, pk=socio_pk)
    contacto = get_object_or_404(SocioContacto, pk=pk, socio=socio)
    
    if request.method == 'POST':
        form = SocioContactoForm(request.POST, instance=contacto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contacto actualizado correctamente')
            return redirect('core:socios_detalle', pk=socio.pk)
    else:
        form = SocioContactoForm(instance=contacto)
    
    return render(request, 'core/socios/contacto_form.html', {
        'form': form,
        'socio': socio,
        'contacto': contacto,
        'accion': 'Editar'
    })


@login_required
def contactos_eliminar(request, socio_pk, pk):
    """Eliminar contacto de un socio"""
    contacto = get_object_or_404(SocioContacto, pk=pk, socio_id=socio_pk)
    
    if request.method == 'POST':
        contacto.delete()
        messages.success(request, 'Contacto eliminado correctamente')
    
    return redirect('core:socios_detalle', pk=socio_pk)


# ==========================================
# CRUD EXPEDIENTES
# ==========================================

@login_required
def expedientes_listar(request):
    """Listar expedientes"""
    expedientes = ExpedienteDigital.objects.all().select_related('socio').order_by('-creado_en')
    return render(request, 'core/expedientes/listar.html', {'expedientes': expedientes})


@login_required
def expedientes_crear(request):
    """Crear expediente"""
    if request.method == 'POST':
        form = ExpedienteDigitalForm(request.POST)
        if form.is_valid():
            expediente = form.save()
            messages.success(request, f'Expediente {expediente.numero_expediente} creado correctamente')
            return redirect('core:expedientes_listar')
    else:
        form = ExpedienteDigitalForm()
    
    return render(request, 'core/expedientes/crear.html', {'form': form})


@login_required
def expedientes_editar(request, pk):
    """Editar expediente"""
    expediente = get_object_or_404(ExpedienteDigital, pk=pk)
    
    if request.method == 'POST':
        form = ExpedienteDigitalForm(request.POST, instance=expediente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expediente actualizado correctamente')
            return redirect('core:expedientes_listar')
    else:
        form = ExpedienteDigitalForm(instance=expediente)
    
    return render(request, 'core/expedientes/editar.html', {'form': form, 'expediente': expediente})


@login_required
def expedientes_eliminar(request, pk):
    """Eliminar expediente"""
    expediente = get_object_or_404(ExpedienteDigital, pk=pk)
    
    if request.method == 'POST':
        try:
            numero = expediente.numero_expediente
            expediente.delete()
            messages.success(request, f'Expediente {numero} eliminado correctamente')
        except Exception as e:
            messages.error(request, f'No se puede eliminar el expediente: {str(e)}')
    
    return redirect('core:expedientes_listar')


# ==========================================
# CRUD ROLES
# ==========================================

@login_required
def roles_listar(request):
    """Listar roles"""
    roles = Rol.objects.all().order_by('nombre_rol')
    return render(request, 'core/roles/listar.html', {'roles': roles})


@login_required
def roles_crear(request):
    """Crear rol"""
    if request.method == 'POST':
        form = RolForm(request.POST)
        if form.is_valid():
            rol = form.save()
            messages.success(request, f'Rol {rol.nombre_rol} creado correctamente')
            return redirect('core:roles_listar')
    else:
        form = RolForm()
    
    return render(request, 'core/roles/crear.html', {'form': form})


@login_required
def roles_editar(request, pk):
    """Editar rol"""
    rol = get_object_or_404(Rol, pk=pk)
    
    if request.method == 'POST':
        form = RolForm(request.POST, instance=rol)
        if form.is_valid():
            form.save()
            messages.success(request, 'Rol actualizado correctamente')
            return redirect('core:roles_listar')
    else:
        form = RolForm(instance=rol)
    
    return render(request, 'core/roles/editar.html', {'form': form, 'rol': rol})


@login_required
def roles_eliminar(request, pk):
    """Eliminar rol"""
    rol = get_object_or_404(Rol, pk=pk)
    
    if request.method == 'POST':
        try:
            nombre = rol.nombre_rol
            rol.delete()
            messages.success(request, f'Rol {nombre} eliminado correctamente')
        except Exception as e:
            messages.error(request, f'No se puede eliminar el rol: {str(e)}')
    
    return redirect('core:roles_listar')


# ==========================================
# CRUD USUARIOS
# ==========================================

@login_required
def usuarios_listar(request):
    """Listar usuarios"""
    usuarios = Usuario.objects.all().select_related('socio').order_by('-creado_en')
    return render(request, 'core/usuarios/listar.html', {'usuarios': usuarios})


@login_required
def usuarios_crear(request):
    """Crear usuario"""
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            password = form.cleaned_data.get('password')
            
            if password:
                usuario.set_password(password)
                usuario.requiere_cambio_password = False
            else:
                usuario.set_password('TemporalPass')
                usuario.requiere_cambio_password = True
            
            usuario.password_updated_at = timezone.now()
            usuario.save()
            
            messages.success(request, f'Usuario {usuario.usuario} creado correctamente')
            return redirect('core:usuarios_listar')
    else:
        form = UsuarioForm()
    
    return render(request, 'core/usuarios/crear.html', {'form': form})


@login_required
def usuarios_editar(request, pk):
    """Editar usuario"""
    usuario = get_object_or_404(Usuario, pk=pk)
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            usuario = form.save(commit=False)
            password = form.cleaned_data.get('password')
            
            if password:
                usuario.set_password(password)
                usuario.password_updated_at = timezone.now()
            
            usuario.save()
            messages.success(request, 'Usuario actualizado correctamente')
            return redirect('core:usuarios_listar')
    else:
        form = UsuarioForm(instance=usuario)
    
    return render(request, 'core/usuarios/editar.html', {'form': form, 'usuario': usuario})


@login_required
def usuarios_eliminar(request, pk):
    """Eliminar usuario"""
    usuario = get_object_or_404(Usuario, pk=pk)
    
    if request.method == 'POST':
        try:
            nombre = usuario.usuario
            usuario.delete()
            messages.success(request, f'Usuario {nombre} eliminado correctamente')
        except Exception as e:
            messages.error(request, f'No se puede eliminar el usuario: {str(e)}')
    
    return redirect('core:usuarios_listar')


@login_required
def usuarios_asignar_roles(request, pk):
    """Asignar roles a un usuario"""
    usuario = get_object_or_404(Usuario, pk=pk)
    
    if request.method == 'POST':
        form = AsignarRolesForm(request.POST)
        if form.is_valid():
            roles_seleccionados = form.cleaned_data['roles']
            
            # Eliminar roles anteriores
            UsuarioRol.objects.filter(usuario=usuario).delete()
            
            # Asignar nuevos roles
            for rol in roles_seleccionados:
                UsuarioRol.objects.create(
                    usuario=usuario,
                    rol=rol,
                    fecha_asignacion=timezone.now().date(),
                    asignado_por=request.user,
                    estado=True
                )
            
            messages.success(request, 'Roles asignados correctamente')
            return redirect('core:usuarios_listar')
    else:
        # Marcar los roles actuales
        roles_actuales = usuario.roles.all()
        form = AsignarRolesForm(initial={'roles': roles_actuales})
    
    return render(request, 'core/usuarios/asignar_roles.html', {
        'form': form,
        'usuario': usuario
    })