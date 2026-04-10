import { Form, Link, useActionData, useNavigation, useSearchParams } from 'react-router'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '~/components/ui/card'
import { Input } from '~/components/ui/input'
import { Label } from '~/components/ui/label'
import { Button } from '~/components/ui/button'

interface ActionData {
  error?: string
}

export default function LoginPage() {
  const actionData = useActionData<ActionData>()
  const navigation = useNavigation()
  const [params] = useSearchParams()
  const isSubmitting = navigation.state === 'submitting'

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <span className="font-display font-bold text-2xl tracking-tight text-foreground">fintech</span>
        </div>
      <Card className="w-full">
        <CardHeader>
          <CardTitle>Iniciar sesión</CardTitle>
          <CardDescription>Ingresa tus credenciales para continuar</CardDescription>
        </CardHeader>

        <Form method="post">
          <CardContent className="space-y-4">
            {params.get('registered') && (
              <p className="text-sm text-green-600">Cuenta creada. Inicia sesión.</p>
            )}
            {actionData?.error && (
              <p className="text-sm text-destructive">{actionData.error}</p>
            )}

            <div className="space-y-1">
              <Label htmlFor="email">Email</Label>
              <Input id="email" name="email" type="email" autoComplete="email" required />
            </div>

            <div className="space-y-1">
              <Label htmlFor="password">Contraseña</Label>
              <Input id="password" name="password" type="password" autoComplete="current-password" required />
            </div>
          </CardContent>

          <CardFooter className="flex flex-col gap-3">
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? 'Ingresando...' : 'Ingresar'}
            </Button>
            <p className="text-sm text-muted-foreground">
              ¿No tienes cuenta?{' '}
              <Link to="/signup" className="underline">
                Regístrate
              </Link>
            </p>
          </CardFooter>
        </Form>
      </Card>
      </div>
    </div>
  )
}
