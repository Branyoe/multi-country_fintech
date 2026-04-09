import { useQuery } from '@tanstack/react-query'
import { fetchCountries } from '../api'

export function useCountries() {
  return useQuery({
    queryKey: ['countries'],
    queryFn: fetchCountries,
    staleTime: Infinity, // metadata estática — solo se invalida manualmente
  })
}
