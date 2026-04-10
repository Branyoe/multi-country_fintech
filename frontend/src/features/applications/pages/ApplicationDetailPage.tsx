import { useCallback, useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, CircleDot } from 'lucide-react'
import { Link, useParams } from 'react-router'

import { Badge } from '~/components/ui/badge'
import { buttonVariants } from '~/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card'
import { cn } from '~/lib/utils'
import { fetchApplicationById } from '~/features/applications/api'
import { useApplicationTimelineSocket } from '~/features/applications/hooks/useApplicationTimelineSocket'
import { useCountries } from '~/features/applications/hooks/useCountries'
import { useStatuses } from '~/features/applications/hooks/useStatuses'
import type {
  ApplicationStatusTransition,
  CreditApplicationDetail,
  TimelineTransitionEvent,
} from '~/features/applications/types'

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('es-MX', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatCurrency(value: string) {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
    maximumFractionDigits: 0,
  }).format(Number(value))
}

function statusVariant(code: string): 'secondary' | 'outline' | 'default' | 'destructive' {
  if (code === 'approved') return 'default'
  if (code === 'rejected') return 'destructive'
  if (code === 'validate_country_rules' || code === 'under_review' || code === 'verificacion_buro') {
    return 'outline'
  }
  return 'secondary'
}

export default function ApplicationDetailPage() {
  const { id } = useParams()
  const queryClient = useQueryClient()
  const { data: countries = [] } = useCountries()
  const statuses = useStatuses()

  const countryMap = useMemo(
    () => Object.fromEntries(countries.map((c) => [c.code, c.label])),
    [countries],
  )
  const statusMap = useMemo(
    () => Object.fromEntries(statuses.map((s) => [s.code, s.label])),
    [statuses],
  )

  const detailQuery = useQuery({
    queryKey: ['application-detail', id],
    queryFn: () => fetchApplicationById(id ?? ''),
    enabled: Boolean(id),
  })

  const onTimelineTransition = useCallback(
    (event: TimelineTransitionEvent) => {
      if (!id || event.application_id !== id) return

      queryClient.setQueryData<CreditApplicationDetail | undefined>(['application-detail', id], (current) => {
        if (!current) return current

        const exists = current.status_history.some(
          (item) =>
            item.from_status === event.transition.from_status
            && item.to_status === event.transition.to_status
            && item.changed_by === event.transition.changed_by
            && item.changed_at === event.transition.changed_at,
        )

        if (exists) return current

        const status_history = [...current.status_history, event.transition].sort(
          (a, b) => new Date(a.changed_at).getTime() - new Date(b.changed_at).getTime(),
        )

        return {
          ...current,
          status_history,
        }
      })
    },
    [id, queryClient],
  )

  const { status: timelineSocketStatus } = useApplicationTimelineSocket({
    applicationId: id,
    onTransition: onTimelineTransition,
  })

  if (!id) {
    return (
      <div className="container mx-auto px-4 sm:px-6 py-8">
        <p className="text-sm text-destructive">ID de solicitud inválido.</p>
      </div>
    )
  }

  if (detailQuery.isLoading) {
    return (
      <div className="container mx-auto px-4 sm:px-6 py-8">
        <p className="text-sm text-muted-foreground">Cargando detalle de solicitud...</p>
      </div>
    )
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <div className="container mx-auto px-4 sm:px-6 py-8 space-y-4">
        <p className="text-sm text-destructive">No fue posible cargar la solicitud.</p>
        <Link to="/" className={buttonVariants({ variant: 'outline', size: 'sm' })}>
          Volver al listado
        </Link>
      </div>
    )
  }

  const app = detailQuery.data
  const timeline = [...(app.status_history ?? [])].sort((a, b) =>
    new Date(a.changed_at).getTime() - new Date(b.changed_at).getTime(),
  )

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 sm:px-6 flex items-center justify-between h-14">
          <span className="font-semibold tracking-tight">Detalle de solicitud</span>
          <Link to="/" className={cn(buttonVariants({ variant: 'outline', size: 'sm' }), 'gap-1.5')}>
            <ArrowLeft className="size-4" />
            Volver
          </Link>
        </div>
      </header>

      <main className="container mx-auto px-4 sm:px-6 py-8 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-2">
              Solicitud {app.id}
              <Badge variant={statusVariant(app.status)}>
                {statusMap[app.status] ?? app.status}
              </Badge>
            </CardTitle>
            <CardDescription>
              {app.country} · {countryMap[app.country] ?? app.country}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Solicitante</p>
              <p className="font-medium">{app.full_name}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Documento</p>
              <p className="font-medium">{app.document_type} · {app.document_number}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Monto solicitado</p>
              <p className="font-medium">{formatCurrency(app.amount_requested)}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Ingreso mensual</p>
              <p className="font-medium">{formatCurrency(app.monthly_income)}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Creada</p>
              <p className="font-medium">{formatDate(app.requested_at)}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Última actualización</p>
              <p className="font-medium">{formatDate(app.updated_at)}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Timeline de transiciones de estatus</CardTitle>
            <CardDescription>
              Historial cronológico de StatusTransitions para esta solicitud.
              {' '}
              {timelineSocketStatus === 'connected' && 'Actualizando en tiempo real.'}
              {timelineSocketStatus === 'reconnecting' && 'Reconectando actualizaciones en vivo...'}
              {timelineSocketStatus === 'disconnected' && 'Sin conexión en vivo.'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {timeline.length === 0 ? (
              <p className="text-sm text-muted-foreground">No hay transiciones registradas.</p>
            ) : (
              <ol className="space-y-4">
                {timeline.map((entry: ApplicationStatusTransition, index) => (
                  <li key={`${entry.changed_at}-${index}`} className="relative pl-6">
                    <span className="absolute left-0 top-1.5">
                      <CircleDot className="size-4 text-primary" />
                    </span>
                    {index < timeline.length - 1 && (
                      <span className="absolute left-1.75 top-5 h-[calc(100%+8px)] w-px bg-border" />
                    )}
                    <div className="space-y-1">
                      <p className="text-sm font-medium">
                        {statusMap[entry.from_status] ?? entry.from_status ?? 'Inicial'}
                        {' -> '}
                        {statusMap[entry.to_status] ?? entry.to_status}
                      </p>
                      <p className="text-xs text-muted-foreground">{formatDate(entry.changed_at)}</p>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
