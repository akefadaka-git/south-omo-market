import { FormEvent, useCallback, useEffect, useState } from 'react';

type QueueItem = {
  id: string;
  title: string;
  description: string;
  price_minor: number;
  currency: string;
  location: string;
  seller_name: string;
};

type AuditEvent = {
  id: string;
  actor_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1').replace(/\/$/, '');

export default function App() {
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState('');
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const loadQueue = useCallback(async (accessToken: string) => {
    const response = await fetch(`${API_BASE}/admin/moderation/queue`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!response.ok) throw new Error(response.status === 403 ? 'Administrator access required.' : 'Could not load moderation queue.');
    setQueue(await response.json() as QueueItem[]);
  }, []);

  const loadAudit = useCallback(async (accessToken: string) => {
    const response = await fetch(`${API_BASE}/admin/audit-events?resource_type=listing&limit=20`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!response.ok) throw new Error('Could not load moderation history.');
    setAuditEvents(await response.json() as AuditEvent[]);
  }, []);

  async function refreshAdminData(accessToken: string) {
    await Promise.all([loadQueue(accessToken), loadAudit(accessToken)]);
  }

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone_number: phone, password }),
      });
      if (!response.ok) throw new Error('Sign-in failed.');
      const data = await response.json() as { access_token: string };
      await refreshAdminData(data.access_token);
      setToken(data.access_token);
      setPassword('');
      setMessage('Signed in. Moderation queue loaded.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unexpected sign-in error.');
    } finally {
      setBusy(false);
    }
  }

  async function decide(listingId: string, decision: 'approve' | 'reject') {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const response = await fetch(`${API_BASE}/admin/moderation/${listingId}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ decision, note: note || null }),
      });
      if (!response.ok) throw new Error(response.status === 403 ? 'Administrator access required.' : 'Moderation action failed.');
      await refreshAdminData(token);
      setNote('');
      setMessage(decision === 'approve' ? 'Listing approved and published.' : 'Listing rejected.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unexpected moderation error.');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!token) return;
    refreshAdminData(token).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : 'Could not refresh administration data.');
    });
  }, [token, loadQueue, loadAudit]);

  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', margin: '2rem auto', maxWidth: 960, padding: 24 }}>
      <p style={{ color: '#356859', fontWeight: 700 }}>SOUTH OMO MARKET</p>
      <h1>Administration · Listing moderation</h1>
      <p>Access is restricted to accounts provisioned with administrator privileges.</p>
      {!token && (
        <form onSubmit={signIn} style={{ display: 'grid', gap: 12, maxWidth: 420 }}>
          <label>Phone number<input required value={phone} onChange={(event) => setPhone(event.target.value)} /></label>
          <label>Password<input required type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          <button disabled={busy} type="submit">{busy ? 'Signing in…' : 'Sign in'}</button>
        </form>
      )}
      {token && (
        <section>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2>Pending review ({queue.length})</h2>
            <button disabled={busy} onClick={() => refreshAdminData(token).catch((reason: unknown) => setError(String(reason)))}>Refresh</button>
          </div>
          <label>Moderation note (optional)<textarea value={note} maxLength={1000} onChange={(event) => setNote(event.target.value)} /></label>
          {queue.length === 0 && <p>No listings are waiting for review.</p>}
          <div style={{ display: 'grid', gap: 16 }}>
            {queue.map((item) => (
              <article key={item.id} style={{ border: '1px solid #ddd', borderRadius: 12, padding: 18 }}>
                <h3>{item.title}</h3>
                <p>{item.description}</p>
                <p>{item.price_minor.toLocaleString()} {item.currency} · {item.location} · Seller: {item.seller_name}</p>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button disabled={busy} onClick={() => decide(item.id, 'approve')}>Approve and publish</button>
                  <button disabled={busy} onClick={() => decide(item.id, 'reject')}>Reject</button>
                </div>
              </article>
            ))}
          </div>
          <h2>Recent moderation history</h2>
          {auditEvents.length === 0 && <p>No moderation decisions recorded yet.</p>}
          <div style={{ display: 'grid', gap: 8 }}>
            {auditEvents.map((event) => (
              <article key={event.id} style={{ border: '1px solid #ddd', borderRadius: 8, padding: 12 }}>
                <strong>{event.action.replace('listing.moderation.', '')}</strong>
                <p>Listing: {event.resource_id}</p>
                <small>{new Date(event.created_at).toLocaleString()} · Administrator: {event.actor_id ?? 'system provisioning'}</small>
                {typeof event.metadata.note === 'string' && event.metadata.note && <p>Note: {event.metadata.note}</p>}
              </article>
            ))}
          </div>
        </section>
      )}
      {error && <p role="alert" style={{ color: '#b42318' }}>{error}</p>}
      {message && <p role="status">{message}</p>}
    </main>
  );
}
