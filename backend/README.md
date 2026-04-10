# Backend — Django REST API

API REST para evaluación de solicitudes de crédito con estrategia por país.

## Stack

| | |
|---|---|
| **Runtime** | Python 3.13 |
| **Framework** | Django 6 + Django REST Framework 3.17 |
| **Auth** | SimpleJWT (Bearer tokens) |
| **CORS** | django-cors-headers |
| **Config** | python-decouple (`.env`) |
| **Package manager** | [uv](https://docs.astral.sh/uv/) |
| **Tests** | pytest + pytest-django |
| **DB (dev)** | SQLite |
| **DB (prod)** | PostgreSQL |

---

## Requisitos

- Python 3.13+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

---

## Arranque rápido

Desde la **raíz del repositorio**:

```bash
bash backend/gen.sh
```

El script hace en orden:

1. Crea `backend/.env` desde `.env.example` si no existe
2. Instala dependencias (`uv sync`)
3. Aplica migraciones
4. Carga fixtures (`backend/fixtures/*.json`)
5. Crea el superuser de Django Admin desde el fixture

Una vez completado verás:

```
  Server    uv run backend/manage.py runserver
  Admin     http://localhost:8000/admin
            admin@dev.local / admin123
  Tests     cd backend && uv run pytest users/tests/ -v
```

---

## Variables de entorno

El archivo `backend/.env` no se versiona. Plantilla en `backend/.env.example`:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

## Logging en base de datos

El proyecto usa `django-db-logger` para almacenar errores HTTP 500 de `django.request` en la base de datos.

Notas:
- Se registra solo nivel `ERROR` para controlar volumen.
- Para agregar logs manuales, usa un logger con handler `db_log` (ver `LOGGING` en `config/settings.py`).
- En entornos con alto volumen, considera una politica de retencion o un job de limpieza periodica.

---

## Estructura

```
backend/
├── config/
│   ├── settings.py       # Configuración global
│   ├── urls.py           # Rutas raíz
│   ├── wsgi.py
│   └── asgi.py
├── users/                # App de autenticación
│   ├── models.py         # Custom User model (UUID + email login)
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   └── tests/
│       └── test_auth.py
├── fixtures/
│   └── users.json        # Superuser de dev (admin@dev.local)
├── manage.py
├── pyproject.toml
└── pytest.ini
```

---

## Endpoints de autenticación

Base URL: `/api/auth/`

### `POST /api/auth/signup/`

Registro de nuevo usuario. No requiere autenticación.

**Body:**
```json
{
  "email": "user@example.com",
  "password": "minimo8chars",
  "role": "user"
}
```

**Respuesta `201`:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "role": "user",
  "created_at": "2026-04-08T00:00:00Z"
}
```

---

### `POST /api/auth/token/`

Login. Devuelve par de tokens JWT.

**Body:**
```json
{
  "email": "user@example.com",
  "password": "minimo8chars"
}
```

**Respuesta `200`:**
```json
{
  "access": "<token>",
  "refresh": "<token>"
}
```

| Token | Duración |
|---|---|
| `access` | 15 minutos |
| `refresh` | 7 días |

---

### `POST /api/auth/token/refresh/`

Renueva el access token usando el refresh token.

**Body:**
```json
{
  "refresh": "<refresh_token>"
}
```

**Respuesta `200`:**
```json
{
  "access": "<nuevo_access_token>"
}
```

---

## Autenticación en endpoints protegidos

Todos los endpoints están protegidos por defecto. Incluir el header:

```
Authorization: Bearer <access_token>
```

Para hacer un endpoint público agregar explícitamente en la view:

```python
permission_classes = (AllowAny,)
```

---

## Modelo User

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | PK, auto-generado |
| `email` | string | Único, usado como username |
| `password` | string | Hashed (PBKDF2) |
| `role` | string | `user` \| `admin` |
| `is_active` | bool | Default `True` |
| `is_staff` | bool | Acceso al admin panel |
| `last_login` | timestamp | |
| `created_at` | timestamp | Auto |

---

## Comandos frecuentes

```bash
# Dev server
uv run backend/manage.py runserver

# Migraciones
uv run backend/manage.py makemigrations <app>
uv run backend/manage.py migrate

# Crear superuser manualmente
uv run backend/manage.py createsuperuser

# Django shell
uv run backend/manage.py shell

# Instalar dependencia
uv --project backend add <paquete>

# Generar fixture desde la DB actual
uv run python manage.py dumpdata users.User --indent 2 > fixtures/users.json
```

---

## Tests

```bash
# Todos los tests
cd backend && uv run pytest users/tests/ -v

# Por clase
uv run pytest users/tests/test_auth.py::TestSignup -v

# Test específico
uv run pytest users/tests/test_auth.py::TestLogin::test_login_success -v
```

Los tests operan contra una DB en memoria (transacciones por test, sin persistencia).

Cobertura actual:

| Suite | Tests |
|---|---|
| `TestSignup` | success, email duplicado, sin email, sin password, password corta, email inválido |
| `TestLogin` | success, password incorrecta, usuario inexistente, campos faltantes |
| `TestTokenRefresh` | success, token inválido, sin token |

---

## Django Admin

```
http://localhost:8000/admin
admin@dev.local / admin123
```

---

## Agregar un nuevo estado a un país

1. **Persistir los datos del nuevo estado**

   **Opción A — fixtures** _(dev / entornos con `loaddata`)_
   - Agregar el `CountryStatus` con un PK nuevo, `country` = PK del país, `code`, `label`, `order` correcto (ajustar el `order` de los estados siguientes si es necesario).
   - Agregar las `StatusTransition` que conectan el nuevo estado (from/to) con los estados adyacentes. Eliminar o redirigir las transiciones antiguas que el nuevo estado reemplaza.

   **Opción B — Django Admin** _(producción)_
   - Desplegar primero el código de los pasos 3 y 4 (workflow + task), de modo que el nuevo `code` ya esté manejado antes de que el estado exista en la base de datos.
   - En `/admin/countries/countrystatus/` crear el `CountryStatus` con el `code`, `label` y `order` deseados.
   - En `/admin/countries/statustransition/` crear las `StatusTransition` necesarias (from/to).
   - Actualizar el fixture `statuses.json` para mantenerlo en sync con la DB de producción.

2. **`backend/conftest.py`** — espejo de los fixtures para tests
   - Agregar `CountryStatus.objects.create(...)` con los mismos valores.
   - Actualizar el `bulk_create` de `StatusTransition` para que el flujo coincida con el de producción.

3. **`applications/workflows/<país>.py`**
   - Si el nuevo estado dispara un Celery task, importarlo en `on_enter()` y agregar el caso `elif state_code == '<code>': <task>.delay(...)`.
   - Si el nuevo estado es el primer estado de procesamiento (bootstrap), sobrescribir `get_bootstrap_state()` para devolver su `code`.

4. **`applications/tasks.py`** _(solo si el estado dispara un task nuevo)_
   - Agregar `@shared_task(bind=True, max_retries=3, name='<nombre>')`.
   - Incluir el guard de idempotencia: `if app.status_code != '<code>': return`.
   - Transicionar al estado siguiente vía `CreditApplicationService.update_status(...)`.

5. **Tests** — actualizar `applications/tests/test_applications.py`
   - Corregir aserciones de status en `TestCreate` si cambia el estado de bootstrap.
   - Agregar o ajustar helpers de avance de estado en `TestTasks._advance_*` si los task tests necesitan pasar por el nuevo estado antes de ejecutar una tarea.
   - Ajustar `TestStatusHistory` si cambia el conteo de entradas o los valores `from_status`/`to_status`.
