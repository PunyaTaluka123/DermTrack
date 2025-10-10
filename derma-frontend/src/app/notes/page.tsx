"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Note = { id: number; text: string; consultation_id?: string | null; updated_at: string };

export default function Notes() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [text, setText] = useState("");

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
    } catch (e: any) {
      setError(e?.message || "Failed to load");
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

      <div className="space-y-2">
        <textarea className="w-full border p-2 rounded" rows={4} placeholder="Write a note..." value={text} onChange={(e)=>setText(e.target.value)} />
        <button className="rounded bg-black text-white px-4 py-2" onClick={add}>Add note</button>
      </div>

      <ul className="divide-y divide-gray-200">
        {notes.map(n => (
          <li key={n.id} className="py-3">
            <div className="text-sm text-gray-500">Updated: {new Date(n.updated_at).toLocaleString()}</div>
            <div className="whitespace-pre-wrap">{n.text}</div>
          </li>
        ))}
      </ul>
    </main>
  );
}
