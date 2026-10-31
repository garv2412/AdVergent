import { test, expect } from '@playwright/test';

test('real commerce publication exposes source freshness and paginated records', async ({ page, request }) => {
  test.skip(!process.env.E2E_OPERATOR_PASSWORD || process.env.E2E_DATABASE_FAILURE === '1', 'Requires healthy real databases and imported commerce fixture');
  test.setTimeout(60000);
  expect((await request.get('/api/commerce')).status()).toBe(401);
  await page.goto('/');
  await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
  await page.getByRole('button', { name: 'Open workspace' }).click();
  const commerce = page.getByRole('region', { name: 'Commerce mirror' });
  await expect(commerce.getByText('3,000', { exact: true })).toBeVisible();
  await expect(commerce.getByRole('status')).toContainText('Commerce freshness: stale');
  await expect(commerce.getByText('Source available minus separate merchant reserve')).toBeVisible();
  await expect(commerce.locator('details')).toHaveCount(25);
  await commerce.getByRole('button', { name: 'Next records' }).click();
  await expect(commerce.getByText('180 records · showing 26–50.', { exact: false })).toBeVisible();
  await commerce.getByLabel('Inspect source collection').selectOption('products');
  await commerce.locator('details').first().locator('summary').click();
  await expect(commerce.getByText('<script>untrusted catalog text</script>', { exact: true })).toBeVisible();
  expect(await page.locator('script').count()).toBe(1); // only the app's script, catalog stays text
  await expect(commerce.getByRole('heading', { name: 'Commerce query evidence' })).toBeVisible();
  await page.screenshot({ path: '../.runtime/real-commerce.png', fullPage: true });
});

test('real commerce outage hides records and preserves source evidence', async ({ page }) => {
  test.skip(!process.env.E2E_OPERATOR_PASSWORD || process.env.E2E_DATABASE_FAILURE !== '1', 'Explicit real outage mode only');
  test.setTimeout(60000);
  await page.goto('/');
  await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
  await page.getByRole('button', { name: 'Open workspace' }).click();
  const commerce = page.getByRole('region', { name: 'Commerce mirror' });
  await expect(commerce.getByRole('alert')).toContainText('Commerce Exasol unavailable', { timeout: 30000 });
  await expect(commerce.locator('details')).toHaveCount(0);
  await expect(commerce.getByText('3,000', { exact: true })).toHaveCount(0);
  await expect(commerce.getByRole('heading', { name: 'Commerce query evidence' })).toBeVisible();
});

test('commerce rendering clears prior records on query failure', async ({ page }) => {
  // Rendering substitutes only, separate from real-database tests above.
  await page.route('**/api/session', route => route.fulfill({ json: { operator: 'demo operator' } }));
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
  await page.route('**/api/foundation', route => route.fulfill({ json: { status: 'not_loaded' } }));
  let failed = false;
  await page.route('**/api/commerce', route => route.fulfill({ json: { status: failed ? 'analytics_unavailable' : 'available', dataset_id: '00000000-0000-0000-0000-000000000001', freshness: 'stale', observed_at: '2026-10-29T18:00:00Z', totals: failed ? null : { orders: 3000, products: 30, variants: 180, lines: 3600, refunds: 143, inventory: 180, sellable_units: 100, missing_cost_lines: 20 } } }));
  await page.route('**/api/commerce/records/**', route => route.fulfill({ json: [{ kind: 'inventory', id: 'i0', updated_at: '2026-10-29T18:00:00Z', data: { available: 0, committed: 3 } }] }));
  await page.goto('/');
  const commerce = page.getByRole('region', { name: 'Commerce mirror' });
  await expect(commerce.locator('details')).toHaveCount(1);
  failed = true;
  await commerce.getByRole('button', { name: 'Query commerce' }).click();
  await expect(commerce.getByRole('alert')).toContainText('Commerce Exasol unavailable');
  await expect(commerce.locator('details')).toHaveCount(0);
});
