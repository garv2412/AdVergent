import { useEffect, useState } from 'react';
import type { components } from './api.generated';
type Snapshot = components['schemas']['AttributionSnapshot'];
const money = (n: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(n / 100);
export function Attribution({ api }: { api: (path: string) => Promise<any> }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function load() {
    setSnapshot(null); setError(''); setBusy(true);
    try { setSnapshot(await api('attribution')); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  useEffect(() => { void load(); }, []);
  const data = snapshot?.data;
  return <section className="commerce" aria-label="Mapping and attribution">
    <div className="section-heading"><h2>Mapping and attribution</h2><button onClick={load} disabled={busy}>{busy ? 'Querying…' : 'Query attribution'}</button></div>
    <p>First-party last identifiable paid click within seven days, including the boundary. No view-through. Attribution describes association; it does not prove incremental profit.</p>
    <p>Placed merchandise excludes tax and precedes refunds and delivery recognition. Contribution accounting follows in Phase 5.</p>
    {error && <p role="alert">{error}</p>}
    {snapshot?.status === 'not_loaded' && <p role="status">No attribution publication. Run the attribution worker.</p>}
    {snapshot?.status === 'analytics_unavailable' && <p role="alert">Attribution Exasol unavailable. Current mappings and allocations cannot be verified.</p>}
    {snapshot?.latest_import_status === 'failed' && <p className="error" role="alert">Latest attribution import failed. Prior complete publication retained.</p>}
    {snapshot?.dependencies_current === false && <p role="status">Upstream publications changed. This attribution retains its pinned historical inputs; refresh attribution to use the current inputs.</p>}
    {data && <>
      <p role="status">Attribution freshness: {snapshot?.freshness}. Source age: {snapshot?.age_seconds} seconds.</p>
      <p data-testid="allocation-reconciliation">Reconciled: {data.reconciliation.orders} orders · {data.reconciliation.lines} lines · {money(data.reconciliation.placed_merchandise_paise)} placed merchandise · {data.reconciliation.refunds} refund links</p>
      <h3>First-party allocation</h3><div className="table-scroll"><table><thead><tr><th>Platform / account / campaign</th><th>Orders</th><th>Lines</th><th>Placed merchandise</th></tr></thead><tbody>{data.groups.map((g, i) => <tr key={i}><td>{g.campaign_id ? `${g.platform} / ${g.account_id} / ${g.campaign_id}` : 'Unattributed'}</td><td>{g.orders}</td><td>{g.lines}</td><td>{money(g.placed_merchandise_paise)}</td></tr>)}</tbody></table></div>
      <h3>Product/ad relationships</h3><p>Native product references remain unverified hints. Reviewed sets apply only to their exact resource and validity interval. Multiple products never imply a narrow advertising control. Mapping evaluation time: {snapshot?.mapping_as_of}.</p>
      <div className="table-scroll"><table><thead><tr><th>Resource identity</th><th>Decision</th><th>Product set</th><th>Evidence</th></tr></thead><tbody>{data.mappings.map(m => <tr key={`${m.platform}:${m.account_id}:${m.resource_id}`}><td>{m.platform} / {m.account_id} / {m.resource_id}</td><td>{m.status}{m.override ? ' · explicit override' : ''}</td><td>{m.products.join(', ') || 'Abstain'}</td><td>{m.evidence_ids.join(', ') || 'No reviewed evidence'}</td></tr>)}</tbody></table></div>
      <details><summary>Mapping provenance, confidence and validity</summary>{data.mapping_evidence.map(m => <article key={m.id}><h4>{m.id} · {m.resource_id}</h4><p>{m.products.join(', ')} · {m.confidence_bps / 100}% confidence · {m.override ? 'Override' : 'Candidate'}</p><p>{m.provenance} · {m.actor} · {m.reason}</p><p>Valid from {m.valid_from} until {m.valid_to} (exclusive)</p></article>)}</details>
      <details><summary>First-party order evidence</summary><p>Each order has exactly one campaign or the unattributed bucket. Latest-time ties across campaigns abstain. No click is inferred from product mappings.</p><div className="table-scroll"><table><thead><tr><th>Order</th><th>Campaign</th><th>Reason</th><th>Click evidence</th></tr></thead><tbody>{data.assignments.filter(a => a.click_ids.length || a.order_id === 'o2').map(a => <tr key={a.order_id}><td>{a.order_id}</td><td>{a.campaign_id || 'Unattributed'}</td><td>{a.reason}</td><td>{a.click_ids.join(', ')}</td></tr>)}</tbody></table></div><p>Remaining orders have no eligible click and remain unattributed.</p></details>
      <details><summary>Purchased product allocations</summary><div className="table-scroll"><table><thead><tr><th>Campaign</th><th>Purchased product</th><th>Lines</th><th>Placed merchandise</th></tr></thead><tbody>{data.product_allocations.map((r, i) => <tr key={i}><td>{r.campaign_id || 'Unattributed'}</td><td>{r.product_id}</td><td>{r.lines}</td><td>{money(r.placed_merchandise_paise)}</td></tr>)}</tbody></table></div></details>
      <details><summary>Platform-reported claims — separate view</summary><p>Synthetic platform claims may overlap. They never enter first-party allocation or store totals.</p>{data.platform_claims.map(c => <p key={c.id}>{c.platform} / {c.account_id} / {c.resource_id} · order {c.order_id} · reported {money(c.reported_value_paise)}</p>)}</details>
    </>}
    {snapshot?.dataset_id && <aside><h3>Attribution query evidence</h3><dl>{Object.entries({ Model: snapshot.model, Dataset: snapshot.dataset_id, Version: snapshot.dataset_version, 'Fixture SHA-256': snapshot.fixture_hash, 'Commerce input': snapshot.commerce_id, 'Ads input': snapshot.ads_id, 'Source observation': snapshot.observed_at, Published: snapshot.published_at, 'Queried (UTC)': snapshot.queried_at ?? 'Query unavailable' }).map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl></aside>}
  </section>;
}
