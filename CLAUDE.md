# CLAUDE.md — bravo-test

## Proyecto
API REST para evaluación de solicitudes de crédito con estrategia por país.
Stack: Django REST Framework · PostgreSQL · Celery · Redis · React+Vite · Nginx · Docker.

---

## Estructura del repo

Monorepo. `frontend/` y `backend/` son subdirectorios — nunca `git init` dentro de ellos.

```
bravo-test/
├── backend/
│   ├── config/               # settings.py, urls.py, celery.py, wsgi.py
│   ├── users/                # auth JWT (signup, token)
│   ├── countries/            # Country, CountryStatus, StatusTransition + validators MX/CO
│   │   └── validators/       # base.py, mx.py, co.py, registry.py
│   ├── applications/         # CreditApplication + services + tasks + filters
│   ├── fixtures/             # users.json, countries.json, statuses.json
│   ├── conftest.py           # pytest fixtures globales (countries, statuses, cache)
│   ├── pytest.ini
│   ├── Dockerfile.dev · Dockerfile.prod
│   ├── entrypoint.dev.sh · entrypoint.prod.sh
│   ├── pyproject.toml        # deps via uv
│   └── .env.example · .env.dev · .env.prod  (no commitear)
├── frontend/
│   ├── src/
│   │   ├── app/              # router.tsx, páginas raíz
│   │   ├── features/
│   │   │   ├── applications/ # types, api, columns, components/, hooks/
│   │   │   └── auth/         # store (Zustand), actions, pages/
│   │   ├── components/
│   │   │   ├── ui/           # shadcn/ui + Base UI
│   │   │   └── data-table/   # DataTable genérico DRF+TanStack
│   │   ├── lib/              # api.ts (axios), auth.ts, form-errors.ts, bootstrap.ts
│   │   ├── shared/types/     # DRFPaginatedParams / DRFPaginatedResponse
│   │   └── types/api.ts      # User, TokenPair, ApiError
│   ├── vite.config.ts
│   ├── Dockerfile.dev · Dockerfile.prod
│   └── nginx.prod.conf
├── docker-compose.dev.yml · docker-compose.prod.yml
├── Makefile
└── docs/                     # architecture.mmd · database/database.mmd · flows/
```

---

## Comandos backend
```bash
# Desde la raíz del repo (uv resuelve el proyecto en backend/)
uv run backend/manage.py runserver
uv run backend/manage.py makemigrations <app>
uv run backend/manage.py migrate
uv --project backend add <paquete>      # instalar dep — no usar pip directamente

# Desde dentro de backend/
cd backend && uv run manage.py <comando>
```
> `cd` no persiste entre llamadas shell. Usar rutas absolutas o encadenar con `&&`.

## Comandos frontend
```bash
cd frontend && npm run dev      # dev local (sin Docker)
cd frontend && npm run build    # tsc -b && vite build
cd frontend && npm run lint
```

## Tests backend
```bash
cd backend && uv run pytest                  # todos los tests
cd backend && uv run pytest applications/    # app específica
cd backend && uv run pytest -q               # quiet
```

## Docker (vía Makefile)
```bash
make dev-build && make dev       # dev: runserver + Vite HMR + 1 worker Celery
make prod-build && make prod     # prod: gunicorn + nginx + 2 workers Celery
make dev-down                    # parar contenedores
make dev-clean                   # parar + borrar volúmenes (reset total)
make logs-dev                    # tail de todos los logs dev
make logs-prod                   # tail de todos los logs prod
```

Archivos env: `backend/.env.dev` (dev) · `backend/.env.prod` (prod).

---

## Stack backend
- Python 3.13 · Django 6 · DRF 3.17 · SimpleJWT · django-cors-headers · Whitenoise · Celery · django-celery-results · django-redis · python-decouple · django-filter
- DB: PostgreSQL 16 (Docker) / SQLite (local sin Docker, controlado por `DB_ENGINE` en .env)
- Cache: Redis (DB 1) — `django-redis` con `IGNORE_EXCEPTIONS=True` (degrada a DB si Redis falla)
- Celery broker: Redis (DB 0)

