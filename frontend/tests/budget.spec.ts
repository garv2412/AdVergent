import {test,expect} from '@playwright/test';

test('real budget exact portfolio, conservative abstention and protected scenario terms',async({page,request})=>{
  test.skip(!process.env.E2E_OPERATOR_PASSWORD||process.env.E2E_DATABASE_FAILURE==='1','Authenticated healthy stores only');
  test.setTimeout(240000);
  expect((await request.get('/api/budget')).status()).toBe(401);
  await page.goto('/');await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
  await page.getByRole('button',{name:'Open workspace'}).click();
  const region=page.getByRole('region',{name:'Budget optimization',exact:true});
  await region.getByRole('button',{name:'Query budget',exact:true}).click();
  await expect(region.getByTestId('budget-summary')).toContainText('abstain',{timeout:180000});
  await expect(region.locator('tbody tr')).toHaveCount(5);
  await expect(region).toContainText('history incomplete');
  await expect(region).toContainText('fewer than three spend levels');
  const s=await(await page.request.get('/api/budget')).json();
  expect(s.status).toBe('available');expect(s.dependencies_current).toBe(true);
  expect(s.data.total_paise).toBe(s.data.allocated_total_paise);
  expect(s.data.rows.every((r:any)=>r.current_paise===r.allocated_paise)).toBe(true);
  expect(s.data.cohort_context.history_complete).toBe(false);
  expect(s.data.cohort_context.windows.every((w:any)=>w.mature>0&&w.immature>0&&w.missing>0)).toBe(true);
  expect(s.data.mutation_enabled).toBe(false);expect(s.data.publishing_enabled).toBe(false);
  expect(s.data.portfolio_contribution_after_ads_paise).toBe(null);
  expect(await region.getByRole('button',{name:/publish|approve|execute/i}).count()).toBe(0);
  await region.screenshot({path:'../.runtime/real-budget.png'});
  await region.getByLabel('Maximum change').fill('333');
  await region.getByRole('button',{name:'Compare allocation'}).click();
  await expect(region.getByTestId('budget-summary')).toContainText('abstain',{timeout:180000});
  await region.getByLabel('Fixed total').fill(String(s.data.total_paise+1));
  await region.getByRole('button',{name:'Compare allocation'}).click();
  await expect(region.getByTestId('budget-summary')).toContainText('infeasible',{timeout:180000});
});

test('actual stopped Exasol removes all budget allocations and response evidence',async({page})=>{
  test.skip(!process.env.E2E_OPERATOR_PASSWORD||process.env.E2E_DATABASE_FAILURE!=='1','Actual outage mode only');
  test.setTimeout(120000);
  await page.goto('/');await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
  await page.getByRole('button',{name:'Open workspace'}).click();
  const region=page.getByRole('region',{name:'Budget optimization',exact:true});
  await region.getByRole('button',{name:'Query budget',exact:true}).click();
  await expect(region.getByRole('alert')).toContainText('Budget Exasol unavailable',{timeout:60000});
  await expect(region.locator('table')).toHaveCount(0);
  await expect(region.getByTestId('budget-summary')).toHaveCount(0);
  await expect(region.locator('details')).toHaveCount(0);
  await expect(region.locator('aside')).toContainText('Query unavailable');
  await region.screenshot({path:'../.runtime/real-budget-outage.png'});
});
