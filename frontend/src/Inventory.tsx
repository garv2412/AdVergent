import { useEffect, useState } from 'react';
import type { components } from './api.generated';
type Snapshot = components['schemas']['InventorySnapshot'];
const value = (v: string | null) => v === null ? 'Unknown' : Number(v).toFixed(2);
export function Inventory({ api }: { api: (path: string) => Promise<any> }) {
  const [s,setS]=useState<Snapshot|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const load=async()=>{setS(null);setError('');setBusy(true);try{setS(await api('inventory'));}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
  useEffect(()=>{void load();},[]);
  const d=s?.data;
  return <section className="inventory commerce" aria-label="Inventory">
    <div className="section-heading"><div><p className="eyebrow">INVENTORY EVIDENCE</p><h2>Stock, demand and size readiness</h2></div><button disabled={busy} onClick={load}>{busy?'Querying inventory…':'Query inventory'}</button></div>
    <p>Simulated warehouse observations and real Exasol calculations. Every advertising recommendation requires explicit approval. No advertising changes can be executed here.</p>
    {error&&<div role="alert" className="error">{error}</div>}
    {s?.status==='not_loaded'&&<p>No inventory publication. Run the inventory worker.</p>}
    {s?.status==='analytics_unavailable'&&<div role="alert" className="error">Inventory Exasol unavailable. Current stock, risk and recommendations cannot be verified.</div>}
    {s?.latest_import_status==='failed'&&<div role="alert" className="error">Latest inventory import failed. Prior complete publication retained.</div>}
    {s?.dependencies_current===false&&<div role="alert" className="error">Pinned inputs changed. All inventory mutation eligibility is blocked.</div>}
    {d&&<>
      <p data-testid="inventory-reconciliation">Reconciled: {d.variants} variants · {d.sellable_units} sellable units · source freshness: {s!.freshness}</p>
      {s!.freshness==='stale'&&<div role="alert" className="error">Stale inventory blocks pause, throttle and recovery eligibility for affected products. Replaying never renews observations.</div>}
      <p>{d.demand_basis}. Sellable stock = available less separate merchant reserve, floored at zero. Commitments are already excluded from available.</p>
      <p>Zero observed demand, sparse demand and missing exposure leave cover uncertain. Receipts do not become current stock; only confirmed, fresh evidence arriving before depletion can bridge cover.</p>
      <div className="table-scroll"><table><thead><tr><th>Product</th><th>Sellable</th><th>Demand / day</th><th>Cover days</th><th>Lead days</th><th>Unavailable weight</th><th>Risk</th><th>Evidence</th></tr></thead><tbody>{d.products.map(p=><tr key={p.product_id}><td>{p.product_id}</td><td>{p.sellable_units}</td><td>{value(p.daily_velocity)}</td><td>{value(p.days_of_cover)}</td><td>{p.lead_days??'Unknown'}</td><td>{p.unavailable_weight_bps===null?'Unknown':`${(Number(p.unavailable_weight_bps)/100).toFixed(2)}%`}</td><td>{p.risk} · {p.suggested_action} advisory · approval required{p.uncertain?' · uncertain':''}</td><td><details><summary>{p.product_id} variant evidence</summary><p>Weights: {p.weight_source}. Lead: {p.lead_source}. Warning: {String(p.warning)}.</p>{p.variants.map((v:any)=><details key={v.variant_id}><summary>{v.variant_id} / {v.size} · {v.sellable_units} units · {v.days_of_cover===null?'Unknown cover':`${value(v.days_of_cover)} days`} · {v.demand_status}</summary><pre>{JSON.stringify(v,null,2)}</pre></details>)}</details></td></tr>)}</tbody></table></div>
      <h3>Approval-required inventory recommendations</h3><p>Exact reviewed resource scope only. Mixed-product resources with unsupported narrow controls remain advisory. Recovery additionally requires a recorded simulated AdVergent pause and cleared blocking conditions. Historical product contribution is an impact context, not incremental profit or a forecast.</p>
      {d.recommendations.filter(r=>r.action!=='none'||r.mapping.status!=='unmapped').map(r=><details key={`${r.platform}:${r.account_id}:${r.resource_id}`}><summary>{r.resource_id} · {r.action} · {r.eligibility} · approval required</summary><p>Affected products: {r.affected_products.join(', ')||'Unresolved'}. Blockers: {r.blockers.join('; ')||'None; explicit approval and future execution-time revalidation still required'}.</p><p>Historical impact: {r.impact.expected_contribution_paise===null?'Unknown — incomplete or absent costs':`${r.impact.expected_contribution_paise} paise`} · {r.impact.missing_lines} incomplete lines. Covered subtotal: {r.impact.covered_subtotal_paise} paise, excludes incomplete lines.</p><p>Daily contribution scenario: {r.impact.daily_contribution_context_paise===null?'Unknown':`${Number(r.impact.daily_contribution_context_paise).toFixed(2)} paise/day`}. {r.impact.scenario_assumption}</p><pre>{JSON.stringify(r,null,2)}</pre></details>)}
      <details><summary>Inventory implementation assumptions</summary><pre>{JSON.stringify(d.assumptions,null,2)}</pre></details>
    </>}
    {s?.dataset_id&&<aside><h3>Inventory evidence</h3><dl><div><dt>Dataset / version</dt><dd>{s.dataset_id} / {s.dataset_version}</dd></div><div><dt>Finance / attribution / commerce / ads</dt><dd>{s.finance_id} / {s.attribution_id} / {s.commerce_id} / {s.ads_id}</dd></div><div><dt>Fixture SHA-256</dt><dd>{s.fixture_hash}</dd></div><div><dt>Oldest stock observation</dt><dd>{s.observed_at}</dd></div><div><dt>Published</dt><dd>{s.published_at}</dd></div><div><dt>Queried (UTC)</dt><dd>{s.queried_at??'Query unavailable'}</dd></div></dl></aside>}
  </section>;
}
