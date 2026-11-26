import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';

type Location = {
  id: string; parent_id: string | null; code: string; level: string;
  name_en: string; name_am: string; description_en: string | null; description_am: string | null;
  address_en: string | null; address_am: string | null; latitude: number | null; longitude: number | null;
  tags: string[]; is_active: boolean;
};
type Draft = Omit<Location, 'id'>;
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1').replace(/\/$/, '');
const TAGS = [
  ['product', 'Products / ምርቶች'], ['service', 'Services / አገልግሎቶች'],
  ['market', 'Markets / ገበያዎች'], ['transport', 'Transport / ትራንስፖርት'],
  ['health', 'Health / ጤና'], ['education', 'Education / ትምህርት'],
  ['agriculture', 'Agriculture / ግብርና'], ['tourism', 'Tourism / ቱሪዝም'],
  ['public_service', 'Public services / ሕዝብ አገልግሎት'],
  ['finance', 'Finance / ፋይናንስ'], ['other', 'Other / ሌላ'],
] as const;
const emptyDraft = (): Draft => ({
  parent_id: null, code: '', level: 'locality', name_en: '', name_am: '',
  description_en: null, description_am: null, address_en: null, address_am: null,
  latitude: null, longitude: null, tags: [], is_active: true,
});
const auth = (token: string) => ({ Authorization: `Bearer ${token}` });

