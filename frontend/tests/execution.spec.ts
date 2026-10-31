import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';

function source(mode: string, tag?: string) {
  return JSON.parse(execFileSync('../.venv/Scripts/python.exe', ['-c', `
import json
from advergent.config import Settings
from advergent.operational import OperationalStore
from advergent.exasol import ExasolAnalytics
from advergent.execution_scenarios import prepare,restore
s=Settings.from_env();store=OperationalStore(s.database_url);a=ExasolAnalytics(s)
if '${mode}'=='restore':restore(store,a);print('{}')
else:print(json.dumps(prepare(store,a,'${mode}',${tag ? JSON.stringify(tag) : 'None'})))
`], { encoding: 'utf8', stdio: 'pipe' }));
}
const headers = { Origin: 'http://127.0.0.1:8000', 'X-AdVergent-Request': '1' };

test('real approved pause A12, recovery A17 and kill switch', async ({ page, request }) => {
  test.skip(!process.env.E2E_OPERATOR_PASSWORD || process.env.E2E_DATABASE_FAILURE === '1', 'Real healthy stores and operator required');
  test.setTimeout(360000);
  expect((await request.get('/api/actions')).status()).toBe(401);
  try {
    const names = source('pause'); const resource = names['m-ad']; const tag = resource.slice('m-ad-'.length);
    await page.goto('/'); await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
    await page.getByRole('button', { name: 'Open workspace' }).click();
    const region = page.getByRole('region', { name: 'Approved execution', exact: true });
    await expect(region.getByRole('status')).toContainText('OFF');
    await region.getByLabel('Exact resource ID', { exact: false }).fill(resource);
    await region.getByLabel('Reason', { exact: true }).fill('Explicit authenticated browser synthetic pause');
    await region.getByRole('button', { name: 'Create proposal for review' }).click();
    const plan = region.getByTestId('action-plan').filter({ hasText: resource }).first();
    await expect(plan.getByRole('heading')).toContainText('proposed', { timeout: 60000 });
    await expect(plan.locator('pre').first()).toContainText('"evidence"');
    await plan.getByRole('button', { name: 'Reject this plan', exact: true }).click();
    await expect(plan.getByRole('heading')).toContainText('rejected');
    await region.getByRole('button', { name: 'Create proposal for review' }).click();
    await expect(plan.getByRole('heading')).toContainText('proposed', { timeout: 60000 });
    let ledger = await (await page.request.get('/api/actions')).json(); const id = ledger.plans[0].id;
    expect(ledger.plans[0].steps).toEqual([]);
    await plan.getByRole('button', { name: 'Explicitly approve this exact simulated plan' }).click();
    await expect(plan.getByRole('heading')).toContainText('approved');
    await plan.getByRole('button', { name: 'Execute approved simulation' }).click();
    await expect(plan.getByRole('heading')).toContainText('succeeded', { timeout: 60000 });
    const duplicate = await page.request.post(`/api/actions/${id}/execute`, { headers, data: {} });
    expect((await duplicate.json()).steps.length).toBe(1);
    source('clear', tag);
    await region.getByRole('combobox').first().selectOption('resume');
    await region.getByRole('button', { name: 'Create proposal for review' }).click();
    await expect(plan.getByRole('heading')).toContainText('proposed', { timeout: 60000 });
    // Source recovery alone has not changed simulator state.
    ledger = await (await page.request.get('/api/actions')).json(); expect(ledger.plans[0].steps).toEqual([]);
    await plan.getByRole('button', { name: 'Explicitly approve this exact simulated plan' }).click();
    await plan.getByRole('button', { name: 'Execute approved simulation' }).click();
    await expect(plan.getByRole('heading')).toContainText('succeeded', { timeout: 60000 });
    await region.getByRole('button', { name: 'Enable kill switch' }).click();
    await expect(region.getByRole('status')).toContainText('ON');
    await region.getByRole('button', { name: 'Disable kill switch' }).click();
    await expect(region.getByRole('status')).toContainText('OFF');
    await plan.screenshot({ path: '../.runtime/real-execution.png' });
  } finally { source('restore'); }
});

test('actual stopped Exasol blocks approved execution A16', async ({ page }) => {
  test.skip(!process.env.E2E_OPERATOR_PASSWORD || process.env.E2E_DATABASE_FAILURE !== '1', 'Actual stopped analytics only');
  test.setTimeout(90000);
  const approved = JSON.parse(readFileSync('../.runtime/phase8-outage.json', 'utf8'));
  await page.goto('/'); await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
  await page.getByRole('button', { name: 'Open workspace' }).click();
  const region = page.getByRole('region', { name: 'Approved execution', exact: true });
  const plan = region.getByTestId('action-plan').filter({ hasText: approved.id });
  await expect(plan.getByRole('heading')).toContainText('approved', { timeout: 60000 });
  await plan.getByRole('button', { name: 'Execute approved simulation' }).click();
  await expect(plan.getByRole('heading')).toContainText('rejected', { timeout: 60000 });
  const ledger = await (await page.request.get('/api/actions')).json();
  const result = ledger.plans.find((p: any) => p.id === approved.id);
  expect(result.error_code).toBe('revalidation_failed');expect(result.steps).toEqual([]);
  await plan.screenshot({ path: '../.runtime/real-execution-outage.png' });
});

