import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
function worker() { execFileSync('../.venv/Scripts/python.exe', ['-m', 'advergent.worker', 'attribution'], { stdio: 'pipe' }); }

test('real attribution reconciles, abstains, preserves multi-product sets and failed publication', async ({ page, request }) => {
  test.skip(!process.env.E2E_OPERATOR_PASSWORD || process.env.E2E_DATABASE_FAILURE === '1', 'Requires real healthy stores and private operator environment');
  test.setTimeout(90000);
  expect((await request.get('/api/attribution')).status()).toBe(401);
  try {
    worker();
    await page.goto('/');
    await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
    await page.getByRole('button', { name: 'Open workspace' }).click();
    const region = page.getByRole('region', { name: 'Mapping and attribution' });
    await expect(region.getByTestId('allocation-reconciliation')).toContainText('3000 orders · 3600 lines · ₹36,99,120.00', { timeout: 30000 });
    await expect(region.getByRole('row').filter({ hasText: 'google / google-inr / g-assets' })).toContainText('p0, p1');
    await expect(region.getByRole('row').filter({ hasText: 'google / google-inr / g-shopping-group' })).toContainText('ambiguous');
    await expect(region.getByRole('row').filter({ hasText: 'meta / meta-inr / m-mixed-ad' })).toContainText('explicit override');
    await expect(region.getByRole('row').filter({ hasText: 'Unattributed' })).toContainText('2996');
    await region.getByText('Mapping provenance, confidence and validity', { exact: true }).click();
    await expect(region.getByText('Valid from', { exact: false }).first()).toBeVisible();
    await region.getByText('First-party order evidence', { exact: true }).click();
    await expect(region.getByRole('row').filter({ hasText: 'ambiguous_click' })).toContainText('Unattributed');
    await region.getByText('Platform-reported claims — separate view', { exact: true }).click();
    await expect(region.getByText('reported ₹1,000.00', { exact: false })).toHaveCount(2);
    const evidence = await region.locator('aside').innerText();
    worker();
    await region.getByRole('button', { name: 'Query attribution' }).click();
    await expect(region.locator('aside')).toContainText(evidence.split('Published')[1].split('Queried (UTC)')[0].trim());
    execFileSync('../.venv/Scripts/python.exe', ['-c', `
import json, tempfile
from pathlib import Path
from uuid import uuid4
from advergent.attribution import import_attribution
from advergent.attribution_fixture import build_fixture
from advergent.config import Settings
from advergent.exasol import ExasolAnalytics
from advergent.operational import OperationalStore
settings=Settings.from_env()
class Broken(ExasolAnalytics):
    def load_attribution(self, run, commerce, data):
        super().load_attribution(run, commerce, dict(data, assignments=data['assignments']+[data['assignments'][-1]]))
with tempfile.TemporaryDirectory() as directory:
    source=build_fixture(); source['version']='browser-failure-'+str(uuid4())
    path=Path(directory)/'source.json'; path.write_text(json.dumps(source))
    try: import_attribution(OperationalStore(settings.database_url), Broken(settings), path)
    except RuntimeError: pass
    else: raise AssertionError('SQL failure did not occur')
`], { stdio: 'pipe' });
    await region.getByRole('button', { name: 'Query attribution' }).click();
    await expect(region.getByRole('alert')).toContainText('Latest attribution import failed');
    await expect(region.getByTestId('allocation-reconciliation')).toContainText('3000 orders');
    await region.getByText('Mapping provenance, confidence and validity', { exact: true }).click();
    await region.getByText('Purchased product allocations', { exact: true }).click();
    await region.screenshot({ path: '../.runtime/real-attribution.png' });
  } finally { worker(); }
});

test('actual Exasol outage hides mappings and allocation while retaining input evidence', async ({ page }) => {
  test.skip(!process.env.E2E_OPERATOR_PASSWORD || process.env.E2E_DATABASE_FAILURE !== '1', 'Explicit real outage mode');
  test.setTimeout(60000);
  await page.goto('/');
  await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
  await page.getByRole('button', { name: 'Open workspace' }).click();
  const region = page.getByRole('region', { name: 'Mapping and attribution' });
  await expect(region.getByRole('alert')).toContainText('Attribution Exasol unavailable', { timeout: 30000 });
  await expect(region.getByTestId('allocation-reconciliation')).toHaveCount(0);
  await expect(region.locator('table')).toHaveCount(0);
  await expect(region.locator('details')).toHaveCount(0);
  await expect(region.locator('aside')).toContainText('Query unavailable');
  await expect(region.locator('aside')).toContainText('last-paid-click-7d-no-view-v1');
  await region.screenshot({ path: '../.runtime/real-attribution-outage.png' });
});
