// Política de permisos del frontend (espejo de `users/permissions.py` en el
// backend). Aquí solo se decide qué se MUESTRA; la autorización real la impone
// el backend. Mantener ambas listas alineadas.

import type { Role, User } from '@/features/auth/types'

/**
 * Administrador general: el único que ve todas las empresas y puede crearlas.
 * Los demás (incluido el rol `admin`) están confinados a la suya.
 */
export function isSuperAdmin(user: User | null): boolean {
  return user?.is_superadmin === true
}

/** Administrador: gestión de usuarios + todos los módulos (dentro de su empresa). */
export function isAdmin(user: User | null): boolean {
  return user?.role === 'admin' || isSuperAdmin(user)
}

/** Operador o Administrador: puede realizar gestiones de escritura. */
export function canOperate(user: User | null): boolean {
  return user?.role === 'operador' || isAdmin(user)
}

export const ROLE_LABELS: Record<Role, string> = {
  admin: 'Administrador',
  operador: 'Operador',
  consulta: 'Consulta',
}
