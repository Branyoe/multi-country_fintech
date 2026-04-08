export interface User {
  id: string
  email: string
  role: 'user' | 'admin'
  created_at: string
}

export interface TokenPair {
  access: string
  refresh: string
}

export interface ApiError {
  detail?: string
  [field: string]: string | string[] | undefined
}
