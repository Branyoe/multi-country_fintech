import type { ColumnDef, CellContext } from '@tanstack/react-table'
import { Link } from 'react-router'
import { Eye } from 'lucide-react'
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

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('es-MX', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function createApplicationColumns(
  countryMap: Record<string, string>,
  statusMap: Record<string, StatusMeta>,
): ColumnDef<CreditApplication, unknown>[] {
  return [
  {
    accessorKey: 'full_name',
    header: 'Solicitante',
    meta: { orderingKey: 'full_name' },
  },
  {
    accessorKey: 'user_email',
    header: 'Creada por',
    meta: { orderingKey: 'user__email' },
    cell: ({ getValue }: Cell) => (
      <span className="text-muted-foreground text-sm font-mono">
        {getValue() as string}
      </span>
    ),
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
    header: 'Fecha',
    meta: { orderingKey: 'requested_at' },
    cell: ({ getValue }: Cell) => formatDate(getValue() as string),
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
