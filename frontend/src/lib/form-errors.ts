import type { FieldValues, Path, UseFormSetError } from 'react-hook-form'

type DRFErrors = Record<string, string | string[]>

/**
 * Parses a DRF error response and routes errors to their correct destination:
 * - Field errors matching `knownFields` → setError (shown inline next to the field)
 * - `non_field_errors` / `detail` / unknown fields → returned as a string for a banner
 *
 * Returns the non-field error message, or null if all errors were field-level.
 */
export function applyApiErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  knownFields: readonly Path<T>[],
): string | null {
  const data = (error as { response?: { data?: unknown } })?.response?.data

  if (!data || typeof data !== 'object') {
    return 'Error de conexión. Intenta nuevamente.'
  }

  const errors = data as DRFErrors

  // Generic string detail (BankProviderError, ValueError, 401, 403…)
  if (typeof errors.detail === 'string') return errors.detail
  if (Array.isArray(errors.detail) && errors.detail.length > 0) return String(errors.detail[0])

  let nonFieldError: string | null = null

  for (const [key, raw] of Object.entries(errors)) {
    const msg = Array.isArray(raw) ? String(raw[0]) : String(raw)

    if (key === 'non_field_errors') {
      nonFieldError = msg
    } else if (knownFields.includes(key as Path<T>)) {
      setError(key as Path<T>, { type: 'server', message: msg })
    } else {
      // Unexpected field from backend — surface it rather than silently discard
      nonFieldError = nonFieldError ?? msg
    }
  }

  return nonFieldError
}
