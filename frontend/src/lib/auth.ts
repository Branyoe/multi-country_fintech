const REFRESH_KEY = 'refresh_token'

export const tokenStorage = {
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  setRefresh: (token: string) => localStorage.setItem(REFRESH_KEY, token),
  clear: () => localStorage.removeItem(REFRESH_KEY),
}
