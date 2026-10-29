"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

type Patient = { id: number; name: string; mrn?: string|null; dob?: string|null; contact?: string|null; created_at: string };
type Consultation = { id: number; patient_id?: number|null; patient_name?: string|null; transcript?: string|null; audio_url?: string|null; created_at: string; consent_given?: boolean|null };
type Note = { id: number; text: string; consultation_id?: number | null; updated_at: string };
type PatientWithCount = Patient & { consultationCount: number };

const generatePatientId = () => {
  const stamp = Date.now().toString(36).toUpperCase();
  return `DERM-${stamp.slice(-6)}`;
};

export default function Dashboard() {
  const router = useRouter();
  const base = process.env.NEXT_PUBLIC_API_BASE_URL!;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);

  const [newPatientName, setNewPatientName] = useState("");
  const [newPatientDob, setNewPatientDob] = useState("");
  const [newPatientContact, setNewPatientContact] = useState("");
  const [newPatientId, setNewPatientId] = useState(() => generatePatientId());
  const [patientSearch, setPatientSearch] = useState("");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [noteText, setNoteText] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editText, setEditText] = useState("");
  const deletePatient = async (id: number) => {
    if (!confirm('Delete this patient? This will also remove consultations and notes.')) return;
    const res = await fetch(`${base}/patients/${id}`, { method: 'DELETE', credentials: 'include' });
    if (res.status === 401) { router.replace('/login'); return; }
    if (!res.ok) { alert('Failed to delete patient'); return; }
    load();
  };

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const meRes = await fetch(`${base}/me`, { credentials: "include" });
      if (meRes.status === 401) { router.replace('/login'); return; }
      if (!meRes.ok) throw new Error('Failed to verify session');
      const [pRes, cRes, nRes] = await Promise.all([
        fetch(`${base}/patients`, { credentials: 'include' }),
        fetch(`${base}/consultations`, { credentials: 'include' }),
        fetch(`${base}/notes`, { credentials: 'include' }),
      ]);
      if (!pRes.ok || !cRes.ok || !nRes.ok) throw new Error('Failed to load data');
      setPatients(await pRes.json());
      setConsultations(await cRes.json());
      setNotes(await nRes.json());
    } catch (e) {
      setError((e as Error)?.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const consultationCounts = useMemo(() => {
    const counts = new Map<number, number>();
    consultations.forEach((c) => {
      if (!c.patient_id) return;
      counts.set(c.patient_id, (counts.get(c.patient_id) ?? 0) + 1);
    });
    return counts;
  }, [consultations]);

  const filteredPatients = useMemo<PatientWithCount[]>(() => {
    const term = patientSearch.trim().toLowerCase();
    const augmented: PatientWithCount[] = patients.map((p) => ({
      ...p,
      consultationCount: consultationCounts.get(p.id) ?? 0,
    }));
    const bySearch = term
      ? augmented.filter((p) => {
          const nameMatch = p.name.toLowerCase().includes(term);
          const idMatch = (p.mrn ?? "").toLowerCase().includes(term);
          return nameMatch || idMatch;
        })
      : augmented;
    const sorted = [...bySearch].sort((a, b) => {
      if (sortOrder === "asc") {
        return a.consultationCount - b.consultationCount;
      }
      return b.consultationCount - a.consultationCount;
    });
    return sorted;
  }, [patients, consultationCounts, patientSearch, sortOrder]);

  const summarizeTranscript = (text?: string | null): string => {
    if (!text) return "No transcript available yet.";
    const singleLine = text.replace(/\s+/g, " ").trim();
    if (!singleLine) return "No transcript available yet.";
    if (singleLine.length <= 140) return singleLine;
    const truncated = singleLine.slice(0, 140);
    const lastSpace = truncated.lastIndexOf(" ");
    return `${lastSpace > 80 ? truncated.slice(0, lastSpace) : truncated}…`;
  };

  const addPatient = async () => {
    const name = newPatientName.trim();
    if (!name) return;
    const payload = {
      name,
      dob: newPatientDob.trim() || null,
      contact: newPatientContact.trim() || null,
      mrn: newPatientId.trim() || null,
    };
    const res = await fetch(`${base}/patients`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
      body: JSON.stringify(payload)
    });
    if (res.status === 401) { router.replace('/login'); return; }
    if (!res.ok) { alert('Failed to add patient'); return; }
    setNewPatientName('');
    setNewPatientDob('');
    setNewPatientContact('');
    setNewPatientId(generatePatientId());
    load();
  };

  const addNote = async () => {
    if (!noteText.trim()) return;
    const res = await fetch(`${base}/notes`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
      body: JSON.stringify({ text: noteText, consultation_id: null })
    });
    if (res.status === 401) { router.replace('/login'); return; }
    if (!res.ok) { alert('Failed to save note'); return; }
    setNoteText('');
    load();
  };

  const startEdit = (note: Note) => { setEditingId(note.id); setEditText(note.text); };
  const cancelEdit = () => { setEditingId(null); setEditText(''); };
  const saveEdit = async (id: number) => {
    if (!editText.trim()) { alert('Note cannot be empty'); return; }
    const res = await fetch(`${base}/notes/${id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
      body: JSON.stringify({ text: editText, consultation_id: notes.find(n=>n.id===id)?.consultation_id ?? null })
    });
    if (res.status === 401) { router.replace('/login'); return; }
    if (!res.ok) { alert('Failed to update note'); return; }
    setEditingId(null); setEditText(''); load();
  };
  const deleteNote = async (id: number) => {
    if (!confirm('Delete this note?')) return;
    const res = await fetch(`${base}/notes/${id}`, { method: 'DELETE', credentials: 'include' });
    if (res.status === 401) { router.replace('/login'); return; }
    if (!res.ok) { alert('Failed to delete note'); return; }
    setNotes(prev => prev.filter(n => n.id !== id));
  };

  if (loading) return <main className="max-w-4xl mx-auto p-6">Loading…</main>;
  if (error) return <main className="max-w-4xl mx-auto p-6 text-red-700">{error}</main>;

  return (
    <main className="max-w-4xl mx-auto p-6 space-y-8">

      <section className="space-y-4">
        <div className="space-y-4 rounded-md border border-gray-200 bg-white p-4 shadow-sm">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold">Patients</h2>
            <p className="text-sm text-gray-600">Capture key demographics and assign an ID before consultations.</p>
          </div>
          <form
            className="grid gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              addPatient();
            }}
          >
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-1">
                <span className="text-sm font-medium text-gray-700">Full Name</span>
                <input
                  required
                  value={newPatientName}
                  onChange={(e) => setNewPatientName(e.target.value)}
                  placeholder="e.g. Jane Smith"
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
              </label>
              <label className="space-y-1">
                <span className="text-sm font-medium text-gray-700">Patient ID</span>
                <div className="flex gap-2">
                  <input
                    value={newPatientId}
                    onChange={(e) => setNewPatientId(e.target.value.toUpperCase())}
                    className="w-full rounded border border-gray-300 px-3 py-2 text-sm uppercase shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                  />
                  <button
                    type="button"
                    onClick={() => setNewPatientId(generatePatientId())}
                    className="shrink-0 rounded border border-gray-300 px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-100"
                  >
                    Refresh
                  </button>
                </div>
              </label>
              <label className="space-y-1">
                <span className="text-sm font-medium text-gray-700">Date of Birth</span>
                <input
                  type="date"
                  value={newPatientDob}
                  onChange={(e) => setNewPatientDob(e.target.value)}
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
              </label>
              <label className="space-y-1">
                <span className="text-sm font-medium text-gray-700">Contact Number</span>
                <input
                  type="tel"
                  value={newPatientContact}
                  onChange={(e) => setNewPatientContact(e.target.value)}
                  placeholder="e.g. +1 555 123 4567"
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
              </label>
            </div>
            <div className="flex justify-end">
              <button
                type="submit"
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
              >
                Add Patient
              </button>
            </div>
          </form>
        </div>

        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <input
            value={patientSearch}
            onChange={(e) => setPatientSearch(e.target.value)}
            placeholder="Search patients by name or ID…"
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200 md:max-w-xs"
          />
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <span>Sort by consultations</span>
            <select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value as "asc" | "desc")}
              className="rounded border border-gray-300 bg-white px-2 py-1 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="desc">High → Low</option>
              <option value="asc">Low → High</option>
            </select>
          </label>
        </div>

        {patients.length === 0 ? (
          <p className="text-sm text-gray-600">No patients yet.</p>
        ) : filteredPatients.length === 0 ? (
          <p className="text-sm text-gray-600">No patients matched your search.</p>
        ) : (
          <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {filteredPatients.map((p) => (
              <li key={p.id} className="space-y-2 rounded-md border border-gray-200 bg-white p-3 shadow-sm">
                <div className="flex items-start justify-between">
                  <a className="font-medium text-blue-700 underline" href={`/patients/${p.id}`}>{p.name}</a>
                  <button onClick={() => deletePatient(p.id)} className="text-xs text-red-700 underline">Delete</button>
                </div>
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>Added {new Date(p.created_at).toLocaleDateString()}</span>
                  <span>{p.consultationCount} consultations</span>
                </div>
                {p.mrn ? <div className="text-sm"><span className="font-medium">Patient ID:</span> {p.mrn}</div> : null}
                {p.dob ? <div className="text-sm"><span className="font-medium">DOB:</span> {p.dob}</div> : null}
                {p.contact ? <div className="text-sm"><span className="font-medium">Contact:</span> {p.contact}</div> : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Recent Consultations</h2>
        {consultations.length === 0 ? (
          <p className="text-sm text-gray-600">No consultations yet.</p>
        ) : (
          <ul className="space-y-3">
            {consultations.map(c => (
              <li key={c.id} className="border rounded p-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-800" title={c.transcript || undefined}>
                      {summarizeTranscript(c.transcript)}
                    </p>
                    <div className="text-xs text-gray-500">Recorded {new Date(c.created_at).toLocaleString()}</div>
                    <div className="text-sm">Patient: {c.patient_name || '—'}</div>
                  </div>
                  {c.consent_given !== undefined && c.consent_given !== null && (
                    <span
                      className={`text-xs font-semibold px-2 py-1 rounded ${
                        c.consent_given
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                      title={c.consent_given ? 'Patient consent obtained' : 'No consent recorded'}
                    >
                      {c.consent_given ? '✓ Consent' : '✗ No Consent'}
                    </span>
                  )}
                </div>
                {c.audio_url ? (
                  <audio controls className="mt-2 w-full" src={c.audio_url.startsWith('http') ? c.audio_url : `${base}${c.audio_url}`}></audio>
                ) : (
                  <div className="text-xs text-gray-500 mt-2">No audio recorded</div>
                )}
                {c.transcript ? (
                  <details className="mt-2 text-sm">
                    <summary className="cursor-pointer text-blue-700">Transcript</summary>
                    <div className="whitespace-pre-wrap mt-1">{c.transcript}</div>
                  </details>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Notes</h2>
        <div className="space-y-2">
          <textarea className="w-full border p-2 rounded" rows={3} placeholder="Quick note…" value={noteText} onChange={e=>setNoteText(e.target.value)} />
          <button className="rounded bg-black text-white px-4 py-2" onClick={addNote}>Add note</button>
        </div>
        <ul className="divide-y divide-gray-200">
          {notes.map(n => (
            <li key={n.id} className="py-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="text-sm text-gray-500">Updated: {new Date(n.updated_at).toLocaleString()}</div>
                  {editingId === n.id ? (
                    <textarea className="mt-2 w-full border p-2 rounded" rows={3} value={editText} onChange={(e)=>setEditText(e.target.value)} />
                  ) : (
                    <div className="whitespace-pre-wrap mt-1">{n.text}</div>
                  )}
                </div>
                <div className="shrink-0 flex flex-col gap-2">
                  {editingId === n.id ? (
                    <>
                      <button className="text-xs bg-green-600 text-white rounded px-2 py-1" onClick={()=>saveEdit(n.id)}>Save</button>
                      <button className="text-xs text-gray-700 underline" onClick={cancelEdit}>Cancel</button>
                    </>
                  ) : (
                    <>
                      <button className="text-xs bg-gray-800 text-white rounded px-2 py-1" onClick={()=>startEdit(n)}>Edit</button>
                      <button className="text-xs text-red-700 underline" onClick={()=>deleteNote(n.id)}>Delete</button>
                    </>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
