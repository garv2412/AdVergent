import {useEffect,useState} from 'react';
import type {components} from './api.generated';
type Snapshot=components['schemas']['ClearanceSnapshot'];
type Terms=components['schemas']['ClearanceRequest'];
const money=(p:number|null)=>p===null?'Unknown':new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format(p/100);
export function Clearance({api}:{api:(path:string,body?:object)=>Promise<any>}) {
  const [s,setS]=useState<Snapshot|null>(null),[terms,setTerms]=useState<Terms|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const load=async(body?:Terms)=>{setS(null);setError('');setBusy(true);try{const result:Snapshot=await api(body?'clearance/scenario':'clearance',body);setS(result);if(result.data)setTerms(result.data.assumptions);}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
  useEffect(()=>{void load();},[]);
  const d=s?.data;
  const fields:[keyof Terms,string][]=[['baseline_bundles','No-action bundles sold'],['scenario_bundles','Scenario bundles sold'],['markdown_bps','Markdown (basis points)'],['additional_spend_paise','Additional spend (INR paise)'],['horizon_days','Horizon days'],['assumed_stock_age_days','Assumed stock age days'],['deadstock_age_days','Deadstock age threshold days'],['holding_paise_per_unit_day','Holding cost (paise / unsold unit / day)'],['variable_paise_per_unit','Variable cost (paise / sold unit)'],['return_loss_paise_per_unit','Expected return loss (paise / sold unit)'],['min_contribution_paise','Minimum contribution (paise)'],['min_margin_bps','Minimum margin (basis points)']];
  return <section className="commerce clearance" aria-label="Clearance">
    <div className="section-heading"><div><p className="eyebrow">SYNTHETIC CLEARANCE</p><h2>Deadstock and scenario comparison</h2></div><button disabled={busy} onClick={()=>void load()}>{busy?'Calculating clearance…':'Query clearance'}</button></div>
    <p>Read-only what-if. No discount, bundle, campaign or advertising change can be published here. Revenue differs from contribution. Sales response and stock age are uncalibrated assumptions.</p>
    {error&&<div role="alert" className="error">{error}</div>}
    {s?.status==='not_loaded'&&<p>Clearance requires published inventory and finance inputs.</p>}
    {s?.status==='analytics_unavailable'&&<div role="alert" className="error">Clearance Exasol unavailable. Current ranking and comparisons cannot be verified.</div>}
    {terms&&<form onSubmit={e=>{e.preventDefault();void load(terms);}} aria-label="Clearance assumptions">
      <p>Each row below is one bundle component; units are required per bundle. Duplicate variant IDs reject. Baseline uses the same mix at full price with zero additional spend. Empty cost fields mean unknown.</p>
      {terms.components!.map((c,i)=><div key={i}><label>Variant ID {i+1}<input required maxLength={100} value={c.variant_id} onChange={e=>setTerms({...terms,components:terms.components!.map((r,j)=>j===i?{...r,variant_id:e.target.value}:r)})}/></label><label>Units per bundle {i+1}<input type="number" required min={1} max={1000} value={c.units_per_bundle??1} onChange={e=>setTerms({...terms,components:terms.components!.map((r,j)=>j===i?{...r,units_per_bundle:Number(e.target.value)}:r)})}/></label>{terms.components!.length>1&&<button type="button" onClick={()=>setTerms({...terms,components:terms.components!.filter((_,j)=>j!==i)})}>Remove component {i+1}</button>}</div>)}
      <button type="button" disabled={terms.components!.length>=20} onClick={()=>setTerms({...terms,components:[...terms.components!,{variant_id:'',units_per_bundle:1}]})}>Add bundle component</button>
      {fields.map(([key,label])=><label key={key}>{label}<input type="number" min={key==='horizon_days'?1:0} step={1} required={!['holding_paise_per_unit_day','variable_paise_per_unit','return_loss_paise_per_unit'].includes(key)} value={(terms[key] as number|null)??''} onChange={e=>setTerms({...terms,[key]:e.target.value===''?null:Number(e.target.value)})}/></label>)}
      <button disabled={busy}>Compare scenario</button>
    </form>}
    {d&&<>
      {d.evidence_blockers.length>0&&<div className="error" role="alert">Evidence blockers: {d.evidence_blockers.join('; ')}. Historical comparison only.</div>}
      <p data-testid="clearance-summary">{d.ranking.length} variants ranked · scenario {d.scenario.limits_pass?'passes arithmetic limits':'fails limits'} · {d.feasible?'evidence sufficient for this synthetic comparison':'not feasible with current evidence'} · publishing disabled</p>
      <div className="table-scroll"><table><thead><tr><th>Alternative</th><th>Units</th><th>Revenue</th><th>Expected contribution after additional spend and holding</th><th>Margin</th><th>COGS unit coverage</th><th>Limits</th></tr></thead><tbody>{(['baseline','scenario'] as const).map(k=>{const r=d[k];return <tr key={k}><td>{k==='baseline'?'No action': 'Configured scenario'}</td><td>{r.units}</td><td>{money(r.revenue_paise)}</td><td>{money(r.expected_contribution_paise)}</td><td>{r.margin_bps===null?'Undefined':`${(Number(r.margin_bps)/100).toFixed(2)}%`}</td><td>{r.cost_coverage_bps/100}%</td><td>{r.blockers.join('; ')||'Pass'}</td></tr>;})}</tbody></table></div>
      <p data-testid="clearance-deltas">Revenue change {money(d.revenue_delta_paise)} · contribution change {money(d.contribution_delta_paise)}. A higher revenue can lose contribution.</p>
      <p>{d.basis}</p>
      <details><summary>Selected stock and cost evidence</summary><pre>{JSON.stringify({selected:d.selected,baseline:d.baseline,scenario:d.scenario,assumptions:d.assumptions},null,2)}</pre></details>
      <h3>Deadstock ranking</h3><p>Score = assumed age × stock above horizon demand, using sufficient exposure-based rates. Unknown demand remains unranked. Candidates require the configured age threshold and positive excess. Stale observations remain labelled.</p>
      <div className="table-scroll"><table><thead><tr><th>Variant / product</th><th>Sellable</th><th>Excess units</th><th>Age × excess</th><th>Candidate</th><th>Evidence</th></tr></thead><tbody>{d.ranking.map(r=><tr key={r.variant_id}><td>{r.variant_id} / {r.product_id}</td><td>{r.sellable_units}</td><td>{r.excess_units??'Unknown'}</td><td>{r.age_excess_score??'Unknown'}</td><td>{r.deadstock_candidate===null?'Uncertain':String(r.deadstock_candidate)}</td><td>{r.fresh?'Fresh':'Stale'} · {r.demand_status} · COGS {r.cost_status}</td></tr>)}</tbody></table></div>
    </>}
    {s&&<aside><h3>Clearance evidence</h3><p>Stock source observation: {s.observed_at??'Unavailable'} · Queried UTC: {s.queried_at??'Query unavailable'} · dependencies current: {String(s.dependencies_current)}</p><pre>{JSON.stringify({pins:s.pins,input_observations:s.input_observations},null,2)}</pre></aside>}
  </section>;
}
