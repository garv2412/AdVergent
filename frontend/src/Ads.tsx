import React, { useEffect, useState } from 'react';
import type { components } from './api.generated';

type Snapshot = components['schemas']['AdSnapshot'];
const money = (paise: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(paise / 100);

export function Ads({ api }: { api: (path: string) => Promise<any> }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setSnapshot(null); setError(''); setBusy(true);
    api('ads').then((value: Snapshot) => { if (active) setSnapshot(value); }).catch(e => { if (active) setError(e.message); }).finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [api, revision]);
  const data = snapshot?.data;
  return <section className="commerce" aria-label="Ad reporting">
    <div className="section-heading"><div><p className="eyebrow">SYNTHETIC META / GOOGLE</p><h2>Ad reporting</h2></div><button disabled={busy} onClick={() => setRevision(x => x + 1)}>Query ad reports</button></div>
    <p>Real Exasol spend queries · INR · reporting day in Asia/Kolkata. Source simulations implement application contracts; live API compatibility is unverified.</p>
    <p>This reporting snapshot is read-only. Simulated changes require separate explicit approval in Approved execution. Native product references here are unverified hints; reviewed mappings and attribution are shown separately.</p>
    {error && <div role="alert" className="error">{error}</div>}
    {snapshot?.status === 'not_loaded' && <div className="empty">No ad publication. Run the ads import worker.</div>}
    {snapshot?.status === 'analytics_unavailable' && <div role="alert" className="error">Ad reporting Exasol unavailable. Current spend and hierarchy cannot be verified.</div>}
    {snapshot?.latest_import_status === 'failed' && <div className="error">Latest ad import failed. Prior complete publication retained.</div>}
    {snapshot?.status === 'available' && data && <>
      <div role="status" className={snapshot.freshness === 'stale' ? 'error' : 'notice'}>Ad freshness: {snapshot.freshness} · source observed {snapshot.observed_at} · {snapshot.age_seconds} seconds old (limit {snapshot.freshness_limit_seconds}s). Replay preserves source time.</div>
      <div className="cards"><article><span>Reported ad spend · INR</span><strong data-testid="ad-spend">{money(data.spend_paise)}</strong><small>{data.report_count} additive half-hour reports; latest revision per grain</small></article><article><span>Resources</span><strong>{data.resources.length}</strong><small>{data.accounts.length} synthetic accounts · {data.budgets.length} distinct budgets</small></article></div>
      <h3>Spend by campaign and reporting day</h3>
      <div className="table-scroll"><table><thead><tr><th>Day · Asia/Kolkata</th><th>Platform / campaign</th><th>Budget</th><th>Reports</th><th>INR spend</th></tr></thead><tbody>{data.groups.map(g => <tr key={`${g.platform}:${g.account_id}:${g.reporting_day}:${g.campaign_id}:${g.budget_id}`}><td>{g.reporting_day}</td><td>{g.platform} / {g.campaign_id}</td><td>{g.budget_id}</td><td>{g.report_count}</td><td>{money(g.spend_paise)}</td></tr>)}</tbody></table></div>
      <h3>Source accounts</h3><ul>{data.accounts.map(a => <li key={`${a.platform}:${a.id}`}>{a.platform} / {a.id}: {a.currency}, source timezone {a.timezone}</li>)}</ul>
      <h3>Budget ownership and shared impact</h3>
      {data.budgets.map(b => <details key={`${b.platform}:${b.account_id}:${b.id}`}><summary>{b.id} · {b.shared ? 'Shared budget' : 'Nonshared budget'} · {money(b.daily_paise)} daily</summary><p>Owner: {b.owner_id ?? 'Google budget resource'}. Members: {data.resources.filter(r => r.platform === b.platform && r.account_id === b.account_id && r.budget_id === b.id).map(r => r.id).join(', ')}.</p><p>Budget change supported by the synthetic contract at this owner. {b.shared && 'All member campaigns are affected.'} This snapshot cannot execute changes. Exact scope, current evidence and explicit approval are checked by the separate simulator.</p></details>)}
      <h3>Hierarchy and adapter capabilities</h3>
      <div className="record-browser">{data.resources.map(r => <details key={`${r.platform}:${r.account_id}:${r.id}`}><summary>{r.id} · {r.kind} · {r.product_scope} product scope</summary><dl>
        <div><dt>Parent / campaign / status</dt><dd>{r.parent_id ?? 'Account root'} / {r.campaign_id} / {r.status}</dd></div>
        <div><dt>Budget owner / effective budget</dt><dd>{r.budget_owner_id ?? 'Ad-set-owned budgets below campaign'} / {r.effective_budget_id ?? r.affected_budget_ids.join(', ')}</dd></div>
        <div><dt>Shared budget members</dt><dd>{r.shared_budget ? r.budget_members.join(', ') : 'Nonshared'}</dd></div>
        <div><dt>Simulated status / budget control at resource</dt><dd>{r.status_control_supported ? 'Supported' : 'Unsupported'} / {r.budget_control_supported ? 'Supported' : 'Unsupported; inspect budget owner'}</dd></div>
        <div><dt>Product-level controls</dt><dd>{r.product_control_supported ? 'Supported' : 'Unsupported — advisory only'}</dd></div>
        <div><dt>Native source product hints · unverified</dt><dd>{r.source_product_refs.join(', ') || 'Unknown'}. No commerce mapping established.</dd></div>
        <div><dt>Capability evidence</dt><dd>{r.capability_evidence}</dd></div><div><dt>Limits</dt><dd>{r.unsupported_reason}</dd></div>
      </dl></details>)}</div>
      <details><summary>Inspect normalized source reports and corrections</summary><div className="table-scroll"><table><thead><tr><th>Resource / revision</th><th>Interval start UTC</th><th>Source day</th><th>India day</th><th>INR spend</th></tr></thead><tbody>{data.reports.map(r => <tr key={r.key}><td>{r.resource_id} / {r.revision}</td><td>{r.interval_start}</td><td>{r.source_day}</td><td>{r.reporting_day}</td><td>{money(r.spend_paise)}</td></tr>)}</tbody></table></div></details>
    </>}
    {snapshot?.dataset_id && <aside><h3>Ad query evidence</h3><dl><div><dt>Dataset / version</dt><dd>{snapshot.dataset_id} / {snapshot.dataset_version}</dd></div><div><dt>Fixture SHA-256</dt><dd>{snapshot.fixture_hash}</dd></div><div><dt>Source observation / scenario clock</dt><dd>{snapshot.observed_at} / {snapshot.scenario_clock}</dd></div><div><dt>Published (UTC)</dt><dd>{snapshot.published_at}</dd></div><div><dt>Queried (UTC)</dt><dd>{snapshot.queried_at ?? 'Query unavailable'}</dd></div></dl></aside>}
  </section>;
}
