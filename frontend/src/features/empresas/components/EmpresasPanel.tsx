// Gestión de empresas (tenants). Página propia, solo para el administrador
// general: es el único que puede dar de alta una empresa y sus claves de
// integración.
//
// No hay borrado: una empresa con usuarios o televisores no se puede eliminar
// (el backend responde 409). Se desactiva, lo que corta el acceso de su gente
// sin destruir el histórico.

import { useState } from 'react'
import { Building2, CircleAlert, KeyRound, Loader2, Plus } from 'lucide-react'
import { type Empresa } from '@/features/empresas/api/empresas.api'
import {
  useActualizarEmpresa,
  useCrearEmpresa,
  useEmpresas,
} from '@/features/empresas/api/empresas.queries'
import { ApiKeysDialog } from '@/features/empresas/components/ApiKeysDialog'
import { ApiError } from '@/lib/http/errors'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

function mensajeDeError(err: unknown): string {
  if (err instanceof ApiError && err.data && typeof err.data === 'object') {
    const data = err.data as Record<string, unknown>
    const primero = Object.values(data)[0]
    return Array.isArray(primero) ? String(primero[0]) : String(primero)
  }
  return (err as Error)?.message ?? 'Error inesperado.'
}

export function EmpresasPanel() {
  const empresasQuery = useEmpresas()
  const crearEmpresa = useCrearEmpresa()
  const actualizarEmpresa = useActualizarEmpresa()

  const empresas = empresasQuery.data?.results ?? []
  const loading = empresasQuery.isPending
  const creando = crearEmpresa.isPending

  const [nombre, setNombre] = useState('')
  const [nit, setNit] = useState('')
  // Errores de acción (crear/alternar); el de carga sale de la query.
  const [actionError, setActionError] = useState<string | null>(null)
  const error =
    actionError ??
    (empresasQuery.isError ? mensajeDeError(empresasQuery.error) : null)

  // Empresa cuya gestión de claves está abierta (null = diálogo cerrado).
  const [empresaClaves, setEmpresaClaves] = useState<Empresa | null>(null)

  async function crear(e: React.FormEvent) {
    e.preventDefault()
    setActionError(null)
    try {
      // La invalidación de la mutación refresca la lista (backend ordena por nombre).
      await crearEmpresa.mutateAsync({ nombre, nit })
      setNombre('')
      setNit('')
    } catch (err) {
      setActionError(mensajeDeError(err))
    }
  }

  async function alternarActiva(empresa: Empresa, activa: boolean) {
    // El switch responde al instante (optimista en el hook) y se revierte si falla.
    setActionError(null)
    try {
      await actualizarEmpresa.mutateAsync({ id: empresa.id, data: { activa } })
    } catch (err) {
      setActionError(mensajeDeError(err))
    }
  }

  return (
    <Card>
      <CardContent className="space-y-6 pt-6">
        {error && (
          <Alert variant="destructive">
            <CircleAlert />
            <AlertTitle>No se pudo completar</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={crear} noValidate className="flex flex-wrap items-end gap-3">
          <div className="grid flex-1 gap-2" style={{ minWidth: '14rem' }}>
            <Label htmlFor="empresa_nombre">Nombre</Label>
            <Input
              id="empresa_nombre"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="Ej. Google Colombia S.A.S."
              required
            />
          </div>
          <div className="grid gap-2" style={{ minWidth: '10rem' }}>
            <Label htmlFor="empresa_nit">NIT (opcional)</Label>
            <Input
              id="empresa_nit"
              value={nit}
              onChange={(e) => setNit(e.target.value)}
              placeholder="900.123.456-7"
            />
          </div>
          <Button type="submit" disabled={creando || !nombre.trim()}>
            {creando ? <Loader2 className="animate-spin" /> : <Plus />}
            {creando ? 'Creando…' : 'Crear empresa'}
          </Button>
        </form>

        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
          </div>
        ) : empresas.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            Aún no hay empresas registradas.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Empresa</TableHead>
                <TableHead>NIT</TableHead>
                <TableHead className="text-right">Usuarios</TableHead>
                <TableHead className="text-right">Televisores</TableHead>
                <TableHead className="text-right">Integración</TableHead>
                <TableHead className="text-right">Activa</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {empresas.map((empresa) => (
                <TableRow key={empresa.id}>
                  <TableCell className="font-medium">
                    <span className="flex items-center gap-2">
                      <Building2 className="size-4 text-muted-foreground" />
                      {empresa.nombre}
                      {!empresa.activa && (
                        <Badge variant="secondary">Desactivada</Badge>
                      )}
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {empresa.nit || '—'}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {empresa.usuarios}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {empresa.televisores}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setEmpresaClaves(empresa)}
                    >
                      <KeyRound /> Claves
                    </Button>
                  </TableCell>
                  <TableCell className="text-right">
                    <Switch
                      checked={empresa.activa}
                      onCheckedChange={(v) => alternarActiva(empresa, v)}
                      aria-label={`Activar ${empresa.nombre}`}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}

        <p className="text-xs text-muted-foreground">
          Al desactivar una empresa, sus usuarios dejan de poder iniciar sesión de
          inmediato. Sus datos se conservan.
        </p>
      </CardContent>

      <ApiKeysDialog empresa={empresaClaves} onClose={() => setEmpresaClaves(null)} />
    </Card>
  )
}