### DRF global
```python
DEFAULT_PERMISSION_CLASSES   = [IsAuthenticated]
DEFAULT_AUTHENTICATION_CLASSES = [JWTAuthentication]
DEFAULT_PAGINATION_CLASS     = PageNumberPagination  # PAGE_SIZE=10
DEFAULT_FILTER_BACKENDS      = [DjangoFilterBackend, SearchFilter, OrderingFilter]
```
- Endpoints públicos: declarar `permission_classes = [AllowAny]` explícitamente
- JWT: access 15 min · refresh 7 días · header `Authorization: Bearer <token>`

---

## Stack frontend
- Vite 8 · React 19 · TypeScript (es2023, bundler module resolution) · Tailwind v4
- shadcn/ui + Base UI (@base-ui/react) · class-variance-authority (CVA) para variantes
- TanStack Query v5 · TanStack Table v8 · react-hook-form · zod · Zustand · React Router v7
- Axios con interceptores (auto-refresh de token en 401, queue de requests paralelos)
- Alias de imports: `~/` → `src/`
- Proxy dev: `/api`, `/admin`, `/static` → `VITE_PROXY_TARGET` (default `http://localhost:8000`)

---

## Apps Django

### `users`
- `User`: AbstractBaseUser, login por email, roles `user|admin`, UUID PK, `db_table='users'`
- Endpoints: `POST /api/auth/signup/` · `POST /api/auth/token/` · `POST /api/auth/token/refresh/`

### `countries`
- `Country`: código, label, regex de documento, `is_active`, `db_table='country'`
- `CountryStatus`: estados por país (`code`, `label`, `is_initial`, `is_terminal`, `order`), `db_table='country_status'`
- `StatusTransition`: transiciones permitidas + `triggers_task` (nombre del Celery task), `db_table='status_transition'`
- `CountryValidation`: resultado por regla financiera, FK a `CreditApplication`, `db_table='country_validations'`
- Endpoint público: `GET /api/countries/` — devuelve países con array `statuses` anidado (cacheado en Redis, invalidación automática via signals)
- Validadores en `countries/validators/`: `BaseCountryValidator` (ABC) → `MXCountryValidator`, `COCountryValidator`
- Registry en `countries/validators/registry.py`: `get_validator(country_code) → BaseCountryValidator`

### `applications`
- `CreditApplication`: FK a `User`, FK a `Country` (como `country_ref`), FK a `CountryStatus` (como `status`), UUID PK, `db_table='credit_applications'`
  - `@property country` → `country_ref.code`
  - `@property status_code` → `status.code` (acceso sin JOIN innecesario)
- `BankProviderData`: OneToOne a `CreditApplication`, datos del buró, `db_table='bank_provider_data'`
- `ApplicationStatusHistory`: historial inmutable de cambios de estado (strings, no FK), `db_table='application_status_history'`
- Endpoints: `GET/POST /api/applications/` · `GET /api/applications/{id}/` · `PATCH /api/applications/{id}/`

---

## Convenciones backend

### Modelos
- UUID PK en todos los modelos: `id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`
- `db_table` explícito (coincidir con ERD en `docs/database/database.mmd`)
- Timestamps: `requested_at`/`created_at` con `auto_now_add=True`, `updated_at` con `auto_now=True`
- FKs con `related_name` siempre definido
- `on_delete=models.PROTECT` en FKs de auditoría/historial

### Serializers (patrón por operación)
- **Write** (`CreditApplicationSerializer`): validación de input, campos `write_only`
- **Update** (`CreditApplicationStatusSerializer`): valida transición via `StatusTransition` en DB
- **Read** (`CreditApplicationReadSerializer`): `SerializerMethodField` + `ReadOnlyField` para campos derivados
- `get_serializer_class()` en el ViewSet despacha por `self.action`

### Views / ViewSets
- Usar mixins explícitos en lugar de `ModelViewSet`:
  ```python
  class CreditApplicationViewSet(
      mixins.RetrieveModelMixin,
      mixins.UpdateModelMixin,
      mixins.ListModelMixin,
      viewsets.GenericViewSet,
  ):
  ```
- `http_method_names` declarado explícitamente para documentar intención
- `get_queryset()` siempre filtra por `self.request.user` (aislamiento por tenant)
- Mapeo de excepciones a HTTP en la vista: `ValueError → 400`, `ValidationError → 422`, `BankProviderError → 502`

