import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import type { Paginated } from '@/shared/types'

/** Maneja el estado de un listado paginado (página, carga, error) sobre React
 *  Query: la página anterior se conserva mientras carga la siguiente (sin
 *  parpadeo) y el resultado queda cacheado para volver a él al instante.
 *
 *  `queryKey` identifica el listado y DEBE incluir sus parámetros (id, filtros…);
 *  la página se le añade internamente. La interfaz de retorno es la misma de
 *  antes, así que las páginas que lo usan no cambian salvo pasar la clave. */
export function usePaginatedList<T>(
  queryKey: readonly unknown[],
  fetcher: (page: number) => Promise<Paginated<T>>,
) {
  const [page, setPage] = useState(1)

  const { data, isPending, isError, error } = useQuery({
    queryKey: [...queryKey, { page }],
    queryFn: () => fetcher(page),
    placeholderData: keepPreviousData,
  })

  return {
    items: data?.results ?? [],
    count: data?.count ?? 0,
    page,
    setPage,
    loading: isPending,
    error: isError ? (error as Error).message : null,
  }
}
