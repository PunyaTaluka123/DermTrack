"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

type Patient = { id: number; name: string; mrn?: string|null; dob?: string|null; contact?: string|null; created_at: string };
type Consultation = { id: number; patient_id?: number|null; patient_name?: string|null; transcript?: string|null; audio_url?: string|null; created_at: string };
type Note = { id: number; text: string; consultation_id?: number | null; updated_at: string };

export default function PatientDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const base = process.env.NEXT_PUBLIC_API_BASE_URL!;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const meRes = await fetch(`${base}/me`, { credentials: 'include' });
      if (meRes.status === 401) { router.replace('/login'); return; }
      const [pRes, cRes, nRes] = await Promise.all([
        fetch(`${base}/patients/${id}`, { credentials: 'include' }),
        fetch(`${base}/patients/${id}/consultations`, { credentials: 'include' }),
        fetch(`${base}/patients/${id}/notes`, { credentials: 'include' }),
      ]);
      if (!pRes.ok) throw new Error('Patient not found');
      setPatient(await pRes.json());
      setConsultations(await cRes.json());
      setNotes(await nRes.json());
    } catch (e:any) {
      setError(e?.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (id) load(); }, [id]);

  const deletePatient = async () => {
    if (!confirm('Delete this patient? This will remove their consultations and notes.')) return;
    const res = await fetch(`${base}/patients/${id}`, { method: 'DELETE', credentials: 'include' });
    if (res.status === 401) { router.replace('/login'); return; }
    if (!res.ok) { alert('Failed to delete patient'); return; }
    router.replace('/dashboard');
  };

  if (loading) return <main className="max-w-3xl mx-auto p-6">Loading…</main>;
  if (error) return <main className="max-w-3xl mx-auto p-6 text-red-700">{error}</main>;
  if (!patient) return <main className="max-w-3xl mx-auto p-6">Patient not found.</main>;

  return (
    <main className="max-w-3xl mx-auto p-6 space-y-8">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{patient.name}</h1>
        <div className="flex items-center gap-3">
          <a className="text-sm bg-blue-600 text-white rounded px-3 py-1" href={`/consult?patient_id=${patient.id}`}>Start Consultation</a>
          <button onClick={deletePatient} className="text-sm text-red-700 underline">Delete Patient</button>
          <a className="text-sm text-blue-700 underline" href="/dashboard">Back to Dashboard</a>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="border rounded p-3">
          <div className="text-sm text-gray-500">Created: {new Date(patient.created_at).toLocaleString()}</div>
          {patient.mrn ? <div className="text-sm">Patient ID: {patient.mrn}</div> : null}
          {patient.dob ? <div className="text-sm">DOB: {patient.dob}</div> : null}
          {patient.contact ? <div className="text-sm">Contact: {patient.contact}</div> : null}
        </div>
      </div>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Consultations</h2>
        {consultations.length === 0 ? (
          <p className="text-sm text-gray-600">No consultations yet.</p>
        ) : (
          <ul className="space-y-3">
            {consultations.map(c => (
              <li key={c.id} className="border rounded p-3">
                <div className="text-sm text-gray-500">{new Date(c.created_at).toLocaleString()}</div>
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
        {notes.length === 0 ? (
          <p className="text-sm text-gray-600">No notes yet.</p>
        ) : (
          <ul className="divide-y divide-gray-200">
            {notes.map(n => (
              <li key={n.id} className="py-3">
                <div className="text-sm text-gray-500">Updated: {new Date(n.updated_at).toLocaleString()}</div>
                <div className="whitespace-pre-wrap">{n.text}</div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
