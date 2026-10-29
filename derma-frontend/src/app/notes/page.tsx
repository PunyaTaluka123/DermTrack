"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Note = { id: number; text: string; consultation_id?: number | null; updated_at: string };
type Consultation = { id: number; doctor?: string|null; patient?: string|null; transcript?: string|null; audio_url?: string|null; created_at: string };

export default function Notes() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [text, setText] = useState("");
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editText, setEditText] = useState("");

  const base = process.env.NEXT_PUBLIC_API_BASE_URL!;

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const meRes = await fetch(`${base}/me`, { credentials: "include" });
      if (meRes.status === 401) {
        router.replace("/login");
        return;
      }
      if (!meRes.ok) throw new Error("Failed to verify session");
      const res = await fetch(`${base}/notes`, { credentials: "include" });
      if (!res.ok) throw new Error("Failed to fetch notes");
      setNotes(await res.json());
      const cRes = await fetch(`${base}/consultations`, { credentials: "include" });
      if (!cRes.ok) throw new Error("Failed to fetch consultations");
      setConsultations(await cRes.json());
    } catch (e) {
      setError((e as Error)?.message || "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const add = async () => {
    if (!text.trim()) return;
    const res = await fetch(`${base}/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ text, consultation_id: null }),
    });
    if (res.status === 401) {
      router.replace("/login");
      return;
    }
    if (!res.ok) {
      alert("Failed to save note");
      return;
    }
    setText("");
    load();
  };

  const logout = async () => {
    await fetch(`${base}/auth/logout`, { method: "POST", credentials: "include" });
    router.replace("/login");
  };

  const startEdit = (note: Note) => {
    setEditingId(note.id);
    setEditText(note.text);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditText("");
  };

  const saveEdit = async (id: number) => {
    if (!editText.trim()) {
      alert("Note cannot be empty");
      return;
    }
    const res = await fetch(`${base}/notes/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ text: editText, consultation_id: notes.find(n=>n.id===id)?.consultation_id ?? null })
    });
    if (res.status === 401) {
      router.replace('/login');
      return;
    }
    if (!res.ok) {
      alert("Failed to update note");
      return;
    }
    setEditingId(null);
    setEditText("");
    load();
  };

  const deleteNote = async (id: number) => {
    if (!confirm("Delete this note?")) return;
    const res = await fetch(`${base}/notes/${id}`, { method: 'DELETE', credentials: 'include' });
    if (res.status === 401) {
      router.replace('/login');
      return;
    }
    if (!res.ok) {
      alert("Failed to delete note");
      return;
    }
    // Optimistically remove or reload
    setNotes(prev => prev.filter(n => n.id !== id));
  };

  if (loading) return <main className="max-w-2xl mx-auto p-6">Loading...</main>;
  if (error) return <main className="max-w-2xl mx-auto p-6 text-red-700">{error}</main>;

  return (
    <main className="max-w-2xl mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-semibold">My Notes</h2>
        <div className="flex items-center gap-4">
          <button onClick={() => router.push('/consult')} className="text-sm bg-blue-600 text-white rounded px-3 py-1">Start Transcription</button>
          <button onClick={logout} className="text-sm text-gray-700 underline">Logout</button>
        </div>
      </div>

      <section className="space-y-3">
        <h3 className="text-lg font-semibold">Consultations</h3>
        {consultations.length === 0 ? (
          <p className="text-gray-600 text-sm">No consultations yet.</p>
        ) : (
          <ul className="space-y-3">
            {consultations.map(c => (
              <li key={c.id} className="border rounded p-3">
                <div className="text-sm text-gray-500">{new Date(c.created_at).toLocaleString()}</div>
                <div className="text-sm">Doctor: {c.doctor || '—'} | Patient: {c.patient || '—'}</div>
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

      <div className="space-y-2">
        <textarea className="w-full border p-2 rounded" rows={4} placeholder="Write a note..." value={text} onChange={(e)=>setText(e.target.value)} />
        <button className="rounded bg-black text-white px-4 py-2" onClick={add}>Add note</button>
      </div>

      <ul className="divide-y divide-gray-200">
        {notes.map(n => (
          <li key={n.id} className="py-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="text-sm text-gray-500">Updated: {new Date(n.updated_at).toLocaleString()}</div>
                {editingId === n.id ? (
                  <textarea className="mt-2 w-full border p-2 rounded" rows={4} value={editText} onChange={(e)=>setEditText(e.target.value)} />
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
    </main>
  );
}
