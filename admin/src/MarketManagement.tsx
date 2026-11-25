import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { marketNamesForDay, WEEKDAYS } from './marketSchedule';

type Market = {
  id: string;
  code: string;
  name: string;
  name_en?: string | null;
  name_am: string | null;
  description: string | null;
  description_am?: string | null;
  address_en?: string | null;
  address_am?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  location_id: string | null;
  is_active: boolean;
  schedule_days: number[];
  schedule_entries?: Array<{ weekday: number; is_active: boolean; effective_from: string | null; effective_until: string | null }>;
};
type Location = { id: string; name: string; level: string };

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1').replace(/\/$/, '');
const headers = (token: string) => ({ Authorization: `Bearer ${token}` });

export default function MarketManagement({ accessToken }: { accessToken: string }) {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [nameAm, setNameAm] = useState('');
  const [description, setDescription] = useState('');
  const [descriptionAm, setDescriptionAm] = useState('');
  const [addressEn, setAddressEn] = useState('');
  const [addressAm, setAddressAm] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [search, setSearch] = useState('');
  const [weekdayFilter, setWeekdayFilter] = useState('all');
  const [auditEvents, setAuditEvents] = useState<Array<{id: string; action: string; resource_id: string; created_at: string; metadata: Record<string, unknown>}>>([]);
  const [locationId, setLocationId] = useState('');
  const [draftDays, setDraftDays] = useState<Record<string, number[]>>({});
  const [draftNames, setDraftNames] = useState<Record<string, string>>({});
  const [draftNamesAm, setDraftNamesAm] = useState<Record<string, string>>({});
  const [draftDescriptions, setDraftDescriptions] = useState<Record<string, string>>({});
  const [draftDescriptionsAm, setDraftDescriptionsAm] = useState<Record<string, string>>({});
  const [draftAddressesEn, setDraftAddressesEn] = useState<Record<string, string>>({});
  const [draftAddressesAm, setDraftAddressesAm] = useState<Record<string, string>>({});
  const [draftLatitudes, setDraftLatitudes] = useState<Record<string, string>>({});
  const [draftLongitudes, setDraftLongitudes] = useState<Record<string, string>>({});
  const [effectiveFrom, setEffectiveFrom] = useState<Record<string, string>>({});
  const [effectiveUntil, setEffectiveUntil] = useState<Record<string, string>>({});
  const [draftLocations, setDraftLocations] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [marketResponse, locationResponse, auditResponse] = await Promise.all([
      fetch(`${API_BASE}/admin/markets`, { headers: headers(accessToken) }),
      fetch(`${API_BASE}/locations?lang=en`, { headers: headers(accessToken) }),
      fetch(`${API_BASE}/admin/markets/audit?limit=100`, { headers: headers(accessToken) }),
    ]);
    if (!marketResponse.ok) throw new Error('Could not load market directory.');
    if (!locationResponse.ok) throw new Error('Could not load geographic locations.');
    if (!auditResponse.ok) throw new Error('Could not load market audit history.');
    const rows = await marketResponse.json() as Market[];
    setMarkets(rows);
    setDraftDays(Object.fromEntries(rows.map((market) => [market.id, market.schedule_days])));
    setDraftNames(Object.fromEntries(rows.map((market) => [market.id, market.name_en ?? market.name])));
    setDraftNamesAm(Object.fromEntries(rows.map((market) => [market.id, market.name_am ?? ''])));
    setDraftDescriptions(Object.fromEntries(rows.map((market) => [market.id, market.description ?? ''])));
    setDraftDescriptionsAm(Object.fromEntries(rows.map((market) => [market.id, market.description_am ?? ''])));
    setDraftAddressesEn(Object.fromEntries(rows.map((market) => [market.id, market.address_en ?? ''])));
    setDraftAddressesAm(Object.fromEntries(rows.map((market) => [market.id, market.address_am ?? ''])));
    setDraftLatitudes(Object.fromEntries(rows.map((market) => [market.id, market.latitude == null ? '' : String(market.latitude)])));
    setDraftLongitudes(Object.fromEntries(rows.map((market) => [market.id, market.longitude == null ? '' : String(market.longitude)])));
    setEffectiveFrom(Object.fromEntries(rows.map((market) => [market.id, market.schedule_entries?.find((entry) => entry.is_active)?.effective_from ?? ''])));
    setEffectiveUntil(Object.fromEntries(rows.map((market) => [market.id, market.schedule_entries?.find((entry) => entry.is_active)?.effective_until ?? ''])));
    setDraftLocations(Object.fromEntries(rows.map((market) => [market.id, market.location_id ?? ''])));
    setLocations(await locationResponse.json() as Location[]);
    setAuditEvents(await auditResponse.json() as typeof auditEvents);
  }, [accessToken]);

  useEffect(() => {
    load().catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Market load failed.'));
  }, [load]);

  async function createMarket(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError(''); setMessage('');
    try {
      const response = await fetch(`${API_BASE}/admin/markets`, {
        method: 'POST',
        headers: { ...headers(accessToken), 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code.trim().toUpperCase(), name: name.trim(), name_am: nameAm.trim(), description: description.trim() || null, description_am: descriptionAm.trim() || null, address_en: addressEn.trim() || null, address_am: addressAm.trim() || null, latitude: latitude.trim() ? Number(latitude) : null, longitude: longitude.trim() ? Number(longitude) : null, location_id: locationId || null }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({})) as { detail?: string };
        throw new Error(body.detail ?? 'Could not create market.');
      }
      setCode(''); setName(''); setNameAm(''); setDescription(''); setDescriptionAm(''); setAddressEn(''); setAddressAm(''); setLatitude(''); setLongitude(''); setLocationId('');
      await load();
      setMessage('Market created. Configure its weekly days below.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Market creation failed.');
    } finally { setBusy(false); }
  }

  async function saveDetails(market: Market) {
    setBusy(true); setError(''); setMessage('');
    try {
      const response = await fetch(`${API_BASE}/admin/markets/${market.id}`, {
        method: 'PATCH',
        headers: { ...headers(accessToken), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: draftNames[market.id] ?? market.name,
          name_am: draftNamesAm[market.id] ?? market.name_am ?? '',
          description: (draftDescriptions[market.id] ?? market.description ?? '').trim() || null,
          description_am: (draftDescriptionsAm[market.id] ?? market.description_am ?? '').trim() || null,
          address_en: (draftAddressesEn[market.id] ?? market.address_en ?? '').trim() || null,
          address_am: (draftAddressesAm[market.id] ?? market.address_am ?? '').trim() || null,
          latitude: (draftLatitudes[market.id] ?? '').trim() ? Number(draftLatitudes[market.id]) : null,
          longitude: (draftLongitudes[market.id] ?? '').trim() ? Number(draftLongitudes[market.id]) : null,
          location_id: draftLocations[market.id] || null,
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({})) as { detail?: string };
        throw new Error(body.detail ?? 'Could not update market details.');
      }
      await load();
      setMessage(`Saved market details for ${market.name}.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Market details update failed.');
    } finally { setBusy(false); }
  }

  async function saveDays(market: Market) {
    setBusy(true); setError(''); setMessage('');
    try {
      const response = await fetch(`${API_BASE}/admin/markets/${market.id}/schedule`, {
        method: 'PUT',
        headers: { ...headers(accessToken), 'Content-Type': 'application/json' },
        body: JSON.stringify({ days: draftDays[market.id] ?? [], effective_from: effectiveFrom[market.id] || null, effective_until: effectiveUntil[market.id] || null }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({})) as { detail?: string };
        throw new Error(body.detail ?? 'Could not update weekly schedule.');
      }
      await load();
      setMessage(`Saved weekly schedule for ${market.name}.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Schedule update failed.');
    } finally { setBusy(false); }
  }

  async function toggleStatus(market: Market) {
    setBusy(true); setError(''); setMessage('');
    try {
      const response = await fetch(`${API_BASE}/admin/markets/${market.id}/status`, {
        method: 'PATCH',
        headers: { ...headers(accessToken), 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !market.is_active }),
      });
      if (!response.ok) throw new Error('Could not update market status.');
      await load();
      setMessage(`${market.name} ${market.is_active ? 'deactivated' : 'activated'}.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Market status update failed.');
    } finally { setBusy(false); }
  }

  return (
    <section aria-labelledby="market-management-title" style={{ marginTop: 32 }}>
      <h2 id="market-management-title">Market directory and weekly schedules</h2>
      <p>Manage markets and recurring days. Location associations are optional and must use an existing verified location.</p>
      <label>Search markets<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Name or code" /></label>
      <label>Filter by weekday<select value={weekdayFilter} onChange={(event) => setWeekdayFilter(event.target.value)}><option value="all">All days</option>{WEEKDAYS.map((day, index) => <option key={day} value={String(index)}>{day}</option>)}</select></label>
      <section aria-label="Weekly schedule overview" style={{ marginBottom: 20 }}>
        <h3>Weekly overview</h3>
        {WEEKDAYS.map((day, weekday) => (
          <p key={day}><strong>{day}:</strong> {marketNamesForDay(markets.map((market) => ({ ...market, schedule_days: draftDays[market.id] ?? market.schedule_days })), weekday).join(', ') || 'No market recorded'}</p>
        ))}
      </section>
      <form onSubmit={createMarket} style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', marginBottom: 20 }}>
        <label>Market code<input required minLength={2} maxLength={40} pattern="[A-Za-z0-9-]+" value={code} onChange={(event) => setCode(event.target.value)} /></label>
        <label>Market name (English)<input required maxLength={120} value={name} onChange={(event) => setName(event.target.value)} /></label>
        <label>Market name (Amharic)<input required maxLength={120} value={nameAm} onChange={(event) => setNameAm(event.target.value)} /></label>
        <label>Description (English)<textarea maxLength={2000} value={description} onChange={(event) => setDescription(event.target.value)} /></label>
        <label>Description (Amharic)<textarea maxLength={2000} value={descriptionAm} onChange={(event) => setDescriptionAm(event.target.value)} /></label>
        <label>Address (English)<input maxLength={500} value={addressEn} onChange={(event) => setAddressEn(event.target.value)} /></label>
        <label>Address (Amharic)<input maxLength={500} value={addressAm} onChange={(event) => setAddressAm(event.target.value)} /></label>
        <label>Latitude<input type="number" min="-90" max="90" step="any" value={latitude} onChange={(event) => setLatitude(event.target.value)} /></label>
        <label>Longitude<input type="number" min="-180" max="180" step="any" value={longitude} onChange={(event) => setLongitude(event.target.value)} /></label>
        <label>Verified location (optional)
          <select value={locationId} onChange={(event) => setLocationId(event.target.value)}>
            <option value="">Not assigned</option>
            {locations.map((location) => <option key={location.id} value={location.id}>{location.name} · {location.level}</option>)}
          </select>
        </label>
        <button type="submit" disabled={busy}>Add market</button>
      </form>
      {markets.filter((market) => (!search.trim() || `${market.name} ${market.code} ${market.description ?? ''}`.toLowerCase().includes(search.trim().toLowerCase())) && (weekdayFilter === 'all' || (draftDays[market.id] ?? market.schedule_days).includes(Number(weekdayFilter)))).map((market) => (
        <article key={market.id} style={{ border: '1px solid #ddd', borderRadius: 12, padding: 16, marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
            <div><h3>{market.name}</h3><small>{market.code} · {market.is_active ? 'Active' : 'Inactive'}</small></div>
            <button type="button" disabled={busy} onClick={() => toggleStatus(market)}>{market.is_active ? 'Deactivate' : 'Activate'}</button>
          </div>
          <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', margin: '14px 0' }}>
            <label>Market name (English)
              <input
                maxLength={120}
                value={draftNames[market.id] ?? market.name}
                onChange={(event) => setDraftNames((current) => ({ ...current, [market.id]: event.target.value }))}
              />
            </label>
            <label>Market name (Amharic)
              <input maxLength={120} value={draftNamesAm[market.id] ?? market.name_am ?? ''} onChange={(event) => setDraftNamesAm((current) => ({ ...current, [market.id]: event.target.value }))} />
            </label>
            <label>Description (English)
              <textarea maxLength={2000} value={draftDescriptions[market.id] ?? market.description ?? ''} onChange={(event) => setDraftDescriptions((current) => ({ ...current, [market.id]: event.target.value }))} />
            </label>
            <label>Description (Amharic)
              <textarea maxLength={2000} value={draftDescriptionsAm[market.id] ?? market.description_am ?? ''} onChange={(event) => setDraftDescriptionsAm((current) => ({ ...current, [market.id]: event.target.value }))} />
            </label>
            <label>Address (English)
              <input maxLength={500} value={draftAddressesEn[market.id] ?? market.address_en ?? ''} onChange={(event) => setDraftAddressesEn((current) => ({ ...current, [market.id]: event.target.value }))} />
            </label>
            <label>Address (Amharic)
              <input maxLength={500} value={draftAddressesAm[market.id] ?? market.address_am ?? ''} onChange={(event) => setDraftAddressesAm((current) => ({ ...current, [market.id]: event.target.value }))} />
            </label>
            <label>Latitude
              <input type="number" min="-90" max="90" step="any" value={draftLatitudes[market.id] ?? ''} onChange={(event) => setDraftLatitudes((current) => ({ ...current, [market.id]: event.target.value }))} />
            </label>
            <label>Longitude
              <input type="number" min="-180" max="180" step="any" value={draftLongitudes[market.id] ?? ''} onChange={(event) => setDraftLongitudes((current) => ({ ...current, [market.id]: event.target.value }))} />
            </label>
            <label>Verified location
              <select
                value={draftLocations[market.id] ?? market.location_id ?? ''}
                onChange={(event) => setDraftLocations((current) => ({ ...current, [market.id]: event.target.value }))}
              >
                <option value="">Not assigned</option>
                {locations.map((location) => <option key={location.id} value={location.id}>{location.name} · {location.level}</option>)}
              </select>
            </label>
            <button type="button" disabled={busy} onClick={() => saveDetails(market)}>Save market details</button>
          </div>
          <fieldset>
            <legend>Weekly market days</legend>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
              {WEEKDAYS.map((day, weekday) => (
                <label key={day} style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
                  <input
                    type="checkbox"
                    checked={(draftDays[market.id] ?? []).includes(weekday)}
                    onChange={(event) => setDraftDays((current) => ({
                      ...current,
                      [market.id]: event.target.checked
                        ? [...(current[market.id] ?? []), weekday].sort((a, b) => a - b)
                        : (current[market.id] ?? []).filter((value) => value !== weekday),
                    }))}
                  />
                  {day}
                </label>
              ))}
            </div>
          </fieldset>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 10 }}>
            <label>Effective from<input type="date" value={effectiveFrom[market.id] ?? ''} onChange={(event) => setEffectiveFrom((current) => ({ ...current, [market.id]: event.target.value }))} /></label>
            <label>Effective until<input type="date" value={effectiveUntil[market.id] ?? ''} onChange={(event) => setEffectiveUntil((current) => ({ ...current, [market.id]: event.target.value }))} /></label>
          </div>
          <button type="button" disabled={busy} onClick={() => saveDays(market)}>Save schedule</button>
        </article>
      ))}
      <section aria-label="Market audit history"><h3>Recent administrator changes</h3>{auditEvents.length === 0 ? <p>No market changes recorded.</p> : <ol>{auditEvents.map((event) => <li key={event.id}><strong>{event.action}</strong> · {event.resource_id} · {new Date(event.created_at).toLocaleString()}</li>)}</ol>}</section>
      {markets.length === 0 && <p>No markets configured.</p>}
      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
    </section>
  );
}
