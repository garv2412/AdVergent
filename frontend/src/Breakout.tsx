import {useEffect,useState} from 'react';
import type {components} from './api.generated';
type Snapshot=components['schemas']['BreakoutSnapshot'];
export function Breakout({api}:{api:(path:string,body?:object)=>Promise<any>}) {
  const [s,setS]=useState<Snapshot|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const load=async()=>{setS(null);setError('');setBusy(true);try{setS(await api('breakout'));}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
  useEffect(()=>{void load();},[]);
  const d=s?.data;
  return <section className="commerce breakout" aria-label="Breakout">
    <div className="section-heading"><div><p className="eyebrow">SYNTHETIC BREAKOUT</p><h2>Signals before scale</h2></div><button disabled={busy} onClick={()=>void load()}>{busy?'Evaluating breakout…':'Query breakout'}</button></div>
    <p>Descriptive evidence only. Sparse or stale observations abstain. No high-confidence prediction, precise budget forecast or publishing.</p>
    {error&&<div role="alert" className="error">{error}</div>}
    {s?.status==='not_loaded'&&<p>Breakout requires coherent published commerce, ads, finance and inventory.</p>}
    {s?.status==='analytics_unavailable'&&<div role="alert" className="error">Breakout Exasol unavailable. Current signals and ranking cannot be verified.</div>}
    {d&&<>
      <p data-testid="breakout-summary">{d.ranking.filter(r=>r.rank!==null).length} ranked · {d.duplicate_events} duplicate deliveries removed · added revenue ₹0.00 · publishing disabled</p>
      <p>{d.basis}</p>
      <p>Signal cutoff UTC: {d.signal_end}. Separate later evaluation ends {d.evaluation_end}. Current inventory and historical margin are context, not a historical portfolio backtest.</p>
      <div className="table-scroll"><table><thead><tr><th>Product / rank</th><th>Views / carts</th><th>Coverage days</th><th>Growth / cart rate / CTR (bps)</th><th>Historical margin (bps)</th><th>Inventory</th><th>Score / blockers</th><th>Later evaluation</th></tr></thead><tbody>{d.ranking.map(r=><tr key={r.product_id} data-testid={`breakout-${r.product_id}`}><td>{r.product_id} / {r.rank??'Abstain'}</td><td>{r.counts.signal.view} / {r.counts.signal.cart}</td><td>{r.tracked_days.baseline} / {r.tracked_days.signal}</td><td>{r.view_growth_bps??'Unknown'} / {r.cart_rate_bps??'Unknown'} / {r.ctr_bps??'Unknown'}</td><td>{r.historical_margin_bps??'Unknown'}</td><td>{r.inventory_risk}</td><td>{r.score??'Unranked'} · {r.blockers.join('; ')}</td><td>{r.evaluation}</td></tr>)}</tbody></table></div>
      <details><summary>Funnel source and evaluation evidence</summary><pre>{JSON.stringify(d,null,2)}</pre></details>
    </>}
    {s&&<aside><h3>Breakout evidence</h3><p>Queried UTC: {s.queried_at??'Query unavailable'} · dependencies current: {String(s.dependencies_current)}</p><pre>{JSON.stringify({pins:s.pins,input_observations:s.input_observations,source_hash:d?.source_hash,source_observed_at:d?.source_observed_at},null,2)}</pre></aside>}
  </section>;
}
