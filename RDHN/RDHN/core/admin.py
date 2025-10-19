from django.contrib import admin
from .models import (
    CatEstado, Socio, SocioContacto, ExpedienteDigital,
    Rol, Usuario, UsuarioRol
)

@admin.register(CatEstado)
class CatEstadoAdmin(admin.ModelAdmin):
    list_display = ['dominio', 'codigo', 'nombre', 'es_final', 'orden']
    list_filter = ['dominio', 'es_final']
    search_fields = ['dominio', 'codigo', 'nombre']
    ordering = ['dominio', 'orden', 'codigo']

@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    list_display = ['numero_socio', 'nombre_completo', 'identidad', 'fecha_ingreso', 'id_estado']
    list_filter = ['id_estado', 'fecha_ingreso']
    search_fields = ['numero_socio', 'primer_nombre', 'primer_apellido', 'identidad']
    ordering = ['-creado_en']

@admin.register(SocioContacto)
class SocioContactoAdmin(admin.ModelAdmin):
    list_display = ['socio', 'tipo', 'valor', 'preferido', 'activo']
    list_filter = ['tipo', 'preferido', 'activo']
    search_fields = ['socio__numero_socio', 'valor']
    ordering = ['socio', 'tipo']

@admin.register(ExpedienteDigital)
class ExpedienteDigitalAdmin(admin.ModelAdmin):
    list_display = ['numero_expediente', 'socio', 'fecha_creacion']
    search_fields = ['numero_expediente', 'socio__numero_socio']
    ordering = ['-creado_en']

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ['nombre_rol', 'estado', 'creado_en']
    list_filter = ['estado']
    search_fields = ['nombre_rol']
    ordering = ['nombre_rol']

# Inline para mostrar los roles asignados en el admin de Usuario
class UsuarioRolInline(admin.TabularInline):
    model = UsuarioRol
    fk_name = 'usuario'  # ✅ Especifica cuál ForeignKey usar
    extra = 1
    fields = ['rol', 'fecha_asignacion', 'fecha_revocacion', 'estado', 'asignado_por']
    readonly_fields = ['fecha_asignacion']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('rol', 'asignado_por')

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'email', 'socio', 'is_active', 'is_staff', 'ultimo_acceso']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'requiere_cambio_password']
    search_fields = ['usuario', 'email', 'socio__numero_socio', 'socio__primer_nombre', 'socio__primer_apellido']
    ordering = ['-creado_en']
    
    