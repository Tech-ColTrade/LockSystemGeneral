// Gestión de las API-keys de integración de UNA empresa. Solo el administrador
// general llega aquí (la página de Empresas ya es superadmin-only).
//
// La clave en claro se muestra UNA sola vez, justo al crearla: el backend solo
// guarda su hash. Por eso, tras crearla, se resalta con un aviso de "cópiala
// ahora". Revocar no borra: desactiva la clave (deja de autenticar).

import { useEffect, useState } from 'react'
import {
  Check,
  Copy,
  KeyRound,
  Loader2,
  Plus,
  ShieldCheck,
  TriangleAlert,
} from 'lucide-react'
import {
  empresasApi,
  type ApiKey,
  type ApiKeyCreada,
  type Empresa,
} from '@/features/empresas/api/empresas.api'
import { ApiError } from '@/lib/http/errors'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'

function mensajeDeError(err: unknown): string {
  if (err instanceof ApiError && err.data && typeof err.data === 'object') {
    const data = err.data as Record<string, unknown>
    const primero = Object.values(data)[0]
    return Array.isArray(primero) ? String(primero[0]) : String(primero)
  }
  return (err as Error)?.message ?? 'Error inesperado.'
}

interface Props {
  empresa: Empresa | null
  onClose: () => void
}

