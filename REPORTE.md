# Reporte de avance — Prueba Técnica Bravo

> Análisis honesto del estado actual del proyecto contra los requisitos de la prueba técnica.
> Fecha: 2026-04-10

---

## Resumen ejecutivo

**Avance global estimado: ~70%**

El proyecto tiene una base sólida: arquitectura limpia, máquina de estados robusta, pipeline asíncrono funcional y realtime vía WebSockets. Se avanzó en un faltante crítico implementando webhook outbound para decisión final. Aún faltan piezas explícitamente requeridas en el PDF: triggers de PostgreSQL, manifiestos de Kubernetes y un README completo en la raíz con análisis de escalabilidad.

---

## Requisitos funcionales

| Req | Descripción | Estado | Avance | Observación |
|-----|------------|--------|--------|-------------|
| 3.1 | Crear solicitudes de crédito | ✅ Completo | 100% | POST `/api/applications/`, form en frontend, pipeline async automático |
| 3.2 | Validación de reglas por país | ⚠️ Parcial | 33% | Solo MX y CO implementados. El PDF menciona 6 países; el mínimo requerido es 2, así que pasa el corte pero es lo mínimo indispensable |
| 3.3 | Integración con proveedor bancario | ⚠️ Parcial | 60% | La arquitectura del validator es correcta (strategy pattern), pero `fetch_bank_data()` devuelve datos hardcodeados. No hay llamada HTTP real ni simulación con delay/error realista |
| 3.4 | Flujo de estados por país | ✅ Completo | 100% | `StatusTransition` en DB enforza transiciones válidas, historial inmutable en `ApplicationStatusHistory` |
| 3.5 | Consultar una solicitud | ✅ Completo | 100% | GET `/api/applications/{id}/` con historial de estados anidado |
| 3.6 | Listar solicitudes con filtros | ✅ Completo | 100% | Filtro por país, estado, búsqueda full-text, ordenamiento, paginación DRF |
| 3.7 | Procesamiento asíncrono y eventos | ⚠️ Parcial | 65% | Celery funciona bien. **Falta**: el PDF exige explícitamente "capacidades nativas de base de datos (funciones y mecanismos de disparo en PostgreSQL)". No existe ningún trigger ni función a nivel de BD |
| 3.8 | Webhooks / procesos externos | ✅ Completo | 100% | Webhook outbound implementado en `notify_final_decision_task`: POST configurable (`WEBHOOK_URL`), payload de decisión final, idempotency key y retry estricto vía Celery |
| 3.9 | Concurrencia y procesamiento en paralelo | ⚠️ Parcial | 70% | Celery está configurado con múltiples workers en prod (`replicas: 2`, `concurrency: 2`). El diseño es correcto pero no está documentado en el README como el PDF requiere |
| 3.10 | Actualización en tiempo real (frontend) | ✅ Completo | 95% | WebSocket vía Django Channels, consumer autenticado con JWT, frontend actualiza timeline por aplicación en tiempo real |

---

## Requisitos no funcionales