### Services layer (`applications/services.py`)
- Lógica de negocio en clase con `@staticmethod` (sin estado, sin instancia)
- `CreditApplicationService.create()`: valida doc → obtiene estado inicial del DB → persiste → despacha Celery task
- `CreditApplicationService.update_status()`: valida transición via `StatusTransition` → actualiza → loguea historia → despacha task si aplica
- Lanza `ValueError` para violaciones de negocio (mapeado a 400 en la vista)

### Filtros (`applications/filters.py`)
- Soporta parámetros repetidos (`?status=pending&status=approved`) y listas con coma
- Relaciones en filtros: `status__code__in`, no `status__in`

### Ordering
- `ordering_fields` usa rutas de ORM para FKs: `status__order`, `country_ref__code`
- `meta: { orderingKey: 'status__order' }` en columnas del frontend mapea al mismo campo

### Celery tasks (`applications/tasks.py`)
- `@shared_task(bind=True, max_retries=3)` — `self.retry(exc=exc, countdown=60)` en excepciones de red
- Guard de idempotencia al inicio: `if app.status_code != 'pending': return`
- `get_or_create()` para `BankProviderData` (seguro en retries)
- Dispatch por nombre: `celery_app.send_task('process_application_mx', args=[str(app.id)])`
- El nombre del task vive en `StatusTransition.triggers_task` — el código no referencia tasks directamente
- Tasks actuales: `process_application_mx` (MX), `consulta_buro_co` (CO)
- No hay Celery Beat configurado (sin tareas periódicas)

### Validators (`countries/validators/`)
```python
class BaseCountryValidator(ABC):
    def validate_document(self, doc) -> tuple[bool, str]       # sync, regex del DB
    def fetch_bank_data(self, doc) -> BankData                  # async (en task), llamada al buró
    def validate_financial_rules(self, amount, income, bank_data) -> tuple[bool, str, str]
    def get_validation_rules(self) -> list[str]                 # etiquetas registradas en CountryValidation
```
- `BankData` es un `@dataclass` con campos `provider_name`, `account_status`, `total_debt`, `credit_score`, `raw_response`
- Para añadir un país: crear `XYCountryValidator`, registrar en `registry.py`, añadir estados/transiciones en fixtures

#### Limitación actual: evaluación agregada de reglas financieras
`validate_financial_rules()` devuelve **un único** `(bool, message, error_field)` para todas las reglas combinadas. `validate_country_rules_task` aplica ese mismo resultado a **todos** los nombres de `get_validation_rules()` al persistir en `CountryValidation`. Consecuencia: si tienes tres reglas y falla solo una, las tres quedan como `passed=False`. Los nombres en `get_validation_rules()` son etiquetas descriptivas, no evaluaciones independientes.

Para agregar una regla nueva dentro de la arquitectura actual ver la sección "Cómo agregar una regla financiera".

### Cómo agregar un nuevo estado a un país

1. **`backend/fixtures/statuses.json`**
   - Agregar el `CountryStatus` con un PK nuevo, `country` = PK del país, `code`, `label`, `order` correcto (ajustar el `order` de los estados siguientes si es necesario).
   - Agregar las `StatusTransition` que conectan el nuevo estado (from/to) con los estados adyacentes. Eliminar o redirigir las transiciones antiguas que el nuevo estado reemplaza.

2. **`backend/conftest.py`** — espejo de los fixtures para tests
   - Agregar `CountryStatus.objects.create(...)` con los mismos valores.
   - Actualizar el `bulk_create` de `StatusTransition` para que el flujo en tests coincida con el de producción.

3. **`applications/workflows/<país>.py`**
   - Si el nuevo estado dispara un Celery task, importarlo en `on_enter()` y agregar el caso `elif state_code == '<code>': <task>.delay(...)`.
   - Si el nuevo estado es el primer estado de procesamiento (bootstrap), sobrescribir `get_bootstrap_state()` para devolver su `code`.

4. **`applications/tasks.py`** (solo si el estado dispara un task nuevo)
   - Agregar `@shared_task(bind=True, max_retries=3, name='<nombre>')`.
   - Incluir el guard de idempotencia: `if app.status_code != '<code>': return`.
   - Transicionar al estado siguiente vía `CreditApplicationService.update_status(...)`.

5. **Tests** — actualizar `applications/tests/test_applications.py`
   - Corregir aserciones de status en `TestCreate` si cambia el estado de bootstrap.
   - Agregar o ajustar helpers de avance de estado en `TestTasks._advance_*` si los tasks tests necesitan llegar al nuevo estado antes de ejecutar una tarea.
   - Ajustar `TestStatusHistory` si cambia el conteo de entradas o los valores de `from_status`/`to_status`.

