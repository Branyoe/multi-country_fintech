import { useMemo } from 'react'
import { DataTable } from '~/components/data-table/DataTable'
import { fetchApplications } from '../api'
import { createApplicationColumns } from '../columns'
import { useCountries } from '../hooks/useCountries'
import { useStatuses } from '../hooks/useStatuses'
import type { FilterConfig } from '~/components/data-table/DataTable'

export function ApplicationsTable() {
  const { data: countries = [] } = useCountries()
  const statuses = useStatuses()

  const countryMap = useMemo(
    () => Object.fromEntries(countries.map((c) => [c.code, c.label])),
    [countries],
  )

  const statusMap = useMemo(
    () => Object.fromEntries(statuses.map((s) => [s.code, s])),
    [statuses],
  )

  const columns = useMemo(
    () => createApplicationColumns(countryMap, statusMap),
    [countryMap, statusMap],
  )

  const filterConfigs: FilterConfig[] = useMemo(
    () => [
      {
        key: 'country',
        label: 'País',
        type: 'multiple',
        options: countries.map((c) => ({ value: c.code, label: c.label })),
      },
      {
        key: 'status',
        label: 'Estado',
        type: 'multiple',
        options: statuses.map((s) => ({ value: s.code, label: s.label })),
      },
    ],
    [countries, statuses],
  )

  return (
    <DataTable
      columns={columns}
      queryKey={['applications']}
      queryFn={fetchApplications}
      initialOrdering="-requested_at"
      filterConfigs={filterConfigs}
      disableOrderingColumns={['actions']}
      emptyState={
        <p className="text-sm text-muted-foreground">
          No hay solicitudes. Crea una nueva para empezar.
        </p>
      }
    />
  )
}
