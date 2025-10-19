from django.urls import path
from . import views

app_name = 'banco'

urlpatterns = [
    # Tipos de Cuenta
    path('tipos-cuenta/', views.tipos_cuenta_listar, name='tipos_cuenta_listar'),
    path('tipos-cuenta/crear/', views.tipos_cuenta_crear, name='tipos_cuenta_crear'),
    path('tipos-cuenta/<int:pk>/editar/', views.tipos_cuenta_editar, name='tipos_cuenta_editar'),
    path('tipos-cuenta/<int:pk>/eliminar/', views.tipos_cuenta_eliminar, name='tipos_cuenta_eliminar'),
    
    # Tipos de Préstamo
    #path('tipos-prestamo/', views.tipos_prestamo_listar, name='tipos_prestamo_listar'),
    #path('tipos-prestamo/crear/', views.tipos_prestamo_crear, name='tipos_prestamo_crear'),
    #path('tipos-prestamo/<int:pk>/editar/', views.tipos_prestamo_editar, name='tipos_prestamo_editar'),
    #path('tipos-prestamo/<int:pk>/eliminar/', views.tipos_prestamo_eliminar, name='tipos_prestamo_eliminar'),
    
    # Cuentas de Ahorro
    path('cuentas/', views.cuentas_listar, name='cuentas_listar'),
    path('cuentas/crear/', views.cuentas_crear, name='cuentas_crear'),
    path('cuentas/<int:pk>/', views.cuentas_detalle, name='cuentas_detalle'),
    path('cuentas/<int:pk>/editar/', views.cuentas_editar, name='cuentas_editar'),
    path('cuentas/<int:pk>/eliminar/', views.cuentas_eliminar, name='cuentas_eliminar'),
    path('cuentas/<int:pk>/depositar/', views.cuentas_depositar, name='cuentas_depositar'),
    path('cuentas/<int:pk>/retirar/', views.cuentas_retirar, name='cuentas_retirar'),
    
    # Transacciones
    path('transacciones/', views.transacciones_listar, name='transacciones_listar'),
    path('transacciones/<int:pk>/', views.transacciones_detalle, name='transacciones_detalle'),
    
    # Préstamos
    #path('prestamos/', views.prestamos_listar, name='prestamos_listar'),
    #path('prestamos/crear/', views.prestamos_crear, name='prestamos_crear'),
   # path('prestamos/<int:pk>/', views.prestamos_detalle, name='prestamos_detalle'),
    #path('prestamos/<int:pk>/editar/', views.prestamos_editar, name='prestamos_editar'),
    #path('prestamos/<int:pk>/eliminar/', views.prestamos_eliminar, name='prestamos_eliminar'),
    #path('prestamos/<int:pk>/aprobar/', views.prestamos_aprobar, name='prestamos_aprobar'),
    #path('prestamos/<int:pk>/rechazar/', views.prestamos_rechazar, name='prestamos_rechazar'),
    #path('prestamos/<int:pk>/desembolsar/', views.prestamos_desembolsar, name='prestamos_desembolsar'),
    
    # Garantes
   # path('prestamos/<int:prestamo_pk>/garantes/agregar/', views.garantes_agregar, name='garantes_agregar'),
    #path('prestamos/<int:prestamo_pk>/garantes/<int:pk>/eliminar/', views.garantes_eliminar, name='garantes_eliminar'),
    
    # Pagos de Préstamos
   # path('prestamos/<int:prestamo_pk>/pagos/crear/', views.pagos_crear, name='pagos_crear'),
    #path('pagos/<int:pk>/', views.pagos_detalle, name='pagos_detalle'),
    
    # Dividendos
    path('dividendos/periodos/', views.periodos_listar, name='periodos_listar'),
    path('dividendos/periodos/crear/', views.periodos_crear, name='periodos_crear'),
    path('dividendos/periodos/', views.dividendos_listar, name='dividendos_listar'),
    
    # Notificaciones
    path('notificaciones/', views.notificaciones_listar, name='notificaciones_listar'),
    path('notificaciones/crear/', views.notificaciones_crear, name='notificaciones_crear'),
    path('notificaciones/<int:pk>/', views.notificaciones_detalle, name='notificaciones_detalle'),
]