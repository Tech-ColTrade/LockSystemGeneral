from django.contrib import admin

from .models import BulkSyncItem, BulkSyncJob, PinCodeUsado, SyncJob, Televisor


@admin.register(Televisor)
class TelevisorAdmin(admin.ModelAdmin):
    list_display = (
        'mac_address', 'serial_number', 'empresa', 'numero_credito',
        'inhabilitado', 'created_at',
    )
    list_filter = ('empresa', 'inhabilitado')
    search_fields = ('mac_address', 'serial_number', 'numero_credito')
    list_select_related = ('empresa',)


@admin.register(SyncJob)
class SyncJobAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'televisor', 'empresa', 'inhabilitar', 'estado', 'porcentaje', 'creado',
    )
    list_filter = ('empresa', 'estado', 'inhabilitar')
    readonly_fields = ('creado', 'actualizado', 'terminado_en')
    list_select_related = ('empresa', 'televisor')


@admin.register(PinCodeUsado)
class PinCodeUsadoAdmin(admin.ModelAdmin):
    list_display = ('mac_address', 'empresa', 'passcode', 'pin_code', 'creado')
    list_filter = ('empresa',)
    search_fields = ('mac_address', 'passcode', 'pin_code')
    list_select_related = ('empresa',)


class BulkSyncItemInline(admin.TabularInline):
    model = BulkSyncItem
    extra = 0


@admin.register(BulkSyncJob)
class BulkSyncJobAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'empresa', 'estado', 'procesados', 'total', 'ok_count',
        'error_count', 'creado',
    )
    list_filter = ('empresa', 'estado')
    readonly_fields = ('creado', 'actualizado', 'terminado_en')
    inlines = [BulkSyncItemInline]