export function ApiKeysDialog({ empresa, onClose }: Props) {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [nombre, setNombre] = useState('')
  const [ips, setIps] = useState('')
  const [expira, setExpira] = useState('')
  const [endurecer, setEndurecer] = useState(false)
  const [creando, setCreando] = useState(false)
  // Clave recién creada: se muestra en claro una única vez.
  const [creada, setCreada] = useState<ApiKeyCreada | null>(null)
  const [copiada, setCopiada] = useState(false)

  useEffect(() => {
    if (!empresa) return
    setLoading(true)
    setError(null)
    setCreada(null)
    setNombre('')
    setIps('')
    setExpira('')
    setEndurecer(false)
    empresasApi
      .listApiKeys(empresa.id)
      .then(setKeys)
      .catch((e) => setError(mensajeDeError(e)))
      .finally(() => setLoading(false))
  }, [empresa])

  async function crear(e: React.FormEvent) {
    e.preventDefault()
    if (!empresa) return
    setCreando(true)
    setError(null)
    try {
      const nueva = await empresasApi.crearApiKey(empresa.id, {
        nombre,
        // Solo se mandan si el usuario decidió endurecer; si no, la clave queda
        // abierta (uso por defecto). La fecha se envía como ISO.
        ...(endurecer && ips.trim() ? { ips_permitidas: ips.trim() } : {}),
        ...(endurecer && expira
          ? { expira: new Date(expira).toISOString() }
          : {}),
      })
      setCreada(nueva)
      setNombre('')
      setIps('')
      setExpira('')
      setEndurecer(false)
      const lista = await empresasApi.listApiKeys(empresa.id)
      setKeys(lista)
    } catch (err) {
      setError(mensajeDeError(err))
    } finally {
      setCreando(false)
    }
  }

  async function revocar(key: ApiKey) {
    if (!empresa) return
    try {
      await empresasApi.revocarApiKey(empresa.id, key.id)
      setKeys((prev) =>
        prev.map((k) => (k.id === key.id ? { ...k, activa: false } : k)),
      )
    } catch (err) {
      setError(mensajeDeError(err))
    }
  }

  function copiar(texto: string) {
    navigator.clipboard.writeText(texto).then(() => {
      setCopiada(true)
      setTimeout(() => setCopiada(false), 2000)
    })
  }

  return (
    <Dialog open={!!empresa} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <KeyRound className="size-4" /> Claves de integración
          </DialogTitle>
          <DialogDescription>
            {empresa?.nombre}. Un integrador usa estas claves para consultar y
            operar los televisores de esta empresa por su serial.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <Alert variant="destructive">
            <TriangleAlert />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {creada && (
          <Alert className="border-amber-500/40 text-amber-700 dark:text-amber-400">
            <TriangleAlert />
            <AlertTitle>Copia la clave ahora — no se vuelve a mostrar</AlertTitle>
            <AlertDescription className="text-amber-700 dark:text-amber-400">
              <div className="mt-2 flex items-center gap-2">
                <code className="flex-1 break-all rounded-md bg-background/60 px-2 py-1 font-mono text-xs">
                  {creada.clave}
                </code>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => copiar(creada.clave)}
                >
                  {copiada ? <Check /> : <Copy />}
                  {copiada ? 'Copiada' : 'Copiar'}
                </Button>
              </div>
            </AlertDescription>
          </Alert>
        )}

        <form onSubmit={crear} className="space-y-3">
          <div className="flex items-end gap-2">
            <div className="grid flex-1 gap-2">
              <Label htmlFor="key_nombre">Nombre del integrador</Label>
              <Input
                id="key_nombre"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder="Ej. ERP de Google"
                required
              />
            </div>
            <Button type="submit" disabled={creando || !nombre.trim()}>
              {creando ? <Loader2 className="animate-spin" /> : <Plus />}
              Generar clave
            </Button>
          </div>

          <button
            type="button"
            onClick={() => setEndurecer((v) => !v)}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <ShieldCheck className="size-3.5" />
            {endurecer ? 'Ocultar' : 'Endurecer (opcional): limitar IPs y caducidad'}
          </button>

          {endurecer && (
            <div className="grid gap-3 rounded-lg border border-dashed p-3">
              <div className="grid gap-1.5">
                <Label htmlFor="key_ips" className="text-xs">
                  IPs o rangos permitidos (uno por línea)
                </Label>
                <textarea
                  id="key_ips"
                  value={ips}
                  onChange={(e) => setIps(e.target.value)}
                  placeholder={'190.0.0.5\n10.0.0.0/24'}
                  rows={3}
                  className="w-full rounded-md border bg-transparent px-3 py-2 font-mono text-xs"
                />
                <p className="text-xs text-muted-foreground">
                  Vacío = la clave funciona desde cualquier IP.
                </p>
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="key_expira" className="text-xs">
                  Caduca el (opcional)
                </Label>
                <Input
                  id="key_expira"
                  type="date"
                  value={expira}
                  onChange={(e) => setExpira(e.target.value)}
                  className="w-fit"
                />
              </div>
            </div>
          )}
        </form>

        <div className="max-h-72 overflow-y-auto">
          {loading ? (
            <div className="space-y-2">
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
            </div>
          ) : keys.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              Esta empresa aún no tiene claves de integración.
            </p>
          ) : (
            <ul className="divide-y">
              {keys.map((k) => (
                <li key={k.id} className="flex items-center gap-3 py-2.5">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{k.nombre}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      <code>{k.prefijo}…</code> · creada{' '}
                      {new Date(k.creada).toLocaleDateString()}
                      {k.ultimo_uso
                        ? ` · último uso ${new Date(k.ultimo_uso).toLocaleDateString()}`
                        : ' · sin uso'}
                    </p>
                    {(k.ips_permitidas.trim() || k.expira) && (
                      <p className="mt-0.5 flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
                        <ShieldCheck className="size-3" />
                        {k.ips_permitidas.trim() && (
                          <span>
                            IPs:{' '}
                            {k.ips_permitidas
                              .split(/[\n,]/)
                              .map((s) => s.trim())
                              .filter(Boolean)
                              .join(', ')}
                          </span>
                        )}
                        {k.expira && (
                          <span>· caduca {new Date(k.expira).toLocaleDateString()}</span>
                        )}
                      </p>
                    )}
                  </div>
                  {k.activa ? (
                    <>
                      <Badge variant="secondary">Activa</Badge>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => revocar(k)}
                      >
                        Revocar
                      </Button>
                    </>
                  ) : (
                    <Badge variant="outline" className="text-muted-foreground">
                      Revocada
                    </Badge>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
