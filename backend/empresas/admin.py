from django.contrib import admin

from .models import Empresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nit', 'activa', 'creado')
    list_filter = ('activa',)
    search_fields = ('nombre', 'nit')
    readonly_fields = ('creado',)
