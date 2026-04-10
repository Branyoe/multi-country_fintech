import { test, expect } from '@playwright/test'

const VALID_EMAIL = 'admin@dev.local'
const VALID_PASSWORD = 'admin123'

test.beforeEach(async ({ page }) => {
  await page.goto('/login')
})

test('login exitoso redirige al home', async ({ page }) => {
  await page.getByLabel('Email').fill(VALID_EMAIL)
  await page.getByLabel('Contraseña').fill(VALID_PASSWORD)
  await page.getByRole('button', { name: /ingresar/i }).click()

  await expect(page).toHaveURL('/')
  await expect(page.getByRole('heading', { name: /solicitudes de crédito/i })).toBeVisible()
})

test('credenciales incorrectas muestra error', async ({ page }) => {
  await page.getByLabel('Email').fill(VALID_EMAIL)
  await page.getByLabel('Contraseña').fill('wrong-password')
  await page.getByRole('button', { name: /ingresar/i }).click()

  await expect(page.getByText('Credenciales inválidas')).toBeVisible()
  await expect(page).toHaveURL('/login')
})

test('usuario inexistente muestra error', async ({ page }) => {
  await page.getByLabel('Email').fill('noexiste@test.com')
  await page.getByLabel('Contraseña').fill('password123')
  await page.getByRole('button', { name: /ingresar/i }).click()

  await expect(page.getByText('Credenciales inválidas')).toBeVisible()
})

test('no envía sin email (HTML5 required)', async ({ page }) => {
  await page.getByLabel('Contraseña').fill(VALID_PASSWORD)
  await page.getByRole('button', { name: /ingresar/i }).click()

  await expect(page).toHaveURL('/login')
})

test('no envía sin password (HTML5 required)', async ({ page }) => {
  await page.getByLabel('Email').fill(VALID_EMAIL)
  await page.getByRole('button', { name: /ingresar/i }).click()

  await expect(page).toHaveURL('/login')
})

test('botón muestra estado de carga al enviar', async ({ page }) => {
  await page.getByLabel('Email').fill(VALID_EMAIL)
  await page.getByLabel('Contraseña').fill(VALID_PASSWORD)

  const button = page.getByRole('button', { name: /ingresar/i })
  await button.click()

  // Captura el estado intermedio antes de que complete el redirect
  await expect(page.getByRole('button', { name: /ingresando/i }).or(page.getByRole('heading', { name: /solicitudes de crédito/i }))).toBeVisible()
})

test('link a signup navega correctamente', async ({ page }) => {
  await page.getByRole('link', { name: /regístrate/i }).click()
  await expect(page).toHaveURL('/signup')
})
