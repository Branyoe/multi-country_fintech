# bravo-test

API REST para evaluación de solicitudes de crédito con estrategia por país.

## Stack

| Capa | Tecnología |
|---|---|
| **Frontend** | Vite 8 + React 19 + TypeScript + Tailwind v4 + shadcn/ui |
| **Backend** | Django 6 + Django REST Framework + SimpleJWT + Whitenoise |
| **Tareas async** | Celery (workers) + Redis |
| **Base de datos** | PostgreSQL 16 (Docker) |
| **Contenedores** | Docker Compose + Make |

---

## Instalación

Prerrequisitos: Docker Desktop y `make`. Docker es el único entorno soportado — no hay soporte para ejecución local sin contenedores.

**Dev** — hot-reload:
```bash
make dev
```

**Prod local** — Daphne + Nginx, imágenes compiladas:
```bash
make prod
```

El env se crea automáticamente en el primer arranque. Acceso en ambos casos: `http://localhost:3000`.

Para detener: `make dev-down` / `make prod-down` — Para resetear BD: `make dev-clean` / `make prod-clean`

> Kubernetes local: ver sección [Kubernetes](#kubernetes).

---

## Entornos Docker

El proyecto tiene dos configuraciones Docker:

| | **Dev** (`docker-compose.dev.yml`) | **Prod** (`docker-compose.prod.yml`) |
|---|---|---|
| Backend server | Django `runserver` + auto-reload | Daphne ASGI (HTTP + WebSockets) |
| Frontend | Vite dev server + HMR | Nginx sirviendo build estático |
| Static files | Django debug | Whitenoise vía Daphne |
| Hot-reload | Sí (backend + frontend) | No |
| Celery workers | 1 réplica | 2 réplicas |
| Base de datos | `bravo_dev` | `bravo` |

> No levantar ambos entornos simultáneamente — comparten los mismos puertos.

---

## Comandos Make

```bash
make dev            # crea .env.dev si falta, construye e inicia (hot-reload)
make dev-down       # detener
make dev-clean      # detener + eliminar volúmenes (reset BD)
make logs-dev       # tail de logs

make prod           # crea .env.prod si falta, construye e inicia
make prod-down
make prod-clean
make logs-prod
```

Fixtures cargados al primer arranque: `admin@dev.local / admin123` y `user@dev.local / user1234`.

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
| POST | `/auth/signup/` | Libre | Registro (siempre crea rol `user`) |
| POST | `/auth/token/` | Libre | Login → access + refresh |
| POST | `/auth/token/refresh/` | Libre | Renovar access token |
| GET | `/auth/me/` | Bearer | Perfil del usuario autenticado |
| GET | `/applications/` | Bearer | Listar solicitudes |
| POST | `/applications/` | Bearer | Crear solicitud |
| GET | `/applications/{id}/` | Bearer | Detalle |
| PATCH | `/applications/{id}/` | Bearer | Actualizar estado |
| GET | `/countries/` | Libre | Metadata de países disponibles |

Header: `Authorization: Bearer <access_token>`

---

## Usuarios y roles

El sistema tiene dos roles: `user` (rol por defecto) y `admin`.

### Diferencias de acceso

| Capacidad | `user` | `admin` |
|---|---|---|
| Crear solicitudes | Sí | Sí |
| Ver sus propias solicitudes | Sí | Sí |
| Ver solicitudes de otros usuarios | No | Sí — ve todas |
| Actualizar estado de cualquier solicitud | No | Sí |

### Cómo se asigna el rol

- **Signup público** (`POST /auth/signup/`): siempre crea un usuario con `role=user`. Aunque el payload incluya `role=admin`, el campo se ignora.
- **Usuarios admin**: se crean únicamente por soporte, a través del Django Admin o directamente en base de datos.

### Indicador de rol en el frontend

El rol del usuario autenticado se muestra como una etiqueta junto al email en el header de la aplicación:

- `Admin` — etiqueta oscura (variante `default`)
- `Usuario` — etiqueta gris (variante `secondary`)

El rol se obtiene del endpoint `GET /auth/me/` al arrancar la app, se persiste en el store de Zustand y no requiere peticiones adicionales durante la sesión.

### Usuarios de fixtures (cargados en cada arranque)

Tanto el entorno dev como prod cargan `backend/fixtures/users.json` al iniciar. Esto crea dos usuarios predefinidos si aún no existen:

| Email | Contraseña | Rol |
|---|---|---|
| `admin@dev.local` | `admin123` | `admin` |
| `user@dev.local` | `user1234` | `user` |

> La carga es idempotente — si los usuarios ya existen, el comando falla silenciosamente sin afectar los datos existentes.

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
│   ├── entrypoint.prod.sh # migrate → loaddata → collectstatic → daphne
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
├── k8s/                   # Manifests de Kubernetes (ver sección siguiente)
├── Makefile               # Shortcuts: make dev / make prod
└── CLAUDE.md              # Instrucciones para el asistente IA
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

**Notas de configuración:**
- `api` y `celery-worker` usan la misma imagen; `celery` solo cambia el `command`.
- Las migrations corren en `job-migrate.yaml` (no en el Deployment) para evitar race condition con 2 réplicas arrancando en paralelo.
- El Ingress apunta todo a `frontend:80`. El Nginx interno ya tiene los bloques `/api/`, `/ws/`, `/static/` correctamente configurados con los headers de WebSocket — no se duplica lógica en el Ingress.
- Redis usa DB0 (broker), DB1 (caché) y DB2 (channel layer) — un solo Service, tres bases de datos.
- `storageClassName` en el PVC está sin hardcodear; usar el default del cluster o sobreescribir según proveedor.

### Simulación local con minikube

Requiere minikube instalado (`winget install Kubernetes.minikube`) y Docker Desktop corriendo.

```bash
# 1. Arrancar cluster con el addon de Ingress
minikube start
minikube addons enable ingress

# 2. Apuntar Docker al daemon de minikube (las imágenes se construyen dentro del cluster)
#    En PowerShell:
minikube -p minikube docker-env --shell powershell | Invoke-Expression
#    En bash/WSL:
eval $(minikube docker-env)

# 3. Construir imágenes (quedan disponibles dentro de minikube sin push a registry)
docker build -t bravo-api:local     ./backend  -f ./backend/Dockerfile.prod
docker build -t bravo-frontend:local ./frontend -f ./frontend/Dockerfile.prod \
  --build-arg VITE_API_BASE_URL=/api

# 4. Reemplazar los nombres de imagen en los manifests:
#    REPLACE_WITH_YOUR_REGISTRY/bravo-api:TAG     → bravo-api:local
#    REPLACE_WITH_YOUR_REGISTRY/bravo-frontend:TAG → bravo-frontend:local

# 5. Completar k8s/secrets/secret-api.yaml y cambiar REPLACE_WITH_YOUR_DOMAIN → bravo.local
#    en configmap-api.yaml e ingress.yaml

# 6. Aplicar
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets/ -f k8s/config/ -f k8s/storage/
kubectl apply -f k8s/postgres/ -f k8s/redis/
kubectl wait --for=condition=ready pod -l app=postgres -n bravo --timeout=120s
kubectl apply -f k8s/api/job-migrate.yaml
kubectl wait --for=condition=complete job/migrate -n bravo --timeout=120s
kubectl apply -f k8s/api/ -f k8s/celery/ -f k8s/frontend/ -f k8s/ingress/

# 7. Exponer el Ingress en localhost (dejarlo corriendo en otra terminal)
minikube tunnel

# 8. Registrar el dominio local (una sola vez)
#    Agregar en C:\Windows\System32\drivers\etc\hosts:
#    127.0.0.1  bravo.local
```

Acceso: `http://bravo.local`

Para detener: `minikube stop`. Para destruir todo: `minikube delete`.

