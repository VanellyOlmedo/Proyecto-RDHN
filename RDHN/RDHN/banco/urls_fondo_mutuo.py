from django.urls import path
from . import views_fondo_mutuo as views

app_name = 'fondo_mutuo'

urlpatterns = [
    # Dashboard
    path('', views.fondo_mutuo_dashboard, name='dashboard'),
    
    # Gestión de Fondos (Períodos)
    path('fondos/', views.fondos_listar, name='fondos_listar'),
    path('fondos/crear/', views.fondos_crear, name='fondos_crear'),
    path('fondos/crear-actual/', views.fondos_crear_actual, name='fondos_crear_actual'),
    path('fondos/<int:pk>/', views.fondos_detalle, name='fondos_detalle'),
    path('fondos/<int:pk>/cerrar/', views.fondos_cerrar, name='fondos_cerrar'),
    
    # Aportes
    path('aportes/crear/', views.aportes_crear, name='aportes_crear'),
    
    # Movimientos
    path('movimientos/', views.movimientos_listar, name='movimientos_listar'),
    path('movimientos/<int:pk>/', views.movimientos_detalle, name='movimientos_detalle'),
    path('movimientos/<int:pk>/imprimir/', views.movimientos_imprimir, name='movimientos_imprimir'),
    
    # Solicitudes de Ayuda
    path('solicitudes/', views.solicitudes_listar, name='solicitudes_listar'),
    path('solicitudes/pendientes/', views.solicitudes_pendientes, name='solicitudes_pendientes'),
    path('solicitudes/crear/', views.solicitudes_crear, name='solicitudes_crear'),
    path('solicitudes/<int:pk>/', views.solicitudes_detalle, name='solicitudes_detalle'),
    path('solicitudes/<int:pk>/aprobar/', views.solicitudes_aprobar, name='solicitudes_aprobar'),
    path('solicitudes/<int:pk>/rechazar/', views.solicitudes_rechazar, name='solicitudes_rechazar'),
    
    # Reportes
    path('reportes/kardex/', views.reportes_kardex, name='reportes_kardex'),
    
    # API AJAX
    path('api/periodo-actual/', views.api_periodo_actual, name='api_periodo_actual'),
    path('api/socio-info/', views.api_socio_info, name='api_socio_info'),
]