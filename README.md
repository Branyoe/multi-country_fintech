# FinTech-test

API REST para evaluación de solicitudes de crédito con estrategia por país. Incluye frontend React, pipeline asíncrono con Celery, WebSockets en tiempo real y manifiestos de Kubernetes.

---

## Stack

| Capa | Tecnología | Por qué |
|---|---|---|
| **Backend** | Django 6 + DRF + Daphne ASGI | Experiencia previa en producción; Daphne permite HTTP y WebSockets en un solo proceso sin servidor adicional |
| **Tareas async** | Celery + Redis (DB0) | Cola distribuida con reintentos nativos y backoff; escala horizontalmente agregando workers |
| **Base de datos** | PostgreSQL 16 | Transacciones ACID necesarias para consistencia en flujos concurrentes; soporte nativo de particionamiento por rango |
| **Cache** | Redis (DB1) | TTL ilimitado para catálogos estáticos; invalidación automática por señales de Django |
| **WebSockets** | Django Channels + Redis (DB2) | Tiempo real sin servidor separado; mismo proceso Daphne; channel layer distribuido |
| **Frontend** | Vite 8 + React 19 + TypeScript + Tailwind v4 | Stack con el que opero en producción actualmente |
| **Contenedores** | Docker Compose + Kubernetes | Reproducibilidad local y manifiestos de despliegue real |

---

## Instalación

Prerrequisitos: Docker Desktop y `make`.

```bash
make dev   # dev con hot-reload
make prod  # prod: Daphne + Nginx, imágenes compiladas
```

El `.env` se crea automáticamente en el primer arranque. Acceso: `http://localhost:3000`.

> Docker es el único entorno soportado.

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

El signup público siempre crea `role=user`; aunque el payload incluya `role=admin`, el campo se ignora. Los usuarios admin se crean desde el Django Admin o directamente en BD.

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

- La metadata de cada país se cachea en Redis al primer acceso con `timeout=None`. Las peticiones siguientes no tocan la BD.
- Al guardar o eliminar un `Country` desde el Admin, una señal `post_save` invalida el cache automáticamente.
- Si Redis no está disponible, `IGNORE_EXCEPTIONS: True` hace fallback silencioso a consulta directa a BD.

**Para agregar un país:**
1. Crear la entrada en el Admin o en `backend/fixtures/countries.json`.
2. Crear `XYZCountryValidator` en `countries/validators/` con las reglas de documento y financieras.
3. Registrarlo en `countries/validators/registry.py`.

No se requiere ningún cambio en el frontend.

---

## Supuestos

- **Proveedores bancarios simulados.** No existen APIs reales de buró. Implementé adapters que devuelven datos mock con la estructura que esperaría un proveedor real por país (score, deuda total, estado de cuenta).
- **Validación de documentos por regex.** La verificación del CURP, Cédula, etc. usa expresiones regulares con la estructura formal del documento. No se consulta ningún registro oficial.
- **Umbrales financieros por criterio propio.** Los ratios de deuda/ingreso y montos máximos se definen en el código de cada validator; los valores son razonables pero no están atados a ninguna regulación real.
- **Estado inicial gestionado en BD.** El estado de bootstrap de cada solicitud lo determina el `CountryStatus` marcado como `is_initial=True`, no un hardcode.
- **Webhooks configurables.** `WEBHOOK_URL` puede estar vacío; si no está configurado, el paso de notificación se omite sin error.
- **Dos países implementados** (MX y CO) como flujos completos end-to-end. El sistema está diseñado para que agregar ES, PT, IT o BR sea solo crear un validator + fixtures, sin cambios en la capa de aplicación.

---

## Decisiones técnicas y arquitectura

### Priorización del trabajo

Empecé por el modelo de datos y la capa backend: primero los modelos y relaciones, luego los serializers y views. Una vez que el CRUD funcionaba, construí el pipeline asíncrono con Celery. Después agregué Django Channels para los WebSockets. El frontend lo construí en paralelo usando el contrato de la API que ya tenía definido. Los manifiestos de Kubernetes y la documentación los dejé para el final porque no bloqueaban nada funcional.

