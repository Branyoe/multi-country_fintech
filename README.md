# bravo-test

API REST para evaluación de solicitudes de crédito con estrategia por país.

## Stack

| Capa | Tecnología |
|---|---|
| **Frontend** | Vite 8 + React 19 + TypeScript + Tailwind v4 + shadcn/ui |
| **Backend** | Django 6 + Django REST Framework + SimpleJWT + Whitenoise |
| **Tareas async** | Celery (workers) + Redis |
| **Base de datos** | PostgreSQL 16 |
| **Contenedores** | Docker Compose + Make |

---

## Instalación

Prerrequisitos: Docker Desktop y `make`. Docker es el único entorno soportado.

```bash
make dev    # dev: hot-reload
make prod   # prod: Daphne + Nginx, imágenes compiladas
```

El `.env` se crea automáticamente en el primer arranque. Acceso: `http://localhost:3000`.

### Diferencias entre entornos

| | Dev | Prod |
|---|---|---|
| Backend | `runserver` + auto-reload | Daphne ASGI (HTTP + WebSockets) |
| Frontend | Vite HMR | Nginx + build estático |
| Celery workers | 1 réplica | 2 réplicas |
| Base de datos | `bravo_dev` | `bravo` |

> No levantar ambos entornos simultáneamente — comparten los mismos puertos.

### Comandos

```bash
make dev / prod              # construye e inicia (crea .env si falta)
make dev-down / prod-down    # detener
make dev-clean / prod-clean  # detener + eliminar volúmenes (reset BD)
make logs-dev / logs-prod    # tail de logs
```

---

## API

Base URL: `http://localhost:8000/api/` (dev) · `http://localhost:3000/api/` (prod)

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| POST | `/auth/signup/` | Libre | Registro |
| POST | `/auth/token/` | Libre | Login → access + refresh |
| POST | `/auth/token/refresh/` | Libre | Renovar access token |
| GET | `/auth/me/` | Bearer | Perfil del usuario autenticado |
| GET | `/countries/` | Libre | Metadata de países disponibles |
| GET | `/applications/` | Bearer | Listar solicitudes |
| POST | `/applications/` | Bearer | Crear solicitud |
| GET | `/applications/{id}/` | Bearer | Detalle |
| PATCH | `/applications/{id}/` | Bearer | Actualizar estado |

Header de autenticación: `Authorization: Bearer <access_token>`

---

## Usuarios y roles

Dos roles: `user` (por defecto) y `admin`.

| Capacidad | `user` | `admin` |
|---|---|---|
| Crear solicitudes | Sí | Sí |
| Ver sus propias solicitudes | Sí | Sí |
| Ver solicitudes de otros usuarios | No | Sí |
| Actualizar estado de cualquier solicitud | No | Sí |

**Asignación de rol:** el signup público siempre crea `role=user`; aunque el payload incluya `role=admin`, el campo se ignora. Los usuarios admin se crean desde el Django Admin o directamente en BD.

**Indicador en el frontend:** el rol se muestra como etiqueta junto al email en el header (`Admin` variante `default`, `Usuario` variante `secondary`). Se obtiene de `GET /auth/me/` al arrancar la app y se persiste en Zustand.

### Usuarios de fixtures

Cargados automáticamente en cada arranque (idempotente):

| Email | Contraseña | Rol |
|---|---|---|
| `admin@dev.local` | `admin123` | `admin` |
| `user@dev.local` | `user1234` | `user` |

---

## Sistema de países dinámico

Los países disponibles se gestionan desde la base de datos, sin tocar el código del frontend.

**Flujo:** `Country (BD) → cache Redis → GET /api/countries/ → Frontend`

- La metadata de cada país (código, tipo de documento, regex de validación) se cachea en Redis al primer acceso. Las peticiones siguientes no tocan la BD.
- Al guardar o eliminar un `Country` desde el Admin, una señal `post_save` invalida el cache automáticamente.
- Si Redis no está disponible, `IGNORE_EXCEPTIONS: True` hace fallback silencioso a consulta directa a BD.

**Para agregar un país:**
1. Crear la entrada en el Admin o en `backend/fixtures/countries.json`.
2. Crear `XYZCountryValidator` en `countries/validators/` con las reglas de documento y financieras.
3. Registrarlo en `countries/validators/registry.py`.

No se requiere ningún cambio en el frontend.

---

## Estructura del repositorio

