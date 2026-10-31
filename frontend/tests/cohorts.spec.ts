import {test,expect} from '@playwright/test';

test('real A20 cohort assignments, mature and partial windows and null costs',async({page,request})=>{
  test.skip(!process.env.E2E_OPERATOR_PASSWORD||process.env.E2E_DATABASE_FAILURE==='1','Authenticated healthy stores only');
  test.setTimeout(180000);
  expect((await request.get('/api/cohorts')).status()).toBe(401);
  await page.goto('/');await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
  await page.getByRole('button',{name:'Open workspace'}).click();
  const region=page.getByRole('region',{name:'Cohorts',exact:true});
  await expect(region.getByTestId('cohort-summary')).toContainText('History incomplete',{timeout:120000});
  await expect(region.getByTestId('cohort-mature').locator('tbody tr').first()).toBeVisible();
  await expect(region.getByTestId('cohort-immature').locator('tbody tr').first()).toBeVisible();
  await expect(region.getByTestId('cohort-mature')).toContainText('Unknown');
  const s=await(await page.request.get('/api/cohorts')).json();
  expect(s.status).toBe('available');expect(s.dependencies_current).toBe(true);
  expect(s.data.history_complete).toBe(false);expect(s.data.mutation_enabled).toBe(false);expect(s.data.publishing_enabled).toBe(false);
  expect(s.data.customers.some((c:any)=>Object.keys(c.weights).length>1)).toBe(true);
  expect(new Set(s.data.customers.map((c:any)=>c.customer_id)).size).toBe(s.data.customers.length);
  expect(await region.getByRole('button',{name:/publish|approve|execute/i}).count()).toBe(0);
  await region.screenshot({path:'../.runtime/real-cohorts.png'});
  await region.getByRole('button',{name:'Query cohorts',exact:true}).click();
  await expect(region.getByTestId('cohort-summary')).toContainText('History incomplete',{timeout:120000});
});

test('actual stopped Exasol removes cohort assignments and contribution',async({page})=>{
  test.skip(!process.env.E2E_OPERATOR_PASSWORD||process.env.E2E_DATABASE_FAILURE!=='1','Actual outage mode only');
  test.setTimeout(120000);
  await page.goto('/');await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
  await page.getByRole('button',{name:'Open workspace'}).click();
  const region=page.getByRole('region',{name:'Cohorts',exact:true});
  await expect(region.getByRole('alert')).toContainText('Cohorts Exasol unavailable',{timeout:60000});
  await expect(region.locator('table')).toHaveCount(0);await expect(region.getByTestId('cohort-summary')).toHaveCount(0);
  await expect(region.locator('details')).toHaveCount(0);await expect(region.locator('aside')).toContainText('Query unavailable');
  await region.screenshot({path:'../.runtime/real-cohorts-outage.png'});
});
