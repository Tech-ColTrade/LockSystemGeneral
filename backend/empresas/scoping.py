"""Aislamiento multi-tenant: la única puerta por la que se acota el acceso.

Regla del sistema: **un usuario solo ve los datos de su empresa**. La excepción
es el superusuario (`empresa` vacía), que ve el sistema completo.

Todo queryset que salga a la API tiene que pasar por `acotar()`, y todo registro
que se cree tiene que tomar su empresa de `empresa_del_usuario()` — **nunca** de
lo que venga en el cuerpo de la petición, o cualquiera podría escribir en otra
empresa mandando un `empresa_id` a mano.

`acotar()` falla cerrado: un usuario que no es superusuario y no tiene empresa
no ve nada (`.none()`), en vez de verlo todo. Si algún día alguien crea un
usuario sin empresa por error, el peor caso es que no vea sus datos, no que vea
los de los demás.
"""
from __future__ import annotations

from rest_framework.exceptions import PermissionDenied


def es_acceso_global(user) -> bool:
    """El usuario ve todas las empresas (superusuario / admin general)."""
    return bool(user and user.is_authenticated and user.is_superuser)


def empresa_del_usuario(user):
    """Empresa a la que está confinado el usuario, o None si es acceso global."""
    if not user or not user.is_authenticated:
        return None
    return user.empresa


def acotar(queryset, user, campo: str = 'empresa'):
    """Acota un queryset a la empresa del usuario.

    `campo` es la ruta a la empresa desde el modelo del queryset: 'empresa' en
    los modelos que la llevan, o algo como 'job__empresa' cuando la empresa vive
    en la tabla padre (p. ej. BulkSyncItem).
    """
    if es_acceso_global(user):
        return queryset
    empresa_id = getattr(user, 'empresa_id', None)
    if empresa_id is None:
        return queryset.none()
    return queryset.filter(**{f'{campo}_id': empresa_id})


def empresa_para_crear(user):
    """Empresa a la que debe pertenecer un registro creado por este usuario.

    El superusuario no tiene empresa propia: no puede crear televisores ni
    usuarios "en el aire", tiene que hacerlo desde la empresa correspondiente
    (ver `EmpresaScopedViewSetMixin.empresa_destino`).
    """
    empresa = empresa_del_usuario(user)
    if empresa is None:
        raise PermissionDenied(
            'Tu cuenta no tiene una empresa asociada, así que no puede crear '
            'registros. Indica la empresa o usa una cuenta de empresa.'
        )
    return empresa


class EmpresaScopedViewSetMixin:
    """Aísla un ViewSet/vista por empresa: lectura acotada y escritura marcada.

    - `get_queryset()` filtra por la empresa del usuario. Como `get_object()`
      sale de este queryset, pedir un registro ajeno da **404** y no 403: un 403
      confirmaría que ese id existe.
    - `perform_create()` sella el registro con la empresa del usuario, ignorando
      cualquier `empresa` que venga en el cuerpo.

    `empresa_campo` se sobreescribe cuando la empresa no está en el propio
    modelo (p. ej. 'job__empresa').
    """

    empresa_campo = 'empresa'

    def get_queryset(self):
        return acotar(super().get_queryset(), self.request.user, self.empresa_campo)

    def empresa_destino(self):
        """Empresa con la que se sellará lo que se cree en esta petición.

        Para un usuario normal es la suya. El superusuario, que no tiene empresa,
        debe indicarla explícitamente (`?empresa=<uuid>` o en el cuerpo).
        """
        user = self.request.user
        if es_acceso_global(user):
            from empresas.models import Empresa

            empresa_id = (
                self.request.data.get('empresa')
                or self.request.query_params.get('empresa')
            )
            if not empresa_id:
                raise PermissionDenied(
                    'Como administrador general debes indicar a qué empresa '
                    'pertenece el registro (campo "empresa").'
                )
            empresa = Empresa.objects.filter(pk=empresa_id).first()
            if empresa is None:
                raise PermissionDenied('La empresa indicada no existe.')
            return empresa
        return empresa_para_crear(user)

    def perform_create(self, serializer):
        serializer.save(empresa=self.empresa_destino())
