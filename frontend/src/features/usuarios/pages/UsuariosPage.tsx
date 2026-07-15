import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Building2, ChevronLeft, ChevronRight, CircleAlert, Plus } from 'lucide-react'
import { useUsuarios } from '@/features/usuarios/api/usuarios.queries'
import { usePermissions } from '@/features/auth/usePermissions'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const PAGE_SIZE = 10

export function UsuariosPage() {
  // La columna Empresa solo tiene sentido para el administrador general: a un
  // admin de empresa todos los usuarios que ve son, por definición, de la suya.
  const { isSuperAdmin } = usePermissions()
  const columnas = isSuperAdmin ? 6 : 5

  const [page, setPage] = useState(1)
  const [query, setQuery] = useState('')
  const [search, setSearch] = useState('')

  const { data, isPending, isFetching, isError, error } = useUsuarios(search, page)
  const items = data?.results ?? []
  const count = data?.count ?? 0

  function onSearch(e: React.FormEvent) {
    e.preventDefault()
    setPage(1)
    setSearch(query.trim())
  }

  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE))
  // Esqueletos solo en la primera carga; al paginar/buscar se atenúan las filas.
  const showSkeleton = isPending
  const refreshing = isFetching && !isPending
  const displayError = isError ? (error as Error).message : null

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Usuarios</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Gestiona las cuentas de la plataforma y sus roles.
          </p>
        </div>
        <Button render={<Link to="/usuarios/nuevo" />}>
          <Plus />
          Nuevo usuario
        </Button>
      </div>

      <form onSubmit={onSearch} className="mb-4 flex max-w-sm gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar por correo o nombre…"
        />
        <Button type="submit" variant="outline">
          Buscar
        </Button>
      </form>

      {displayError && (
        <Alert variant="destructive" className="mb-4">
          <CircleAlert />
          <AlertTitle>No se pudo cargar</AlertTitle>
          <AlertDescription>{displayError}</AlertDescription>
        </Alert>
      )}

      <Card className="gap-0 overflow-hidden p-0">
        <Table
          aria-busy={refreshing}
          className={
            refreshing ? 'opacity-60 transition-opacity duration-200' : undefined
          }
        >
          <TableHeader>
            <TableRow>
              <TableHead>Correo</TableHead>
              <TableHead>Nombre</TableHead>
              {isSuperAdmin && <TableHead>Empresa</TableHead>}
              <TableHead>Rol</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead className="text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {showSkeleton ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: columnas }).map((__, j) => (
                    <TableCell key={j}>
                      <Skeleton className="h-4 w-full max-w-32" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columnas}
                  className="h-24 text-center text-muted-foreground"
                >
                  No se encontraron usuarios.
                </TableCell>
              </TableRow>
            ) : (
              items.map((u) => (
                <TableRow key={u.id}>
                  <TableCell className="font-medium">
                    <Link to={`/usuarios/${u.id}/editar`} className="hover:underline">
                      {u.email}
                    </Link>
                  </TableCell>
                  <TableCell>{u.full_name || '—'}</TableCell>
                  {isSuperAdmin && (
                    <TableCell>
                      {u.empresa ? (
                        <span className="flex items-center gap-1.5">
                          <Building2 className="size-3.5 text-muted-foreground" />
                          {u.empresa.nombre}
                        </span>
                      ) : (
                        <Badge variant="outline" className="text-muted-foreground">
                          Admin general
                        </Badge>
                      )}
                    </TableCell>
                  )}
                  <TableCell>
                    <Badge variant="secondary">{u.role_display}</Badge>
                  </TableCell>
                  <TableCell>
                    {u.is_active ? (
                      <Badge variant="secondary">Activo</Badge>
                    ) : (
                      <Badge variant="outline" className="text-muted-foreground">
                        Inactivo
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      render={<Link to={`/usuarios/${u.id}/editar`} />}
                    >
                      Editar
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Card>

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-end gap-2 text-sm text-muted-foreground">
          <span>
            Página {page} de {totalPages}
          </span>
          <Button
            variant="outline"
            size="icon-sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            aria-label="Anterior"
          >
            <ChevronLeft />
          </Button>
          <Button
            variant="outline"
            size="icon-sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            aria-label="Siguiente"
          >
            <ChevronRight />
          </Button>
        </div>
      )}
    </div>
  )
}
