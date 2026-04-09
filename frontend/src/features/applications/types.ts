export type ApplicationStatus = 'pending' | 'under_review' | 'approved' | 'rejected'
export type ApplicationCountry = 'MX' | 'CO'

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
