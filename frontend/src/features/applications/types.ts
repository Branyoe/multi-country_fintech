export type ApplicationStatus = string
export type ApplicationCountry = string

export interface StatusMeta {
  code: string
  label: string
  is_terminal: boolean
  order: number
}

export interface CountryMeta {
  code: string
  label: string
  document_type: string
  document_hint: string
  document_example: string
  document_regex: string
  statuses: StatusMeta[]
}

export interface CreditApplication {
  id: string
  user_email: string
  country: ApplicationCountry
  full_name: string
  document_type: string
  document_number: string
  amount_requested: string
  monthly_income: string
  status: ApplicationStatus
  requested_at: string
  updated_at: string
}

export interface CreateApplicationPayload {
  country: ApplicationCountry
  full_name: string
  document_number: string
  amount_requested: string
  monthly_income: string
}
