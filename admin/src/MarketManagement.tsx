import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { marketNamesForDay, WEEKDAYS } from './marketSchedule';

type Market = {
  id: string;
  code: string;
  name: string;
  location_id: string | null;
  is_active: boolean;
  schedule_days: number[];
};
type Location = { id: string; name: string; level: string };

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1').replace(/\/$/, '');
const headers = (token: string) => ({ Authorization: `Bearer ${token}` });

export default function MarketManagement({ accessToken }: { accessToken: string }) {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [locationId, setLocationId] = useState('');
  const [draftDays, setDraftDays] = useState<Record<string, number[]>>({});
  const [draftNames, setDraftNames] = useState<Record<string, string>>({});
  const [draftLocations, setDraftLocations] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [marketResponse, locationResponse] = await Promise.all([
      fetch(`${API_BASE}/admin/markets`, { headers: headers(accessToken) }),
      fetch(`${API_BASE}/locations?lang=en`, { headers: headers(accessToken) }),
    ]);
    if (!marketResponse.ok) throw new Error('Could not load market directory.');
    if (!locationResponse.ok) throw new Error('Could not load geographic locations.');
    const rows = await marketResponse.json() as Market[];
    setMarkets(rows);
    setDraftDays(Object.fromEntries(rows.map((market) => [market.id, market.schedule_days])));
    setDraftNames(Object.fromEntries(rows.map((market) => [market.id, market.name])));
    setDraftLocations(Object.fromEntries(rows.map((market) => [market.id, market.location_id ?? ''])));
    setLocations(await locationResponse.json() as Location[]);
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
        body: JSON.stringify({ code: code.trim().toUpperCase(), name: name.trim(), location_id: locationId || null }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({})) as { detail?: string };
        throw new Error(body.detail ?? 'Could not create market.');
      }
      setCode(''); setName(''); setLocationId('');
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
        body: JSON.stringify({ days: draftDays[market.id] ?? [] }),
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
      <section aria-label="Weekly schedule overview" style={{ marginBottom: 20 }}>
        <h3>Weekly overview</h3>
        {WEEKDAYS.map((day, weekday) => (
          <p key={day}><strong>{day}:</strong> {marketNamesForDay(markets.map((market) => ({ ...market, schedule_days: draftDays[market.id] ?? market.schedule_days })), weekday).join(', ') || 'No market recorded'}</p>
        ))}
      </section>
      <form onSubmit={createMarket} style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', marginBottom: 20 }}>
        <label>Market code<input required minLength={2} maxLength={40} pattern="[A-Za-z0-9-]+" value={code} onChange={(event) => setCode(event.target.value)} /></label>
        <label>Market name<input required maxLength={120} value={name} onChange={(event) => setName(event.target.value)} /></label>
        <label>Verified location (optional)
          <select value={locationId} onChange={(event) => setLocationId(event.target.value)}>
            <option value="">Not assigned</option>
            {locations.map((location) => <option key={location.id} value={location.id}>{location.name} · {location.level}</option>)}
          </select>
        </label>
        <button type="submit" disabled={busy}>Add market</button>
      </form>
      {markets.map((market) => (
        <article key={market.id} style={{ border: '1px solid #ddd', borderRadius: 12, padding: 16, marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
            <div><h3>{market.name}</h3><small>{market.code} · {market.is_active ? 'Active' : 'Inactive'}</small></div>
            <button type="button" disabled={busy} onClick={() => toggleStatus(market)}>{market.is_active ? 'Deactivate' : 'Activate'}</button>
          </div>
          <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', margin: '14px 0' }}>
            <label>Market name
              <input
                maxLength={120}
                value={draftNames[market.id] ?? market.name}
                onChange={(event) => setDraftNames((current) => ({ ...current, [market.id]: event.target.value }))}
              />
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
          <button type="button" disabled={busy} onClick={() => saveDays(market)}>Save schedule</button>
        </article>
      ))}
      {markets.length === 0 && <p>No markets configured.</p>}
      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
    </section>
  );
}
