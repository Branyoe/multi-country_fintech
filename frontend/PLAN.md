# Frontend — Plan de arranque

> Documento temporal de planeación. Se elimina una vez que el proyecto esté inicializado y documentado en `README.md`.

---

## Stack

| Herramienta | Versión objetivo | Rol |
|---|---|---|
| Vite | 6.x | Bundler / dev server |
| React | 19.x | UI |
| TypeScript | 5.x | Tipado |
| Tailwind CSS | 4.x | Estilos utilitarios |
| shadcn/ui | latest | Componentes accesibles sobre Radix |
| React Router | 7.x | Routing en modo data (loaders/actions) |
| TanStack Query | 5.x | Server state / cache de API |
| Zustand | 5.x | Client state (auth, UI global) |
| React Hook Form | 7.x | Formularios |
| Zod | 3.x | Validación de esquemas (forms + API response) |
| Axios | 1.x | HTTP client con interceptors |

---

## Estructura de carpetas

```
frontend/
├── public/
├── src/
│   ├── app/
│   │   ├── router.tsx          # Definición de rutas (createBrowserRouter)
│   │   └── App.tsx             # RouterProvider raíz
│   ├── features/               # Una carpeta por dominio
│   │   ├── auth/
│   │   │   ├── components/     # LoginForm, SignupForm
│   │   │   ├── loaders.ts      # loader de rutas auth
│   │   │   ├── actions.ts      # action de login/signup
│   │   │   └── store.ts        # Zustand slice de auth
│   │   ├── applications/
│   │   │   ├── components/
│   │   │   ├── loaders.ts
│   │   │   └── actions.ts
│   │   └── dashboard/
│   │       ├── components/
│   │       └── loaders.ts
│   ├── lib/
│   │   ├── api.ts              # Instancia de axios + interceptors
│   │   ├── auth.ts             # Token helpers (get/set/clear/refresh)
│   │   └── ws.ts               # WebSocket client (futuro)
│   ├── components/             # Componentes genéricos / UI compartida
│   │   └── ui/                 # Generados por shadcn
│   ├── hooks/                  # Custom hooks transversales
│   ├── types/                  # Tipos globales / respuestas de API
│   └── main.tsx
├── .env.local                  # Variables locales (no versionado)
├── .env.example
├── tailwind.config.ts
├── tsconfig.json
└── vite.config.ts
```

---

## React Router en modo data

Se usa `createBrowserRouter` con loaders y actions en lugar del modo declarativo clásico.

### Estructura de rutas

```
/                         → redirect → /dashboard  (requiresAuth)
/login                    → LoginPage
/signup                   → SignupPage
/dashboard                → DashboardPage          (requiresAuth)
/applications             → ApplicationListPage    (requiresAuth)
/applications/new         → ApplicationFormPage    (requiresAuth)
/applications/:id         → ApplicationDetailPage  (requiresAuth)
```

### Loader de ruta protegida

Cada ruta privada declara un `loader` que verifica el token antes de renderizar.
Si no hay token válido, retorna un `redirect('/login')` — sin componente wrapper adicional.

```ts
// Ejemplo: features/applications/loaders.ts
export async function applicationsLoader() {
  const token = authStore.getState().accessToken
  if (!token) return redirect('/login')
  return await api.get('/applications/')
}
```

### Action de formulario

Los formularios usan `<Form method="post">` de React Router.
El `action` recibe el `request`, extrae el body, llama a la API y retorna errores o hace redirect.

```ts
// features/auth/actions.ts
export async function loginAction({ request }: ActionFunctionArgs) {
  const data = await request.formData()
  try {
    const tokens = await api.post('/auth/token/', { email, password })
    authStore.getState().setTokens(tokens)
    return redirect('/dashboard')
  } catch (e) {
    return { error: 'Credenciales inválidas' }
  }
}
```

### Error boundaries

Cada ruta define `errorElement` para capturar errores de loader/action sin romper el árbol de rutas.

---

## Manejo de autenticación

### Almacenamiento de tokens

