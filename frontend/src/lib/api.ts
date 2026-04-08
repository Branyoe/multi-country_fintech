import axios from 'axios'
import { tokenStorage } from '~/lib/auth'
import { useAuthStore } from '~/features/auth/store'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api',
})

// Inject access token on every request
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-refresh on 401
let isRefreshing = false
let queue: Array<(token: string) => void> = []

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config

    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error)
    }

    const refresh = tokenStorage.getRefresh()
    if (!refresh) {
      useAuthStore.getState().clearAuth()
      window.location.href = '/login'
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve) => {
        queue.push((token) => {
          original.headers.Authorization = `Bearer ${token}`
          resolve(api(original))
        })
      })
    }

    isRefreshing = true
    original._retry = true

    try {
      const { data } = await axios.post(
        `${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'}/auth/token/refresh/`,
        { refresh },
      )
      useAuthStore.getState().setTokens(data.access, refresh)
      queue.forEach((cb) => cb(data.access))
      queue = []
      original.headers.Authorization = `Bearer ${data.access}`
      return api(original)
    } catch {
      useAuthStore.getState().clearAuth()
      window.location.href = '/login'
      return Promise.reject(error)
    } finally {
      isRefreshing = false
    }
  },
)
