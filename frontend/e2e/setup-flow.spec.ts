import { test, expect } from '@playwright/test'

test.describe('Setup flow', () => {
  test('shows setup page on first run', async ({ page }) => {
    await page.goto('/setup')
    await expect(page.getByRole('heading', { name: /setup/i })).toBeVisible()
  })

  test('completes setup and redirects to dashboard', async ({ page }) => {
    await page.goto('/setup')
    await page.getByLabel(/username/i).fill('admin')
    await page.getByLabel(/password/i).fill('TestPassword1!')
    await page.getByLabel(/confirm/i).fill('TestPassword1!')
    await page.getByRole('button', { name: /create/i }).click()
    await expect(page).toHaveURL(/\/admin/)
  })
})