Prioricé extensibilidad sobre cobertura de países: prefería tener MX y CO bien implementados con el patrón correcto que tener cuatro países con lógica pegada en el código.

### Patrón Strategy por país

Cada país tiene un `CountryValidator` que encapsula sus reglas de documento y financieras. El `registry.py` devuelve el validator correcto dado un código de país. El código de aplicación nunca conoce los países concretos: llama a `get_validator(country_code)` y delega.

Agregar un país nuevo requiere solo crear la clase y registrarla, sin modificar ninguna lógica existente. Lo mismo aplica para los adapters de proveedores bancarios: cada validator implementa `fetch_bank_data()` con la firma de su proveedor.

### Pipeline asíncrono con Celery

La creación de una solicitud es síncrona y devuelve `201` inmediatamente. El procesamiento ocurre en background:

```
MX: validating_document_task → fetching_bank_data_task → validate_country_rules_task → notify_final_decision_task
CO:                            fetching_bank_data_task → validate_country_rules_task → notify_final_decision_task
```

El nombre del Celery task que dispara cada transición de estado vive en `StatusTransition.triggers_task` (columna en BD), no hardcodeado. Esto permite cambiar el comportamiento desde el Admin sin redeployar.

Cada task tiene `max_retries=3` con `countdown=60s` y un guard de idempotencia al inicio (`if app.status_code != 'expected_state': return`), lo que hace el pipeline seguro en retries y con múltiples workers concurrentes.

### WebSockets en tiempo real

`ApplicationTimelineConsumer` (Django Channels) gestiona la conexión `ws://.../ws/applications/{id}/timeline/`. Al conectar, valida el JWT del query param, verifica ownership de la solicitud y suscribe al grupo `application_{id}`.

La publicación usa `transaction.on_commit`: cuando `update_status()` commitea el cambio, llama a `async_to_sync(channel_layer.group_send)` dentro del callback de commit, garantizando que el WebSocket solo recibe eventos de transacciones ya persistidas y no de rollbacks.

### Caché de catálogos

`GET /api/countries/` es el endpoint más llamado del frontend. Lo cacheo en Redis con `timeout=None` porque los países raramente cambian. La invalidación es automática vía señal `post_save`/`post_delete` en el modelo `Country`, conectada en `CountriesConfig.ready()`. Si Redis no está disponible, el sistema degrada silenciosamente a consulta directa.

### Webhooks de notificación

`notify_final_decision_task` se ejecuta en estados terminales (`approved`, `rejected`). Envía un POST a `WEBHOOK_URL` con el resultado de la solicitud. Si falla, reintenta con backoff hasta 3 veces. El historial de estados (`ApplicationStatusHistory`) permite auditar qué ocurrió incluso si el webhook no llega.

### Concurrencia

El diseño admite escalar Celery horizontalmente sin inconsistencias:
- `get_or_create()` en `BankProviderData` garantiza idempotencia si dos workers procesan el mismo task.
- Los guards de estado al inicio de cada task previenen ejecución duplicada.
- `transaction.on_commit` evita publicar eventos WebSocket de transacciones que hayan hecho rollback.
- En Kubernetes, los workers son un `Deployment` independiente del API, escalable por separado.

---

## Aportes no explícitos en el enunciado

Incluí lo siguiente sin que estuviera pedido, porque lo consideré parte de una entrega completa:

- **Frontend con DataTable** paginado, filtros múltiples, ordenamiento por columna y debounce en búsqueda — no solo un CRUD básico.
- **Timeline en tiempo real por solicitud**: cada cambio de estado aparece en el detalle en tiempo real vía WebSocket.
- **`ApplicationStatusHistory`**: registro inmutable de cada transición (estado anterior, nuevo, timestamp). Auditoría sin depender de logs del servidor.
- **`CountryValidation` por regla**: cada regla financiera evaluada queda persistida con su resultado. Permite trazabilidad granular del motivo de rechazo.
- **Diagramas en `docs/`** (Mermaid): arquitectura, ERD, flujos de estado MX/CO, pipeline de solicitudes, WebSocket, caché.
- **Manifiestos Kubernetes production-ready**: StatefulSet para Postgres, Job para migrations (evita race condition en multi-replica), probes calibradas, límites de recursos.
- **Entornos dev/prod diferenciados** con scripts de entrypoint separados y compose files distintos.
- **Tests backend** con `pytest` + fixtures globales: auth, CRUD, flujo completo de tasks MX/CO, historial de estados, validaciones de documentos.

