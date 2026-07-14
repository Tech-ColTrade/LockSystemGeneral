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

export const empresasApi = {
  list: () => apiFetch<Paginated<Empresa>>('/api/empresas/'),

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
