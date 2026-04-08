import axios from 'axios'
import { tokenStorage } from '~/lib/auth'
import { useAuthStore } from '~/features/auth/store'

export async function bootstrap() {
  const refresh = tokenStorage.getRefresh()

  if (refresh) {
    try {
      const { data } = await axios.post(
        `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'}/auth/token/refresh/`,
        { refresh },
      )
      useAuthStore.getState().setTokens(data.access, refresh)
    } catch {
      tokenStorage.clear()
    }
  }

  useAuthStore.getState().setReady()
}