---

## Seguridad

- **JWT**: access token de 15 min, refresh de 7 días. El frontend maneja auto-refresh con cola de requests paralelos para evitar refreshes duplicados en requests concurrentes.
- **Aislamiento por usuario**: `get_queryset()` siempre filtra por `request.user`. Un usuario no puede ver ni modificar solicitudes de otro.
- **PII y datos bancarios**: `BankProviderData.raw_response` almacena la respuesta del buró pero no se serializa en ninguna respuesta al cliente. Los campos sensibles son `write_only` o se excluyen del serializer de lectura.
- **CORS**: restringido al origen del frontend (`CORS_ALLOWED_ORIGINS`).
- **Roles**: el signup público no puede autopromovarse a admin. La asignación de rol admin es exclusivamente vía Django Admin o BD directa.
- **WebSocket**: el JWT se valida en el handshake. Ownership de la solicitud verificado antes de permitir la suscripción.

---

## Escalabilidad

El sistema está diseñado para escalar a millones de solicitudes sin cambios de arquitectura.

### Índices recomendados

```sql
-- Filtros frecuentes en el listado
CREATE INDEX idx_apps_user          ON credit_applications(user_id);
CREATE INDEX idx_apps_country       ON credit_applications(country_ref_id);
CREATE INDEX idx_apps_status        ON credit_applications(status_id);
CREATE INDEX idx_apps_requested     ON credit_applications(requested_at DESC);

-- Compuesto para la consulta más común: "mis solicitudes, filtradas y ordenadas"
CREATE INDEX idx_apps_user_status_date
    ON credit_applications(user_id, status_id, requested_at DESC);

-- Índice parcial: solicitudes activas (no terminales) — el subset que más se consulta y actualiza
CREATE INDEX idx_apps_active
    ON credit_applications(status_id)
    WHERE status_id NOT IN (/* ids de estados terminales */);

-- Historial de estados por solicitud
CREATE INDEX idx_history_app
    ON application_status_history(application_id, changed_at DESC);
```

Todos los PKs son UUID para evitar hot-spots en inserciones concurrentes de alto volumen.

### Particionamiento

Cuando `credit_applications` supere los ~50-100M de filas, la partiría por rango de fecha:

```sql
-- Partición mensual: credit_applications_2024_01, _2024_02, ...
PARTITION BY RANGE (requested_at)
```

El listado siempre incluye `requested_at` como filtro de rango, lo que permite partition pruning y evita scans completos de la tabla.

### Consultas críticas

| Consulta | Estrategia |
|---|---|
| Listado paginado con filtros | Índice compuesto + LIMIT/OFFSET; keyset pagination para páginas profundas (> 10k) |
| Detalle de solicitud | PK lookup (UUID) — O(1) |
| Dashboard estadístico por país/estado | Vista materializada actualizada vía Celery beat o en cada cambio de estado |

El serializer de lectura solo incluye los campos que renderiza el frontend. Sin `SELECT *`.

### Archivado

Solicitudes con estado terminal de más de 12 meses se moverían a `credit_applications_archive` con el mismo schema. Las consultas activas no tocan registros históricos. `pg_partman` puede automatizar la rotación de particiones antiguas.

---

## Modelo de datos

El ERD completo está en `docs/database/database.mmd`.

