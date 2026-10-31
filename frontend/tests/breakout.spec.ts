import {test,expect} from '@playwright/test';

test('real breakout A19 deduplicated coverage, time evaluation and no added revenue',async({page,request})=>{
  test.skip(!process.env.E2E_OPERATOR_PASSWORD||process.env.E2E_DATABASE_FAILURE==='1','Authenticated healthy stores only');
  test.setTimeout(120000);
  expect((await request.get('/api/breakout')).status()).toBe(401);
  await page.goto('/');await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
  await page.getByRole('button',{name:'Open workspace'}).click();
  const region=page.getByRole('region',{name:'Breakout',exact:true});
  await expect(region.getByTestId('breakout-summary')).toContainText('0 ranked',{timeout:60000});
  await expect(region.getByTestId('breakout-summary')).toContainText('1 duplicate deliveries removed');
  await expect(region.getByTestId('breakout-summary')).toContainText('added revenue ₹0.00');
  await expect(region.getByTestId('breakout-p0')).toContainText('Abstain');
  await expect(region.getByTestId('breakout-p0')).toContainText('sparse funnel evidence');
  await expect(region.getByTestId('breakout-p1')).toContainText('stale or future funnel source');
  await expect(region.getByTestId('breakout-p1')).toContainText('sustained');
  const snap=await(await page.request.get('/api/breakout')).json();
  expect(snap.dependencies_current).toBe(true);expect(snap.data.added_revenue_paise).toBe(0);
  expect(snap.data.ranking).toHaveLength(30);
  expect(snap.data.ranking.find((r:any)=>r.product_id==='p0').counts.signal.click).toBe(2);
  expect(snap.data.mutation_enabled).toBe(false);expect(snap.data.publishing_enabled).toBe(false);
  expect(await region.getByRole('button',{name:/publish|approve|execute/i}).count()).toBe(0);
  await region.screenshot({path:'../.runtime/real-breakout.png'});
  await region.getByRole('button',{name:'Query breakout',exact:true}).click();
  await expect(region.getByTestId('breakout-summary')).toContainText('0 ranked',{timeout:60000});
});

test('actual stopped Exasol suppresses all breakout signals',async({page})=>{
  test.skip(!process.env.E2E_OPERATOR_PASSWORD||process.env.E2E_DATABASE_FAILURE!=='1','Actual outage mode only');
  test.setTimeout(120000);
  await page.goto('/');await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
  await page.getByRole('button',{name:'Open workspace'}).click();
  const region=page.getByRole('region',{name:'Breakout',exact:true});
  await expect(region.getByRole('alert')).toContainText('Breakout Exasol unavailable',{timeout:60000});
  await expect(region.locator('table')).toHaveCount(0);await expect(region.locator('details')).toHaveCount(0);
  await expect(region.getByTestId('breakout-summary')).toHaveCount(0);
  await expect(region.locator('aside')).toContainText('Query unavailable');
  await region.screenshot({path:'../.runtime/real-breakout-outage.png'});
});
