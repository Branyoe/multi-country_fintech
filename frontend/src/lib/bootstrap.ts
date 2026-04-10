import axios from 'axios'
import { tokenStorage } from '~/lib/auth'
import { useAuthStore } from '~/features/auth/store'
import { api } from '~/lib/api'
import type { User } from '~/types/api'

export async function bootstrap() {
  const refresh = tokenStorage.getRefresh()

  if (refresh) {
    try {
      const { data } = await axios.post(
        `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'}/auth/token/refresh/`,
        { refresh },
      )
      useAuthStore.getState().setTokens(data.access, refresh)
      const { data: user } = await api.get<User>('/auth/me/')
      useAuthStore.getState().setUser(user)
    } catch {
      tokenStorage.clear()
    }
  }

  useAuthStore.getState().setReady()
}
