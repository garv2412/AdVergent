import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';

test('A26 actual halfway SQL failure retains the prior version in API and browser', async ({ page }) => {
  test.skip(!process.env.E2E_OPERATOR_PASSWORD || process.env.E2E_DATABASE_FAILURE === '1', 'Private healthy stores only');
  test.setTimeout(180000);
  try {
    execFileSync('../.venv/Scripts/python.exe', ['../scripts/fail-demo-refresh.py'], { stdio: 'pipe' });
    await page.goto('/');
    await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
    await page.getByRole('button', { name: 'Open workspace' }).click();
    await expect(page.getByText('Latest refresh failed. The prior complete publication is retained.', { exact: true })).toBeVisible();
    await expect(page.getByText('₹300.00', { exact: true })).toBeVisible();
    const response = await page.request.get('/api/foundation');
    expect(response.status()).toBe(200);
    const snapshot = await response.json();
    expect(snapshot.status).toBe('available');
    expect(snapshot.latest_refresh_status).toBe('failed');
    expect(snapshot.dataset_version).toBe('foundation-v1');
    expect(snapshot.metric.contribution_after_ads_paise).toBe(30000);
    await page.screenshot({ path: '../.runtime/phase14-failed-refresh.png', fullPage: true });
  } finally {
    execFileSync('../.venv/Scripts/python.exe', ['-m', 'advergent.worker', 'refresh'], { stdio: 'pipe' });
  }
});
