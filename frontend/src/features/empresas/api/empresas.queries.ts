// Hooks de React Query para empresas (tenants). Mismo patrón que televisores.
// El toggle de "activa" conserva la actualización OPTIMISTA (el switch responde
// al instante y se revierte si el backend falla), ahora vía onMutate/onError.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  empresasApi,
  type Empresa,
  type EmpresaInput,
} from '@/features/empresas/api/empresas.api'
import type { Paginated } from '@/shared/types'

export const empresasKeys = {
  all: ['empresas'] as const,
  list: () => ['empresas', 'list'] as const,
}

/** Lista de empresas (solo administrador general). */
export function useEmpresas(enabled = true) {
  return useQuery({
    queryKey: empresasKeys.list(),
    queryFn: () => empresasApi.list(),
    enabled,
  })
}

export function useCrearEmpresa() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: EmpresaInput) => empresasApi.create(data),
    onSuccess: () => {
      // Refresca la lista: la nueva empresa aparece (el backend ordena por nombre).
      qc.invalidateQueries({ queryKey: empresasKeys.all })
    },
  })
}

export function useActualizarEmpresa() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<EmpresaInput> }) =>
      empresasApi.update(id, data),
    // Optimista: pinta el cambio en la caché antes de que responda el backend.
    onMutate: async ({ id, data }) => {
      await qc.cancelQueries({ queryKey: empresasKeys.list() })
      const prev = qc.getQueryData<Paginated<Empresa>>(empresasKeys.list())
      if (prev) {
        qc.setQueryData<Paginated<Empresa>>(empresasKeys.list(), {
          ...prev,
          results: prev.results.map((e) =>
            e.id === id ? { ...e, ...data } : e,
          ),
        })
      }
      return { prev }
    },
    // Si falla, se revierte al estado anterior (el switch vuelve a su lugar).
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(empresasKeys.list(), ctx.prev)
    },
    // Al terminar (ok o error) se revalida para quedar consistentes con el server.
    onSettled: () => {
      qc.invalidateQueries({ queryKey: empresasKeys.all })
    },
  })
}
