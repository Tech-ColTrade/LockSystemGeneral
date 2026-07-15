"""Permisos DRF basados en el rol del usuario.

La política se define aquí (una sola fuente de verdad) y las vistas la aplican.
El frontend oculta/deshabilita botones, pero la autorización real vive en el
backend: aunque alguien llame la API a mano, estos permisos la protegen.
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Solo administradores (rol admin o superusuario)."""

    message = 'Se requiere rol de Administrador.'

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_admin_role)


class IsSuperAdmin(BasePermission):
    """Solo el administrador general (superusuario), el que ve todas las empresas."""

    message = 'Se requiere ser Administrador general.'

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_superadmin)


class CanOperate(BasePermission):
    """Solo operadores o administradores (acciones de escritura/gestión).

    Excluye al administrador general (ver `User.can_operate`): es de solo lectura
    sobre los datos de las empresas.
    """

    message = 'Se requiere rol de Operador o Administrador.'

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.can_operate)


class IsNotGlobalAdmin(BasePermission):
    """Permite a cualquier usuario de empresa (incluido Consulta) pero NO al
    administrador general.

    Es para acciones que el rol Consulta sí puede hacer pero que mutan datos
    —entregar un Código Pin lo marca como usado y desbloquea el equipo—, de las
    que el auditor global debe quedar fuera para ser de solo lectura de verdad.
    """

    message = 'El administrador general es de solo lectura sobre los televisores.'

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and not user.is_superadmin)
