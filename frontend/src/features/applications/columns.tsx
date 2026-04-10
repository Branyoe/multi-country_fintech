import type { ColumnDef, CellContext } from '@tanstack/react-table'
import { Link } from 'react-router'
import { Copy, Eye } from 'lucide-react'
import { Badge } from '~/components/ui/badge'
import { buttonVariants } from '~/components/ui/button'
import { cn } from '~/lib/utils'
import type { CreditApplication, ApplicationCountry, ApplicationStatus, StatusMeta } from './types'

type Cell = CellContext<CreditApplication, unknown>
type BadgeVariant = 'secondary' | 'outline' | 'default' | 'destructive' | 'status-approved' | 'status-rejected' | 'status-pending' | 'status-review'

function statusVariant(code: string): BadgeVariant {
  if (code === 'approved') return 'status-approved'
  if (code === 'rejected') return 'status-rejected'
  if (code === 'created' || code === 'pending') return 'status-pending'
  return 'status-review'
}


function formatCurrency(value: string) {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
    maximumFractionDigits: 0,
  }).format(Number(value))
}

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString('es-MX', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function copyToClipboard(text: string) {
  if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
  }
}

export function createApplicationColumns(
  countryMap: Record<string, string>,
  statusMap: Record<string, StatusMeta>,
): ColumnDef<CreditApplication, unknown>[] {
  return [
  {
    accessorKey: 'id',
    header: 'ID',
    meta: { orderingKey: 'id' },
    cell: ({ getValue }: Cell) => {
      const id = String(getValue())
      return (
        <div className="flex items-center gap-1.5 min-w-0">
          <span
            className="text-muted-foreground text-xs font-mono truncate max-w-32.5"
            title={id}
          >
            {id}
          </span>
          <button
            type="button"
            className={cn(
              buttonVariants({ variant: 'ghost', size: 'icon-sm' }),
              'shrink-0',
            )}
            onClick={() => {
              void copyToClipboard(id)
            }}
            aria-label={`Copiar ID ${id}`}
            title="Copiar ID"
          >
            <Copy className="size-3.5" aria-hidden="true" />
          </button>
        </div>
      )
    },
  },
  {
    accessorKey: 'full_name',
    header: 'Solicitante',
    meta: { orderingKey: 'full_name' },
  },
  {
    accessorKey: 'document_type',
    header: 'Tipo doc.',
    meta: { orderingKey: 'document_type' },
  },
  {
    accessorKey: 'document_number',
    header: 'Documento',
    meta: { orderingKey: 'document_number' },
  },
  {
    accessorKey: 'amount_requested',
    header: 'Monto solicitado',
    meta: { orderingKey: 'amount_requested' },
    cell: ({ getValue }: Cell) => formatCurrency(getValue() as string),
  },
  {
    accessorKey: 'monthly_income',
    header: 'Ingreso mensual',
    meta: { orderingKey: 'monthly_income' },
    cell: ({ getValue }: Cell) => formatCurrency(getValue() as string),
  },
  {
    accessorKey: 'country',
    header: 'País',
    meta: { orderingKey: 'country_ref__code' },
    cell: ({ getValue }: Cell) => {
      const val = getValue() as ApplicationCountry
      return (
        <Badge variant="outline" className="font-mono text-xs">
          {val} · {countryMap[val] ?? val}
        </Badge>
      )
    },
  },
  {
    accessorKey: 'status',
    header: 'Estado',
    meta: { orderingKey: 'status__order' },
    cell: ({ getValue }: Cell) => {
      const code = getValue() as ApplicationStatus
      return (
        <Badge variant={statusVariant(code)}>
          {statusMap[code]?.label ?? code}
        </Badge>
      )
    },
  },
  {
    accessorKey: 'requested_at',
    header: 'Fecha-hora',
    meta: { orderingKey: 'requested_at' },
    cell: ({ getValue }: Cell) => formatDateTime(getValue() as string),
  },
  {
    id: 'actions',
    header: 'Acciones',
    enableSorting: false,
    cell: ({ row }: Cell) => (
      <Link
        to={`/applications/${row.original.id}`}
        className={cn(buttonVariants({ variant: 'ghost', size: 'sm' }), 'gap-1.5')}
      >
        <Eye className="size-4" />
        Ver detalle
      </Link>
    ),
  },
  ]
}
