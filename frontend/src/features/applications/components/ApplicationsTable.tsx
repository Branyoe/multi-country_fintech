import { DataTable } from '~/components/data-table/DataTable'
import { fetchApplications } from '../api'
import { applicationColumns } from '../columns'
import type { FilterConfig } from '~/components/data-table/DataTable'

const filterConfigs: FilterConfig[] = [
  {
    key: 'country',
    label: 'País',
    type: 'multiple',
    options: [
      { value: 'MX', label: 'México' },
      { value: 'CO', label: 'Colombia' },
    ],
  },
  {
    key: 'status',
    label: 'Estado',
    type: 'multiple',
    options: [
      { value: 'pending', label: 'Pendiente' },
      { value: 'under_review', label: 'En revisión' },
      { value: 'approved', label: 'Aprobada' },
      { value: 'rejected', label: 'Rechazada' },
    ],
  },
]

export function ApplicationsTable() {
  return (
    <DataTable
      columns={applicationColumns}
      queryKey={['applications']}
      queryFn={fetchApplications}
      initialOrdering="-requested_at"
      filterConfigs={filterConfigs}
      disableOrderingColumns={['document_type', 'document_number', 'country']}
      emptyState={
        <p className="text-sm text-muted-foreground">
          No hay solicitudes. Crea una nueva para empezar.
        </p>
      }
    />
  )
}
