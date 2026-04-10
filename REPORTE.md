# Reporte de avance — Prueba Técnica Bravo

> Análisis actualizado del estado real del código frente a Prueba Técnica.pdf.
> Fecha: 2026-04-10

---

## Resumen ejecutivo

**Avance global estimado: ~68%**

El proyecto está bien encaminado en arquitectura, flujo de estados, asincronía con Celery, webhook outbound y actualización realtime por WebSocket. Los principales gaps para cumplimiento del documento siguen siendo:

1. Falta de mecanismos nativos de PostgreSQL (funciones + triggers) conectados a trabajo asíncrono (bloqueante de 3.7).
2. Ausencia total de manifiestos Kubernetes (bloqueante de 4.8 y sección 6).
3. Falta de análisis de escalabilidad solicitado explícitamente en README (4.5).
4. Seguridad de PII incompleta (`document_number` en texto plano).
5. Frontend no permite actualizar estado de solicitud (requerido en sección 5).

---

## Evidencia revisada

- Requisitos PDF: Prueba Técnica.pdf (secciones 3, 4, 5 y 6).
- Backend: aplicaciones, validadores, workflows, consumers, settings, compose, entrypoints y tests.
- Frontend: features/applications (tabla, crear, detalle, socket hook, API).
- Infra/docs: README raíz, backend/README.md, Makefile, docker-compose dev/prod.

---

## Requisitos funcionales (Sección 3)

| Req | Descripción | Estado | Avance | Evidencia / nota |
|-----|-------------|--------|--------|------------------|
| 3.1 | Crear solicitudes de crédito | ✅ Completo | 95% | POST `/api/applications/`, formulario funcional, historial inicial y arranque de pipeline en backend |
| 3.2 | Validación de reglas por país | ⚠️ Parcial | 55% | Solo MX/CO implementados; cumple objetivo mínimo de “al menos dos países”, pero no cobertura multipaís total |
| 3.3 | Integración con proveedor bancario por país | ⚠️ Parcial | 65% | Estrategia por país correcta (`MXCountryValidator`, `COCountryValidator`), pero `fetch_bank_data()` es mock fijo sin integración HTTP real |
| 3.4 | Estados de solicitud por país | ✅ Completo | 95% | Catálogo de estados/transiciones en BD (`CountryStatus`, `StatusTransition`) + historial inmutable |
| 3.5 | Consultar solicitud individual | ✅ Completo | 100% | GET `/api/applications/{id}/` retorna detalle + historial |
| 3.6 | Listar solicitudes filtradas | ✅ Completo | 100% | Filtros por país/estado, búsqueda (`id`, solicitante, creador, documento), ordenamiento y paginación |
| 3.7 | Procesamiento asíncrono y eventos | ⚠️ Parcial | 60% | Celery y eventos app-level sí; **faltan** funciones/trigger nativos PostgreSQL y flujo DB→trabajo asíncrono |
| 3.8 | Webhooks / procesos externos | ✅ Completo | 100% | `notify_final_decision_task` con POST configurable, idempotency-key, timeout y retry |
| 3.9 | Concurrencia y procesamiento paralelo | ⚠️ Parcial | 80% | Prod con workers múltiples (`replicas: 2`, `concurrency=2`) + guards de idempotencia en tasks |
| 3.10 | Actualización realtime en frontend | ✅ Completo | 95% | Channels + Consumer autenticado + actualización incremental de línea de tiempo |

---

## Requisitos no funcionales (Sección 4)

| Req | Descripción | Estado | Avance | Evidencia / nota |
|-----|-------------|--------|--------|------------------|
| 4.1 | Arquitectura modular/extensible | ✅ Completo | 95% | Separación por capas y strategy/registry por país y workflow |
| 4.2 | Seguridad de APIs y PII | ⚠️ Parcial | 65% | JWT + autorización por usuario bien; PII (`document_number`) sin cifrado y token WS en query string |
| 4.3 | Observabilidad | ⚠️ Parcial | 70% | Hay `LOGGING` en `settings.py` + `django-db-logger` + logs con `extra`; falta estandarización JSON/centralización/alerting |
| 4.4 | Reproducibilidad | ⚠️ Parcial | 80% | README raíz + Makefile + Docker Compose; aún hay drift documental respecto al código real |
| 4.5 | Escalabilidad (análisis en README) | ❌ Ausente | 15% | No existe análisis formal de índices, particionamiento, cuellos de botella y archivado |
| 4.6 | Colas y encolamiento | ✅ Completo | 90% | Celery/Redis, producción y consumo de tareas, retries e idempotencia |
| 4.7 | Caching | ✅ Completo | 90% | Cache Redis de países con invalidación automática por señales |
| 4.8 | Despliegue Kubernetes | ❌ Ausente | 0% | No hay manifiestos YAML ni chart/kustomize |

