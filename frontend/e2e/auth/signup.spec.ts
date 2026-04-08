import { test, expect } from '@playwright/test'

function uniqueEmail() {
  return `test_${Date.now()}@example.com`
}

test.beforeEach(async ({ page }) => {
  await page.goto('/signup')
})

test('signup exitoso redirige a login con banner', async ({ page }) => {
  await page.getByLabel('Email').fill(uniqueEmail())
  await page.getByLabel('Contraseña').fill('securepass123')
  await page.getByRole('button', { name: /crear cuenta/i }).click()

  await expect(page).toHaveURL(/\/login\?registered=1/)
  await expect(page.getByText('Cuenta creada. Inicia sesión.')).toBeVisible()
})

test('email duplicado muestra error', async ({ page }) => {
  const email = uniqueEmail()

  // Primer registro
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Contraseña').fill('securepass123')
  await page.getByRole('button', { name: /crear cuenta/i }).click()
  await expect(page).toHaveURL(/\/login/)

  // Segundo intento con el mismo email
  await page.goto('/signup')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Contraseña').fill('securepass123')
  await page.getByRole('button', { name: /crear cuenta/i }).click()

  await expect(page.getByText(/ya existe|email/i)).toBeVisible()
  await expect(page).toHaveURL('/signup')
})

test('no envía con password menor a 8 caracteres (HTML5 minLength)', async ({ page }) => {
  await page.getByLabel('Email').fill(uniqueEmail())
  await page.getByLabel('Contraseña').fill('corta')
  await page.getByRole('button', { name: /crear cuenta/i }).click()

  await expect(page).toHaveURL('/signup')
})

test('no envía sin email (HTML5 required)', async ({ page }) => {
  await page.getByLabel('Contraseña').fill('securepass123')
  await page.getByRole('button', { name: /crear cuenta/i }).click()

  await expect(page).toHaveURL('/signup')
})

test('link a login navega correctamente', async ({ page }) => {
  await page.getByRole('link', { name: /inicia sesión/i }).click()
  await expect(page).toHaveURL('/login')
})
