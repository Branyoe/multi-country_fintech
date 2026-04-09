import { api } from '~/lib/api'
import type { DRFPaginatedParams, DRFPaginatedResponse } from '~/shared/types/pagination.types'
import type { CreditApplication, CreateApplicationPayload } from './types'

export function fetchApplications(
  params: DRFPaginatedParams,
): Promise<DRFPaginatedResponse<CreditApplication>> {
  return api.get('/applications/', { params }).then((r) => r.data)
}

export function createApplication(
  payload: CreateApplicationPayload,
): Promise<CreditApplication> {
  return api.post('/applications/', payload).then((r) => r.data)
}