---

## Entregables (Sección 6)

| Entregable | Estado | Avance | Observación |
|------------|--------|--------|-------------|
| Repositorio con backend/frontend/async/colas/cache/despliegue | ⚠️ Parcial | 85% | Backend/frontend/async/colas/cache sí; despliegue K8s no |
| README completo (setup, supuestos, seguridad, escalabilidad, concurrencia, colas, cache, webhooks) | ⚠️ Parcial | 60% | Hay README raíz, pero incompleto para escalabilidad y con inconsistencias |
| Configuración Kubernetes | ❌ Ausente | 0% | No existe carpeta/manifiestos |
| Makefile/Justfile | ✅ Completo | 100% | Targets dev/prod/logs/clean/full-restart presentes |

---

## Frontend requerido (Sección 5)

| Funcionalidad | Estado | Avance | Observación |
|---------------|--------|--------|-------------|
| Crear solicitudes | ✅ | 100% | Modal funcional con validación y manejo de errores |
| Ver lista de solicitudes | ✅ | 100% | DataTable con filtros, ordenamiento y paginación server-side |
| Ver detalle de solicitud | ✅ | 95% | Vista de detalle estable y copy mejorado |
| Actualizar estado | ❌ | 20% | No existe interacción de UI que llame PATCH en frontend |
| Realtime en UI | ✅ | 95% | Línea de tiempo en vivo por WebSocket |

---

## Hallazgos clave (actualización respecto al reporte previo)

1. Sí existe `LOGGING` en backend (antes se reportaba ausente).
2. Sí existe README en la raíz (antes se reportaba ausente), pero no cubre 4.5 y tiene drift con el código:
	- describe Gunicorn en prod, mientras entrypoint usa Daphne.
	- menciona `/api/applications/countries/`, pero el endpoint real es `/api/countries/`.
3. El frontend no cumple aún el punto “actualizar estado” del requerimiento 5.
4. Webhook outbound está correctamente implementado y probado.

---

## Tareas faltantes priorizadas (cumplimiento del documento)

### P0 — Bloqueantes de cumplimiento explícito

1. **Implementar trigger + función PostgreSQL + puente a trabajo asíncrono (Req 3.7)**
	- Idea mínima: crear `application_event_outbox` y una función `fn_enqueue_status_event()`.
	- Trigger `AFTER INSERT` en `application_status_history` inserta evento en outbox.
	- Worker Celery consume outbox y despacha lógica asíncrona (webhook, auditoría, notificaciones).
	- Ejemplo de salida esperada: operación en BD genera fila en outbox sin depender de lógica Python en request.

2. **Agregar manifiestos Kubernetes (Req 4.8 + sección 6)**
	- Mínimo viable:
	  - `k8s/api-deployment.yaml`, `k8s/api-service.yaml`
	  - `k8s/frontend-deployment.yaml`, `k8s/frontend-service.yaml`
	  - `k8s/celery-deployment.yaml`
	  - `k8s/postgres-statefulset.yaml`, `k8s/redis-deployment.yaml`
	  - `k8s/configmap.yaml`, `k8s/secret.example.yaml`, `k8s/ingress.yaml`
	- Incluir variables de entorno y probes básicas.

3. **Completar README con análisis de escalabilidad (Req 4.5 + sección 6)**
	- Incluir explícitamente:
	  - índices recomendados,
	  - estrategia de particionamiento,
	  - consultas críticas + mitigación de cuellos,
	  - archivado/retención.

### P1 — Importantes para nota técnica y riesgo

4. **Completar UI para actualizar estado (Req 5)**
	- Añadir en detalle un selector de estado permitido + botón “Actualizar”.
	- Crear método frontend `updateApplicationStatus(id, status)` que haga PATCH.
	- Refrescar cache local y línea de tiempo tras éxito.

5. **Endurecer manejo de PII (Req 4.2)**
	- Opción A: cifrado de `document_number` (campo cifrado + clave por entorno).
	- Opción B (mínima): mascar en respuestas/listados y mantener valor claro solo en flujos estrictamente necesarios.
	- Documentar decisión y trade-offs en README.

