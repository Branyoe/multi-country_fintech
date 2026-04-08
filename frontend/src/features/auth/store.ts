import { create } from 'zustand'
import type { User } from '~/types/api'
import { tokenStorage } from '~/lib/auth'

interface AuthState {
  accessToken: string | null
  user: User | null
  isReady: boolean
  setTokens: (access: string, refresh: string) => void
  setUser: (user: User) => void
  clearAuth: () => void
  setReady: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  isReady: false,

  setTokens: (access, refresh) => {
    tokenStorage.setRefresh(refresh)
    set({ accessToken: access })
  },

  setUser: (user) => set({ user }),

  clearAuth: () => {
    tokenStorage.clear()
    set({ accessToken: null, user: null })
  },

  setReady: () => set({ isReady: true }),
}))
