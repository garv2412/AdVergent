import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
function worker() { execFileSync('../.venv/Scripts/python.exe', ['-m','advergent.worker','finance'], { stdio:'pipe' }); }
function scenario(mode: 'corrected' | 'failure') {
  execFileSync('../.venv/Scripts/python.exe', ['-c', `
import json,tempfile
from pathlib import Path
from uuid import uuid4
from advergent.finance import import_finance
from advergent.finance_fixture import build_fixture
from advergent.config import Settings
from advergent.operational import OperationalStore
from advergent.exasol import ExasolAnalytics
s=Settings.from_env();store=OperationalStore(s.database_url)
class Broken(ExasolAnalytics):
    def load_finance(self,run,cid,aid,tid,rows):
        super().load_finance(run,cid,aid,tid,rows+[rows[-1]])
f=build_fixture();f['version']='browser-${mode}-'+str(uuid4())
if '${mode}'=='corrected':
    f['corrections']=[dict(line_id='l0-0',unit_cost_paise=25000,effective_at='2026-05-01T00:00:00Z',source='explicit historical invoice',reason='correct invoice',status='actual')]
    next(r for r in f['recoveries'] if r['refund_id']=='r0')['recovered_value_paise']=20000
    next(r for r in f['orders'] if r['order_id']=='o0')['delivered_at']='2026-10-29T17:00:00Z'
with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'finance.json';path.write_text(json.dumps(f))
    if '${mode}'=='failure':
        try:import_finance(store,Broken(s),path)
        except RuntimeError:pass
        else:raise AssertionError('Actual SQL failure required')
    else:import_finance(store,ExasolAnalytics(s),path)
`], { stdio:'pipe' });
}

test('real finance A01-A08, historical correction, partial reserve and SQL failure preserve exact allocation', async ({ page, request }) => {
  test.skip(!process.env.E2E_OPERATOR_PASSWORD || process.env.E2E_DATABASE_FAILURE === '1', 'Requires real healthy stores and private operator environment');
  test.setTimeout(120000);
  expect((await request.get('/api/finance')).status()).toBe(401);
  try {
    worker();
    await page.goto('/');
    await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
    await page.getByRole('button', { name:'Open workspace' }).click();
    const region=page.getByRole('region', { name:'Finance', exact:true });
    await expect(region.getByTestId('finance-reconciliation')).toContainText('3000 orders');
    await expect(region.getByTestId('finance-reconciliation')).toContainText('3600 lines');
    await expect(region.getByText('Cost coverage', { exact:false })).toContainText('98.50%');
    await expect(region.getByText('Unknown — incomplete costs', { exact:true }).first()).toBeVisible();
    await expect(region.getByRole('row').filter({ hasText:'Unattributed' })).toContainText('2996');
    let snapshot=await (await page.request.get('/api/finance')).json();
    expect(snapshot.status,'Real finance snapshot must be available').toBe('available');
    expect(snapshot.data).not.toBeNull();
    let data=snapshot.data;
    expect(data.totals.net_sales_paise).toBe(148747000);
    expect(data.totals.unsettled_cod_paise).toBe(44531500);
    expect(data.lines.find((l:any)=>l.line_id==='l18-0').contribution_before_ads_paise).toBe(-12001);
    expect(data.lines.find((l:any)=>l.line_id==='l0-0').campaign_id).toBe('g-pmax');
    expect(data.lines.find((l:any)=>l.line_id==='l1-0').contribution_before_ads_paise).toBe(41499);
    const published=(await region.locator('aside').innerText()).split('Published')[1].split('Queried')[0];
    worker();await region.getByRole('button',{name:'Query finance',exact:true}).click();
    await expect(region.locator('aside')).toContainText(published.trim());
    scenario('corrected');await region.getByRole('button',{name:'Query finance',exact:true}).click();
    await expect(region.getByText('Cost coverage', { exact:false })).toContainText('53 incomplete lines');
    snapshot=await (await page.request.get('/api/finance')).json();
    expect(snapshot.status,'Corrected real finance snapshot must be available').toBe('available');
    expect(snapshot.data).not.toBeNull();
    data=snapshot.data;
    const line=data.lines.find((l:any)=>l.line_id==='l0-0');
    expect(line.contribution_before_ads_paise).toBe(51999);expect(line.reserve_paise).toBe(6450);expect(line.exposed_units).toBe(1);
    expect(line.evidence.original_line.unit_cost_paise).toBeNull();
    await region.getByText('Line economics and historical provenance',{exact:true}).click();
    await region.locator('summary').filter({hasText:'l0-0 / o0'}).click();
    await expect(region.locator('pre').first()).toContainText('explicit historical invoice');
    await region.getByText('Transaction-day finance · Asia/Kolkata',{exact:true}).click();
    await expect(region.getByRole('cell',{name:'2026-10-29',exact:true})).toBeVisible();
    scenario('failure');await region.getByRole('button',{name:'Query finance',exact:true}).click();
    await expect(region.getByRole('alert')).toContainText('Latest finance import failed');
    await expect(region.getByTestId('finance-reconciliation')).toContainText('3000 orders');
    await region.screenshot({path:'../.runtime/real-finance.png'});
  } finally { worker(); }
});

test('actual Exasol outage removes finance, cash, ratios and line evidence', async ({ page }) => {
  test.skip(!process.env.E2E_OPERATOR_PASSWORD || process.env.E2E_DATABASE_FAILURE !== '1', 'Explicit actual outage mode');
  test.setTimeout(60000);
  await page.goto('/');await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
  await page.getByRole('button',{name:'Open workspace'}).click();
  const region=page.getByRole('region',{name:'Finance',exact:true});
  await expect(region.getByRole('alert')).toContainText('Finance Exasol unavailable',{timeout:30000});
  await expect(region.getByTestId('finance-reconciliation')).toHaveCount(0);
  await expect(region.locator('table')).toHaveCount(0);await expect(region.locator('details')).toHaveCount(0);
  await expect(region.locator('aside')).toContainText('Query unavailable');
  await expect(region.locator('aside')).toContainText('Finance evidence');
  await region.screenshot({path:'../.runtime/real-finance-outage.png'});
});
