// Cliente global de React Query.
//
// Estrategia anti-datos-rancios (lo que más importa):
//   - `staleTime` moderado: los datos se muestran al instante desde caché y se
//     revalidan en segundo plano. No es agresivo: a los 30 s ya se refrescan.
//   - Las MUTACIONES (create/update/delete) invalidan sus listas explícitamente
//     (ver los hooks *.queries.ts), así que un registro nuevo aparece siempre.
//   - `refetchOnWindowFocus`: al volver a la pestaña se revalida.
//   - No se reintentan errores 4xx (deterministas): evita machacar un 403/404.

import { QueryClient } from '@tanstack/react-query'

import { ApiError } from '@/lib/http/errors'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000, // 30 s "fresco"; luego se revalida en segundo plano.
      gcTime: 5 * 60_000, // 5 min en memoria tras dejar de usarse.
      refetchOnWindowFocus: true,
      retry: (failureCount, error) => {
        // Un 4xx no cambia si se reintenta: no insistas.
        if (
          error instanceof ApiError &&
          error.status >= 400 &&
          error.status < 500
        ) {
          return false
        }
        return failureCount < 2
      },
    },
  },
})
