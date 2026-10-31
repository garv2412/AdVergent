import React, { useEffect, useState } from 'react';
import type { components } from './api.generated';

type Snapshot = components['schemas']['CommerceSnapshot'];
type Record = components['schemas']['Record'];
const kinds = ['products', 'variants', 'customers', 'orders', 'lines', 'refunds', 'inventory'] as const;
const pageSize = 25;

export function Commerce({ api }: { api: (path: string) => Promise<any> }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [records, setRecords] = useState<Record[]>([]);
  const [kind, setKind] = useState<typeof kinds[number]>('inventory');
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setBusy(true); setError(''); setSnapshot(null); setRecords([]);
    api('commerce').then((result: Snapshot) => { if (active) setSnapshot(result); }).catch(e => { if (active) setError(e.message); }).finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [revision, api]);
  useEffect(() => {
    let active = true;
    setRecords([]);
    if (snapshot?.status !== 'available' || !snapshot.dataset_id) return;
    setBusy(true); setError('');
    api(`commerce/records/${kind}?dataset_id=${encodeURIComponent(snapshot.dataset_id)}&limit=${pageSize}&offset=${offset}`).then(result => { if (active) setRecords(result); }).catch(e => { if (active) { setError(e.message); setSnapshot(null); } }).finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [snapshot?.dataset_id, revision, kind, offset, api]);
  const total = snapshot?.totals?.[kind] ?? 0;
  return <section className="commerce" aria-label="Commerce mirror">
    <div className="section-heading"><div><p className="eyebrow">SHOPIFY-SHAPED FIXTURE SOURCE</p><h2>Commerce mirror</h2></div><button disabled={busy} onClick={() => { setOffset(0); setRevision(x => x + 1); }}>Query commerce</button></div>
    <p>Source records and placed merchandise values. Financial recognition follows in Phase 5.</p>
    {error && <div className="error" role="alert">{error}</div>}
    {snapshot?.status === 'not_loaded' && <div className="empty">No commerce publication. Run the commerce import worker.</div>}
    {snapshot?.status === 'analytics_unavailable' && <div className="error" role="alert">Commerce Exasol unavailable. Current commerce records cannot be verified.</div>}
    {snapshot?.latest_import_status === 'failed' && <div className="error">Latest commerce import failed. Prior complete publication retained; checkpoint page {snapshot.next_page}.</div>}
    {snapshot?.status === 'available' && <>
      <div className={snapshot.freshness === 'stale' ? 'error' : 'notice'} role="status">Commerce freshness: {snapshot.freshness} · source observed {snapshot.observed_at} · {snapshot.age_seconds?.toLocaleString('en-IN')} seconds old (limit {snapshot.freshness_limit_seconds}s). Import time does not refresh source time.</div>
      <div className="cards"><article><span>Orders mirrored</span><strong>{snapshot.totals?.orders.toLocaleString('en-IN')}</strong><small>{snapshot.totals?.lines.toLocaleString('en-IN')} lines · {snapshot.totals?.refunds} refunds</small></article><article><span>Catalog variants</span><strong>{snapshot.totals?.variants}</strong><small>{snapshot.totals?.products} products · {snapshot.totals?.missing_cost_lines} lines with unknown costs</small></article><article><span>Sellable units · one warehouse</span><strong>{snapshot.totals?.sellable_units.toLocaleString('en-IN')}</strong><small>Source available minus separate merchant reserve</small></article></div>
      <div className="record-browser"><label htmlFor="collection">Inspect source collection</label><select id="collection" value={kind} onChange={e => { setKind(e.target.value as typeof kind); setOffset(0); }}>{kinds.map(value => <option key={value}>{value}</option>)}</select>
        <p>{total} records · showing {total ? offset + 1 : 0}–{Math.min(offset + pageSize, total)}. Expand a record for source fields.</p>
        {records.map(record => <details key={record.id}><summary>{record.id} <span>updated {record.updated_at}</span></summary><dl>{Object.entries(record.data).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{value === null ? 'Unknown' : String(value)}</dd></div>)}</dl></details>)}
        <div className="actions"><button disabled={busy || offset === 0} onClick={() => setOffset(x => x - pageSize)}>Previous records</button><button disabled={busy || offset + pageSize >= total} onClick={() => setOffset(x => x + pageSize)}>Next records</button></div>
      </div>
    </>}
    {snapshot?.dataset_id && <aside><h3>Commerce query evidence</h3><dl><div><dt>Dataset / version</dt><dd>{snapshot.dataset_id} / {snapshot.dataset_version}</dd></div><div><dt>Fixture SHA-256</dt><dd>{snapshot.fixture_hash}</dd></div><div><dt>Published (UTC)</dt><dd>{snapshot.published_at}</dd></div><div><dt>Scenario clock (UTC)</dt><dd>{snapshot.scenario_clock}</dd></div><div><dt>Reconciliation repairs</dt><dd>{snapshot.repair_count}</dd></div><div><dt>Queried (UTC)</dt><dd>{snapshot.queried_at ?? 'Query unavailable'}</dd></div></dl></aside>}
  </section>;
}
