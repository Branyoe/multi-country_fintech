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
