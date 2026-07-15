"""CRUD de empresas. Reservado al administrador general (superusuario).

Vive en Configuración: es el único lugar donde se dan de alta los tenants. Un
administrador de empresa NO llega aquí — solo gestiona usuarios dentro de la
suya.
"""
from __future__ import annotations

from django.db.models import Count
from django.db.models.deletion import ProtectedError
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from empresas.models import ApiKey, Empresa
from users.permissions import IsSuperAdmin

from .serializers import (
    ApiKeyCreadaSerializer,
    ApiKeySerializer,
    EmpresaSerializer,
)


class EmpresaViewSet(viewsets.ModelViewSet):
    serializer_class = EmpresaSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
    search_fields = ['nombre', 'nit']
    ordering_fields = ['nombre', 'creado']

    def get_queryset(self):
        # El sufijo `_count` no es cosmético: una anotación no puede llamarse
        # igual que la relación que cuenta ('usuarios', 'televisores').
        return Empresa.objects.annotate(
            usuarios_count=Count('usuarios', distinct=True),
            televisores_count=Count('televisores', distinct=True),
        )

    def destroy(self, request, *args, **kwargs):
        # Las FK son PROTECT: una empresa con datos no se borra por accidente.
        # Se desactiva (`activa=False`), que además corta el acceso a sus usuarios.
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {
                    'detail': 'Esta empresa tiene usuarios o televisores asociados. '
                    'Desactívala en vez de eliminarla.'
                },
                status=status.HTTP_409_CONFLICT,
            )

    # ------------------------------------------------------------------
    # API-keys de integración de la empresa (crear / listar / revocar).
    # Solo el administrador general (permiso del viewset) las gestiona.
    # ------------------------------------------------------------------
    @action(detail=True, methods=['get', 'post'], url_path='api-keys')
    def api_keys(self, request, pk=None):
        empresa = self.get_object()
        if request.method == 'POST':
            nombre = str(request.data.get('nombre', '')).strip()
            if not nombre:
                return Response(
                    {'nombre': 'Ponle un nombre para identificar al integrador.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Endurecimiento opcional: si no se envían, la clave queda sin
            # restricción de IP y sin caducidad (el uso documentado por defecto).
            api_key, clave = ApiKey.generar(
                empresa=empresa,
                nombre=nombre,
                ips_permitidas=str(request.data.get('ips_permitidas', '')),
                expira=request.data.get('expira') or None,
            )
            # La clave en claro SOLO viaja en esta respuesta; después no se puede
            # recuperar (en la base queda su hash). Si se pierde, se genera otra.
            return Response(
                ApiKeyCreadaSerializer(
                    {
                        'id': api_key.id,
                        'nombre': api_key.nombre,
                        'prefijo': api_key.prefijo,
                        'clave': clave,
                    }
                ).data,
                status=status.HTTP_201_CREATED,
            )

        keys = empresa.api_keys.all()
        return Response(ApiKeySerializer(keys, many=True).data)

    @action(
        detail=True,
        methods=['post'],
        url_path=r'api-keys/(?P<key_id>[0-9a-f-]+)/revocar',
    )
    def revocar_api_key(self, request, pk=None, key_id=None):
        empresa = self.get_object()
        api_key = empresa.api_keys.filter(pk=key_id).first()
        if api_key is None:
            return Response(
                {'detail': 'API key no encontrada.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        # Revocar = desactivar (no se borra): así el prefijo no se reutiliza y el
        # registro sirve de bitácora de qué claves existieron.
        api_key.activa = False
        api_key.save(update_fields=['activa'])
        return Response(ApiKeySerializer(api_key).data)
