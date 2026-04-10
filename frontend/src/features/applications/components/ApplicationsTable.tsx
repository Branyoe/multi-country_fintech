import { useMemo } from 'react'
import { DataTable } from '~/components/data-table/DataTable'
import { fetchApplications } from '../api'
import { createApplicationColumns } from '../columns'
import { useCountries } from '../hooks/useCountries'
import type { FilterConfig } from '~/components/data-table/DataTable'

const STATUS_FILTER: FilterConfig = {
  key: 'status',
  label: 'Estado',
  type: 'multiple',
  options: [
    { value: 'pending', label: 'Pendiente' },
    { value: 'under_review', label: 'En revisión' },
    { value: 'approved', label: 'Aprobada' },
    { value: 'rejected', label: 'Rechazada' },
  ],
}

export function ApplicationsTable() {
  const { data: countries = [] } = useCountries()

  const countryMap = useMemo(
    () => Object.fromEntries(countries.map((c) => [c.code, c.label])),
    [countries],
  )

  const columns = useMemo(() => createApplicationColumns(countryMap), [countryMap])

  const filterConfigs: FilterConfig[] = useMemo(
    () => [
      {
        key: 'country',
        label: 'País',
        type: 'multiple',
        options: countries.map((c) => ({ value: c.code, label: c.label })),
      },
      STATUS_FILTER,
    ],
    [countries],
  )

  return (
    <DataTable
      columns={columns}
      queryKey={['applications']}
      queryFn={fetchApplications}
      initialOrdering="-requested_at"
      filterConfigs={filterConfigs}
      disableOrderingColumns={['document_type', 'document_number']}
      emptyState={
        <p className="text-sm text-muted-foreground">
          No hay solicitudes. Crea una nueva para empezar.
        </p>
      }
    />
  )
}
