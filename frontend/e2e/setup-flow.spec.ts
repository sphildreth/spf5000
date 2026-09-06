import { expect, test } from '@playwright/test'

import { ADMIN_PASSWORD, ADMIN_USERNAME } from './credentials'

test.describe('Setup flow', () => {
  // Runs as its own project before the auth specs, which sign in with these credentials.
  test('shows setup page on first run', async ({ page }) => {
    await page.goto('/setup')
    await expect(page.getByRole('heading', { name: /set up the admin account/i })).toBeVisible()
  })

  test('completes setup and redirects to dashboard', async ({ page }) => {
    await page.goto('/setup')
    await page.getByLabel(/admin username/i).fill(ADMIN_USERNAME)
    // `exact` because "Confirm password" also matches /password/i.
    await page.getByLabel('Password', { exact: true }).fill(ADMIN_PASSWORD)
    await page.getByLabel(/confirm password/i).fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: /create admin/i }).click()
    await expect(page).toHaveURL(/\/admin/)
  })
})
