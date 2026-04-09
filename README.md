# bravo-test

API REST para evaluación de solicitudes de crédito con estrategia por país.

## Stack

| Capa | Tecnología |
|---|---|
| **Frontend** | Vite 8 + React 19 + TypeScript + Tailwind v4 + shadcn/ui |
| **Backend** | Django 6 + Django REST Framework + SimpleJWT |
| **Tareas async** | Celery + Redis |
| **Base de datos** | PostgreSQL (Docker) / SQLite (dev local) |
| **Contenedores** | Docker Compose |

---

## Modos de desarrollo

### Docker — stack completo (recomendado)

Levanta todos los servicios: PostgreSQL, Redis, Django API (Gunicorn), Celery Worker y el frontend servido por Nginx.

**Prerrequisitos:** Docker + Docker Compose instalados.

```bash
# 1. Copiar variables de entorno para Docker
cp backend/.env.example backend/.env.docker
# Editar backend/.env.docker si querés cambiar credenciales

# 2. Construir y levantar
docker compose up --build
```

| Servicio | URL |
|---|---|
| Frontend + API (via Nginx) | http://localhost:3000 |
| Admin panel | http://localhost:3000/api/admin → redirige a Django |

> El primer arranque aplica migraciones y carga el usuario admin automáticamente.
> Credenciales del admin: `admin@dev.local` / `admin123`

**Comandos útiles:**

```bash
# Levantar en background
docker compose up -d --build

# Ver logs de un servicio
docker compose logs -f api
docker compose logs -f celery_worker

# Parar todo
docker compose down

# Parar y borrar volúmenes (reset completo de base de datos)
docker compose down -v
```

**Servicios internos:**

| Contenedor | Rol | Puerto interno |
|---|---|---|
| `postgres` | Base de datos PostgreSQL 16 | 5432 |
| `redis` | Broker Celery + caché | 6379 |
| `api` | Django + Gunicorn | 8000 |
| `celery_worker` | Celery worker | — |
| `frontend` | Nginx (SPA + proxy `/api/`) | 80 → host 3000 |

---

### Dev local — sin Docker

Para desarrollo rápido con hot-reload. Usa SQLite en lugar de PostgreSQL.

**Prerrequisitos:** Python 3.13+, [uv](https://docs.astral.sh/uv/getting-started/installation/), Node 22+.

#### Backend

```bash
# Primera vez: inicializar todo (dependencias + migraciones + fixtures)
bash gen.sh

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

**Variables de entorno backend** (`backend/.env`):
```env
SECRET_KEY=dev-secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
CELERY_BROKER_URL=redis://localhost:6379/0
```

> Sin Docker, Celery requiere Redis corriendo localmente. Si no lo necesitás, podés ignorar `CELERY_BROKER_URL` — Django arranca igual.

---

## Estructura del repositorio

```
bravo-test/
├── backend/               # Django REST API
│   ├── config/            # Settings, URLs, Celery
│   ├── users/             # Auth (JWT, signup, login)
│   ├── applications/      # Solicitudes de crédito (CRUD)
│   ├── fixtures/          # Datos iniciales (admin)
│   ├── Dockerfile
│   └── entrypoint.sh
├── frontend/              # Vite + React
│   ├── src/
│   │   ├── features/auth/ # Login, signup
│   │   ├── lib/           # api.ts (axios), bootstrap.ts, store
│   │   └── app/           # Router, páginas
│   ├── e2e/               # Tests Playwright
│   ├── Dockerfile
│   └── nginx.conf
├── docs/
│   ├── arquitecture/      # Diagrama de arquitectura
│   ├── database/          # ERD
│   └── flows/             # Flujos auth, crédito
├── docker-compose.yml
└── gen.sh                 # Script de inicialización local
```

---

## Tests

### Backend (pytest)

```bash
cd backend

# Todos los tests
uv run pytest -v

# Por app
uv run pytest users/tests/ -v
uv run pytest applications/tests/ -v
```

### Frontend — E2E (Playwright)

Requiere el backend corriendo en `:8000`.

```bash
cd frontend

# Correr tests headless
npm run test:e2e

# Modo UI interactivo
npm run test:e2e:ui
```

---

## API — endpoints principales

Base URL (Docker): `http://localhost:3000/api/`
Base URL (dev local): `http://localhost:8000/api/`

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| POST | `/auth/signup/` | Libre | Registro |
| POST | `/auth/token/` | Libre | Login → access + refresh |
| POST | `/auth/token/refresh/` | Libre | Renovar access token |
| GET | `/applications/` | Bearer | Listar mis solicitudes |
| POST | `/applications/` | Bearer | Crear solicitud |
| GET | `/applications/{id}/` | Bearer | Detalle |
| PATCH | `/applications/{id}/` | Bearer | Actualizar estado |

Header de autenticación: `Authorization: Bearer <access_token>`
