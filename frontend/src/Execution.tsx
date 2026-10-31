import React, { useEffect, useState } from 'react';

type Step = { ordinal: number; request_id: string; resource_key: string; outcome: string; actual: { value: string | number; revision: number } | null };
type Term = { platform: string; account_id: string; resource_id: string; kind: string; before: { value: string | number; revision: number }; after: string | number; scope: { products: string[]; members: string[]; shared: boolean } };
type Plan = { id: string; digest: string; status: string; expires_at: string; error_code: string | null; plan: { action: string; changes: Term[]; evidence: Record<string, string>; reason: string; clock_valid_until?: string }; steps: Step[]; events: unknown[] };
type Ledger = { simulated: boolean; kill_switch: boolean; plans: Plan[] };
const amount = (value: string | number) => typeof value === 'number' ? `${new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(value / 100)} (${value} paise)` : value;
export function Execution({ api }: { api: (path: string, body?: object) => Promise<any> }) {
  const [ledger, setLedger] = useState<Ledger | null>(null);
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const [action, setAction] = useState('pause'); const [platform, setPlatform] = useState('meta');
  const [account, setAccount] = useState('meta-inr'); const [resource, setResource] = useState('');
  const [recipient, setRecipient] = useState(''); const [donorAmount, setDonorAmount] = useState(''); const [recipientAmount, setRecipientAmount] = useState('');
  const [reason, setReason] = useState(''); const [recovery, setRecovery] = useState('');
  const [showHistory, setShowHistory] = useState(false);
  async function run(work: () => Promise<unknown>) {
    setBusy(true); setError('');
    try { await work(); setLedger(await api('actions')); }
    catch (e) { setError((e as Error).message + ' Evidence may be stale, unavailable, blocked or changed. Query current evidence and create a new proposal.'); }
    finally { setBusy(false); }
  }
  useEffect(() => { void run(async () => {}); }, []);
  const paise = (s: string) => {
    if (!/^\d{1,10}(\.\d{1,2})?$/.test(s)) throw new Error('Enter an exact nonnegative INR amount with at most two decimals.');
    const [r, p = ''] = s.split('.'); return Number(r) * 100 + Number(p.padEnd(2, '0'));
  };
  return <section className="execution commerce" aria-label="Approved execution">
    <div className="section-heading"><h2>Approved execution · simulator</h2><button disabled={busy} onClick={() => void run(async () => {})}>Query action ledger</button></div>
    <p>Every pause, throttle, resume, transfer and recovery needs an explicit approval of the displayed exact plan. Budgets use INR; no live platform is connected. Historical default evidence blocks new proposals.</p>
    {error && <p className="error" role="alert">{error}</p>}
    <p role="status">Kill switch: {busy || error || !ledger ? 'unknown · query pending or unavailable' : ledger.kill_switch ? 'ON · new mutations blocked' : 'OFF'}</p>
    <button disabled={busy || !ledger} onClick={() => void run(() => api('actions/kill-switch', { stopped: !ledger?.kill_switch }))}>{ledger?.kill_switch ? 'Disable kill switch' : 'Enable kill switch'}</button>
    <form onSubmit={e => { e.preventDefault(); void run(async () => {
      const base = { platform, account_id: account, currency: 'INR' };
      const changes = action === 'transfer' ? [
        { ...base, resource_id: resource, kind: 'budget', after: paise(donorAmount) },
        { ...base, resource_id: recipient, kind: 'budget', after: paise(recipientAmount) }
      ] : [{ ...base, resource_id: resource, kind: ['throttle', 'recovery'].includes(action) ? 'budget' : 'status', after: ['throttle', 'recovery'].includes(action) ? paise(donorAmount) : action === 'pause' ? 'paused' : 'active' }];
      await api('actions/propose', { client_key: crypto.randomUUID(), action, changes, reason, recovery_of: action === 'recovery' ? recovery : null });
    }); }}>
      <h3>Create a proposal</h3>
      <label>Action<select value={action} onChange={e => setAction(e.target.value)}><option value="pause">Pause</option><option value="resume">Resume approved system pause</option><option value="throttle">Reduce inventory-constrained budget</option><option value="transfer">Exact INR transfer</option><option value="recovery">Recover partial budget transfer</option></select></label>
      <label>Platform<select value={platform} onChange={e => setPlatform(e.target.value)}><option>meta</option><option>google</option></select></label>
      <label>Exact account ID<input required value={account} onChange={e => setAccount(e.target.value)} /></label>
      <label>Exact resource ID (budget ID for throttle/transfer/recovery)<input required value={resource} onChange={e => setResource(e.target.value)} /></label>
      {['transfer', 'throttle', 'recovery'].includes(action) && <label>New donor / throttle / recovery daily budget (INR)<input required value={donorAmount} onChange={e => setDonorAmount(e.target.value)} /></label>}
      {action === 'transfer' && <><label>Exact recipient budget ID<input required value={recipient} onChange={e => setRecipient(e.target.value)} /></label><label>New recipient daily budget (INR)<input required value={recipientAmount} onChange={e => setRecipientAmount(e.target.value)} /></label></>}
      {action === 'recovery' && <label>Original partial plan ID<input required value={recovery} onChange={e => setRecovery(e.target.value)} /></label>}
      <label>Reason<input required maxLength={500} value={reason} onChange={e => setReason(e.target.value)} /></label>
      <button disabled={busy}>Create proposal for review</button>
    </form>
    <p>Approval expires 30 minutes after proposal creation. Displayed monetary values in evidence are exact integer paise (100 paise = INR 1). A transfer reduces and verifies the donor first. Recovery cannot recover already spent advertising.</p>
    {(ledger?.plans.length ?? 0) > 10 && <button className="secondary" onClick={() => setShowHistory(!showHistory)}>{showHistory ? 'Show 10 recent plans' : 'Show 50 recent plans'}</button>}
    {ledger?.plans.slice(0, showHistory ? 50 : 10).map(p => <article key={p.id} data-testid="action-plan">
      <h3>{p.status} · {p.id}</h3><p>Approval expires (UTC): {p.expires_at}<br />Evidence valid until (UTC): {p.plan.clock_valid_until ?? 'Historical plan; new proposal required'} · {p.error_code}</p>
      {p.plan.changes.map(c => <p key={`${c.platform}/${c.account_id}/${c.kind}/${c.resource_id}`}><b>{c.platform} / {c.account_id} / {c.resource_id}</b><br />{amount(c.before.value)} → {amount(c.after)} · expected revision {c.before.revision}<br />Reviewed products: {c.scope.products.join(', ')}. Members: {c.scope.members.join(', ')}{c.kind === 'budget' ? ` · ${c.scope.shared ? 'shared' : 'unshared'} daily budget` : ''}.</p>)}
      {p.steps.map(s => <p key={s.request_id}>Step {s.ordinal + 1} · {s.resource_key} · {s.outcome} · Read-back: {s.actual ? typeof s.actual.value === 'number' ? `${new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(s.actual.value / 100)} (${s.actual.value} paise), revision ${s.actual.revision}` : `${s.actual.value}, revision ${s.actual.revision}` : 'unknown'}</p>)}
      <pre>{JSON.stringify(p.plan, null, 2)}</pre>
      <details><summary>Approval digest, read-back and audit</summary><pre>{JSON.stringify(p, null, 2)}</pre></details>
      {p.status === 'proposed' && <button disabled={busy} onClick={() => void run(() => api(`actions/${p.id}/approve`, { digest: p.digest, approve: true }))}>Explicitly approve this exact simulated plan</button>}
      {['proposed', 'approved'].includes(p.status) && <button className="secondary" disabled={busy} onClick={() => void run(() => api(`actions/${p.id}/reject`, {}))}>Reject this plan</button>}
      {['approved', 'revalidating', 'unknown', 'executing'].includes(p.status) && <button disabled={busy} onClick={() => void run(() => api(`actions/${p.id}/execute`, {}))}>{p.status === 'approved' ? 'Execute approved simulation' : 'Read back uncertain outcome'}</button>}
    </article>)}
  </section>;
}
