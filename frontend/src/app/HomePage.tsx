import { useAuthStore } from '~/features/auth/store'
import { tokenStorage } from '~/lib/auth'
import { useNavigate } from 'react-router'
import { Button } from '~/components/ui/button'
import { ApplicationsTable } from '~/features/applications/components/ApplicationsTable'
import { CreateApplicationForm } from '~/features/applications/components/CreateApplicationForm'

export default function HomePage() {
  const { user, clearAuth } = useAuthStore()
  const navigate = useNavigate()

  function logout() {
    clearAuth()
    tokenStorage.clear()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container flex items-center justify-between h-14">
          <span className="font-semibold tracking-tight">bravo</span>
          <div className="flex items-center gap-4">
            {user && (
              <span className="text-sm text-muted-foreground">{user.email}</span>
            )}
            <Button variant="outline" size="sm" onClick={logout}>
              Cerrar sesión
            </Button>
          </div>
        </div>
      </header>

      <main className="container py-8 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Solicitudes de crédito sss
            </h1>
            <p className="text-sm text-muted-foreground">
              Gestiona y consulta las solicitudes de crédito
            </p>
          </div>
          <CreateApplicationForm />
        </div>

        <ApplicationsTable />
      </main>
    </div>
  )
}
