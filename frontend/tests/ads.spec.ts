import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';

function worker(fixture?: string) {
  execFileSync('../.venv/Scripts/python.exe', ['-m', 'advergent.worker', 'ads', ...(fixture ? ['--fixture', `../fixtures/${fixture}`] : [])], { stdio: 'pipe' });
}

test('real ad reporting replaces corrections, replays stably and preserves failed publication', async ({ page, request }) => {
  test.skip(!process.env.E2E_OPERATOR_PASSWORD || process.env.E2E_DATABASE_FAILURE === '1', 'Requires real stores and private operator environment');
  test.setTimeout(90000);
  expect((await request.get('/api/ads')).status()).toBe(401);
  try {
    worker('ads-initial-v1.json');
    await page.goto('/');
    await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
    await page.getByRole('button', { name: 'Open workspace' }).click();
    const ads = page.getByRole('region', { name: 'Ad reporting' });
    await expect(ads.getByTestId('ad-spend')).toHaveText('₹2,900.21');
    await expect(ads.getByRole('status')).toContainText('Ad freshness: stale');
    worker();
    await ads.getByRole('button', { name: 'Query ad reports' }).click();
    await expect(ads.getByTestId('ad-spend')).toHaveText('₹2,100.22');
    await expect(ads.getByText('7 additive half-hour reports; latest revision per grain')).toBeVisible();
    const evidence = await ads.locator('aside').innerText();
    worker();
    await ads.getByRole('button', { name: 'Query ad reports' }).click();
    await expect(ads.getByTestId('ad-spend')).toHaveText('₹2,100.22');
    // Publication timestamp and source observation survive replay.
    const published = evidence.split('Published (UTC)')[1].split('Queried (UTC)')[0].trim();
    await expect(ads.locator('aside')).toContainText(published);
    await ads.locator('summary').filter({ hasText: 'g-shared · Shared budget' }).click();
    await expect(ads.getByText('All member campaigns are affected.', { exact: false })).toBeVisible();
    await expect(ads.getByText('g-search-a, g-search-b', { exact: false }).first()).toBeVisible();
    await ads.locator('summary').filter({ hasText: 'g-assets · asset_group' }).click();
    await expect(ads.locator('details[open]').getByText('Unsupported — advisory only', { exact: true })).toBeVisible();
    await ads.locator('summary').filter({ hasText: 'Inspect normalized source reports' }).click();
    await expect(ads.getByRole('cell', { name: 'g-assets / 2', exact: true })).toBeVisible();
    await ads.screenshot({ path: '../.runtime/real-ad-capabilities.png' });
    // A real duplicate-key error rolls back the analytical transaction.
    execFileSync('../.venv/Scripts/python.exe', ['-c', `
import json, tempfile
from pathlib import Path
from uuid import uuid4
from advergent.ads import import_ads
from advergent.ads_fixture import build_fixture
from advergent.config import Settings
from advergent.exasol import ExasolAnalytics
from advergent.operational import OperationalStore
settings=Settings.from_env()
class Broken(ExasolAnalytics):
    def load_ads(self, run, fixture, reports):
        super().load_ads(run, fixture, reports+[reports[-1]])
with tempfile.TemporaryDirectory() as directory:
    source=build_fixture()
    source['version']='browser-failure-'+str(uuid4())
    path=Path(directory)/'source.json'
    path.write_text(json.dumps(source))
    try: import_ads(OperationalStore(settings.database_url), Broken(settings), path)
    except RuntimeError: pass
    else: raise AssertionError('SQL failure did not occur')
`], { stdio: 'pipe' });
    await ads.getByRole('button', { name: 'Query ad reports' }).click();
    await expect(ads.getByText('Latest ad import failed. Prior complete publication retained.')).toBeVisible();
    await expect(ads.getByTestId('ad-spend')).toHaveText('₹2,100.22');
    await expect(ads.getByRole('heading', { name: 'Ad query evidence' })).toBeVisible();
    await page.screenshot({ path: '../.runtime/real-ad-reporting.png', fullPage: true });
  } finally {
    worker();
  }
});

test('actual Exasol outage hides ad spend, hierarchy and capabilities while retaining evidence', async ({ page }) => {
  test.skip(!process.env.E2E_OPERATOR_PASSWORD || process.env.E2E_DATABASE_FAILURE !== '1', 'Explicit real outage mode only');
  test.setTimeout(60000);
  await page.goto('/');
  await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
  await page.getByRole('button', { name: 'Open workspace' }).click();
  const ads = page.getByRole('region', { name: 'Ad reporting' });
  await expect(ads.getByRole('alert')).toContainText('Ad reporting Exasol unavailable', { timeout: 30000 });
  await expect(ads.getByTestId('ad-spend')).toHaveCount(0);
  await expect(ads.locator('details')).toHaveCount(0);
  await expect(ads.getByRole('heading', { name: 'Ad query evidence' })).toBeVisible();
  await expect(ads.locator('aside')).toContainText('Query unavailable');
  await page.screenshot({ path: '../.runtime/real-ad-outage.png', fullPage: true });
});
