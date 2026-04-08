import { useAuthStore } from '~/features/auth/store'
import { Button } from '~/components/ui/button'
import { tokenStorage } from '~/lib/auth'
import { useNavigate } from 'react-router'

export default function HomePage() {
  const { user, clearAuth } = useAuthStore()
  const navigate = useNavigate()

  function logout() {
    clearAuth()
    tokenStorage.clear()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 bg-background">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Bienvenido</h1>
        {user && (
          <p className="text-muted-foreground text-sm">{user.email}</p>
        )}
        <p className="text-xs text-muted-foreground uppercase tracking-widest">
          scaffold
        </p>
      </div>
      <Button variant="outline" onClick={logout}>
        Cerrar sesión
      </Button>
    </div>
  )
}