export default function LocationManagement({ accessToken }: { accessToken: string }) {
  const [rows, setRows] = useState<Location[]>([]);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [createDraft, setCreateDraft] = useState<Draft>(emptyDraft());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    const response = await fetch(`${API_BASE}/admin/locations`, { headers: auth(accessToken) });
    if (!response.ok) throw new Error(response.status === 403 ? 'Administrator access required.' : 'Could not load locations.');
    const data = await response.json() as Location[];
    setRows(data);
    setDrafts(Object.fromEntries(data.map((row) => [row.id, {
      parent_id: row.parent_id, code: row.code, level: row.level,
      name_en: row.name_en, name_am: row.name_am,
      description_en: row.description_en, description_am: row.description_am,
      address_en: row.address_en, address_am: row.address_am,
      latitude: row.latitude, longitude: row.longitude, tags: row.tags ?? [], is_active: row.is_active,
    }])));
  }, [accessToken]);

  useEffect(() => { load().catch((reason: unknown) => setError(String(reason))); }, [load]);

  function changeDraft(id: string, key: keyof Draft, value: unknown) {
    setDrafts((current) => ({ ...current, [id]: { ...current[id], [key]: value } }));
  }
  function changeCreate(key: keyof Draft, value: unknown) {
    setCreateDraft((current) => ({ ...current, [key]: value }));
  }
  function toggleTag(tags: string[], tag: string) {
    return tags.includes(tag) ? tags.filter((item) => item !== tag) : [...tags, tag];
  }
  async function saveCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(''); setMessage('');
    try {
      const response = await fetch(`${API_BASE}/admin/locations`, {
        method: 'POST', headers: { ...auth(accessToken), 'Content-Type': 'application/json' },
        body: JSON.stringify(createDraft),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({})) as { detail?: string };
        throw new Error(body.detail ?? 'Could not create location.');
      }
      setCreateDraft(emptyDraft()); await load(); setMessage('Location created.');
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Location creation failed.'); }
    finally { setBusy(false); }
  }
  async function save(row: Location) {
    setBusy(true); setError(''); setMessage('');
    try {
      const draft = drafts[row.id];
      const response = await fetch(`${API_BASE}/admin/locations/${row.id}`, {
        method: 'PATCH', headers: { ...auth(accessToken), 'Content-Type': 'application/json' },
        body: JSON.stringify(draft),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({})) as { detail?: string };
        throw new Error(body.detail ?? 'Could not save location.');
      }
      await load(); setMessage(`Saved ${draft.name_en} / ${draft.name_am}.`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Location update failed.'); }
    finally { setBusy(false); }
  }
  async function toggleActive(row: Location) {
    setBusy(true); setError(''); setMessage('');
    try {
      const response = await fetch(`${API_BASE}/admin/locations/${row.id}/status`, {
        method: 'PATCH', headers: { ...auth(accessToken), 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !row.is_active }),
      });
      if (!response.ok) throw new Error('Could not update location status.');
      await load(); setMessage(`${row.name_en} ${row.is_active ? 'deactivated' : 'activated'}.`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Status update failed.'); }
    finally { setBusy(false); }
  }

  function fields(draft: Draft, onChange: (key: keyof Draft, value: unknown) => void, lockedCode = false, excludeId?: string) {
    return <>
      <label>Location level<select value={draft.level} onChange={(e) => onChange('level', e.target.value)}>
        {['zone', 'woreda', 'town', 'locality'].map((level) => <option key={level} value={level}>{level}</option>)}
      </select></label>
      <label>Parent location<select value={draft.parent_id ?? ''} onChange={(e) => onChange('parent_id', e.target.value || null)}>
        <option value="">No parent (zone only)</option>
        {rows.filter((item) => item.is_active && item.id !== excludeId).map((item) =>
          <option key={item.id} value={item.id}>{item.name_en} / {item.name_am} · {item.level}</option>)}
      </select></label>
      <label>Code<input required disabled={lockedCode} value={draft.code} onChange={(e) => onChange('code', e.target.value.toUpperCase())} maxLength={80} /></label>
      <label>English name<input required value={draft.name_en} onChange={(e) => onChange('name_en', e.target.value)} maxLength={120} /></label>
      <label>Amharic name<input required value={draft.name_am} onChange={(e) => onChange('name_am', e.target.value)} maxLength={120} /></label>
      <label>Description (English)<textarea value={draft.description_en ?? ''} onChange={(e) => onChange('description_en', e.target.value || null)} maxLength={4000} /></label>
      <label>Description (Amharic)<textarea value={draft.description_am ?? ''} onChange={(e) => onChange('description_am', e.target.value || null)} maxLength={4000} /></label>
      <label>Address (English)<input value={draft.address_en ?? ''} onChange={(e) => onChange('address_en', e.target.value || null)} maxLength={500} /></label>
      <label>Address (Amharic)<input value={draft.address_am ?? ''} onChange={(e) => onChange('address_am', e.target.value || null)} maxLength={500} /></label>
      <label>Latitude<input type="number" min="-90" max="90" step="any" value={draft.latitude ?? ''} onChange={(e) => onChange('latitude', e.target.value === '' ? null : Number(e.target.value))} /></label>
      <label>Longitude<input type="number" min="-180" max="180" step="any" value={draft.longitude ?? ''} onChange={(e) => onChange('longitude', e.target.value === '' ? null : Number(e.target.value))} /></label>
      <fieldset style={{ gridColumn: '1 / -1', display: 'flex', flexWrap: 'wrap', gap: 12 }}>
        <legend>Location tags · What is available here?</legend>
        {TAGS.map(([tag, label]) => <label key={tag} style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
          <input type="checkbox" checked={draft.tags.includes(tag)} onChange={() => onChange('tags', toggleTag(draft.tags, tag))} />{label}
        </label>)}
      </fieldset>
    </>;
  }

  return <section aria-labelledby="location-management-title" style={{ marginTop: 32 }}>
    <h2 id="location-management-title">Geographic locations · የአካባቢ አስተዳደር</h2>
    <p>Maintain the official English and Amharic names, hierarchy, descriptions, addresses, map coordinates and service/product tags. Changes are audit-logged.</p>
    {error && <p role="alert" style={{ color: '#b42318' }}>{error}</p>}
    {message && <p role="status">{message}</p>}
    <form onSubmit={saveCreate} style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', border: '1px solid #ddd', borderRadius: 12, padding: 16 }}>
      <h3 style={{ gridColumn: '1 / -1' }}>Add location</h3>
      {fields(createDraft, changeCreate)}
      <button type="submit" disabled={busy}>Create location</button>
    </form>
    <h3>Existing locations ({rows.length})</h3>
    <div style={{ display: 'grid', gap: 14 }}>
      {rows.map((row) => {
        const draft = drafts[row.id];
        if (!draft) return null;
        return <article key={row.id} style={{ border: '1px solid #ddd', borderRadius: 12, padding: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
            <strong>{row.code} · {row.level}</strong>
            <span>{row.is_active ? 'Active' : 'Inactive'}</span>
          </div>
          <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', marginTop: 12 }}>
            {fields(draft, (key, value) => changeDraft(row.id, key, value), true, row.id)}
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <button disabled={busy} onClick={() => save(row)}>Save changes</button>
            <button disabled={busy} onClick={() => toggleActive(row)}>{row.is_active ? 'Deactivate' : 'Activate'}</button>
          </div>
        </article>;
      })}
    </div>
  </section>;
}
