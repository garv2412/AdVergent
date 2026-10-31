import {useEffect,useState} from 'react';
import type {components} from './api.generated';
type Snapshot=components['schemas']['DecisionSnapshot'];
type History=components['schemas']['DecisionHistory'];
export function Decisions({api}:{api:(path:string,body?:object)=>Promise<any>}) {
  const [s,setS]=useState<Snapshot|null>(null),[history,setHistory]=useState<History|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const [links,setLinks]=useState<Record<string,string>>({});
  useEffect(()=>{const deadline=s?.data?.valid_until;if(!deadline)return;let timer:number|undefined;const check=()=>{const remaining=Date.parse(deadline)-Date.now();if(!Number.isFinite(remaining)||remaining<=0){setS(null);setError('Decision evidence expired. Query again.');}else{timer=window.setTimeout(check,Math.min(remaining,60000));}};check();return()=>window.clearTimeout(timer);},[s]);
  const load=async()=>{setS(null);setHistory(null);setError('');setBusy(true);try{setS(await api('decisions'));setHistory(await api('decisions/history'));}catch(e){setS(null);setError((e as Error).message);}finally{setBusy(false);}};
  const track=async(key:string)=>{if(!s?.data)return;setError('');setBusy(true);try{setHistory(await api('decisions/track',{digest:s.data.digest,key}));}catch(e){setS(null);setError((e as Error).message);}finally{setBusy(false);}};
  const link=async(o:History['observations'][number])=>{setError('');setBusy(true);try{setHistory(await api('decisions/track',{digest:o.digest,key:o.resource_key,action_id:links[o.digest+o.resource_key]}));}catch(e){setS(null);setError((e as Error).message);}finally{setBusy(false);}};
  return <section className="commerce breakout" aria-label="Unified decisions">
    <div className="section-heading"><div><p className="eyebrow">EVIDENCE AND CONFLICTS</p><h2>One coherent decision per resource</h2></div><button disabled={busy} onClick={()=>void load()}>{busy?'Querying decisions…':'Query decisions'}</button></div>
    <p>Inventory protection takes precedence. Exact scope, fixed budget bounds and abstention remain in force. No publishing or advertising changes; every future mutation requires separate exact explicit approval.</p>
    {error&&<div role="alert" className="error">{error}</div>}
    {s&&s.status!=='available'&&<div role="alert" className="error">{s.status==='analytics_unavailable'?'Decisions Exasol unavailable. Current decisions cannot be verified.':s.status==='inputs_changed'?'Decision inputs, state or evidence time changed. Query again.':'Coherent evidence is not loaded.'}</div>}
    {s?.data&&<>
      <p data-testid="decisions-summary">{s.data.decisions.length} resource decisions · Fixed total {String(s.data.budget.total_paise)} paise · Allocated {String(s.data.budget.allocated_total_paise)} paise</p>
      <p>{s.data.basis} Frozen unsafe baselines do not endorse continued spending.</p>
      <div className="table-scroll"><table aria-label="Current unified decisions"><thead><tr><th>Exact resource</th><th>Decision</th><th>Scope</th><th>Evidence and conflicts</th><th>Observation</th></tr></thead><tbody>{s.data.decisions.map(r=><tr key={r.key}><td>{r.platform} / {r.resource_id}<br/>{r.resource_kind}</td><td>{r.advice}</td><td>{r.products.join(', ')||'Unresolved'}<br/>{r.members.join(', ')}</td><td>{r.explanation}<details><summary>{r.blockers.length} blockers / {r.suppressed.length} suppressed alternatives</summary><p>{r.blockers.join('; ')}</p><p>{r.suppressed.join('; ')}</p><pre>{JSON.stringify(r.evidence,null,2)}</pre></details></td><td><button disabled={busy} onClick={()=>void track(r.key)}>Record observation</button></td></tr>)}</tbody></table></div>
      <details><summary>Separate context and proposal validity</summary><pre>{JSON.stringify({context:s.data.context,proposals:s.data.proposal_validity,tracked:s.data.tracked_validity},null,2)}</pre></details>
      <aside><h3>Decision query evidence</h3><p>Queried UTC: {s.queried_at} · Valid until: {s.data.valid_until??'No future evidence boundary'}</p><pre>{JSON.stringify({pins:s.pins,observations:s.input_observations,digest:s.data.digest},null,2)}</pre></aside>
    </>}
    {history&&<details><summary>Retained recommendation observations ({history.observations.length})</summary><p>Without an explicit exact action link, outcome is not_observed. Action status and read-back do not establish financial benefit. Financial outcome: Unknown. Historical records remain audit evidence, not current advice.</p>
      <div className="table-scroll"><table aria-label="Recommendation outcomes"><thead><tr><th>Observation</th><th>Validity</th><th>Recorded outcome</th><th>Existing action association</th></tr></thead><tbody>{history.observations.map(o=><tr key={o.digest+o.resource_key}><td>{o.resource_key}<br/>{o.recorded_at} · {o.recorded_by}</td><td>{String(s?.data?.tracked_validity?.find(v=>v.digest===o.digest&&v.key===o.resource_key)?.validity??'Unknown until current query')}</td><td>{o.outcome}<br/>Financial effect: Unknown</td><td>{o.action_id?<>{o.action_id}<br/>Linked {o.linked_at}</>:<form onSubmit={e=>{e.preventDefault();void link(o);}}><label>Existing action ID<input aria-label={'Existing action ID for '+o.resource_key} required pattern="[a-fA-F0-9-]{36}" value={links[o.digest+o.resource_key]??''} onChange={e=>setLinks({...links,[o.digest+o.resource_key]:e.target.value})}/></label><button disabled={busy}>Link existing action</button></form>}</td></tr>)}</tbody></table></div>
      <p>Linking requires an action proposed after this observation with matching exact terms and evidence. Linking creates no proposal, approval or advertising change.</p><details><summary>Retained snapshots and action read-back</summary><pre>{JSON.stringify(history,null,2)}</pre></details>
    </details>}
  </section>;
}
