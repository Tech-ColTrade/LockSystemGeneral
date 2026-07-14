"""Autenticación JWT con revocación server-side.

SimpleJWT es stateless: un token válido lo es hasta que expira. Para poder
"cerrar sesión de verdad" (invalidar tokens ya emitidos) sin depender de la app
`token_blacklist` (bloqueada en este entorno por el límite de rutas de Windows),
cada JWT lleva la **versión de token** con la que se emitió (claim `tv`). El
logout incrementa `user.token_version`, de modo que todos los tokens anteriores
dejan de coincidir. Es exacto: no tiene la ambigüedad de segundos que tendría
comparar por fecha de emisión (`iat`).
"""
from __future__ import annotations

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

# Nombre del claim que transporta la versión de token.
TOKEN_VERSION_CLAIM = 'tv'


def token_esta_revocado(user, validated_token) -> bool:
    """True si la versión del token no coincide con la vigente del usuario."""
    return validated_token.get(TOKEN_VERSION_CLAIM) != getattr(user, 'token_version', 0)


def empresa_inactiva(user) -> bool:
    """True si el usuario pertenece a una empresa desactivada.

    Desactivar la empresa corta el acceso de toda su gente sin tener que ir
    usuario por usuario. Se comprueba en cada petición y no solo en el login:
    de lo contrario, un token ya emitido seguiría entrando hasta expirar.
    """
    empresa = getattr(user, 'empresa', None)
    return empresa is not None and not empresa.activa


class RevocationAwareJWTAuthentication(JWTAuthentication):
    """JWTAuthentication que además respeta la revocación por versión de token."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if token_esta_revocado(user, validated_token):
            raise InvalidToken('La sesión fue cerrada. Inicia sesión de nuevo.')
        if empresa_inactiva(user):
            raise InvalidToken('La empresa de tu cuenta está desactivada.')
        return user
