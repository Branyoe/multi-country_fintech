import { useState } from 'react'
import { useAuthStore } from '~/features/auth/store'
import { tokenStorage } from '~/lib/auth'
import { useNavigate } from 'react-router'
import { Button } from '~/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '~/components/ui/dialog'
import { LogOut, User } from 'lucide-react'
import { Badge } from '~/components/ui/badge'
import { ApplicationsTable } from '~/features/applications/components/ApplicationsTable'
import { CreateApplicationForm } from '~/features/applications/components/CreateApplicationForm'

export default function HomePage() {
  const { user, clearAuth } = useAuthStore()
  const navigate = useNavigate()
  const [logoutOpen, setLogoutOpen] = useState(false)

  function logout() {
    clearAuth()
    tokenStorage.clear()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b shadow-sm">
        <div className="container mx-auto px-4 sm:px-6 flex items-center justify-between h-14">
          <span className="font-display font-bold tracking-tight text-lg">fintech</span>
          <div className="flex items-center gap-3">
            {user && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-secondary border border-border">
                <div className="flex items-center justify-center w-6 h-6 rounded-full bg-primary text-primary-foreground shrink-0">
                  <User className="size-3.5" />
                </div>
                <div className="hidden sm:flex items-center gap-1.5">
                  <span className="text-sm text-foreground max-w-[150px] truncate">
                    {user.email}
                  </span>
                  <Badge
                    variant={user.role === 'admin' ? 'default' : 'secondary'}
                    className="text-[10px] h-4 px-1.5 shrink-0"
                  >
                    {user.role === 'admin' ? 'Admin' : 'Usuario'}
                  </Badge>
                </div>
              </div>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setLogoutOpen(true)}
              className="gap-1.5 text-muted-foreground hover:text-foreground"
            >
              <LogOut className="size-4" />
              <span className="hidden sm:inline">Cerrar sesión</span>
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 sm:px-6 py-8 space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="font-display text-2xl font-bold tracking-tight">
              Solicitudes de crédito
            </h1>
            <p className="text-sm text-muted-foreground">
              Gestiona y consulta las solicitudes de crédito
            </p>
          </div>
          <div className="self-start sm:shrink-0">
            <CreateApplicationForm />
          </div>
        </div>

        <ApplicationsTable />
      </main>

      <Dialog open={logoutOpen} onOpenChange={setLogoutOpen}>
        <DialogContent showCloseButton={false} className="max-w-xs">
          <DialogHeader>
            <div className="flex items-center gap-3 pb-1">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-destructive/10 shrink-0">
                <LogOut className="size-5 text-destructive" />
              </div>
              <DialogTitle>¿Cerrar sesión?</DialogTitle>
            </div>
            <DialogDescription>
              Tu sesión actual se cerrará. Necesitarás volver a iniciar sesión para continuar.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" className="flex-1" />}>
              Cancelar
            </DialogClose>
            <Button variant="destructive" className="flex-1" onClick={logout}>
              Cerrar sesión
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