### Cómo agregar una regla financiera a un país

> **Restricción de arquitectura:** todas las reglas de un país comparten el mismo resultado en `CountryValidation` (ver limitación descrita arriba). Las reglas nuevas deben poder evaluarse con los mismos parámetros que ya recibe `validate_financial_rules` (`amount`, `income`, `bank_data`).

1. **`countries/validators/<país>.py`** — añadir la lógica en `validate_financial_rules()`
   ```python
   def validate_financial_rules(self, amount, income, bank_data):
       if <condición_nueva>:
           return False, '<mensaje>', '<campo_o_non_field_errors>'
       # reglas existentes …
       return True, '', ''
   ```
   El primer `return False` que se alcance cortocircuita el resto.

2. **Mismo archivo** — registrar el nombre en `get_validation_rules()`
   ```python
   def get_validation_rules(self) -> list[str]:
       return ['regla_existente', 'nombre_nueva_regla']
   ```
   El nombre es una cadena libre; se almacena en `CountryValidation.rule_name`.

3. **Tests** — clase `TestTasks` en `applications/tests/test_applications.py`
   - Test que verifique rechazo: `_create_app` con valores que disparen la regla → `_advance_mx_to_fetching` si es MX → `fetching_bank_data_task` → `validate_country_rules_task` → `assert app.status_code == 'rejected'`.
   - Verificar que el nombre queda registrado: `rules = list(CountryValidation.objects.filter(application=app).values_list('rule_name', flat=True)); assert 'nombre_nueva_regla' in rules`.

### Cache de países
- `countries/cache.py::get_countries_cached()` → `{code: Country}` desde Redis, con `prefetch_related('statuses')`
- Invalidación automática via `post_save`/`post_delete` signals conectados en `CountriesConfig.ready()`

---

## Convenciones frontend

### Feature structure
```
src/features/<feature>/
├── types.ts          # interfaces y tipos del dominio
├── api.ts            # funciones de API (thin wrappers sobre axios)
├── columns.tsx       # ColumnDef[] de TanStack Table
├── components/       # componentes específicos del feature
└── hooks/            # custom hooks (useCountries, useStatuses, etc.)
```

### API layer (`src/lib/api.ts`)
- `api`: cliente autenticado — inyecta `Authorization: Bearer` via interceptor de request
- `publicApi`: cliente sin auth (para signup, token, countries)
- `serializeParams`: arrays serialized como parámetros repetidos (`?status=a&status=b`), no como `status[]=a`
- Interceptor de response: detecta 401 → intenta refresh → reintenta request original — cola los requests paralelos con flag `isRefreshing` para evitar refreshes duplicados

### React Query
- `staleTime: Infinity` para datos estáticos (países, catálogos) — sin peticiones extra en refocus
- `queryKey` incluye todos los params de paginación/filtro/orden → refetch automático al cambiar
- `placeholderData: (prev) => prev` en DataTable para evitar flicker durante refetch
- `refetchOnWindowFocus: false` en DataTable

### TanStack Table + DataTable
- Paginación y sorting **manual** (enviados al backend vía params, no computados en cliente)
- `meta: { orderingKey: 'field__subfield' }` en columnas mapea el sort al campo DRF
- `FilterConfig` y `FilterOption` son los tipos del DataTable genérico:
  ```typescript
  interface FilterConfig {
    key: string; label: string; type?: 'single' | 'multiple'
    options?: FilterOption[]; isSearchable?: boolean; allowEmpty?: boolean
  }
  ```
- `disableOrderingColumns: []` habilita ordering en todas las columnas
- Debounce de 300ms en búsqueda de texto

### Formularios
- `zod` define el schema → `zodResolver` conecta con `react-hook-form`
- `applyApiErrors(err, setError, knownFields)` en `src/lib/form-errors.ts` enruta errores DRF:
  - Campos conocidos → `setError(field, ...)` (error inline)
  - `non_field_errors` y campos desconocidos → banner de error
- Campos numéricos como `string` en el form (el API los recibe como string)

### Auth (Zustand)
- `useAuthStore` en `src/features/auth/store.ts`: `accessToken` en memoria, `refreshToken` en `localStorage`
- `bootstrap()` en `src/lib/bootstrap.ts`: intenta refresh al arrancar la app antes de montar el router
- `requireAuth` loader en el router: redirige a `/login?next=...` si no hay token

