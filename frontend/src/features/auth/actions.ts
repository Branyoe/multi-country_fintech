import { redirect } from 'react-router'
import type { ActionFunctionArgs } from 'react-router'
import { api } from '~/lib/api'
import { useAuthStore } from '~/features/auth/store'
import type { TokenPair } from '~/types/api'

export async function loginAction({ request }: ActionFunctionArgs) {
  const form = await request.formData()
  const email = form.get('email') as string
  const password = form.get('password') as string

  try {
    const { data } = await api.post<TokenPair>('/auth/token/', { email, password })
    useAuthStore.getState().setTokens(data.access, data.refresh)
    return redirect('/')
  } catch (err: unknown) {
    if (axios.isAxiosError(err)) {
      return { error: err.response?.data?.detail ?? 'Credenciales inválidas' }
    }
    return { error: 'Error inesperado' }
  }
}

export async function signupAction({ request }: ActionFunctionArgs) {
  const form = await request.formData()
  const email = form.get('email') as string
  const password = form.get('password') as string

  try {
    await api.post('/auth/signup/', { email, password })
    return redirect('/login?registered=1')
  } catch (err: unknown) {
    if (axios.isAxiosError(err)) {
      const data = err.response?.data ?? {}
      return {
        error:
          data.email?.[0] ??
          data.password?.[0] ??
          data.detail ??
          'Error al registrarse',
      }
    }
    return { error: 'Error inesperado' }
  }
}

// Needed for the isAxiosError helper above
import axios from 'axios'
