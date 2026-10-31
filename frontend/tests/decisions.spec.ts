import {test,expect} from '@playwright/test';

test('real unified decisions preserve scope and uncertainty and record no invented outcome',async({page,request})=>{
  test.skip(!process.env.E2E_OPERATOR_PASSWORD||process.env.E2E_DATABASE_FAILURE==='1','Authenticated healthy stores only');
  test.setTimeout(300000);
  expect((await request.get('/api/decisions')).status()).toBe(401);
  await page.goto('/');await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
  await page.getByRole('button',{name:'Open workspace'}).click();
  const region=page.getByRole('region',{name:'Unified decisions',exact:true});
  await region.getByRole('button',{name:'Query decisions',exact:true}).click();
  await expect(region.getByTestId('decisions-summary')).toContainText('19 resource decisions',{timeout:180000});
  await expect(region.getByRole('table',{name:'Current unified decisions'}).locator('tbody tr')).toHaveCount(19);
  await expect(region).toContainText('Allocated 1100000 paise');
  await expect(region.getByRole('table',{name:'Current unified decisions'}).locator('tbody')).toContainText('abstain');
  expect(await region.getByRole('button',{name:/publish|approve|execute/i}).count()).toBe(0);
  const tracking=page.waitForResponse(r=>r.url().endsWith('/api/decisions/track')&&r.request().method()==='POST');
  await region.getByRole('button',{name:'Record observation',exact:true}).first().click();
  const saved=await tracking;expect(saved.status()).toBe(200);
  const observations=(await saved.json()).observations;
  expect(observations.length).toBeGreaterThan(0);
  expect(observations.every((r:any)=>r.outcome==='not_observed'&&r.financial_outcome_paise===null)).toBe(true);
  await expect(region.getByText(/Retained recommendation observations/)).toBeVisible({timeout:180000});
  await region.getByText(/Retained recommendation observations/).click();
  await expect(region).toContainText('Financial outcome: Unknown');
  await expect(region).toContainText('not_observed');
  await expect(region.getByRole('table',{name:'Recommendation outcomes'})).toContainText('not_observed');
  await region.getByText(/Retained recommendation observations/).click();
  await region.screenshot({path:'../.runtime/real-decisions.png'});
});

test('actual stopped Exasol removes all current unified decisions',async({page})=>{
  test.skip(!process.env.E2E_OPERATOR_PASSWORD||process.env.E2E_DATABASE_FAILURE!=='1','Actual outage mode only');
  test.setTimeout(120000);
  await page.goto('/');await page.getByLabel('Operator password').fill(process.env.E2E_OPERATOR_PASSWORD!);
  await page.getByRole('button',{name:'Open workspace'}).click();
  const region=page.getByRole('region',{name:'Unified decisions',exact:true});
  await region.getByRole('button',{name:'Query decisions',exact:true}).click();
  await expect(region.getByRole('alert')).toContainText('Decisions Exasol unavailable',{timeout:90000});
  await expect(region.getByRole('table',{name:'Current unified decisions'})).toHaveCount(0);
  await expect(region.getByTestId('decisions-summary')).toHaveCount(0);
  await expect(region.getByRole('button',{name:'Record observation'})).toHaveCount(0);
  await region.screenshot({path:'../.runtime/real-decisions-outage.png'});
});
