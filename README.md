# bravo-test

API REST para evaluación de solicitudes de crédito con estrategia por país.

## Stack

| Capa | Tecnología |
|---|---|
| **Frontend** | Vite 8 + React 19 + TypeScript + Tailwind v4 + shadcn/ui |
| **Backend** | Django 6 + Django REST Framework + SimpleJWT + Whitenoise |
| **Tareas async** | Celery (workers) + Redis |
| **Base de datos** | PostgreSQL 16 (Docker) / SQLite (dev local sin Docker) |
| **Contenedores** | Docker Compose + Make |

---

## Entornos Docker

El proyecto tiene dos configuraciones Docker:

| | **Dev** (`docker-compose.dev.yml`) | **Prod** (`docker-compose.prod.yml`) |
|---|---|---|
| Backend server | Django `runserver` + auto-reload | Gunicorn (2 workers) |
| Frontend | Vite dev server + HMR | Nginx sirviendo build estático |
| Static files | Django debug | Whitenoise vía Gunicorn |
| Hot-reload | Sí (backend + frontend) | No |
| Celery workers | 1 réplica | 2 réplicas |
| Base de datos | `bravo_dev` | `bravo` |

> No levantar ambos entornos simultáneamente — comparten los mismos puertos.

---

## Desarrollo con Docker (recomendado)

Todos los servicios corren en contenedores con hot-reload: los cambios de código se reflejan instantáneamente sin reconstruir imágenes.

**Prerrequisitos:** Docker Desktop + `make`.

```bash
# 1. Copiar variables de entorno para dev
cp backend/.env.example backend/.env.dev

# 2. Construir imágenes (solo la primera vez o al cambiar deps)
make dev-build

# 3. Levantar el entorno
make dev
```

**Accesos:**

| Servicio | URL |
|---|---|
| Frontend (HMR) | http://localhost:3000 |
| API directa | http://localhost:8000/api/ |
| Django Admin | http://localhost:8000/admin/ |
| PostgreSQL | `localhost:5432` — DB: `bravo_dev`, user/pass: `bravo/bravo` |
| Redis | `localhost:6379` |

**Crear superusuario:**

```bash
docker compose -f docker-compose.dev.yml exec api python manage.py createsuperuser
```

**Hot-reload:**

| Servicio | Comportamiento |
|---|---|
| Backend | `runserver` detecta cambios en `.py` y recarga automáticamente |
| Frontend | Vite HMR actualiza el browser sin recargar la página |
| Celery | Requiere reinicio manual: `docker compose -f docker-compose.dev.yml restart celery_worker` |

---

## Producción local con Docker

Simula el entorno productivo: Gunicorn + Nginx, imágenes compiladas, sin hot-reload.

```bash
# 1. Copiar variables de entorno
cp backend/.env.example backend/.env.prod

# 2. Construir y levantar
make prod-build
make prod
```

**Accesos:**

| Servicio | URL |
|---|---|
| Frontend (Nginx) | http://localhost:3000 |
| Django Admin | http://localhost:3000/admin/ |
| PostgreSQL | `localhost:5432` — DB: `bravo`, user/pass: `bravo/bravo` |
| Redis | `localhost:6379` |

> El primer arranque aplica migraciones, carga el usuario admin (`admin@dev.local` / `admin123`) y recolecta los archivos estáticos automáticamente.

---

## Comandos Make

```bash
# ── Dev ──────────────────────────────────────────────────────────────────────
make dev-build      # construir imágenes dev (primera vez o al cambiar deps)
make dev            # levantar entorno dev con hot-reload
make dev-down       # detener entorno dev
make dev-clean      # detener + eliminar volúmenes dev (reset BD)
make logs-dev       # seguir logs del entorno dev

# ── Prod ─────────────────────────────────────────────────────────────────────
make prod-build     # construir imágenes prod
make prod           # levantar entorno prod
make prod-down      # detener entorno prod
make prod-clean     # detener + eliminar volúmenes prod (reset BD)
make logs-prod      # seguir logs del entorno prod
```

---

## Dev local — sin Docker

Para desarrollo ultra-rápido con SQLite y sin contenedores.

