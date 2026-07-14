// Tipos del dominio de autenticación (alineados con la API de Django `users`).

export type Role = 'admin' | 'operador' | 'consulta'

/** Empresa (tenant) tal como viene anidada en el perfil. */
export interface EmpresaBreve {
  id: string
  nombre: string
}

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  role: Role
  role_display: string
  /**
   * Empresa a la que pertenece la cuenta: define QUÉ datos ve (el rol define
   * qué puede hacer). Es `null` solo en el administrador general.
   */
  empresa: EmpresaBreve | null
  /** Administrador general: ve y gestiona todas las empresas. */
  is_superadmin: boolean
  is_active: boolean
  date_joined: string
  /** Preferencia de color de acento (clave del preset, p. ej. 'neutro'). */
  accent: string
}

export interface AuthTokens {
  access: string
  refresh: string
}

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated'
