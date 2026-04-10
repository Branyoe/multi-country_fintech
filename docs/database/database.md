# Modelo de datos — Fintech Multipaís (Bravo)

## ERD

```mermaid
erDiagram

    USERS {
        uuid id PK
        string email UK
        string hashed_password
        string role
        boolean is_active
        boolean is_staff
        timestamp last_login
        timestamp created_at
    }

    COUNTRY {
        bigint id PK
        string code UK
        string label
        string document_type
        string document_hint
        string document_example
        string document_regex
        boolean is_active
    }

    COUNTRY_STATUS {
        bigint id PK
        bigint country_id FK
        string code
        string label
        boolean is_initial
        boolean is_terminal
        int order
    }

    STATUS_TRANSITION {
        bigint id PK
        bigint from_status_id FK
        bigint to_status_id FK
    }

    CREDIT_APPLICATIONS {
        uuid id PK
        uuid user_id FK
        bigint country_ref_id FK
        string full_name
        string document_type
        string document_number
        decimal amount_requested
        decimal monthly_income
        bigint status_id FK
        timestamp requested_at
        timestamp updated_at
    }

    COUNTRY_VALIDATIONS {
        uuid id PK
        uuid application_id FK
        string rule_name
        boolean passed
        string detail
        timestamp evaluated_at
    }

    BANK_PROVIDER_DATA {
        uuid id PK
        uuid application_id FK
        string provider_name
        decimal total_debt
        int credit_score
        string account_status
        jsonb raw_response
        timestamp fetched_at
    }

    APPLICATION_STATUS_HISTORY {
        uuid id PK
        uuid application_id FK
        string from_status
        string to_status
        string changed_by
        jsonb metadata
        timestamp changed_at
    }

    USERS ||--o{ CREDIT_APPLICATIONS : "crea"
    COUNTRY ||--o{ COUNTRY_STATUS : "define estados"
    COUNTRY_STATUS ||--o{ STATUS_TRANSITION : "from_status"
    COUNTRY_STATUS ||--o{ STATUS_TRANSITION : "to_status"
    COUNTRY ||--o{ CREDIT_APPLICATIONS : "country_ref"
    COUNTRY_STATUS ||--o{ CREDIT_APPLICATIONS : "status actual"
    CREDIT_APPLICATIONS ||--o{ COUNTRY_VALIDATIONS : "tiene"
    CREDIT_APPLICATIONS ||--|| BANK_PROVIDER_DATA : "tiene"
    CREDIT_APPLICATIONS ||--o{ APPLICATION_STATUS_HISTORY : "registra"
```

---

## Descripción de tablas

### `users`
Usuarios del sistema autenticado. El campo `role` soporta autorización básica (`user`, `admin`) y se complementa con flags de Django (`is_active`, `is_staff`).

### `country`
Catálogo de países habilitados para originación de crédito. Contiene reglas de documento por país (`document_type`, `document_regex`, `document_hint`) y estado de activación.

### `country_status`
Estados de solicitud configurados por país. Cada estado tiene código, etiqueta, orden de presentación y flags de estado inicial/terminal.

### `status_transition`
Transiciones permitidas entre estados (`from_status` -> `to_status`) dentro del mismo país. Es la fuente de verdad de la máquina de estados DB-driven.

### `credit_applications`
Tabla central del sistema. La solicitud referencia país mediante `country_ref_id` y estado actual mediante `status_id`.

**Estados vigentes por flujo (ejemplo):**
`created|pending` → `fetching_bank_data` → `validate_country_rules` → `approved|rejected` (con salida técnica a `technical_error`).

### `country_validations`
Registro de cada regla evaluada por país. Una aplicación puede tener múltiples filas aquí, una por regla (ej: `curp_format`, `income_ratio`, `document_exists`). Permite auditar exactamente qué regla falló.

### `bank_provider_data`
Respuesta del proveedor bancario mock por país. El campo `raw_response` en `jsonb` almacena la respuesta completa sin normalizar, ya que cada proveedor devuelve campos distintos (CO retorna `total_debt`, BR retorna `credit_score`, etc.).

### `application_status_history`
Historial completo de transiciones de estado. Cada cambio genera una fila nueva con `metadata` en JSON para trazabilidad técnica (task, evento, razón de fallo, etc.).

---

## Índices recomendados

```sql
-- Consultas frecuentes por país y estado FK
CREATE INDEX idx_applications_country_status ON credit_applications (country_ref_id, status_id);

-- Listados paginados por fecha
CREATE INDEX idx_applications_requested_at ON credit_applications (requested_at DESC);

-- Lookup por documento por país
CREATE INDEX idx_applications_document ON credit_applications (country_ref_id, document_number);

-- Historial de una aplicación
CREATE INDEX idx_status_history_application ON application_status_history (application_id, changed_at DESC);

-- Estado actual por país (catálogo)
CREATE INDEX idx_country_status_country_order ON country_status (country_id, "order");
```

---

## Notas de evolución

El modelo evolucionó desde estados y país como strings en `credit_applications` a un diseño normalizado:

1. `country` migró a `country_ref` (FK a `country`).
2. `status` migró a FK a `country_status`.
3. Se introdujo `status_transition` como definición DB-driven de transiciones permitidas.
4. `application_status_history` añadió `metadata` y aumentó longitud de `from_status`/`to_status` para códigos largos de estado.