test('real partial INR transfer displays actual budgets and approved inverse recovery', async ({ page }) => {
  test.skip(!process.env.E2E_OPERATOR_PASSWORD || process.env.E2E_DATABASE_FAILURE === '1', 'Real healthy stores only');
  test.setTimeout(360000);
  try {
    const names = source('clear');
    await page.goto('/');await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
    await page.getByRole('button', { name: 'Open workspace' }).click();
    const region = page.getByRole('region', { name: 'Approved execution', exact: true });
    await expect(region.getByRole('status')).toContainText('OFF', { timeout: 60000 });
    const adResponse = await page.request.get('/api/ads');expect(adResponse.status()).toBe(200);
    const ads = await adResponse.json();expect(ads.status).toBe('available');
    const donor = ads.data.budgets.find((b: any) => b.id === names['m-set-budget']);
    const recipient = ads.data.budgets.find((b: any) => b.id === names['m-campaign-budget']);
    const proposal = await page.request.post('/api/actions/propose', { headers, data: {
      client_key: crypto.randomUUID(), action: 'transfer', reason: 'Explicit browser partial-transfer acceptance', recovery_of: null,
      changes: [{ platform: 'meta', account_id: 'meta-inr', resource_id: donor.id, kind: 'budget', after: donor.daily_paise - 12345 },
        { platform: 'meta', account_id: 'meta-inr', resource_id: recipient.id, kind: 'budget', after: recipient.daily_paise + 12345 }]
    } });
    expect(proposal.ok()).toBeTruthy();const p = await proposal.json();
    await region.getByRole('button', { name: 'Query action ledger' }).click();
    const plan = region.getByTestId('action-plan').filter({ hasText: p.id });
    await plan.getByRole('button', { name: 'Explicitly approve this exact simulated plan' }).click();
    // Trusted fault adapter executes the browser-approved durable plan. No failure
    // injection or unapproved mutation endpoint is exposed to the application.
    execFileSync('../.venv/Scripts/python.exe', ['-c', `
from advergent.config import Settings
from advergent.operational import OperationalStore
from advergent.exasol import ExasolAnalytics
from advergent.execution import Executor,Simulator
s=Settings.from_env();store=OperationalStore(s.database_url)
class FailedRecipient(Simulator):
 def apply(self,rid,intent):
  if rid.endswith(':1'):raise RuntimeError('synthetic recipient rejection')
  super().apply(rid,intent)
assert Executor(store,ExasolAnalytics(s),FailedRecipient(store)).execute('${p.id}')['status']=='partially_succeeded'
`], { stdio: 'pipe' });
    await region.getByRole('button', { name: 'Query action ledger' }).click();
    await expect(plan.getByRole('heading')).toContainText('partially_succeeded');
    await plan.getByText('Approval digest, read-back and audit', { exact: true }).click();
    const ledger = await (await page.request.get('/api/actions')).json();const actual = ledger.plans.find((x: any) => x.id === p.id);
    expect(actual.steps.map((s: any) => s.actual.value)).toEqual([donor.daily_paise - 12345, recipient.daily_paise]);
    await expect(plan.locator('details pre')).toContainText('"actual"');
    await plan.screenshot({ path: '../.runtime/real-execution-partial.png' });
    const recovery = await page.request.post('/api/actions/propose', { headers, data: {
      client_key: crypto.randomUUID(), action: 'recovery', recovery_of: p.id, reason: 'Explicit partial transfer inverse',
      changes: [{ platform: 'meta', account_id: 'meta-inr', resource_id: donor.id, kind: 'budget', after: donor.daily_paise }]
    } });
    expect(recovery.ok()).toBeTruthy();const r = await recovery.json();
    expect((await page.request.post(`/api/actions/${r.id}/execute`, { headers, data: {} })).ok()).toBeTruthy();
    await region.getByRole('button', { name: 'Query action ledger' }).click();
    const recovered = region.getByTestId('action-plan').filter({ hasText: r.id });
    await expect(recovered.getByRole('heading')).toContainText('proposed');
    await recovered.getByRole('button', { name: 'Explicitly approve this exact simulated plan' }).click();
    await recovered.getByRole('button', { name: 'Execute approved simulation' }).click();
    await expect(recovered.getByRole('heading')).toContainText('succeeded', { timeout: 60000 });
  } finally { source('restore'); }
});
