# E2E Tests — Playwright

Tests end-to-end con Playwright sobre Chromium. Cubren los flujos de autenticación (login y signup) contra el backend real.

---

## Prerrequisitos

- Backend corriendo en `http://localhost:8000` con el fixture de usuarios cargado
- El script `gen.sh` en la raíz levanta el backend y carga los fixtures:
  ```bash
  bash backend/gen.sh
  uv run backend/manage.py runserver
  ```
- Credenciales del fixture: `admin@dev.local` / `admin123`

---

## Correr los tests

```bash
# Headless (CI / terminal)
npm run test:e2e

# Modo UI interactivo
npm run test:e2e:ui

# Un archivo específico
npx playwright test e2e/auth/login.spec.ts

# Con reporte HTML
npx playwright test --reporter=html && npx playwright show-report
```

El dev server (`localhost:3000`) se levanta automáticamente si no está corriendo.
Si ya está corriendo, Playwright lo reutiliza (`reuseExistingServer: true`).

---

## Estructura

```
frontend/
├── playwright.config.ts
└── e2e/
    └── auth/
        ├── login.spec.ts
        └── signup.spec.ts
```

---

## Casos cubiertos

### login.spec.ts

| Test | Descripción |
|---|---|
| login exitoso | Email+password válidos → redirect a `/`, "Bienvenido" visible |
| credenciales incorrectas | Password inválida → mensaje "Credenciales inválidas" |
| usuario inexistente | Email desconocido → mensaje de error |
| sin email | Submit vacío → permanece en `/login` (HTML5 required) |
| sin password | Submit vacío → permanece en `/login` (HTML5 required) |
| estado de carga | Botón muestra "Ingresando..." durante el submit |
| link a signup | Click en "Regístrate" → navega a `/signup` |

### signup.spec.ts

| Test | Descripción |
|---|---|
| signup exitoso | Email único → redirect a `/login?registered=1`, banner verde |
| email duplicado | Mismo email dos veces → mensaje de error visible |
| password corta | < 8 caracteres → permanece en `/signup` (HTML5 minLength) |
| sin email | Submit vacío → permanece en `/signup` (HTML5 required) |
| link a login | Click en "Inicia sesión" → navega a `/login` |

---

## Configuración

`playwright.config.ts`:
- **Browser**: Chromium
- **Base URL**: `http://localhost:3000`
- **Paralelismo**: desactivado (`workers: 1`) — los tests de auth comparten estado de BD
- **Artefactos en fallo**: screenshot + video en `playwright-report/`

---

## Convenciones para nuevos tests

- Un archivo por feature: `e2e/<feature>/<feature>.spec.ts`
- Usar siempre `getByLabel()` y `getByRole()` en lugar de selectores CSS
- Emails únicos con `Date.now()` para tests de creación: `test_${Date.now()}@example.com`
- No depender de datos de tests anteriores — cada test debe ser independiente
- Usar `test.beforeEach` para navegación inicial a la página bajo test
