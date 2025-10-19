from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenRefreshView
from . import views, api_views

app_name = 'core'

urlpatterns = [
    # Home y Dashboard
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Autenticación
    path('login/', views.login_view, name='login'),
    path('verificar-2fa/', views.verificar_2fa_view, name='verificar_2fa'),
    path('reenviar-codigo-2fa/', views.reenviar_codigo_2fa_view, name='reenviar_codigo_2fa'),
    path('logout/', views.logout_view, name='logout'),
    path('cambiar-password/', views.cambiar_password_view, name='cambiar_password'),
    path('recuperar-password/', views.recuperar_password_view, name='recuperar_password'),
    path('restablecer-password/<str:token>/', views.restablecer_password_view, name='restablecer_password'),
    
    # Estados
    path('estados/', views.estados_listar, name='estados_listar'), 
    path('estados/crear/', views.estados_crear, name='estados_crear'),
    path('estados/<int:pk>/editar/', views.estados_editar, name='estados_editar'),
    path('estados/<int:pk>/eliminar/', views.estados_eliminar, name='estados_eliminar'),
    
    # Socios
    path('socios/', views.socios_listar, name='socios_listar'),
    path('socios/crear/', views.socios_crear, name='socios_crear'),
    path('socios/<int:pk>/', views.socios_detalle, name='socios_detalle'),
    path('socios/<int:pk>/editar/', views.socios_editar, name='socios_editar'),
    path('socios/<int:pk>/eliminar/', views.socios_eliminar, name='socios_eliminar'),
    
    # Contactos de Socios
    path('socios/<int:socio_pk>/contactos/crear/', views.contactos_crear, name='contactos_crear'),
    path('socios/<int:socio_pk>/contactos/<int:pk>/editar/', views.contactos_editar, name='contactos_editar'),
    path('socios/<int:socio_pk>/contactos/<int:pk>/eliminar/', views.contactos_eliminar, name='contactos_eliminar'),
    
    # Expedientes
    path('expedientes/', views.expedientes_listar, name='expedientes_listar'),
    path('expedientes/crear/', views.expedientes_crear, name='expedientes_crear'),
    path('expedientes/<int:pk>/editar/', views.expedientes_editar, name='expedientes_editar'),
    path('expedientes/<int:pk>/eliminar/', views.expedientes_eliminar, name='expedientes_eliminar'),
    
    # Roles
    path('roles/', views.roles_listar, name='roles_listar'),
    path('roles/crear/', views.roles_crear, name='roles_crear'),
    path('roles/<int:pk>/editar/', views.roles_editar, name='roles_editar'),
    path('roles/<int:pk>/eliminar/', views.roles_eliminar, name='roles_eliminar'),
    
    # Usuarios
    path('usuarios/', views.usuarios_listar, name='usuarios_listar'),
    path('usuarios/crear/', views.usuarios_crear, name='usuarios_crear'),
    path('usuarios/<int:pk>/editar/', views.usuarios_editar, name='usuarios_editar'),
    path('usuarios/<int:pk>/eliminar/', views.usuarios_eliminar, name='usuarios_eliminar'),
    path('usuarios/<int:pk>/asignar-roles/', views.usuarios_asignar_roles, name='usuarios_asignar_roles'),

    #path('api/auth/login/', api_views.api_login, name='api_login'),
    #path('api/auth/verificar-2fa/', api_views.api_verificar_2fa, name='api_verificar_2fa'),
    #path('api/auth/reenviar-2fa/', api_views.api_reenviar_codigo_2fa, name='api_reenviar_2fa'),
    #path('api/auth/cambiar-password/', api_views.api_cambiar_password, name='api_cambiar_password'),
    #path('api/auth/refresh/', api_views.api_refresh_token, name='api_refresh_token'),
    #path('api/auth/logout/', api_views.api_logout, name='api_logout'),
    #path('api/auth/me/', api_views.api_usuario_actual, name='api_usuario_actual'),
] 