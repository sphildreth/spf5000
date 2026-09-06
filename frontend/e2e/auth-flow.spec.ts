import { expect, test } from '@playwright/test'

import { ADMIN_PASSWORD, ADMIN_USERNAME, WRONG_PASSWORD } from './credentials'

test.describe('Auth flow', () => {
  // The appliance-setup project has already created the administrator used here.
  test('shows login page for unauthenticated users', async ({ page }) => {
    await page.goto('/admin')
    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible()
  })

  test('login fails with wrong credentials', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel(/username/i).fill(ADMIN_USERNAME)
    await page.getByLabel(/password/i).fill(WRONG_PASSWORD)
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page.getByText(/invalid/i)).toBeVisible()
  })

  test('login succeeds with correct credentials', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel(/username/i).fill(ADMIN_USERNAME)
    await page.getByLabel(/password/i).fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page).toHaveURL(/\/admin/)
  })

  test('logout redirects to login', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel(/username/i).fill(ADMIN_USERNAME)
    await page.getByLabel(/password/i).fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: /sign in/i }).click()
    await page.getByRole('button', { name: /log out/i }).click()
    await expect(page).toHaveURL(/\/login/)
  })
})
