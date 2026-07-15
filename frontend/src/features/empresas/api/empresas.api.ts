// Capa de acceso a la API de empresas (tenants). Solo el administrador general.

import { apiFetch } from '@/lib/http/client'
import type { Paginated } from '@/shared/types'

export interface Empresa {
  id: string
  nombre: string
  nit: string
  activa: boolean
  creado: string
  /** Cuántos usuarios y televisores tiene (los cuenta el backend). */
  usuarios: number
  televisores: number
}

export interface EmpresaInput {
  nombre: string
  nit?: string
  activa?: boolean
}

export interface ApiKey {
  id: string
  nombre: string
  prefijo: string
  activa: boolean
  /** IPs/rangos permitidos (uno por línea). Vacío = cualquier IP. */
  ips_permitidas: string
  /** Fecha de caducidad ISO, o null = no expira. */
  expira: string | null
  creada: string
  ultimo_uso: string | null
}

export interface CrearApiKeyInput {
  nombre: string
  /** Opcional. Endurecimiento: solo estas IPs/rangos podrán usar la clave. */
  ips_permitidas?: string
  /** Opcional. Endurecimiento: fecha ISO de caducidad. */
  expira?: string | null
}

/** Respuesta de creación: la clave en claro viene UNA sola vez. */
export interface ApiKeyCreada {
  id: string
  nombre: string
  prefijo: string
  clave: string
}

export const empresasApi = {
  list: () => apiFetch<Paginated<Empresa>>('/api/empresas/'),

  // --- API-keys de integración (por empresa) ---
  listApiKeys: (empresaId: string) =>
    apiFetch<ApiKey[]>(`/api/empresas/${empresaId}/api-keys/`),

  crearApiKey: (empresaId: string, data: CrearApiKeyInput) =>
    apiFetch<ApiKeyCreada>(`/api/empresas/${empresaId}/api-keys/`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  revocarApiKey: (empresaId: string, keyId: string) =>
    apiFetch<ApiKey>(`/api/empresas/${empresaId}/api-keys/${keyId}/revocar/`, {
      method: 'POST',
    }),

  create: (data: EmpresaInput) =>
    apiFetch<Empresa>('/api/empresas/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: Partial<EmpresaInput>) =>
    apiFetch<Empresa>(`/api/empresas/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
}