| Req | Descripción | Estado | Avance | Observación |
|-----|------------|--------|--------|-------------|
| 4.1 | Arquitectura modular y extensible | ✅ Completo | 95% | Capas bien separadas: views → services → tasks → validators → registry. Agregar un país nuevo requiere solo un archivo nuevo y una entrada en el registry |
| 4.2 | Seguridad de APIs | ⚠️ Parcial | 65% | JWT implementado correctamente (access 15min / refresh 7 días), aislamiento por usuario en todos los endpoints. **Problema**: `document_number` se almacena en texto plano en la BD (PII). El PDF menciona explícitamente "manejo seguro de PII" |
| 4.3 | Observabilidad | ⚠️ Parcial | 40% | Hay logs con `extra` estructurado en puntos clave (transiciones de estado, decisión final, errores WebSocket). Sin embargo: sin configuración de `LOGGING` en `settings.py`, sin handlers a archivo, sin nivel de log configurable por env, sin formato JSON. Los logs de Celery tasks no están estructurados |
| 4.4 | Reproducibilidad (README + setup) | ⚠️ Parcial | 55% | Docker Compose funcional, Makefile con targets claros. **Problemas**: el README está en `backend/README.md`, no en la raíz del repo. El PDF pide instrucciones para correr en menos de 5 minutos desde la raíz |
| 4.5 | Escalabilidad / grandes volúmenes | ❌ Ausente | 5% | El PDF exige explícitamente en el README: análisis de índices recomendados, estrategias de particionamiento, consultas críticas y cuellos de botella, estrategias de archivado. Nada de esto existe. Los modelos tienen UUIDs como PK (no óptimo para tablas con millones de filas por fragmentación de índice) |
| 4.6 | Colas y encolamiento | ✅ Completo | 90% | Celery + Redis broker, 3 tasks con retry, idempotencia, serialización JSON. Solo falta documentación en README |
| 4.7 | Caching | ✅ Completo | 90% | Redis cache para países con invalidación automática via signals. Documentado en el código pero no en README |
| 4.8 | Despliegue en Kubernetes | ❌ Ausente | 0% | Solo Docker Compose. El PDF requiere manifiestos YAML de K8s para todos los componentes principales (API, frontend, workers, DB, Redis). Sin esto, el entregable de despliegue no cumple |

---

## Entregables requeridos (Sección 6)

| Entregable | Estado | Avance | Observación |
|------------|--------|--------|-------------|
| Repositorio completo (backend + frontend + async) | ✅ Completo | 95% | Todo en un monorepo bien estructurado |
| README con instrucciones de instalación | ⚠️ Parcial | 50% | Existe en `backend/README.md`. Falta: raíz del repo, análisis de escalabilidad, descripción de webhooks, estrategia de concurrencia, caching, colas |
| README con supuestos y decisiones técnicas | ⚠️ Parcial | 60% | Hay decisiones documentadas pero incompletas para lo que pide el PDF |
| Archivos de configuración para Kubernetes | ❌ Ausente | 0% | No existen |
| Makefile con comandos clave | ✅ Completo | 100% | `make dev`, `make prod`, `make dev-down`, `make dev-clean`, `make logs-dev`, etc. |

---

## Frontend (Sección 5)

| Funcionalidad | Estado | Avance |
|---------------|--------|--------|
| Crear solicitudes | ✅ | 100% — Modal con form dinámico, hints por país, validación Zod + errores de API inline |
| Ver lista de solicitudes | ✅ | 100% — DataTable con filtros, ordenamiento y paginación manual |
| Ver detalles de una solicitud | ✅ | 90% — Panel de detalle presente |
| Actualizar estado | ✅ | 90% — PATCH con selección de transiciones válidas |
| Visualizar cambios en tiempo real | ✅ | 95% — Timeline de transiciones vía WebSocket por aplicación |

---

## Lo que falta: descripción concreta

### 1. Webhooks (requisito 3.8) — COMPLETADO
Se implementó webhook outbound en el pipeline asíncrono para estados terminales (`approved`/`rejected`).

**Implementación realizada**:
- `backend/applications/tasks.py`: `notify_final_decision_task` ahora envía POST a `WEBHOOK_URL`.
- `backend/config/settings.py`: nuevas variables `WEBHOOK_URL`, `WEBHOOK_TIMEOUT_SECONDS`, `WEBHOOK_RETRY_COUNTDOWN_SECONDS`.
- `backend/.env.example`: documentación de variables de webhook.
- `backend/applications/tests/test_applications.py`: pruebas para envío exitoso, skip sin URL, noop en estado no terminal, retry en error y retries agotados.

**Validación**:
- `uv run pytest applications/tests/test_applications.py -k "notify_final_decision" -q` → 5 passed.