### shadcn/ui + Base UI
- Componentes en `src/components/ui/` — importar desde `~/components/ui/`
- `buttonVariants` de CVA para reusar estilos de botón sin el componente Button (ej: links)
- Variantes Badge: `secondary` (pending), `outline` (en revisión / verificacion_buro), `default` (approved), `destructive` (rejected)

---

## Infra y despliegue

### Servicios Docker

| Servicio | Dev | Prod |
|---|---|---|
| API | `runserver` | Gunicorn 2 workers, timeout 60s |
| Frontend | Vite HMR :3000 | Nginx :3000 sirve build estático |
| Celery | 1 worker, debug | 2 replicas, 2 concurrency, info |
| Postgres | 16-alpine, `bravo_dev` | 16-alpine, `bravo` |
| Redis | 7-alpine | 7-alpine |

### Nginx (prod, `frontend/nginx.prod.conf`)
- `/` → SPA fallback: `try_files $uri $uri/ /index.html` (React Router maneja rutas)
- `/api/` → proxy a `http://api:8000/api/`
- `/admin/` → proxy a `http://api:8000/admin/`
- `/static/` → proxy a `http://api:8000/static/` (servido por Whitenoise)

### Whitenoise (static files)
- Storage: `CompressedManifestStaticFilesStorage` — compresión gzip + hashes en nombres
- `collectstatic --noinput` corre en `entrypoint.prod.sh` antes de Gunicorn

### Entrypoints
Ambos entrypoints ejecutan al inicio del contenedor:
1. `migrate --noinput`
2. `loaddata fixtures/users.json` (con `|| echo ...` — idempotente)
3. `loaddata fixtures/countries.json`
4. `loaddata fixtures/statuses.json`
5. *(solo prod)* `collectstatic --noinput`
6. Inicia servidor (runserver / gunicorn)

### Variables de entorno requeridas
```
SECRET_KEY, DEBUG, ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS, CSRF_TRUSTED_ORIGINS
DB_ENGINE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
CELERY_BROKER_URL   # redis://...:6379/0
CACHE_URL           # redis://...:6379/1
```
Local sin Docker: omitir `DB_ENGINE` → SQLite automático. Redis opcional (cache degrada a DB).

---

## Testing

### Fixtures globales (`backend/conftest.py`, `autouse=True`)
- `locmem_cache`: reemplaza Redis por cache en memoria para todos los tests
- `setup_countries`: crea MX y CO via `bulk_create`, limpia cache antes/después
- `setup_statuses`: crea `CountryStatus` y `StatusTransition` para MX (4 estados, 4 transiciones) y CO (5 estados, 6 transiciones)
- `mock_celery_send_task`: parchea `applications.services.celery_app.send_task` — los tasks nunca se ejecutan en tests

### Patrones de test
```python
# Helper de payload reutilizable
def payload(**kwargs):
    base = {'country': 'MX', 'full_name': '...', 'document_number': 'PERJ800101HDFRZN09', ...}
    base.update(kwargs)
    return base

# Auth client via JWT real
def _make_auth_client(email, password):
    c = Client()
    res = c.post(reverse('auth-token'), {'email': email, 'password': password}, content_type='application/json')
    c.defaults['HTTP_AUTHORIZATION'] = f"Bearer {res.json()['access']}"
    return c

# Clases de test agrupadas por dominio
@pytest.mark.django_db
class TestAuth: ...
class TestCreate: ...
class TestList: ...
class TestTasks: ...
```
- `pytest.ini`: `DJANGO_SETTINGS_MODULE=config.settings`
- Tests en `applications/tests/test_applications.py`

---

## Commits

**No hacer commits sin que el usuario lo indique explícitamente.**

Formato: `<type>(<scope>): <descripción>`
Scopes: `frontend` · `backend` · `docker` · `docs` · `config`

```
feat(backend): add country validator strategy
feat(frontend): add credit applications table
fix(docker): fix postgres healthcheck race condition
chore(frontend): install @tanstack/react-table
docs: update architecture diagram
```
Co-author en cada commit: `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`

---

## ERD
`docs/database/database.mmd` — fuente de verdad del schema. Verificar antes de crear o modificar modelos.
