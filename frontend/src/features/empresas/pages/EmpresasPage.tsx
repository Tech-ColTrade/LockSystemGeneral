// Página de Empresas (tenants). Ruta propia con entrada en el sidebar, visible
// solo para el administrador general. El CRUD vive en EmpresasPanel; aquí solo
// se le pone el encabezado de página, para que sea consistente con Usuarios.

import { EmpresasPanel } from '@/features/empresas/components/EmpresasPanel'

export function EmpresasPage() {
  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Empresas</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Da de alta las empresas del sistema. Cada una ve únicamente sus
          televisores, registros y usuarios.
        </p>
      </div>

      <EmpresasPanel />
    </div>
  )
}
