# CLAUDE.md — bravo-test

## Proyecto
API REST para evaluación de solicitudes de crédito con estrategia por país.
Stack: Django REST Framework · PostgreSQL · Celery · Redis · React+Vite · Nginx · Docker.

## Repo
Monorepo. `frontend/` y `backend/` son subdirectorios — nunca `git init` dentro de ellos.

```
bravo-test/
├── backend/
│   ├── config/          # settings, urls, celery
│   ├── users/           # auth JWT
│   ├── applications/    # solicitudes de crédito
│   ├── common/applications/countries/  # strategy validators MX/CO
│   ├── fixtures/users.json
│   ├── Dockerfile.prod · Dockerfile.dev
│   ├── entrypoint.prod.sh · entrypoint.dev.sh
│   └── .env.example · .env.prod · .env.dev  (no commitear)
├── frontend/
│   ├── src/features/applications/  # types, api, columns, components
│   ├── src/components/data-table/  # DataTable genérico DRF+TanStack
│   ├── src/shared/types/           # DRFPaginatedParams/Response
│   ├── Dockerfile.prod · Dockerfile.dev
│   └── nginx.prod.conf
├── docker-compose.prod.yml · docker-compose.dev.yml
├── Makefile
└── docs/  # arquitecture.mmd · database.mmd · flows/
```

## Comandos backend
```bash
uv run backend/manage.py runserver        # dev local
uv run backend/manage.py makemigrations <app>
uv run backend/manage.py migrate
uv --project backend add <paquete>        # instalar dep (no pip)
```
> Usar rutas absolutas o encadenar en un solo comando — `cd` persiste entre llamadas shell.

## Docker
```bash
make dev-build && make dev    # dev: runserver + Vite HMR + 1 worker
make prod-build && make prod  # prod: gunicorn + nginx + 2 workers
make dev-clean                # resetear volúmenes dev
```
Archivos env: `backend/.env.dev` (dev) · `backend/.env.prod` (prod).

## Stack backend
- Python 3.13 · Django 6 · DRF 3.17 · SimpleJWT · django-cors-headers · Whitenoise · Celery · django-celery-results
- DB: PostgreSQL (Docker) / SQLite (local sin Docker)
- `DEFAULT_AUTHENTICATION_CLASSES`: JWTAuthentication — `DEFAULT_PERMISSION_CLASSES`: IsAuthenticated
- Paginación: `PageNumberPagination`, `PAGE_SIZE=10`
- Endpoints públicos: declarar `permission_classes = (AllowAny,)` explícitamente
- JWT: access 15 min · refresh 7 días · header `Authorization: Bearer <token>`

## Stack frontend
- Vite 8 · React 19 · TypeScript · Tailwind v4 · shadcn/ui (Base UI) · TanStack Query + Table · react-hook-form · zod
- Alias de imports: `~/` → `src/`
- Proxy dev: `VITE_PROXY_TARGET=http://api:8000` (docker) / `http://localhost:8000` (local)

## Apps Django activas

### `users`
- `User`: AbstractBaseUser, login por email, roles `user|admin`, UUID PK
- Endpoints: `POST /api/auth/signup/` · `/api/auth/token/` · `/api/auth/token/refresh/`

### `applications`
- Modelos: `CreditApplication`, `BankProviderData`, `CountryValidation`, `ApplicationStatusHistory`
- `CreditApplicationService`: valida doc → mock bank → reglas financieras → persiste → Celery task
- Strategy por país en `common/applications/countries/`: `MXCountryValidator`, `COCountryValidator`
- Endpoints: `GET/POST /api/applications/` · `PATCH /api/applications/{id}/`

## Convenciones backend
- App en `backend/<app>/`, URLs en `config/urls.py` bajo `/api/<app>/`
- Serializers en `<app>/serializers.py`, vistas en `<app>/views.py`
- Modelos: `db_table` explícito (coincidir con ERD en `docs/database/database.mmd`), UUID PK, `created_at`/`updated_at`

## Convenciones frontend
- Feature en `src/features/<feature>/` con `types.ts`, `api.ts`, `columns.tsx`, `components/`
- shadcn components en `src/components/ui/` — importar desde `~/components/ui/`

## Commits
**No hacer commits sin que el usuario lo indique explícitamente.**

Formato: `<type>(<scope>): <descripción>`
Scopes: `frontend` · `backend` · `docker` · `docs` · `config`
Ejemplos:
```
feat(frontend): add credit applications table
feat(backend): add country validator strategy
fix(docker): fix postgres healthcheck race condition
chore(frontend): install @tanstack/react-table
docs: update README with Docker environments
```
Co-author en cada commit: `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`

## ERD
`docs/database/database.mmd` — fuente de verdad. Verificar antes de crear/modificar modelos.
