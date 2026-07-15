from django.contrib import admin

from .models import ApiKey, Empresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nit', 'activa', 'creado')
    list_filter = ('activa',)
    search_fields = ('nombre', 'nit')
    readonly_fields = ('creado',)


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    # La clave nunca se muestra (solo su hash existe): desde el admin se pueden
    # revocar (activa=False), no ver. Para crear una con su clave visible se usa
    # el endpoint de gestión (empresas/<id>/api-keys/).
    list_display = (
        'nombre', 'empresa', 'prefijo', 'activa', 'expira', 'creada', 'ultimo_uso',
    )
    list_filter = ('empresa', 'activa')
    search_fields = ('nombre', 'prefijo')
    # ips_permitidas y expira SÍ se pueden editar desde el admin (endurecer una
    # clave existente); el prefijo y el hash no.
    readonly_fields = ('prefijo', 'hash_clave', 'creada', 'ultimo_uso')
    list_select_related = ('empresa',)
