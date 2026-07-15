// Hooks de React Query para televisores. Es el PATRÓN a replicar en las demás
// features (empresas, usuarios…): claves jerárquicas + mutaciones que invalidan.
//
// Anti-datos-rancios: toda mutación invalida `televisoresKeys.all`, que cubre
// listas y detalles. Así, tras crear/editar/borrar, la lista se vuelve a pedir
// y el cambio se ve al instante (no queda "escondido" por la caché).

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'

import { televisoresApi } from '@/features/televisores/api/televisores.api'
import type { TelevisorInput } from '@/features/televisores/types'

export const televisoresKeys = {
  // Raíz de todo lo cacheado de televisores. Invalidar aquí refresca todo.
  all: ['televisores'] as const,
  list: (search: string, page: number) =>
    ['televisores', 'list', { search, page }] as const,
  detail: (id: number | string) =>
    ['televisores', 'detail', String(id)] as const,
}

/** Lista paginada. `keepPreviousData` conserva la página anterior mientras
 *  carga la siguiente (la tabla no parpadea a vacío). */
export function useTelevisores(search: string, page: number) {
  return useQuery({
    queryKey: televisoresKeys.list(search, page),
    queryFn: () => televisoresApi.list(search, page),
    placeholderData: keepPreviousData,
  })
}

/** Detalle de un televisor. `enabled` permite no pedirlo (p. ej. en "crear"). */
export function useTelevisor(id: number | string, enabled = true) {
  return useQuery({
    queryKey: televisoresKeys.detail(id),
    queryFn: () => televisoresApi.get(id),
    enabled: enabled && id != null && id !== '',
  })
}

export function useCrearTelevisor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TelevisorInput) => televisoresApi.create(data),
    onSuccess: () => {
      // El nuevo registro debe aparecer: se refresca toda la caché de televisores.
      qc.invalidateQueries({ queryKey: televisoresKeys.all })
    },
  })
}

export function useActualizarTelevisor(id: number | string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<TelevisorInput>) =>
      televisoresApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: televisoresKeys.all })
    },
  })
}

export function useEliminarTelevisor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number | string) => televisoresApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: televisoresKeys.all })
    },
  })
}
