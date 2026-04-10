import { test, expect } from '@playwright/test'

const VALID_EMAIL = 'admin@dev.local'
const VALID_PASSWORD = 'admin123'

async function login(page: import('@playwright/test').Page) {
  await page.goto('/login')
  await page.getByLabel('Email').fill(VALID_EMAIL)
  await page.getByLabel('Contraseña').fill(VALID_PASSWORD)
  await page.getByRole('button', { name: /ingresar/i }).click()
  await expect(page).toHaveURL('/')
}

test.beforeEach(async ({ page }) => {
  await login(page)
})

test('la página principal muestra el heading correcto', async ({ page }) => {
  await expect(page.getByRole('heading', { name: /solicitudes de crédito/i })).toBeVisible()
})

test('la tabla de solicitudes muestra columnas correctas', async ({ page }) => {
  await expect(page.getByRole('columnheader', { name: /solicitante/i })).toBeVisible()
  await expect(page.getByRole('columnheader', { name: /creada por/i })).toBeVisible()
  await expect(page.getByRole('columnheader', { name: /país/i })).toBeVisible()
  await expect(page.getByRole('columnheader', { name: /estado/i })).toBeVisible()
  await expect(page.getByRole('columnheader', { name: /fecha/i })).toBeVisible()
})

test('botón nueva solicitud abre el dialog', async ({ page }) => {
  await page.getByRole('button', { name: /nueva solicitud/i }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
})

test('dialog de nueva solicitud se cierra con Escape', async ({ page }) => {
  await page.getByRole('button', { name: /nueva solicitud/i }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).not.toBeVisible()
})

test('crear solicitud completa aparece en la tabla con email', async ({ page }) => {
  await page.getByRole('button', { name: /nueva solicitud/i }).click()
  await expect(page.getByRole('dialog')).toBeVisible()

  // Fill the form
  await page.getByLabel(/nombre completo/i).fill('Juan Pérez Test')
  // Select country MX using the combobox trigger
  const countrySelect = page.getByRole('combobox').first()
  await countrySelect.click()
  // Wait for dropdown and select México (with accent)
  await page.getByRole('option').filter({ hasText: /m.xico/i }).first().click()
  // Fill document
  await page.getByLabel(/documento/i).fill('PERJ800101HDFRZN09')
  // Fill amount
  await page.getByLabel(/monto/i).fill('50000')
  // Fill income
  await page.getByLabel(/ingreso/i).fill('20000')

  await page.getByRole('button', { name: /crear solicitud/i }).click()

  // Wait for dialog to close
  await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 5000 })

  // The new row should appear with the admin email (use first() since multiple rows may exist)
  await expect(page.getByRole('cell', { name: VALID_EMAIL }).first()).toBeVisible({ timeout: 5000 })
})

test('usuario puede cerrar sesión con confirmación', async ({ page }) => {
  await page.getByRole('button', { name: /cerrar sesión/i }).click()
  // Confirmation dialog must appear
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByRole('heading', { name: /¿cerrar sesión\?/i })).toBeVisible()
  // Confirm logout
  await page.getByRole('button', { name: /cerrar sesión/i }).last().click()
  await expect(page).toHaveURL('/login')
})
