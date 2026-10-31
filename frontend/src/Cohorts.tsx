import {useEffect,useState} from 'react';
import type {components} from './api.generated';
type Snapshot=components['schemas']['CohortSnapshot'];
const money=(v:number|null)=>v===null?'Unknown':new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format(v/100);
export function Cohorts({api}:{api:(path:string)=>Promise<any>}) {
  const [s,setS]=useState<Snapshot|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const load=async()=>{setS(null);setError('');setBusy(true);try{setS(await api('cohorts'));}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
  useEffect(()=>{void load();},[]);
  const d=s?.data;
  return <section className="commerce breakout" aria-label="Cohorts">
    <div className="section-heading"><div><p className="eyebrow">SYNTHETIC CUSTOMER COHORTS</p><h2>Contribution after the first delivery</h2></div><button disabled={busy} onClick={()=>void load()}>{busy?'Querying cohorts…':'Query cohorts'}</button></div>
    <p>First observed purchase · incomplete history · realized contribution before ads. Descriptive evidence, not calibrated LTV or incremental profit. Publishing disabled.</p>
    {error&&<div role="alert" className="error">{error}</div>}
    {s?.status==='not_loaded'&&<p>Publish coherent commerce, attribution and finance inputs to view cohorts.</p>}
    {s?.status==='inputs_changed'&&<div role="alert" className="error">Cohort inputs changed. Query again after coherent sources are restored.</div>}
    {s?.status==='analytics_unavailable'&&<div role="alert" className="error">Cohorts Exasol unavailable. Current cohort contribution cannot be verified.</div>}
    {d&&<>
      <p data-testid="cohort-summary">{d.customers.length} assigned customers · {d.customers_without_delivery} ordering customers without observed delivery · {d.zero_value_unassigned} zero-value unassigned. History incomplete.</p>
      <p>Observed through UTC {d.cutoff}; available financial history begins {d.history_start}. Windows are half-open 60/90 days from first delivery. Later refunds do not rewrite an earlier window. Acquisition expenses before delivery are included once.</p>
      {[true,false].map(mature=><div key={String(mature)} data-testid={mature?'cohort-mature':'cohort-immature'}><h3>{mature?'Mature windows':'Immature windows — partial contribution'}</h3><div className="table-scroll"><table><thead><tr><th>Acquisition month / product</th><th>Days</th><th>Exact customer weight</th><th>Missing / customers</th><th>Full contribution before ads</th><th>Known customer subtotal</th></tr></thead><tbody>{d.buckets.filter(b=>b.mature===mature).map(b=><tr key={`${b.acquisition_month}-${b.product_id}-${b.days}`}><td>{b.acquisition_month} / {b.product_id}</td><td>{b.days}</td><td>{b.customer_weight}</td><td>{b.missing_customers} / {b.customers}</td><td>{money(b.contribution_before_ads_paise)}</td><td>{money(b.known_customer_contribution_paise)}</td></tr>)}</tbody></table></div></div>)}
      <p>Known customer subtotals exclude incomplete customers and are not full estimates or bounds. Product fractions sum to one per assigned customer; customer totals allocate exact paise. Mature and immature rows must be compared separately.</p>
      <details><summary>Customer assignments, event coverage and source evidence</summary><pre>{JSON.stringify(d,null,2)}</pre></details>
    </>}
    {s&&<aside><h3>Cohort query evidence</h3><p>Queried UTC: {s.queried_at??'Query unavailable'} · dependencies current: {String(s.dependencies_current)}</p><pre>{JSON.stringify({pins:s.pins,input_observations:s.input_observations},null,2)}</pre></aside>}
  </section>;
}