| Token | Dónde | Por qué |
|---|---|---|
| `access_token` | Memoria (Zustand) | No persiste entre tabs; más seguro ante XSS |
| `refresh_token` | `localStorage` | Necesita sobrevivir reload de página |

Al recargar la página: si hay `refresh_token` en `localStorage`, llamar a `/auth/token/refresh/` antes de renderizar cualquier ruta protegida. Si falla → limpiar y redirigir a login.

### Flujo de arranque

```
main.tsx
  └─ bootstrap()              ← intenta refresh si hay token guardado
       ├─ éxito → setAccessToken en Zustand → renderiza App
       └─ fallo → clearTokens → renderiza App (loader redirigirá a /login)
```

### Axios interceptors (`lib/api.ts`)

**Request interceptor:**
- Inyecta `Authorization: Bearer <accessToken>` en cada request

**Response interceptor:**
- Si respuesta es `401`:
  1. Intenta `POST /auth/token/refresh/` con el refresh token
  2. Si éxito → actualiza `accessToken` en Zustand → reintenta el request original
  3. Si falla → `clearTokens()` + `redirect('/login')`
- Solo un refresh en vuelo simultáneo (cola de requests pendientes mientras refresca)

```ts
// lib/api.ts — pseudocódigo
let isRefreshing = false
let queue: (() => void)[] = []

api.interceptors.response.use(null, async (error) => {
  if (error.response?.status !== 401) throw error
  if (isRefreshing) return new Promise(resolve => queue.push(resolve))

  isRefreshing = true
  try {
    const { access } = await refreshTokens()
    setAccessToken(access)
    queue.forEach(r => r())
    return api.request(error.config)   // reintenta
  } catch {
    clearTokens()
    window.location.href = '/login'
  } finally {
    isRefreshing = false
    queue = []
  }
})
```

### Zustand store de auth (`features/auth/store.ts`)

```ts
interface AuthState {
  accessToken: string | null
  user: { id: string; email: string; role: 'user' | 'admin' } | null
  setTokens: (access: string, refresh: string) => void
  clearTokens: () => void
}
```

---

## Estado global

| Lib | Qué maneja |
|---|---|
| **Zustand** | Auth (tokens, user), UI global (sidebar open, tema) |
| **TanStack Query** | Todos los datos del servidor (applications, user profile) |

TanStack Query se encarga de cache, refetch, loading/error states para datos de API.
Zustand solo para estado que no viene del servidor.

---

## Variables de entorno

```env
# .env.local (no versionado)
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_BASE_URL=ws://localhost:8000/ws
```

El cliente Axios se inicializa con `baseURL: import.meta.env.VITE_API_BASE_URL`.

---

## WebSocket (futuro)

Para recibir actualizaciones de estado de aplicaciones en tiempo real desde Django Channels.

- Se conecta a `ws://localhost:8000/ws/applications/<id>/`
- Autenticación: JWT en query param o subprotocolo al conectar
- `lib/ws.ts` expondrá un hook `useApplicationStatus(id)` que escucha el socket y actualiza el estado local
- Reconexión automática con backoff exponencial

---

## Convenciones

- **Archivos**: `kebab-case` para carpetas, `PascalCase` para componentes, `camelCase` para utils/hooks
- **Tipos de API**: definidos en `src/types/api.ts` — un tipo por recurso (User, Application, etc.)
- **Componentes shadcn**: se generan en `src/components/ui/` y no se modifican directamente
- **Formularios**: siempre React Hook Form + Zod schema; nunca estado local manual para inputs
- **Queries**: una query key por recurso (`['applications']`, `['applications', id]`)
- **Rutas**: declaradas todas en `src/app/router.tsx` — único archivo de verdad del routing

---

## Orden de implementación sugerido

1. Init Vite + TS + Tailwind + shadcn
2. `lib/api.ts` — axios con interceptors (sin auth aún)
3. Auth store (Zustand) + helpers de token
4. Login page + action → prueba real contra `/api/auth/token/`
5. Bootstrap de refresh al cargar la app
6. Signup page
7. Rutas protegidas con loader guard
8. Dashboard básico
9. Formulario de solicitud de crédito
10. WebSocket para status en tiempo real
