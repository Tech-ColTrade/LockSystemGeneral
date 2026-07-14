// Hook de conveniencia: expone los flags de permiso del usuario autenticado.

import { useAuth } from '@/features/auth/context/auth-context'
import { canOperate, isAdmin, isSuperAdmin } from '@/features/auth/permissions'

export function usePermissions() {
  const { user } = useAuth()
  return {
    user,
    isAdmin: isAdmin(user),
    isSuperAdmin: isSuperAdmin(user),
    canOperate: canOperate(user),
    /** Empresa de la sesión (null en el administrador general). */
    empresa: user?.empresa ?? null,
  }
}
