import { useCallback, useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';

type Provider = {
  provider_id: string;
  verification_status: string;
  business_id: string;
  business_code: string;
  legal_name: string;
  display_name: string;
  business_type: string;
  requested_at: string;
  contact_user_id: string;
  contact_display_name: string;
  contact_phone: string;
};

type Payment = {
  payment_id: string;
  amount_minor: number;
  currency: string;
  payment_method: string;
  external_reference: string | null;
  evidence_ref: string;
  status: string;
  received_at: string | null;
  verified_at: string | null;
};

type Advertisement = {
  advertisement_id: string;
  advertisement_status: string;
  published_at: string | null;
  expires_at: string | null;
  opportunity_id: string;
  title: string;
  description: string;
  occupation_code: string;
  location_code: string;
  employment_type: string;
  requirements: Array<Record<string, unknown>>;
  opportunity_status: string;
  provider_id: string;
  provider_status: string;
  business_code: string;
  provider_name: string;
  agreement_id: string;
  terms_version: string;
  agreed_price_minor: number;
  currency: string;
  duration_days: number;
  agreement_status: string;
  provider_accepted_at: string | null;
  provider_acceptance_evidence: string | null;
  verified_payment_minor: number;
  payments: Payment[];
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1').replace(/\/$/, '');
const authHeaders = (token: string) => ({ Authorization: `Bearer ${token}` });
const panelStyle = { border: '1px solid #d0d5dd', borderRadius: 12, padding: 18, marginTop: 16 };
const fieldStyle = { display: 'grid', gap: 5, marginBottom: 10 } as const;
const money = (minor: number, currency = 'ETB') => `${(minor / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;

async function responseError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => ({})) as { detail?: string };
  if (response.status === 403) return new Error('Owner role and the required employment permission are required.');
  if (response.status === 401) return new Error('Your session has expired. Sign in again.');
  return new Error(body.detail ?? fallback);
}

export default function EmploymentAgencyManagement({ accessToken }: { accessToken: string }) {
  const [authorized, setAuthorized] = useState<boolean | null>(null);
  const [providersPending, setProvidersPending] = useState<Provider[]>([]);
  const [providersVerified, setProvidersVerified] = useState<Provider[]>([]);
  const [advertisements, setAdvertisements] = useState<Advertisement[]>([]);
  const [providerFilter, setProviderFilter] = useState('pending');
  const [adFilter, setAdFilter] = useState('pending_owner');
  const [rejectionReasons, setRejectionReasons] = useState<Record<string, string>>({});
  const [paymentNotes, setPaymentNotes] = useState<Record<string, string>>({});
  const [providerId, setProviderId] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [occupationCode, setOccupationCode] = useState('');
  const [locationCode, setLocationCode] = useState('KOYBE');
  const [employmentType, setEmploymentType] = useState('full_time');
  const [requirementsText, setRequirementsText] = useState('');
  const [priceMinor, setPriceMinor] = useState('100000');
  const [durationDays, setDurationDays] = useState('30');
  const [termsVersion, setTermsVersion] = useState('EMPLOYMENT-ADS-1.0');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    setError('');
    const [pendingResponse, verifiedResponse, adsResponse] = await Promise.all([
      fetch(`${API_BASE}/employment/admin/providers?status=pending`, { headers: authHeaders(accessToken) }),
      fetch(`${API_BASE}/employment/admin/providers?status=verified`, { headers: authHeaders(accessToken) }),
      fetch(`${API_BASE}/employment/admin/advertisements?status=all`, { headers: authHeaders(accessToken) }),
    ]);
    const failed = [pendingResponse, verifiedResponse, adsResponse].find((response) => !response.ok);
    if (failed) throw await responseError(failed, 'Could not load employment agency administration.');
    const [pending, verified, ads] = await Promise.all([
      pendingResponse.json() as Promise<Provider[]>,
      verifiedResponse.json() as Promise<Provider[]>,
      adsResponse.json() as Promise<Advertisement[]>,
    ]);
    setProvidersPending(pending);
    setProvidersVerified(verified);
    setAdvertisements(ads);
    setProviderId((current) => current || verified[0]?.provider_id || '');
    setAuthorized(true);
  }, [accessToken]);

  useEffect(() => {
    setAuthorized(null);
    load().catch((reason: unknown) => {
      setAuthorized(false);
      setError(reason instanceof Error ? reason.message : 'Could not verify Owner access.');
    });
  }, [load]);

  const pendingAds = useMemo(
    () => advertisements.filter((item) => item.advertisement_status === 'pending_owner'),
    [advertisements],
  );
  const publishedAds = useMemo(
    () => advertisements.filter((item) => item.advertisement_status === 'published'),
    [advertisements],
  );
  const shownAds = adFilter === 'published' ? publishedAds : pendingAds;

  async function runOwnerAction(action: () => Promise<void>, success: string) {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await action();
      await load();
      setMessage(success);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Owner action failed.');
    } finally {
      setBusy(false);
    }
  }

  async function verifyProvider(provider: Provider) {
    await runOwnerAction(async () => {
      const response = await fetch(`${API_BASE}/employment/admin/providers/${provider.provider_id}/verify`, {
        method: 'POST', headers: authHeaders(accessToken),
      });
      if (!response.ok) throw await responseError(response, 'Provider verification failed.');
    }, `${provider.display_name} verified; its owner membership is now active.`);
  }

  async function rejectProvider(provider: Provider) {
    const reason = (rejectionReasons[provider.provider_id] ?? '').trim();
    if (reason.length < 3) {
      setError('Enter a rejection reason of at least three characters.');
      return;
    }
    await runOwnerAction(async () => {
      const response = await fetch(`${API_BASE}/employment/admin/providers/${provider.provider_id}/reject`, {
        method: 'POST',
        headers: { ...authHeaders(accessToken), 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      });
      if (!response.ok) throw await responseError(response, 'Provider rejection failed.');
      setRejectionReasons((current) => ({ ...current, [provider.provider_id]: '' }));
    }, `${provider.display_name} rejected; the reason was recorded.`);
  }

  async function createAdvertisement(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsedRequirements = requirementsText.split('\n').map((line) => line.trim()).filter(Boolean)
      .map((code) => ({ code }));
    await runOwnerAction(async () => {
      const response = await fetch(`${API_BASE}/employment/admin/advertisements`, {
        method: 'POST',
        headers: { ...authHeaders(accessToken), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider_id: providerId,
          title: title.trim(),
          description: description.trim(),
          occupation_code: occupationCode.trim().toUpperCase(),
          location_code: locationCode.trim().toUpperCase(),
          employment_type: employmentType,
          requirements: parsedRequirements,
          agreed_price_minor: Number(priceMinor),
          duration_days: Number(durationDays),
          terms_version: termsVersion.trim(),
        }),
      });
      if (!response.ok) throw await responseError(response, 'Could not prepare the advertisement.');
      setTitle('');
      setDescription('');
      setOccupationCode('');
      setRequirementsText('');
    }, 'Advertisement prepared. The provider must accept the agreement and submit payment evidence.');
  }

  async function verifyPayment(ad: Advertisement, payment: Payment) {
    const note = (paymentNotes[payment.payment_id] ?? '').trim();
    if (note.length < 3) {
      setError('Enter a verification note of at least three characters before verifying payment.');
      return;
    }
    await runOwnerAction(async () => {
      const response = await fetch(
        `${API_BASE}/employment/admin/advertisements/${ad.advertisement_id}/payments/${payment.payment_id}/verify`,
        {
          method: 'POST',
          headers: { ...authHeaders(accessToken), 'Content-Type': 'application/json' },
          body: JSON.stringify({ verification_note: note }),
        },
      );
      if (!response.ok) throw await responseError(response, 'Payment verification failed.');
      setPaymentNotes((current) => ({ ...current, [payment.payment_id]: '' }));
    }, 'Payment evidence verified.');
  }

  async function publishAdvertisement(ad: Advertisement) {
    await runOwnerAction(async () => {
      const response = await fetch(`${API_BASE}/employment/admin/advertisements/${ad.advertisement_id}/publish`, {
        method: 'POST', headers: authHeaders(accessToken),
      });
      if (!response.ok) throw await responseError(response, 'Advertisement publication failed.');
    }, 'Advertisement published. Its public visibility and expiry are now controlled by the API.');
  }

  if (authorized === null) {
    return <section style={panelStyle} aria-busy="true"><h2>Employment agency administration</h2><p>Checking Owner authorization…</p></section>;
  }
  if (!authorized) {
    return <section style={panelStyle}><h2>Employment agency administration</h2><p role="alert">{error || 'Owner access is not available for this account.'}</p><p>No Owner actions are enabled. The API remains the authorization authority.</p></section>;
  }

  return (
    <section style={panelStyle} aria-labelledby="employment-agency-heading">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <p style={{ color: '#356859', fontWeight: 700, marginBottom: 4 }}>OWNER CONTROLLED</p>
          <h2 id="employment-agency-heading">Employment agency administration</h2>
          <p>Provider verification, paid advertisement preparation, payment evidence review and publication.</p>
        </div>
        <button type="button" disabled={busy} onClick={() => load().catch((reason: unknown) => setError(String(reason)))}>Refresh agency queues</button>
      </div>

      <section aria-labelledby="provider-queue-heading">
        <h3 id="provider-queue-heading">Provider verification queue ({providersPending.length})</h3>
        {providersPending.length === 0 && <p>No pending provider requests.</p>}
        <div style={{ display: 'grid', gap: 12 }}>
          {providersPending.map((provider) => (
            <article key={provider.provider_id} style={{ border: '1px solid #d0d5dd', borderRadius: 10, padding: 14 }}>
              <h4>{provider.display_name} · {provider.business_code}</h4>
              <p>{provider.legal_name} · {provider.business_type}</p>
              <p>Contact: {provider.contact_display_name} · {provider.contact_phone}</p>
              <small>Requested: {new Date(provider.requested_at).toLocaleString()}</small>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
                <button type="button" disabled={busy} onClick={() => verifyProvider(provider)}>Verify provider and activate membership</button>
              </div>
              <label style={fieldStyle}>Rejection reason
                <textarea
                  rows={2}
                  maxLength={1000}
                  value={rejectionReasons[provider.provider_id] ?? ''}
                  onChange={(event) => setRejectionReasons((current) => ({ ...current, [provider.provider_id]: event.target.value }))}
                />
              </label>
              <button type="button" disabled={busy || (rejectionReasons[provider.provider_id] ?? '').trim().length < 3} onClick={() => rejectProvider(provider)}>Reject request</button>
            </article>
          ))}
        </div>
      </section>

      <section aria-labelledby="prepare-ad-heading" style={{ marginTop: 24 }}>
        <h3 id="prepare-ad-heading">Prepare provider-sponsored advertisement</h3>
        {providersVerified.length === 0 ? <p>Verify a provider before preparing an advertisement.</p> : (
          <form onSubmit={createAdvertisement} style={{ display: 'grid', gap: 10, maxWidth: 760 }}>
            <label style={fieldStyle}>Verified provider
              <select required value={providerId} onChange={(event) => setProviderId(event.target.value)}>
                {providersVerified.map((provider) => <option key={provider.provider_id} value={provider.provider_id}>{provider.display_name} · {provider.business_code}</option>)}
              </select>
            </label>
            <label style={fieldStyle}>Advertisement title<input required minLength={3} maxLength={180} value={title} onChange={(event) => setTitle(event.target.value)} /></label>
            <label style={fieldStyle}>Description<textarea required minLength={10} maxLength={5000} rows={4} value={description} onChange={(event) => setDescription(event.target.value)} /></label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
              <label style={fieldStyle}>Occupation code<input required minLength={2} maxLength={80} value={occupationCode} onChange={(event) => setOccupationCode(event.target.value)} /></label>
              <label style={fieldStyle}>Location code<input required minLength={2} maxLength={80} value={locationCode} onChange={(event) => setLocationCode(event.target.value)} /></label>
              <label style={fieldStyle}>Employment type
                <select value={employmentType} onChange={(event) => setEmploymentType(event.target.value)}>
                  <option value="full_time">Full time</option><option value="part_time">Part time</option><option value="seasonal">Seasonal</option><option value="contract">Contract</option><option value="temporary">Temporary</option>
                </select>
              </label>
              <label style={fieldStyle}>Advertising price (ETB, minor units)
                <input required type="number" min="1" step="1" value={priceMinor} onChange={(event) => setPriceMinor(event.target.value)} />
              </label>
              <label style={fieldStyle}>Duration (days)
                <input required type="number" min="1" max="365" step="1" value={durationDays} onChange={(event) => setDurationDays(event.target.value)} />
              </label>
              <label style={fieldStyle}>Terms version<input required minLength={1} maxLength={40} value={termsVersion} onChange={(event) => setTermsVersion(event.target.value)} /></label>
            </div>
            <label style={fieldStyle}>Requirements (one code per line)
              <textarea rows={3} value={requirementsText} onChange={(event) => setRequirementsText(event.target.value)} placeholder="experience&#10;education" />
            </label>
            <p>Price entered in minor units. Example: 100000 = ETB 1,000.00. Payment remains direct/offline; this screen does not activate a gateway.</p>
            <button type="submit" disabled={busy || !providerId || Number(priceMinor) <= 0 || Number(durationDays) <= 0}>Prepare advertisement and agreement</button>
          </form>
        )}
      </section>

      <section aria-labelledby="advertisement-queue-heading" style={{ marginTop: 24 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center' }}>
          <h3 id="advertisement-queue-heading">Advertisements</h3>
          <label>View
            <select value={adFilter} onChange={(event) => setAdFilter(event.target.value)}>
              <option value="pending_owner">Awaiting Owner publication</option>
              <option value="published">Published</option>
            </select>
          </label>
        </div>
        {shownAds.length === 0 && <p>No advertisements in this queue.</p>}
        <div style={{ display: 'grid', gap: 14 }}>
          {shownAds.map((ad) => (
            <article key={ad.advertisement_id} style={{ border: '1px solid #d0d5dd', borderRadius: 10, padding: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                <h4>{ad.title}</h4><strong>{ad.advertisement_status.replace(/_/g, ' ')}</strong>
              </div>
              <p>{ad.provider_name} · {ad.business_code} · {ad.location_code} · {ad.employment_type.replace(/_/g, ' ')}</p>
              <p>{ad.description}</p>
              <p>Agreement {ad.agreement_status} · Terms {ad.terms_version} · {ad.duration_days} days · {money(ad.agreed_price_minor, ad.currency)}</p>
              <p>Provider acceptance: {ad.provider_accepted_at ? new Date(ad.provider_accepted_at).toLocaleString() : 'Awaiting provider acceptance'}</p>
              {ad.provider_acceptance_evidence && <p>Acceptance evidence: {ad.provider_acceptance_evidence}</p>}
              <p>Verified payment total: <strong>{money(ad.verified_payment_minor, ad.currency)}</strong> / {money(ad.agreed_price_minor, ad.currency)}</p>
              <h5>Submitted payment evidence ({ad.payments.length})</h5>
              {ad.payments.length === 0 && <p>No payment evidence submitted.</p>}
              {ad.payments.map((payment) => (
                <div key={payment.payment_id} style={{ borderTop: '1px solid #eaecf0', paddingTop: 10, marginTop: 10 }}>
                  <p>{money(payment.amount_minor, payment.currency)} · {payment.payment_method.replace(/_/g, ' ')} · {payment.status}</p>
                  {payment.external_reference && <p>External reference: {payment.external_reference}</p>}
                  <p>Evidence reference: {payment.evidence_ref}</p>
                  {payment.status === 'submitted' && ad.advertisement_status === 'pending_owner' && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'end' }}>
                      <label style={{ ...fieldStyle, flex: '1 1 280px' }}>Verification note
                        <input minLength={3} maxLength={1000} value={paymentNotes[payment.payment_id] ?? ''} onChange={(event) => setPaymentNotes((current) => ({ ...current, [payment.payment_id]: event.target.value }))} />
                      </label>
                      <button type="button" disabled={busy || (paymentNotes[payment.payment_id] ?? '').trim().length < 3} onClick={() => verifyPayment(ad, payment)}>Verify payment evidence</button>
                    </div>
                  )}
                </div>
              ))}
              {ad.advertisement_status === 'pending_owner' && (
                <button type="button" disabled={busy || !ad.provider_accepted_at || ad.agreement_status !== 'accepted' || ad.provider_status !== 'verified' || ad.verified_payment_minor < ad.agreed_price_minor} onClick={() => publishAdvertisement(ad)}>
                  Publish advertisement
                </button>
              )}
              {ad.advertisement_status === 'published' && <p>Published: {ad.published_at ? new Date(ad.published_at).toLocaleString() : 'recorded'} · Expires: {ad.expires_at ? new Date(ad.expires_at).toLocaleString() : 'not available'}</p>}
            </article>
          ))}
        </div>
      </section>
      {error && <p role="alert" style={{ color: '#b42318' }}>{error}</p>}
      {message && <p role="status">{message}</p>}
    </section>
  );
}
