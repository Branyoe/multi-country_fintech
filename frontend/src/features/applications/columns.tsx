import type { ColumnDef, CellContext } from '@tanstack/react-table'
import { Badge } from '~/components/ui/badge'
import type { CreditApplication, ApplicationCountry, ApplicationStatus } from './types'

type Cell = CellContext<CreditApplication, unknown>

const STATUS_LABELS: Record<ApplicationStatus, string> = {
  pending: 'Pendiente',
  under_review: 'En revisión',
  approved: 'Aprobada',
  rejected: 'Rechazada',
}

const STATUS_VARIANTS: Record<
  ApplicationStatus,
  'secondary' | 'outline' | 'default' | 'destructive'
> = {
  pending: 'secondary',
  under_review: 'outline',
  approved: 'default',
  rejected: 'destructive',
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
): ColumnDef<CreditApplication, unknown>[] {
  return [
  {
    accessorKey: 'full_name',
    header: 'Solicitante',
    meta: { orderingKey: 'full_name' },
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
    meta: { orderingKey: 'status' },
    cell: ({ getValue }: Cell) => {
      const status = getValue() as ApplicationStatus
      return (
        <Badge variant={STATUS_VARIANTS[status]}>
          {STATUS_LABELS[status]}
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
  ]
}