6. **Corregir drift documental README ↔ código**
	- Runtime prod real (Daphne), endpoint de países correcto, flujo actual de realtime.

### P2 — Mejoras de robustez y demo

7. **Simulación de proveedor bancario más realista (Req 3.3)**
	- Respuesta variable por documento, fallas intermitentes controladas y latencia distribuida.
	- Registrar razón de rechazo/aprobación ligada a señal del “proveedor”.

8. **Observabilidad estructurada de punta a punta (Req 4.3)**
	- Formato JSON consistente, correlation-id por solicitud, logging homogéneo para tasks y webhook.

---

## Priorización alternativa por riesgo (si cambia la estrategia)

| Prioridad por riesgo | Riesgo | Acción recomendada |
|----------------------|--------|--------------------|
| R1 | Incumplimiento directo del enunciado (descalificación técnica) | Triggers PostgreSQL + K8s + README escalabilidad |
| R2 | Riesgo de seguridad / compliance | Protección de PII y revisión de exposición de datos |
| R3 | Riesgo funcional de demo | UI de actualización de estado + pruebas E2E |
| R4 | Riesgo operativo | Observabilidad y simulación de proveedor más robusta |

---

## Estimación de esfuerzo restante

| Tarea | Esfuerzo estimado | Impacto |
|------|--------------------|---------|
| Trigger + outbox + consumidor async | 4–6h | Alto |
| Manifiestos Kubernetes base | 4–6h | Alto |
| README de escalabilidad completo | 2–3h | Alto |
| UI actualización de estado + test | 2–3h | Alto |
| PII (cifrado/masking + doc) | 2–4h | Medio-Alto |
| Observabilidad estructurada | 1–2h | Medio |
| Simulación proveedor realista | 1–2h | Medio |
| **Total aproximado** | **16–26h** | |

---

## Simulación de proveedores bancarios — patrón Adapter

### Problema
`fetch_bank_data` en `MXCountryValidator` y `COCountryValidator` construía el dataclass `BankData` con datos hardcodeados directamente en el código. No había distinción entre el formato bruto que devuelve cada proveedor bancario real y la representación interna del sistema.

### Solución
Se introdujo el **patrón Adapter** con tres capas:

1. **Perfiles JSON por proveedor** (`countries/validators/providers/`): cada archivo simula la respuesta real del proveedor con su nomenclatura propia. `cnbv_mx.json` usa campos en español (`score_crediticio`, `deuda_total_mxn`, `estatus_cuenta`) al estilo CNBV; `datacredito_co.json` usa camelCase (`totalObligaciones`, `estadoCuenta`) al estilo DataCrédito. Cada archivo tiene cuatro perfiles con distintos niveles de deuda y score para simular variedad.

2. **Adaptadores por proveedor** (`countries/validators/adapters/`): `CNBVMXAdapter` y `DataCreditoCOAdapter` implementan `BankProviderAdapter.parse(raw) -> BankData`, traduciendo los campos del proveedor al contrato interno. El validator no sabe nada del formato del proveedor.

3. **Selección determinística de perfil**: `fetch_bank_data` selecciona el perfil usando `hashlib.md5(document)` en lugar de `hash()` (que varía por sesión en Python), garantizando que el mismo documento siempre obtiene el mismo perfil simulado.

### Por qué así
- **Separación de responsabilidades**: el validator sabe *qué* consultar, el adaptador sabe *cómo* interpretar la respuesta. Añadir un proveedor nuevo es crear un JSON + un adapter sin tocar la lógica de validación.
- **Realismo**: `raw_response` en `BankProviderData` queda guardado en el formato original del proveedor, no en una estructura genérica inventada.
- **Determinismo en tests**: `hashlib.md5` produce el mismo índice de perfil independientemente de `PYTHONHASHSEED`, por lo que los tests son reproducibles.

---

## Puntos fuertes actuales

- Arquitectura extensible por país con strategy + registry + workflow.
- Máquina de estados en BD con transiciones controladas y audit trail.
- Realtime por WebSocket autenticado y actualización incremental de la vista.
- Pipeline asíncrono con tareas idempotentes y reintentos.
- Cache de catálogos con invalidación automática.
- Cobertura de tests backend relevante para flujo principal y webhook.
