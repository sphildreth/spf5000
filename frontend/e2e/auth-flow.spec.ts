import { test, expect } from '@playwright/test'

test.describe('Auth flow', () => {
  test('shows login page for unauthenticated users', async ({ page }) => {
    await page.goto('/admin')
    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByRole('heading', { name: /login/i })).toBeVisible()
  })

  test('login fails with wrong credentials', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel(/username/i).fill('admin')
    await page.getByLabel(/password/i).fill('wrongpassword')
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page.getByText(/invalid/i)).toBeVisible()
  })

  test('login succeeds with correct credentials', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel(/username/i).fill('admin')
    await page.getByLabel(/password/i).fill('test-password-1')
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page).toHaveURL(/\/admin/)
  })

  test('logout redirects to login', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel(/username/i).fill('admin')
    await page.getByLabel(/password/i).fill('test-password-1')
    await page.getByRole('button', { name: /sign in/i }).click()
    await page.getByRole('button', { name: /logout/i }).click()
    await expect(page).toHaveURL(/\/login/)
  })
})
