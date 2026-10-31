import { test, expect } from '@playwright/test';

test('real API denies unauthenticated access and UI displays login', async ({ page, request }) => {
  expect((await request.get('/api/foundation')).status()).toBe(401);
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Operator access' })).toBeVisible();
  await expect(page.getByText('Real Exasol analytics', { exact: false })).toBeVisible();
  await page.screenshot({ path: '../.runtime/login-preview.png', fullPage: true });
});

test('real operator path queries Exasol and logs out', async ({ page }) => {
  test.skip(!process.env.E2E_OPERATOR_PASSWORD || process.env.E2E_DATABASE_FAILURE === '1', 'Requires real healthy databases and private operator password');
  test.setTimeout(60000);
  await page.goto('/');
  await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
  await page.getByRole('button', { name: 'Open workspace' }).click();
  await expect(page.getByText('₹300.00', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Query evidence', exact: true })).toBeVisible();
  await page.screenshot({ path: '../.runtime/real-foundation.png', fullPage: true });
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page.getByRole('heading', { name: 'Operator access' })).toBeVisible({ timeout: 30000 });
});

test('real database outage is shown in the browser', async ({ page }) => {
  test.skip(process.env.E2E_DATABASE_FAILURE !== '1' || !process.env.E2E_OPERATOR_PASSWORD, 'Explicit real outage check only');
  test.setTimeout(60000);
  await page.goto('/');
  await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
  await page.getByRole('button', { name: 'Open workspace' }).click();
  await expect(page.getByRole('alert').filter({ hasText: /^Exasol unavailable/ })).toContainText('Exasol unavailable', { timeout: 30000 });
  await expect(page.getByText('₹300.00', { exact: true })).toHaveCount(0);
  await page.screenshot({ path: '../.runtime/real-exasol-outage.png', fullPage: true });
});

test('UI contract fixture hides old numbers on analytics failure and allows reauthentication', async ({ page }) => {
  // Route substitutes verify rendering only, never Exasol or operational persistence.
  await page.route('**/api/session', route => route.fulfill({ json: { operator: 'demo operator' } }));
  await page.route('**/api/commerce', route => route.fulfill({ json: { status: 'not_loaded' } }));
  await page.route('**/api/ads', route => route.fulfill({ json: { status: 'not_loaded' } }));
  await page.route('**/api/attribution', route => route.fulfill({ json: { status: 'not_loaded' } }));
  await page.route('**/api/finance', route => route.fulfill({ json: { status: 'not_loaded' } }));
  await page.route('**/api/inventory', route => route.fulfill({ json: { status: 'not_loaded' } }));
  await page.route('**/api/diagnostics', route => route.fulfill({ json: { status: 'not_loaded' } }));
  await page.route('**/api/clearance', route => route.fulfill({ json: { status: 'not_loaded' } }));
  await page.route('**/api/breakout', route => route.fulfill({ json: { status: 'not_loaded' } }));
  await page.route('**/api/cohorts', route => route.fulfill({ json: { status: 'not_loaded' } }));
  await page.route('**/api/budget', route => route.fulfill({ json: { status: 'not_loaded' } }));
  await page.route('**/api/actions', route => route.fulfill({ json: { simulated: true, kill_switch: false, plans: [] } }));
  let state = 'available';
  await page.route('**/api/foundation', route => state === 'expired' ? route.fulfill({ status: 401, json: { detail: 'Authentication required' } }) : route.fulfill({ json: {
    status: state, dataset_id: '00000000-0000-0000-0000-000000000001', dataset_version: 'foundation-v1', fixture_hash: 'test-only', published_at: '2026-10-01T00:00:00Z', queried_at: state === 'available' ? '2026-10-01T00:00:01Z' : null,
    metric: state === 'available' ? { line_count: 2, net_sales_paise: 400000, product_cost_paise: 220000, variable_cost_paise: 50000, ad_spend_paise: 100000, contribution_before_ads_paise: 130000, contribution_after_ads_paise: 30000 } : null,
  } }));
  await page.goto('/');
  await expect(page.getByText('₹300.00', { exact: true })).toBeVisible();
  state = 'analytics_unavailable';
  await page.getByRole('button', { name: 'Query Exasol' }).click();
  await expect(page.getByRole('alert')).toContainText('Exasol unavailable');
  await expect(page.getByText('₹300.00', { exact: true })).toHaveCount(0);
  state = 'expired';
  await page.getByRole('button', { name: 'Query Exasol' }).click();
  await expect(page.getByRole('heading', { name: 'Operator access' })).toBeVisible();
});
