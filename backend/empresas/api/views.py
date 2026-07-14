"""CRUD de empresas. Reservado al administrador general (superusuario).

Vive en Configuración: es el único lugar donde se dan de alta los tenants. Un
administrador de empresa NO llega aquí — solo gestiona usuarios dentro de la
suya.
"""
from __future__ import annotations

from django.db.models import Count
from django.db.models.deletion import ProtectedError
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from empresas.models import Empresa
from users.permissions import IsSuperAdmin

from .serializers import EmpresaSerializer


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
