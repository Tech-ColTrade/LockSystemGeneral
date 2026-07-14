// Gestión de empresas (tenants). Vive en Configuración y solo la ve el
// administrador general: es el único que puede dar de alta una empresa.
//
// No hay borrado: una empresa con usuarios o televisores no se puede eliminar
// (el backend responde 409). Se desactiva, lo que corta el acceso de su gente
// sin destruir el histórico.

import { useEffect, useState } from 'react'
import { Building2, CircleAlert, Loader2, Plus } from 'lucide-react'
import { empresasApi, type Empresa } from '@/features/empresas/api/empresas.api'
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
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [nombre, setNombre] = useState('')
  const [nit, setNit] = useState('')
  const [creando, setCreando] = useState(false)

  useEffect(() => {
    let activo = true
    empresasApi
      .list()
      .then((r) => activo && setEmpresas(r.results))
      .catch((e) => activo && setError(mensajeDeError(e)))
      .finally(() => activo && setLoading(false))
    return () => {
      activo = false
    }
  }, [])

  async function crear(e: React.FormEvent) {
    e.preventDefault()
    setCreando(true)
    setError(null)
    try {
      const nueva = await empresasApi.create({ nombre, nit })
      setEmpresas((prev) => [...prev, nueva].sort((a, b) => a.nombre.localeCompare(b.nombre)))
      setNombre('')
      setNit('')
    } catch (err) {
      setError(mensajeDeError(err))
    } finally {
      setCreando(false)
    }
  }

  async function alternarActiva(empresa: Empresa, activa: boolean) {
    // Optimista: el switch responde al instante y se revierte si el backend falla.
    setEmpresas((prev) =>
      prev.map((e) => (e.id === empresa.id ? { ...e, activa } : e)),
    )
    try {
      await empresasApi.update(empresa.id, { activa })
    } catch (err) {
      setEmpresas((prev) =>
        prev.map((e) => (e.id === empresa.id ? { ...e, activa: !activa } : e)),
      )
      setError(mensajeDeError(err))
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
    </Card>
  )
}
