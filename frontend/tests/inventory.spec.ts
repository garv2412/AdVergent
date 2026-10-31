import { test,expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
function worker(){execFileSync('../.venv/Scripts/python.exe',['-m','advergent.worker','inventory'],{stdio:'pipe'});}
function scenario(mode:'fresh'|'arithmetic'|'receipt'|'recovery'|'merchant'|'blocked'|'failure'){
  execFileSync('../.venv/Scripts/python.exe',['-c',`
import json,tempfile
from pathlib import Path
from datetime import datetime,timezone,timedelta
from uuid import uuid4
from advergent.inventory import import_inventory
from advergent.inventory_fixture import build_fixture
from advergent.config import Settings
from advergent.operational import OperationalStore
from advergent.exasol import ExasolAnalytics
s=Settings.from_env();store=OperationalStore(s.database_url)
class Broken(ExasolAnalytics):
    def load_inventory(self,run,fid,f):
        f.observations.append(f.observations[-1]);super().load_inventory(run,fid,f)
f=build_fixture();f['version']='browser-${mode}-'+str(uuid4());now=datetime.now(timezone.utc).isoformat()
if '${mode}'!='failure':
    f['observed_at']=now
    for r in f['observations']:
        r['stock_observed_at']=now
        if '${mode}'=='fresh' and 6<=int(r['variant_id'][1:])<12:r.update(available=100,eligible_units=28)
        if '${mode}' in ('recovery','merchant','blocked') and int(r['variant_id'][1:])<6:r.update(available=40,eligible_units=28)
    if '${mode}'=='arithmetic':
        next(r for r in f['observations'] if r['variant_id']=='v6').update(merchant_reserve=5,committed=999)
        next(r for r in f['observations'] if r['variant_id']=='v7')['merchant_reserve']=999
    if '${mode}'=='receipt':
        f['receipts'][0].update(expected_at=(datetime.now(timezone.utc)+timedelta(days=3)).isoformat(),quantity=200,observed_at=now)
    for state in f['resource_states']:
        state['observed_at']=now
        if state['resource_id']=='m-ad' and '${mode}' in ('recovery','merchant','blocked'):
            state.update(status='paused',paused_by='merchant' if '${mode}'=='merchant' else 'AdVergent',pause_evidence_id='simulated-prior-approved-pause')
            if '${mode}'=='blocked':state['blockers']=['unresolved destination issue']
with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'inventory.json';path.write_text(json.dumps(f))
    if '${mode}'=='failure':
        try:import_inventory(store,Broken(s),path)
        except RuntimeError:pass
        else:raise AssertionError('Actual SQL failure required')
    else:import_inventory(store,ExasolAnalytics(s),path)
`],{stdio:'pipe'});
}

test('real inventory A09-A11, uncertainty, freshness, recovery restrictions and failure preservation',async({page,request})=>{
  test.skip(!process.env.E2E_OPERATOR_PASSWORD||process.env.E2E_DATABASE_FAILURE==='1','Real healthy stores and private operator required');
  test.setTimeout(240000);
  expect((await request.get('/api/inventory')).status()).toBe(401);
  try{
    worker();await page.goto('/');await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);await page.getByRole('button',{name:'Open workspace'}).click();
    const region=page.getByRole('region',{name:'Inventory',exact:true});
    await expect(region.getByTestId('inventory-reconciliation')).toContainText('180 variants',{timeout:60000});
    await expect(region.getByRole('alert')).toContainText('Stale inventory');
    let snap=await(await page.request.get('/api/inventory')).json();
    const v=snap.data.products.find((p:any)=>p.product_id==='p1').variants.find((v:any)=>v.variant_id==='v6');
    expect(Number(v.days_of_cover)).toBe(4);expect(v.sellable_units).toBe(40);expect(Number(v.daily_velocity)).toBe(10);
    expect(snap.data.products.find((p:any)=>p.product_id==='p1').suggested_action).toBe('throttle');
    expect(Number(snap.data.products.find((p:any)=>p.product_id==='p0').unavailable_weight_bps)).toBe(6000);
    for(const pid of ['p2','p3','p4'])expect(snap.data.products.find((p:any)=>p.product_id===pid).days_of_cover).toBeNull();
    expect(snap.data.products.find((p:any)=>p.product_id==='p5').lead_days).toBeNull();
    expect(snap.data.recommendations.every((r:any)=>r.eligibility!=='eligible')).toBe(true);
    const published=snap.published_at;worker();await region.getByRole('button',{name:'Query inventory',exact:true}).click();
    snap=await(await page.request.get('/api/inventory')).json();expect(snap.published_at).toBe(published);expect(snap.freshness).toBe('stale');
    await region.getByText('p1 variant evidence',{exact:true}).click();await region.locator('summary').filter({hasText:'v6 / S'}).click();
    await expect(region.locator('summary').filter({hasText:'v6 / S'}).locator('..').locator('pre')).toContainText('late-v6');
    await expect(region.locator('summary').filter({hasText:'v6 / S'})).toContainText('4.00 days');
    await expect(region.getByRole('cell',{name:'p0',exact:true}).locator('..')).toContainText('60.00%');
    for(const mode of ['arithmetic','receipt'] as const){
      scenario(mode);await region.getByRole('button',{name:'Query inventory',exact:true}).click();
      snap=await(await page.request.get('/api/inventory')).json();const variants=snap.data.products.find((p:any)=>p.product_id==='p1').variants;const v=variants.find((v:any)=>v.variant_id==='v6');
      if(mode==='arithmetic'){expect(v.sellable_units).toBe(35);expect(Number(v.days_of_cover)).toBe(3.5);expect(variants.find((v:any)=>v.variant_id==='v7').sellable_units).toBe(0);}
      else{expect(v.sellable_units).toBe(40);expect(v.replenishment_sufficient).toBe(true);expect(v.qualified_receipt_ids).toContain('late-v6');}
    }
    scenario('fresh');await region.getByRole('button',{name:'Query inventory',exact:true}).click();
    await expect(region.getByTestId('inventory-reconciliation')).toContainText('source freshness: fresh');
    snap=await(await page.request.get('/api/inventory')).json();
    expect(snap.data.recommendations.find((r:any)=>r.resource_id==='m-ad').eligibility).toBe('eligible');
    expect(snap.data.products.find((p:any)=>p.product_id==='p1').risk).toBe('clear');
    const mixed=snap.data.recommendations.find((r:any)=>r.resource_id==='g-assets');expect(mixed.eligibility).toBe('advisory');expect(mixed.blockers.join(' ')).toContain('mixed-product');
    expect(snap.data.recommendations.find((r:any)=>r.resource_id==='m-ad').impact.expected_contribution_paise).toBeNull();
    for(const mode of ['recovery','merchant','blocked'] as const){
      scenario(mode);await region.getByRole('button',{name:'Query inventory',exact:true}).click();
      snap=await(await page.request.get('/api/inventory')).json();const r=snap.data.recommendations.find((r:any)=>r.resource_id==='m-ad');
      expect(r.action).toBe(mode==='merchant'?'advisory':'recovery');expect(r.eligibility).toBe(mode==='recovery'?'eligible':'advisory');expect(r.approval_required).toBe(true);expect(r.mutation_enabled).toBe(false);
    }
    const before=snap.dataset_id;scenario('failure');await region.getByRole('button',{name:'Query inventory',exact:true}).click();
    await expect(region.getByRole('alert')).toContainText('Latest inventory import failed');
    snap=await(await page.request.get('/api/inventory')).json();expect(snap.dataset_id).toBe(before);
    await region.screenshot({path:'../.runtime/real-inventory.png'});
    expect(await region.getByRole('button').count()).toBe(1);
  }finally{worker();}
});

test('actual stopped Exasol removes inventory, eligibility and current evidence',async({page})=>{
  test.skip(!process.env.E2E_OPERATOR_PASSWORD||process.env.E2E_DATABASE_FAILURE!=='1','Explicit actual outage mode');test.setTimeout(90000);
  await page.goto('/');await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);await page.getByRole('button',{name:'Open workspace'}).click();
  const region=page.getByRole('region',{name:'Inventory',exact:true});
  await expect(region.getByRole('alert')).toContainText('Inventory Exasol unavailable',{timeout:60000});
  await expect(region.getByTestId('inventory-reconciliation')).toHaveCount(0);await expect(region.locator('table')).toHaveCount(0);await expect(region.locator('details')).toHaveCount(0);
  await expect(region.locator('aside')).toContainText('Query unavailable');await expect(region.locator('aside')).toContainText('Inventory evidence');
  await region.screenshot({path:'../.runtime/real-inventory-outage.png'});
});
