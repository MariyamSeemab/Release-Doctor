import { test, expect } from '@playwright/test'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000'

test.describe('Critical UI flows', () => {
  test('login page renders and accepts credentials', async ({ page }) => {
    await page.goto(`${BASE}/login`)
    await expect(page.locator('h1')).toContainText('Release Doctor')
    await page.fill('input[type="text"]', 'demo')
    await page.fill('input[type="password"]', 'demo')
    await page.click('button[type="submit"]')
    // Should redirect to dashboard after login
    await page.waitForURL(/\/$/, { timeout: 10000 })
    await expect(page).toHaveURL(/\/$/)
  })

  test('dashboard shows "Analyze a Release" button', async ({ page }) => {
    await page.goto(`${BASE}/login`)
    await page.fill('input[type="text"]', 'demo')
    await page.fill('input[type="password"]', 'demo')
    await page.click('button[type="submit"]')
    await page.waitForURL(/\/$/)
    await expect(page.locator('text=Analyze a Release')).toBeVisible()
  })

  test('project setup page renders form fields', async ({ page }) => {
    await page.goto(`${BASE}/login`)
    await page.fill('input[type="text"]', 'demo')
    await page.fill('input[type="password"]', 'demo')
    await page.click('button[type="submit"]')
    await page.waitForURL(/\/$/)
    await page.click('text=Analyze a Release')
    await page.waitForURL(/\/projects\/setup/)
    await expect(page.locator('h1')).toContainText('New Analysis')
    await expect(page.locator('input[placeholder="OrderFlow"]')).toBeVisible()
  })

  test('header shows logo and navigation', async ({ page }) => {
    await page.goto(`${BASE}/login`)
    await page.fill('input[type="text"]', 'demo')
    await page.fill('input[type="password"]', 'demo')
    await page.click('button[type="submit"]')
    await page.waitForURL(/\/$/)
    await expect(page.locator('header')).toBeVisible()
    await expect(page.locator('text=Release Doctor').first()).toBeVisible()
  })
})
