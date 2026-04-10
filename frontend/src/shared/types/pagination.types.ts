export interface DRFPaginatedParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
  [key: string]: string | number | boolean | string[] | undefined
}

export interface DRFPaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