```
bravo-test/
├── backend/
│   ├── config/            # Settings, URLs, Celery, ASGI
│   ├── users/             # Auth JWT (signup, login, me)
│   ├── countries/         # Country, CountryStatus, validators por país
│   ├── applications/      # CreditApplication, servicios, tasks, workflows
│   ├── fixtures/          # Datos iniciales (users, countries, statuses)
│   ├── Dockerfile.dev / Dockerfile.prod
│   ├── entrypoint.prod.sh # migrate → loaddata → collectstatic → daphne
│   └── .env.example / .env.prod.example
├── frontend/
│   ├── src/
│   │   ├── features/      # auth, applications
│   │   ├── components/    # ui, data-table
│   │   └── lib/           # api.ts (axios), bootstrap.ts
│   ├── e2e/               # Tests Playwright
│   ├── Dockerfile.dev / Dockerfile.prod
│   └── nginx.prod.conf    # SPA + proxy /api/ /admin/ /static/ /ws/
├── k8s/                   # Manifests de Kubernetes
├── docs/
│   ├── arquitecture/      # Diagrama de arquitectura (.mmd)
│   ├── database/          # ERD
│   └── flows/             # Flujos de auth, solicitudes, cache, WebSocket
├── docker-compose.dev.yml
├── docker-compose.prod.yml
└── Makefile
```

---

## Tests

### Backend

```bash
cd backend && uv run pytest -v
cd backend && uv run pytest applications/ -v
```

### Frontend E2E (Playwright)

Requiere el backend corriendo en `:8000`.

```bash
cd frontend && npm run test:e2e
cd frontend && npm run test:e2e:ui   # modo UI interactivo
```

---

## Kubernetes

Namespace: `bravo`. Requiere un controlador Ingress nginx instalado en el cluster.

### Estructura de k8s/

```
k8s/
├── namespace.yaml
├── config/configmap-api.yaml       # Variables no sensibles (DB_HOST, Redis URLs, ALLOWED_HOSTS…)
├── secrets/secret-api.yaml         # Template — completar y NO commitear con valores reales
├── storage/pvc-postgres.yaml       # PVC 10Gi ReadWriteOnce para Postgres
├── postgres/                       # StatefulSet + Service headless
├── redis/                          # Deployment (Recreate) + Service
├── api/
│   ├── job-migrate.yaml            # Corre migrate+loaddata una sola vez antes del Deployment
│   ├── deployment-api.yaml         # Daphne ASGI, 2 réplicas
│   └── service-api.yaml
├── celery/deployment-celery.yaml   # 2 réplicas × concurrency 2, sin Service
├── frontend/                       # Nginx SPA, 2 réplicas + Service
└── ingress/ingress.yaml            # Todo entra por frontend:80 — Nginx proxea /api/ /ws/ internamente
```

**Notas:**
- `api` y `celery-worker` usan la misma imagen; `celery` solo cambia el `command`.
- Las migrations corren en `job-migrate.yaml` (no en el Deployment) para evitar race condition con 2 réplicas arrancando en paralelo.
- El Ingress apunta todo a `frontend:80`. El Nginx interno gestiona `/api/`, `/ws/` y `/static/` con los headers de WebSocket correctos.
- Redis usa DB0 (broker), DB1 (caché) y DB2 (channel layer).
- `storageClassName` en el PVC está sin hardcodear; usar el default del cluster o sobreescribir según proveedor.

### Simulación local con minikube

Requiere minikube (`winget install Kubernetes.minikube`) y Docker Desktop.

```bash
# Arrancar cluster
minikube start
minikube addons enable ingress

# Apuntar Docker al daemon de minikube
minikube -p minikube docker-env --shell powershell | Invoke-Expression  # PowerShell
eval $(minikube docker-env)                                               # bash/WSL

# Construir imágenes localmente (sin push a registry)
docker build -t bravo-api:local      ./backend  -f ./backend/Dockerfile.prod
docker build -t bravo-frontend:local ./frontend -f ./frontend/Dockerfile.prod \
  --build-arg VITE_API_BASE_URL=/api

# Reemplazar en los manifests:
#   REPLACE_WITH_YOUR_REGISTRY/bravo-api:TAG      → bravo-api:local
#   REPLACE_WITH_YOUR_REGISTRY/bravo-frontend:TAG → bravo-frontend:local
# Reemplazar REPLACE_WITH_YOUR_DOMAIN → bravo.local (configmap, ingress)
# Completar k8s/secrets/secret-api.yaml

# Aplicar
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets/ -f k8s/config/ -f k8s/storage/
kubectl apply -f k8s/postgres/ -f k8s/redis/
kubectl wait --for=condition=ready pod -l app=postgres -n bravo --timeout=120s
kubectl apply -f k8s/api/job-migrate.yaml
kubectl wait --for=condition=complete job/migrate -n bravo --timeout=120s
kubectl apply -f k8s/api/ -f k8s/celery/ -f k8s/frontend/ -f k8s/ingress/

# Exponer Ingress (mantener corriendo en otra terminal)
minikube tunnel
```

Agregar `127.0.0.1 bravo.local` en `C:\Windows\System32\drivers\etc\hosts`. Acceso: `http://bravo.local`.

Para detener: `minikube stop` — Para destruir todo: `minikube delete`.