### 2. Triggers de PostgreSQL (requisito 3.7) — BLOQUEANTE
El PDF dice literalmente: *"Utilizar capacidades nativas de base de datos (funciones y mecanismos de disparo en PostgreSQL)"*. La implementación actual hace todo a nivel de aplicación (Django). Necesita al menos una función PL/pgSQL con un trigger (ej: auditoría en `application_status_history` o notificación via `pg_notify`).

### 3. Kubernetes (requisito 4.8) — BLOQUEANTE
Manifiestos YAML para: `Deployment` de API, `Deployment` de workers Celery, `Deployment` de frontend, `Service` para cada componente, `Ingress`, `ConfigMap`/`Secret` para variables de entorno. Al menos 4-5 archivos. ~3-4 horas de trabajo.

### 4. README en raíz con análisis completo (requisito 4.4, 4.5) — IMPORTANTE
El README actual está en `backend/` y no cubre:
- Análisis de índices recomendados para la tabla `credit_applications`
- Estrategia de particionamiento (ej: por `country_ref` o por rango de fecha)
- Consultas críticas y cómo evitar N+1 o full scans
- Estrategia de archivado para solicitudes antiguas
- Descripción de la estrategia de caching y su invalidación
- Descripción del flujo de colas (qué se encola, cómo se consume)
- Descripción de la estrategia de concurrencia (cómo se escalan los workers)

### 5. PII en texto plano (requisito 4.2) — IMPORTANTE
`document_number` se guarda sin cifrar. La prueba evalúa "manejo seguro de PII". Solución mínima: cifrado simétrico con `cryptography` (Fernet) en el modelo, o al menos una nota en el README sobre la estrategia de PII con `django-fernet-fields`.

### 6. Configuración de logging estructurado (requisito 4.3) — MENOR
Sin un bloque `LOGGING` en `settings.py`, los logs no son configurables ni persistibles. Debería existir al menos un handler para `applications` y `countries` con formato JSON.

### 7. Proveedor bancario simulado (requisito 3.3) — MENOR
`fetch_bank_data()` devuelve un `BankData` hardcodeado en ambos países. El evaluador esperará ver al menos un delay real (hay un `asyncio.sleep` en el task, pero la "llamada" al banco es instantánea y determinista). Añadir variabilidad (errores ocasionales, respuestas distintas por número de documento) haría la demo más convincente.

---

## Estimación de esfuerzo para completar

| Ítem | Esfuerzo estimado | Impacto en nota |
|------|------------------|-----------------|
| Trigger PostgreSQL (auditoría o pg_notify) | ~3h | Alto |
| Manifiestos Kubernetes | ~4h | Alto |
| README raíz con análisis de escalabilidad | ~3h | Alto |
| Logging estructurado en settings.py | ~1h | Medio |
| PII: cifrado de document_number o documentación de estrategia | ~2h | Medio |
| Simulación bancaria con errores aleatorios | ~1h | Bajo |
| **Total** | **~14h** | |

---

## Puntos fuertes del proyecto

Estos aspectos están bien ejecutados y destacarán positivamente ante el evaluador:

- **Arquitectura del validator**: el patrón strategy con `BaseCountryValidator` + registry es extensible de verdad. Agregar un país es agregar un archivo.
- **Máquina de estados en BD**: `StatusTransition` enforza transiciones a nivel de datos, no solo a nivel de código. Difícil de romper.
- **WebSockets bien integrados**: la autenticación JWT en el handshake WS, el uso de `transaction.on_commit()` para publicar eventos y el consumer por aplicación están bien pensados.
- **Idempotencia en Celery**: el guard al inicio de cada task (`if app.status_code != expected: return`) evita efectos secundarios en retries.
- **Aislamiento multi-tenant**: `get_queryset()` siempre filtra por `request.user`. No hay riesgo de data leakage entre usuarios.
- **Cache con invalidación automática**: Django signals invalidan el cache de países en cada cambio, sin TTL artificial.
