import { useEffect,useState } from 'react';
import type { components } from './api.generated';
type Snapshot=components['schemas']['DiagnosticsSnapshot'];
export function Diagnostics({api}:{api:(path:string)=>Promise<any>}){
  const [s,setS]=useState<Snapshot|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const load=async()=>{setS(null);setError('');setBusy(true);try{setS(await api('diagnostics'));}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
  useEffect(()=>{void load();},[]);
  return <section className="commerce" aria-label="Diagnostics">
    <div className="section-heading"><div><p className="eyebrow">DIAGNOSTIC EVIDENCE</p><h2>Destinations, prices and creative review</h2></div><button disabled={busy} onClick={load}>{busy?'Querying diagnostics…':'Query diagnostics'}</button></div>
    <p>Fixture observations only. No crawling. All suggestions are advisory and approval-required; advertising mutations are disabled. Catalog and page text are untrusted evidence.</p>
    {error&&<div role="alert" className="error">{error}</div>}
    {s?.status==='not_loaded'&&<p>No diagnostics publication. Run the diagnostics worker.</p>}
    {s?.status==='analytics_unavailable'&&<div role="alert" className="error">Diagnostics Exasol unavailable. Current checks and suggestions cannot be verified.</div>}
    {s?.latest_import_status==='failed'&&<div role="alert" className="error">Latest diagnostics import failed. Prior complete publication retained.</div>}
    {s?.dependencies_current===false&&<div role="alert" className="error">Pinned inputs changed. Suggestions are withheld.</div>}
    {s?.data&&<><p data-testid="diagnostics-summary">{s.data.recommendations.length} resource reviews · source freshness: {s.freshness}</p><p>{s.data.basis}</p>
      {s.freshness==='stale'&&<div role="alert" className="error">Stale diagnostic observations. Replay never renews source evidence.</div>}
      {s.data.recommendations.map((r:any)=><article key={`${r.platform}:${r.account_id}:${r.resource_id}`}><h3>{r.resource_id} · advisory · approval required</h3>
        <p>Reviewed products: {r.mapping.products.join(', ')||'Unresolved'}. Blockers: {r.blockers.join('; ')||'None; review and approval still required'}.</p>
        <div className="table-scroll"><table><thead><tr><th>Variant</th><th>Destination</th><th>Price</th><th>Catalog paise</th></tr></thead><tbody>{r.destinations.map((d:any)=><tr key={`${d.variant_id}:${d.url}`}><td>{d.variant_id}</td><td>{d.status}</td><td>{d.price_status}</td><td>{d.catalog_price_paise}</td></tr>)}</tbody></table></div>
        {r.fatigue.map((f:any)=><p key={f.creative_id}>{f.creative_id}: {f.status} · prior CTR {f.prior_ctr??'Unknown'} / current {f.current_ctr??'Unknown'}. {f.interpretation}</p>)}
        {r.suggestions.map((c:any)=><p key={c.product_id}>{c.product_id}: {c.text} Sizes: {c.facts.sizes.join(', ')}. Colors: {c.facts.colors.join(', ')}. {c.basis}</p>)}
        <details><summary>{r.resource_id} supporting evidence</summary><pre>{JSON.stringify(r,null,2)}</pre></details>
      </article>)}
      <details><summary>Diagnostic assumptions and SQL evidence</summary><pre>{JSON.stringify({...s.data,recommendations:undefined},null,2)}</pre></details>
    </>}
    {s?.dataset_id&&<aside><h3>Diagnostics evidence</h3><p>Dataset: {s.dataset_id} / {s.dataset_version}</p><p>Inventory: {s.inventory_id}</p><p>SHA-256: {s.fixture_hash}</p><p>Observed: {s.observed_at} · Published: {s.published_at}</p><p>Queried: {s.queried_at??'Query unavailable'}</p></aside>}
  </section>;
}
