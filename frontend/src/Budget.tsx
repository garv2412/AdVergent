import {useState} from 'react';
import type {components} from './api.generated';
type Snapshot=components['schemas']['BudgetSnapshot'];
const money=(v:number|null)=>v===null?'Unknown':new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format(v/100);
export function Budget({api}:{api:(path:string,body?:object)=>Promise<any>}) {
  const [s,setS]=useState<Snapshot|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const [bound,setBound]=useState('1000'),[total,setTotal]=useState('');
  const load=async(scenario=false)=>{setS(null);setError('');setBusy(true);try{
    setS(await api(scenario?'budget/scenario':'budget',scenario?{change_bps:Number(bound),total_paise:total===''?null:Number(total)}:undefined));
  }catch(e){setError((e as Error).message);}finally{setBusy(false);}};
  const d=s?.data;
  return <section className="commerce breakout" aria-label="Budget optimization">
    <div className="section-heading"><div><p className="eyebrow">CONSERVATIVE SYNTHETIC SCENARIOS</p><h2>Allocate within the evidence</h2></div><button disabled={busy} onClick={()=>void load()}>{busy?'Querying budget…':'Query budget'}</button></div>
    <p>Fixed daily INR total · maximum 10% change per budget · inventory takes precedence. No publishing or advertising changes. Every future mutation needs separate exact explicit approval.</p>
    {!s&&!busy&&!error&&<p>Query budget to inspect current evidence and compare the fixed allocation.</p>}
    <form onSubmit={e=>{e.preventDefault();void load(true);}}>
      <label>Maximum change (basis points, 1000 = 10%)<input type="number" min="0" max="1000" step="1" required value={bound} onChange={e=>setBound(e.target.value)}/></label>
      <label>Fixed total (integer paise; blank uses existing total)<input type="number" min="0" max="10000000000000" step="1" value={total} onChange={e=>setTotal(e.target.value)}/></label>
      <button disabled={busy}>Compare allocation</button>
    </form>
    {error&&<div role="alert" className="error">{error}</div>}
    {s?.status==='not_loaded'&&<p>Coherent finance, inventory and diagnostic evidence is required.</p>}
    {s?.status==='inputs_changed'&&<div role="alert" className="error">Budget inputs, state or evidence time changed. Query again.</div>}
    {s?.status==='analytics_unavailable'&&<div role="alert" className="error">Budget Exasol unavailable. Current allocations and response evidence cannot be verified.</div>}
    {d&&<>
      <p data-testid="budget-summary">{d.status} · Requested fixed total {money(d.terms.total_paise??d.total_paise)} · Existing {money(d.total_paise)} · Allocated {money(d.allocated_total_paise)} · Applied change bound {d.terms.change_bps??1000} basis points · Conservative scenario delta (exact paise): {d.conservative_delta_paise??'Unknown / abstained'}</p>
      <p>{d.blockers.join('; ')}. Frozen unsafe budgets retain the baseline for comparison; this does not endorse continued spending. Review inventory protection separately.</p>
      <p>{d.basis} Full portfolio contribution after ads: Unknown.</p>
      <div className="table-scroll"><table><thead><tr><th>Budget / whole scope</th><th>Baseline INR</th><th>Allocation INR</th><th>Bounds INR</th><th>Response sensitivity</th><th>Abstention / blockers</th></tr></thead><tbody>{d.rows.map(r=><tr key={r.key}><td>{r.platform} / {r.budget_id}<br/>{r.shared?'Shared · ':''}{r.members.join(', ')}<br/>{r.products.join(', ')}</td><td>{money(r.current_paise)}</td><td>{money(r.allocated_paise)}</td><td>{money(r.minimum_paise)}–{money(r.maximum_paise)}</td><td>{r.response.status} · {r.response.days} {r.response.days===1?'day':'days'} / {r.response.spend_levels} {r.response.spend_levels===1?'level':'levels'}<br/>{r.response.lower_slope??'Unknown'} to {r.response.upper_slope??'Unknown'}</td><td>{r.blockers.length?<>{r.blockers.find(b=>b.startsWith('inventory '))??r.blockers.find(b=>b.startsWith('exact reviewed'))??r.blockers[0]}<details><summary>{r.blockers.length} blockers and abstention reasons</summary><p>{r.blockers.join('; ')}</p></details></>:'Supported descriptive scenario only'}</td></tr>)}</tbody></table></div>
      <p>Separate cohort context: history incomplete. Mature and immature 60/90-day windows and missing costs remain separate; no cohort multiplier enters this allocation.</p>
      <details><summary>Response observations, terms and cohort coverage</summary><pre>{JSON.stringify(d,null,2)}</pre></details>
    </>}
    {s&&<aside><h3>Budget query evidence</h3><p>Queried UTC: {s.queried_at??'Query unavailable'} · dependencies current: {String(s.dependencies_current)}</p><pre>{JSON.stringify({pins:s.pins,input_observations:s.input_observations},null,2)}</pre></aside>}
  </section>;
}
