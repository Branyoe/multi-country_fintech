import { useMemo } from 'react'
import { useCountries } from './useCountries'
import type { StatusMeta } from '../types'

export function useStatuses(): StatusMeta[] {
  const { data: countries = [] } = useCountries()
  return useMemo(() => {
    const seen = new Set<string>()
    const result: StatusMeta[] = []
    for (const c of countries) {
      for (const s of c.statuses) {
        if (!seen.has(s.code)) {
          seen.add(s.code)
          result.push(s)
        }
      }
    }
    return result.sort((a, b) => a.order - b.order)
  }, [countries])
}