| Tabla | Descripción |
|---|---|
| `users` | Usuario con rol `user/admin`, login por email, UUID PK |
| `country` | País disponible: código, label, regex de documento, activo |
| `country_status` | Estado por país: código, label, orden, `is_initial`, `is_terminal` |
| `status_transition` | Transiciones permitidas entre estados; `triggers_task` define el Celery task |
| `credit_applications` | Solicitud de crédito: FK a usuario, país, estado actual |
| `bank_provider_data` | Datos del buró: OneToOne con solicitud; `raw_response` del proveedor simulado |
| `country_validations` | Resultado por regla financiera evaluada: `rule_name`, `passed`, `message` |
| `application_status_history` | Historial inmutable de transiciones: estado anterior, nuevo, timestamp |

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

---

## Cobertura del enunciado

| # | Requerimiento | Implementado | Notas |
|---|---|---|---|
| 3.1 | Crear solicitudes con todos los campos requeridos | Sí | `POST /api/applications/` — valida doc, persiste, despacha Celery task inmediatamente |
| 3.2 | Reglas por país — MX: CURP + relación ingreso/monto | Sí | `MXCountryValidator`: regex CURP + ratio income × factor ≥ amount |
| 3.2 | Reglas por país — CO: CC + deuda total/ingreso | Sí | `COCountryValidator`: regex CC + debt-to-income ratio |
| 3.3 | Integración con proveedor bancario por país | Sí | Adapters simulados por país en `fetch_bank_data()` con estructura diferenciada por proveedor |
| 3.4 | Flujo de estados extensible por país | Sí | `CountryStatus` + `StatusTransition` en BD; ningún estado hardcodeado en el código |
| 3.5 | Consultar una solicitud por ID | Sí | `GET /api/applications/{id}/` |
| 3.6 | Listar solicitudes con filtros | Sí | Filtros: país, estado, búsqueda por nombre/documento, rango de fechas, ordenamiento, paginación |
| 3.7 | Procesamiento asíncrono que no bloquea la API | Sí | Pipeline Celery 3–4 steps; `201` inmediato en creación |
| 3.7 | Operación en BD → trabajo asíncrono en cola | Sí | `transaction.on_commit` encola Celery task post-commit; WebSocket event post-commit |
| 3.8 | Webhook a sistema externo | Sí | `notify_final_decision_task` → POST a `WEBHOOK_URL` con reintentos en fallo |
| 3.9 | Concurrencia y workers en paralelo | Sí | 2 workers Celery en prod; idempotencia via guards + `get_or_create`; escalable sin cambios de código |
| 3.10 | Actualización en tiempo real en el frontend | Sí | Django Channels + WebSocket; timeline por solicitud actualizado en tiempo real |
| 4.1 | Código modular y extensible | Sí | Strategy pattern por país; service layer; mixins explícitos en ViewSets |
| 4.2 | Seguridad, JWT y autorización básica | Sí | JWT 15min/7días; RBAC user/admin; PII no expuesta en responses; CORS restringido |
| 4.3 | Observabilidad | Sí | `ApplicationStatusHistory` como auditoría; logs Celery; manejo explícito de errores en views |
| 4.4 | Reproducibilidad en < 5 min | Sí | `make dev` crea `.env`, construye e inicia; fixtures se cargan automáticamente |
| 4.5 | Análisis de escalabilidad y grandes volúmenes | Sí | Ver sección "Escalabilidad" — índices, particionamiento, consultas críticas, archivado |
| 4.6 | Colas y encolamiento de trabajos | Sí | Celery + Redis; pipeline descrito en "Decisiones técnicas" |
| 4.7 | Caché con estrategia de invalidación | Sí | Redis `timeout=None` para países; invalidación automática por señales de Django |
| 4.8 | Manifiestos Kubernetes | Sí | Manifests completos en `k8s/`; Job para migrations; sin Helm (no era necesario para el alcance) |
| 5 | Frontend completo | Sí | Crear, listar, detalle, actualizar estado, timeline en tiempo real |
| Extra | Países adicionales | — | MX + CO implementados; arquitectura lista para ES/PT/IT/BR sin cambios en la capa de aplicación |
| Extra | Auditoría detallada | Sí | `ApplicationStatusHistory` + `CountryValidation` por regla financiera evaluada |