**Prerrequisitos:** Python 3.13+, [uv](https://docs.astral.sh/uv/getting-started/installation/), Node 22+.

#### Backend

```bash
# Primera vez: dependencias + migraciones + fixtures
bash backend/gen.sh

# Servidor de desarrollo
uv run backend/manage.py runserver
# → http://localhost:8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

El proxy de Vite (`/api/`, `/admin/`, `/static/`) apunta a `http://localhost:8000` por defecto.

**Variables de entorno** (`backend/.env`):
```env
SECRET_KEY=dev-secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://localhost:8000
CELERY_BROKER_URL=redis://localhost:6379/0
```

---

## Tests

### Backend (pytest)

```bash
uv run pytest -v
uv run pytest applications/tests/ -v
uv run pytest users/tests/ -v
```

### Frontend — E2E (Playwright)

Requiere el backend corriendo en `:8000`.

```bash
cd frontend
npm run test:e2e
npm run test:e2e:ui   # modo UI interactivo
```

---

## API — endpoints principales

Base URL (Docker dev): `http://localhost:8000/api/`
Base URL (Docker prod): `http://localhost:3000/api/`

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| POST | `/auth/signup/` | Libre | Registro |
| POST | `/auth/token/` | Libre | Login → access + refresh |
| POST | `/auth/token/refresh/` | Libre | Renovar access token |
| GET | `/applications/` | Bearer | Listar solicitudes |
| POST | `/applications/` | Bearer | Crear solicitud |
| GET | `/applications/{id}/` | Bearer | Detalle |
| PATCH | `/applications/{id}/` | Bearer | Actualizar estado |
| GET | `/applications/countries/` | Libre | Metadata de países disponibles |

Header: `Authorization: Bearer <access_token>`

---

## Sistema de países dinámico

Los países disponibles para crear solicitudes de crédito se gestionan desde la base de datos, **sin tocar el código del frontend**.

### Cómo funciona

```
BD → modelo Country → cache Redis → GET /api/applications/countries/ → Frontend
```

1. El modelo `Country` almacena la metadata de cada país: código, nombre, tipo de documento, hint, ejemplo y regex de validación.
2. El backend cachea esa información en Redis al primer acceso. Las siguientes peticiones no tocan la base de datos.
3. Cuando un administrador edita o elimina un país desde el **Django Admin**, una señal `post_save` invalida el cache automáticamente.
4. El frontend consulta el endpoint al cargar la app y usa esa respuesta para: poblar el selector de países, mostrar la descripción del formato de documento y construir los filtros de la tabla.

### Agregar un país nuevo

1. Crea la entrada en la BD desde el Admin (`/admin/applications/country/`) o añadela a `backend/fixtures/countries.json`.
2. Crea su clase `XYZCountryValidator` en `backend/common/applications/countries/` con las reglas de validación del documento y las reglas financieras.
3. Registra el validator en `backend/common/applications/countries/registry.py`.

No se requiere ningún cambio en el frontend.

### Por qué esta decisión

- **Sin duplicación**: antes, los nombres y formatos de países estaban hardcodeados en 5 lugares del frontend y en el backend. Cualquier cambio requería desplegar ambos lados.
- **Editable sin deploy**: labels, hints y ejemplos son datos, no código. Un admin puede ajustarlos en caliente.
- **Sin costo en rendimiento**: el cache Redis sirve la metadata sin queries a BD en condiciones normales. Si Redis no está disponible, `IGNORE_EXCEPTIONS: True` hace que las operaciones fallen silenciosamente y el sistema siga funcionando (con queries directas a BD como fallback).

---

## Estructura del repositorio

```
bravo-test/
├── backend/               # Django REST API
│   ├── config/            # Settings, URLs, Celery
│   ├── users/             # Auth (JWT, signup, login)
│   ├── applications/      # Solicitudes de crédito (CRUD)
│   ├── common/            # Código compartido (validators por país)
│   ├── fixtures/          # Datos iniciales (admin)
│   ├── Dockerfile.prod    # Imagen producción (multi-stage)
│   ├── Dockerfile.dev     # Imagen desarrollo (deps only, sin código)
│   ├── entrypoint.prod.sh # migrate → loaddata → collectstatic → gunicorn
│   ├── .env.example       # Plantilla de variables de entorno
│   ├── .env.prod        # Config para prod Docker (no commitear)
│   └── .env.dev           # Config para dev Docker (no commitear)
├── frontend/              # Vite + React
│   ├── src/
│   │   ├── features/      # auth, applications
│   │   ├── components/    # ui, data-table
│   │   ├── lib/           # api.ts (axios), bootstrap.ts
│   │   └── app/           # router, páginas
│   ├── e2e/               # Tests Playwright
│   ├── Dockerfile.prod    # Imagen producción (build + Nginx)
│   ├── Dockerfile.dev     # Imagen desarrollo (node_modules only)
│   └── nginx.prod.conf    # SPA + proxy /api/ /admin/ /static/
├── docs/
│   ├── arquitecture/      # Diagrama de arquitectura (.mmd)
│   ├── database/          # ERD — fuente de verdad del esquema
│   └── flows/             # Flujos auth, solicitud de crédito
├── docker-compose.prod.yml     # Orquestación producción
├── docker-compose.dev.yml # Orquestación desarrollo (hot-reload)
├── Makefile               # Shortcuts: make dev / make prod
└── CLAUDE.md              # Instrucciones para el asistente IA
```
