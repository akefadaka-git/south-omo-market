import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import MarketManagement from './MarketManagement';
import LocationManagement from './LocationManagement';
import EmploymentAgencyManagement from './EmploymentAgencyManagement';

type QueueItem = {
  id: string;
  title: string;
  description: string;
  price_minor: number;
  currency: string;
  location: string;
  seller_name: string;
};

type ListingEditQueueItem = {
  edit_id: string;
  listing_id: string;
  listing_status: string;
  seller_name: string;
  current: Record<string, unknown>;
  proposed_values: Record<string, unknown>;
  changed_fields: string[];
  submitted_at: string;
};

type Evidence = { summary: string; reference?: string };
type ReportItem = {
  id: string;
  reporter_user_id: string | null;
  reason: string;
  description: string;
  evidence: Evidence[];
  status: 'pending' | 'in_review' | 'resolved' | 'dismissed';
  review_note: string | null;
  previous_target_status: string | null;
  target: {
    type: 'listing' | 'seller';
    id: string;
    title?: string;
    status?: string;
    seller_name?: string;
    suspended?: boolean;
  } | null;
  created_at: string;
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
const authHeaders = (accessToken: string) => ({ Authorization: `Bearer ${accessToken}` });

export default function App() {
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState('');
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [listingEdits, setListingEdits] = useState<ListingEditQueueItem[]>([]);
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [adminAuthorized, setAdminAuthorized] = useState<boolean | null>(null);

  const loadQueue = useCallback(async (accessToken: string) => {
    const response = await fetch(`${API_BASE}/admin/moderation/queue`, {
      headers: authHeaders(accessToken),
    });
    if (!response.ok) throw new Error(response.status === 403 ? 'Administrator access required.' : 'Could not load moderation queue.');
    setQueue(await response.json() as QueueItem[]);
  }, []);

  const loadListingEdits = useCallback(async (accessToken: string) => {
    const response = await fetch(`${API_BASE}/admin/moderation/listing-edits`, {
      headers: authHeaders(accessToken),
    });
    if (!response.ok) throw new Error(response.status === 403 ? 'Administrator access required.' : 'Could not load listing edit queue.');
    setListingEdits(await response.json() as ListingEditQueueItem[]);
  }, []);

  const loadReports = useCallback(async (accessToken: string) => {
    const headers = authHeaders(accessToken);
    const [pendingResponse, reviewResponse] = await Promise.all([
      fetch(`${API_BASE}/admin/reports?status=pending`, { headers }),
      fetch(`${API_BASE}/admin/reports?status=in_review`, { headers }),
    ]);
    if (!pendingResponse.ok || !reviewResponse.ok) throw new Error(pendingResponse.status === 403 || reviewResponse.status === 403 ? 'Administrator access required.' : 'Could not load abuse reports.');
    const [pending, inReview] = await Promise.all([
      pendingResponse.json() as Promise<ReportItem[]>,
      reviewResponse.json() as Promise<ReportItem[]>,
    ]);
    setReports([...pending, ...inReview]);
  }, []);

  const loadAudit = useCallback(async (accessToken: string) => {
    const response = await fetch(`${API_BASE}/admin/audit-events?limit=30`, {
      headers: authHeaders(accessToken),
    });
    if (!response.ok) throw new Error(response.status === 403 ? 'Administrator access required.' : 'Could not load moderation history.');
    setAuditEvents(await response.json() as AuditEvent[]);
  }, []);

  async function refreshAdminData(accessToken: string) {
    await Promise.all([loadQueue(accessToken), loadListingEdits(accessToken), loadReports(accessToken), loadAudit(accessToken)]);
    setAdminAuthorized(true);
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
      setToken(data.access_token);
      setPassword('');
      setAdminAuthorized(null);
      setMessage('Signed in. Checking account permissions for available administration areas.');
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
        headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
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

  async function decideListingEdit(editId: string, decision: 'approve' | 'reject') {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const response = await fetch(`${API_BASE}/admin/moderation/listing-edits/${editId}/decision`, {
        method: 'POST',
        headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, note: note || null }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({})) as { detail?: string };
        throw new Error(body.detail ?? 'Listing edit moderation failed.');
      }
      await refreshAdminData(token);
      setNote('');
      setMessage(decision === 'approve' ? 'Listing edit approved; the new version is now public.' : 'Listing edit rejected; the approved version was preserved.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unexpected listing edit moderation error.');
    } finally {
      setBusy(false);
    }
  }

  async function decideReport(reportId: string, decision: string) {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const response = await fetch(`${API_BASE}/admin/reports/${reportId}/decision`, {
        method: 'POST',
        headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, note: note || null }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({})) as { detail?: string };
        throw new Error(body.detail ?? 'Report action failed.');
      }
      await refreshAdminData(token);
      setNote('');
      setMessage(`Report action completed: ${decision.replace(/_/g, ' ')}.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unexpected report action error.');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!token) return;
    setAdminAuthorized(null);
    Promise.all([loadQueue(token), loadListingEdits(token), loadReports(token), loadAudit(token)])
      .then(() => setAdminAuthorized(true))
      .catch((reason: unknown) => {
        setAdminAuthorized(false);
        if (!(reason instanceof Error && reason.message === 'Administrator access required.')) {
          setError(reason instanceof Error ? reason.message : 'Could not refresh administration data.');
        }
      });
  }, [token, loadQueue, loadListingEdits, loadReports, loadAudit]);

  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', margin: '2rem auto', maxWidth: 960, padding: 24 }}>
      <p style={{ color: '#356859', fontWeight: 700 }}>SOUTH OMO MARKET</p>
      <h1>Administration · Moderation and trust</h1>
      <p>Access is restricted to accounts provisioned with administrator privileges.</p>
      {!token && (
        <form onSubmit={signIn} style={{ display: 'grid', gap: 12, maxWidth: 420 }}>
          <label>Phone number<input required value={phone} onChange={(event) => setPhone(event.target.value)} /></label>
          <label>Password<input required type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          <button disabled={busy} type="submit">{busy ? 'Signing in…' : 'Sign in'}</button>
        </form>
      )}
      {token && (
        <>
        {adminAuthorized === true && <section>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2>Pending listing review ({queue.length})</h2>
            <button disabled={busy} onClick={() => refreshAdminData(token).catch((reason: unknown) => setError(String(reason)))}>Refresh all</button>
          </div>
          <label>Moderation note (optional)<textarea value={note} maxLength={2000} onChange={(event) => setNote(event.target.value)} /></label>
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

          <h2>Published listing edits awaiting review ({listingEdits.length})</h2>
          {listingEdits.length === 0 && <p>No published-listing edits are awaiting review.</p>}
          <div style={{ display: 'grid', gap: 16 }}>
            {listingEdits.map((edit) => (
              <article key={edit.edit_id} aria-labelledby={`listing-edit-${edit.edit_id}`} style={{ border: '1px solid #ddd', borderRadius: 12, padding: 18 }}>
                <h3 id={`listing-edit-${edit.edit_id}`}>Edit request · {edit.listing_id}</h3>
                <p>Seller: {edit.seller_name} · Submitted: {new Date(edit.submitted_at).toLocaleString()}</p>
                <p><strong>Changed fields:</strong> {edit.changed_fields.join(', ')}</p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 12 }}>
                  <section><h4>Currently published version</h4><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify(edit.current, null, 2)}</pre></section>
                  <section><h4>Proposed version changes</h4><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify(edit.proposed_values, null, 2)}</pre></section>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button disabled={busy} onClick={() => decideListingEdit(edit.edit_id, 'approve')}>Approve edit</button>
                  <button disabled={busy} onClick={() => decideListingEdit(edit.edit_id, 'reject')}>Reject edit</button>
                </div>
              </article>
            ))}
          </div>

          <h2>Reports and complaints ({reports.length})</h2>
          {reports.length === 0 && <p>No open reports.</p>}
          <div style={{ display: 'grid', gap: 16 }}>
            {reports.map((report) => (
              <article key={report.id} aria-labelledby={`report-${report.id}`} style={{ border: '1px solid #ddd', borderRadius: 12, padding: 18 }}>
                <h3 id={`report-${report.id}`}>{report.reason.replace(/_/g, ' ')} · {report.status.replace(/_/g, ' ')}</h3>
                <p>{report.description}</p>
                <p><strong>Target:</strong> {report.target?.type === 'listing'
                  ? `Listing: ${report.target.title ?? report.target.id} · Seller: ${report.target.seller_name ?? 'unknown'}`
                  : `Seller: ${report.target?.seller_name ?? report.target?.id ?? 'unavailable'}`}</p>
                <p><strong>Submitted:</strong> {new Date(report.created_at).toLocaleString()}</p>
                {report.evidence.length > 0 && (
                  <section aria-label="Submitted evidence">
                    <strong>Evidence supplied</strong>
                    <ul>{report.evidence.map((item, index) => (
                      <li key={index}>{item.summary}{item.reference ? ` · Reference: ${item.reference}` : ''}</li>
                    ))}</ul>
                  </section>
                )}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {report.status === 'pending' && <button disabled={busy} onClick={() => decideReport(report.id, 'investigate')}>Start investigation</button>}
                  {report.target?.type === 'listing' && ['published', 'pending_review'].includes(report.target.status ?? '') && <button disabled={busy} onClick={() => decideReport(report.id, 'block_listing')}>Block listing</button>}
                  {report.target?.type === 'listing' && report.target.status === 'rejected' && report.previous_target_status && <button disabled={busy} onClick={() => decideReport(report.id, 'restore_listing')}>Restore listing</button>}
                  {report.target?.type === 'seller' && !report.target.suspended && <button disabled={busy} onClick={() => decideReport(report.id, 'block_seller')}>Suspend seller</button>}
                  {report.target?.type === 'seller' && report.target.suspended && <button disabled={busy} onClick={() => decideReport(report.id, 'unblock_seller')}>Reinstate seller</button>}
                  {report.target?.type === 'seller' && report.target.suspended && <p role="status">Reinstate the seller before closing this report.</p>}
                  <button disabled={busy || (report.target?.type === 'seller' && report.target.suspended)} onClick={() => decideReport(report.id, 'resolve')}>Resolve</button>
                  <button disabled={busy || (report.target?.type === 'seller' && report.target.suspended) || Boolean(report.previous_target_status)} onClick={() => decideReport(report.id, 'dismiss')}>Dismiss</button>
                </div>
              </article>
            ))}
          </div>

          <MarketManagement accessToken={token} />
          <LocationManagement accessToken={token} />

          <h2>Recent audit history</h2>
          {auditEvents.length === 0 && <p>No moderation events recorded yet.</p>}
          <div style={{ display: 'grid', gap: 8 }}>
            {auditEvents.map((event) => (
              <article key={event.id} style={{ border: '1px solid #ddd', borderRadius: 8, padding: 12 }}>
                <strong>{event.action}</strong>
                <p>{event.resource_type}: {event.resource_id}</p>
                <small>{new Date(event.created_at).toLocaleString()} · Administrator/actor: {event.actor_id ?? 'system provisioning'}</small>
                {typeof event.metadata.note === 'string' && event.metadata.note && <p>Note: {event.metadata.note}</p>}
              </article>
            ))}
          </div>
        </section>}
        {adminAuthorized === false && <p role="status">General administrator controls are unavailable for this account. Owner employment controls are checked separately using Owner-only API permissions.</p>}
        <EmploymentAgencyManagement accessToken={token} />
        </>
      )}
      {error && <p role="alert" style={{ color: '#b42318' }}>{error}</p>}
      {message && <p role="status">{message}</p>}
    </main>
  );
}
