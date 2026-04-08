import { createBrowserRouter, redirect } from 'react-router'
import type { LoaderFunctionArgs } from 'react-router'
import { useAuthStore } from '~/features/auth/store'
import { loginAction, signupAction } from '~/features/auth/actions'
import LoginPage from '~/features/auth/pages/LoginPage'
import SignupPage from '~/features/auth/pages/SignupPage'
import HomePage from '~/app/HomePage'

function requireAuth({ request }: LoaderFunctionArgs) {
  const token = useAuthStore.getState().accessToken
  if (!token) {
    const url = new URL(request.url)
    return redirect(`/login?next=${url.pathname}`)
  }
  return null
}

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
    action: loginAction,
  },
  {
    path: '/signup',
    element: <SignupPage />,
    action: signupAction,
  },
  {
    path: '/',
    loader: requireAuth,
    element: <HomePage />,
  },
])
