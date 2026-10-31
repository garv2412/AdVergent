import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import type { components } from './api.generated';
import './style.css';
import { Commerce } from './Commerce';
import { Ads } from './Ads';
import { Attribution } from './Attribution';
import { Finance } from './Finance';
import { Inventory } from './Inventory';
import { Diagnostics } from './Diagnostics';
import { Execution } from './Execution';
import { Clearance } from './Clearance';
import { Breakout } from './Breakout';
import { Cohorts } from './Cohorts';
import { Budget } from './Budget';
import { Decisions } from './Decisions';

type Snapshot = components['schemas']['Snapshot'];
const money = (paise: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(paise / 100);
async function api(path: string, body?: object) {
  const response = await fetch(`/api/${path}`, { method: body ? 'POST' : 'GET', headers: body ? { 'Content-Type': 'application/json', 'X-AdVergent-Request': '1' } : {}, body: body ? JSON.stringify(body) : undefined });
  if (!response.ok) throw new ApiError(response.status, response.status === 401 ? 'Authentication required or password incorrect.' : response.status === 503 ? 'Operational database unavailable. Try again when it is restored.' : 'Request failed. Try again.');
  return response.status === 204 ? undefined : response.json();
}
class ApiError extends Error { constructor(public status: number, message: string) { super(message); } }
function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const load = async () => {
    setBusy(true); setError(''); setSnapshot(null);
    try { setSnapshot(await api('foundation')); }
    catch (e) { setError((e as Error).message); if (e instanceof ApiError && e.status === 401) setAuthenticated(false); }
    finally { setBusy(false); }
  };
  useEffect(() => { api('session').then(() => { setAuthenticated(true); void load(); }).catch((e) => { if (!e.message.startsWith('Authentication')) setError(e.message); }); }, []);
  return <main>
    <header><a className="brand" href="/">AdVergent<span> / Synthetic local demo</span></a><span className="phase">PHASE 14</span></header>
    <div className="notice">Synthetic commerce & ad data · Real Exasol analytics · Simulated actions only</div>
    <p className="notice">Historical evidence may be stale. Missing costs remain unknown. Recommendations may abstain; every advertising change requires separate explicit approval.</p>
    <section className="intro"><p className="eyebrow">THE COMMERCE CONTROL ROOM</p><h1>Every decision starts<br />with a trusted number.</h1><p>One merchant. One warehouse. A traceable view of contribution.</p></section>
    {error && <div className="error" role="alert">{error}</div>}
    {!authenticated ? <form onSubmit={async e => { e.preventDefault(); setBusy(true); setError(''); try { await api('login', { password }); setPassword(''); setAuthenticated(true); await load(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); } }}>
      <h2>Operator access</h2><p>Sign in to inspect the foundation dataset.</p><label htmlFor="password">Operator password</label><input id="password" type="password" autoComplete="current-password" required maxLength={1024} value={password} onChange={e => setPassword(e.target.value)} /><button disabled={busy}>{busy ? 'Connecting…' : 'Open workspace →'}</button>
    </form> : <section className="workspace">
      <div className="section-heading"><div><p className="eyebrow">GOLDEN DATASET</p><h2>Contribution overview</h2></div><div className="actions"><button disabled={busy} onClick={load}>{busy ? 'Querying…' : 'Query Exasol'}</button><button className="secondary" onClick={async () => { try { await api('logout', {}); setAuthenticated(false); setSnapshot(null); } catch (e) { setError((e as Error).message); } }}>Sign out</button></div></div>
      <p>Separate two-line foundation fixture. These cards do not calculate finance for the commerce or ad-reporting publications; commerce finance is shown separately below.</p>
      {snapshot?.status === 'not_loaded' && <div className="empty" role="status">No published dataset. Run the foundation refresh worker to load and verify the golden fixture.</div>}
      {snapshot?.status === 'analytics_unavailable' && <div className="error" role="alert">Exasol unavailable. Current metrics cannot be verified. Restore the database and query again.</div>}
      {snapshot?.latest_refresh_status === 'failed' && <div className="error">Latest refresh failed. The prior complete publication is retained.</div>}
      {snapshot?.metric && <><div className="cards"><article><span>Net sales · excluding tax</span><strong>{money(snapshot.metric.net_sales_paise)}</strong><small>{snapshot.metric.line_count} delivered fixture lines</small></article><article><span>Contribution before ads</span><strong>{money(snapshot.metric.contribution_before_ads_paise)}</strong><small>After product & variable costs</small></article><article className="accent"><span>Contribution after ads</span><strong>{money(snapshot.metric.contribution_after_ads_paise)}</strong><small>Contribution, not accounting net profit</small></article></div>
      <div className="breakdown"><h3>Follow the calculation</h3><dl><div><dt>Net product cost</dt><dd>{money(snapshot.metric.product_cost_paise)}</dd></div><div><dt>Other variable costs</dt><dd>{money(snapshot.metric.variable_cost_paise)}</dd></div><div><dt>Meta + Google spend</dt><dd>{money(snapshot.metric.ad_spend_paise)}</dd></div></dl></div></>}
      {snapshot?.dataset_id && <aside><h3>Query evidence</h3><dl><div><dt>Dataset</dt><dd>{snapshot.dataset_version}</dd></div><div><dt>Run / dataset ID</dt><dd>{snapshot.dataset_id}</dd></div><div><dt>Fixture SHA-256</dt><dd>{snapshot.fixture_hash}</dd></div><div><dt>Published</dt><dd>{snapshot.published_at}</dd></div><div><dt>Queried (UTC)</dt><dd>{snapshot.queried_at ?? 'Query unavailable'}</dd></div></dl></aside>}
      <Budget api={api} />
      <Decisions api={api} />
      <Cohorts api={api} />
      <Breakout api={api} />
      <Clearance api={api} />
      <Inventory api={api} />
      <Diagnostics api={api} />
      <Execution api={api} />
      <Finance api={api} />
      <Commerce api={api} />
      <Ads api={api} />
      <Attribution api={api} />
    </section>}
    <footer>Synthetic commerce and ad reporting · Real Exasol queries · Explicitly approved simulations · No live platform connections</footer>
  </main>;
}
createRoot(document.getElementById('root')!).render(<App />);
