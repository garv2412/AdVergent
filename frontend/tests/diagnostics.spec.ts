import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
function worker(command='diagnostics'){execFileSync('../.venv/Scripts/python.exe',['-m','advergent.worker',command],{stdio:'pipe'});}
function scenario(mode:'fresh'|'suggestion'|'failure'){
  execFileSync('../.venv/Scripts/python.exe',['-c',`
import json,tempfile
from pathlib import Path
from datetime import datetime,timezone
from uuid import uuid4
from advergent.config import Settings
from advergent.operational import OperationalStore
from advergent.exasol import ExasolAnalytics
from advergent.diagnostics import import_diagnostics
from advergent.diagnostics_fixture import build_fixture
from advergent.inventory import import_inventory
s=Settings.from_env();store=OperationalStore(s.database_url);a=ExasolAnalytics(s)
f=build_fixture();f['version']='browser-diagnostics-${mode}-'+str(uuid4())
class Broken(ExasolAnalytics):
 def load_diagnostics(self,run,iid,f):
  f.checks.append(f.checks[-1]);super().load_diagnostics(run,iid,f)
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'source.json'
 if '${mode}' in ('fresh','suggestion'):
  now=datetime.now(timezone.utc);stamp=now.isoformat();delta=now-datetime.fromisoformat(f['observed_at'])
  inv=store.inventory_publication()[0]['configuration'];inv['version']='diagnostics-browser-inventory-'+str(uuid4());inv['observed_at']=stamp
  for r in inv['observations']:
   r['stock_observed_at']=stamp
   if '${mode}'=='suggestion' and int(r['variant_id'][1:])<6:r.update(available=100,eligible_units=28)
  for r in inv['resource_states']:r['observed_at']=stamp
  p.write_text(json.dumps(inv));import_inventory(store,a,p)
  if '${mode}'=='suggestion':f['checks']=[c for c in f['checks'] if c['id'] in ('healthy-1','creative-destination')]
  f['observed_at']=stamp
  for c in f['checks']:c['observed_at']=(datetime.fromisoformat(c['observed_at'].replace('Z','+00:00'))+delta).isoformat()
  for w in f['windows']:
   for k in ('start','end'):w[k]=(datetime.fromisoformat(w[k].replace('Z','+00:00'))+delta).isoformat()
 p.write_text(json.dumps(f))
 if '${mode}'=='failure':
  try:import_diagnostics(store,Broken(s),p)
  except RuntimeError:pass
  else:raise AssertionError('Actual SQL failure required')
 else:import_diagnostics(store,a,p)
`],{stdio:'pipe'});
}

test('real diagnostics A22-A24, grounded fatigue review and failure preservation',async({page,request})=>{
  test.skip(!process.env.E2E_OPERATOR_PASSWORD||process.env.E2E_DATABASE_FAILURE==='1','Real healthy stores and private operator required');test.setTimeout(240000);
  expect((await request.get('/api/diagnostics')).status()).toBe(401);
  try{
    worker();await page.goto('/');await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);await page.getByRole('button',{name:'Open workspace'}).click();
    const region=page.getByRole('region',{name:'Diagnostics',exact:true});
    await expect(region.getByTestId('diagnostics-summary')).toContainText('2 resource reviews',{timeout:60000});
    await expect(region.getByRole('alert')).toContainText('Stale diagnostic');
    let snap=await(await page.request.get('/api/diagnostics')).json();const published=snap.published_at;
    expect(snap.data.recommendations.every((r:any)=>r.mutation_enabled===false&&r.approval_required===true)).toBe(true);
    worker();snap=await(await page.request.get('/api/diagnostics')).json();expect(snap.published_at).toBe(published);
    scenario('fresh');await region.getByRole('button',{name:'Query diagnostics',exact:true}).click();
    await expect(region.getByTestId('diagnostics-summary')).toContainText('fresh',{timeout:60000});
    for(const state of ['uncertain_transient','confirmed_not_found','redirect_review','uncertain_bot_block','archived_product','uncertain_variant','expired_offer','variant_price_mismatch'])await expect(region.getByRole('cell',{name:state,exact:true})).toBeVisible();
    await region.getByText('m-ad supporting evidence',{exact:true}).click();
    await expect(region.locator('pre').filter({hasText:'approve all actions'})).toContainText('<script>');
    expect(await region.locator('script').count()).toBe(0);
    snap=await(await page.request.get('/api/diagnostics')).json();
    const ds=snap.data.recommendations.find((r:any)=>r.resource_id==='m-ad').destinations;
    expect(ds.find((d:any)=>d.status==='confirmed_not_found').evidence.length).toBe(2);
    expect(snap.data.recommendations.find((r:any)=>r.resource_id==='g-search-b-ad').fatigue[0].status).toBe('possible_fatigue');
    await region.getByText('m-ad supporting evidence',{exact:true}).click();
    await region.screenshot({path:'../.runtime/real-diagnostics.png'});
    scenario('suggestion');await region.getByRole('button',{name:'Query diagnostics',exact:true}).click();
    await expect(region.getByText('p0: Consider a new size and color presentation for review.',{exact:false})).toBeVisible({timeout:60000});
    snap=await(await page.request.get('/api/diagnostics')).json();const before=snap.dataset_id;
    expect(snap.data.recommendations.find((r:any)=>r.resource_id==='g-search-b-ad').suggestions).toEqual([]);
    await region.screenshot({path:'../.runtime/real-diagnostics-suggestion.png'});
    scenario('failure');await region.getByRole('button',{name:'Query diagnostics',exact:true}).click();
    await expect(region.getByRole('alert')).toContainText('Latest diagnostics import failed');
    snap=await(await page.request.get('/api/diagnostics')).json();expect(snap.dataset_id).toBe(before);
    expect(await region.getByRole('button').count()).toBe(1);
  }finally{worker('inventory');worker();}
});

test('actual stopped Exasol removes diagnostic checks and suggestions',async({page})=>{
  test.skip(!process.env.E2E_OPERATOR_PASSWORD||process.env.E2E_DATABASE_FAILURE!=='1','Actual outage mode only');test.setTimeout(90000);
  await page.goto('/');await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);await page.getByRole('button',{name:'Open workspace'}).click();
  const region=page.getByRole('region',{name:'Diagnostics',exact:true});
  await expect(region.getByRole('alert')).toContainText('Diagnostics Exasol unavailable',{timeout:60000});
  await expect(region.getByTestId('diagnostics-summary')).toHaveCount(0);await expect(region.locator('table')).toHaveCount(0);await expect(region.locator('details')).toHaveCount(0);
  await expect(region.locator('aside')).toContainText('Query unavailable');await expect(region.locator('aside')).toContainText('Diagnostics evidence');
  await region.screenshot({path:'../.runtime/real-diagnostics-outage.png'});
});
