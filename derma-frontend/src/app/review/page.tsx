"use client";
import { useEffect, useMemo, useRef, useState } from "react";

export default function Review() {
    const [text, setText] = useState("");
    const [patients, setPatients] = useState<{id:number; name:string}[]>([]);
    const [patientId, setPatientId] = useState<number | null>(null);
    const [newPatient, setNewPatient] = useState("");
    const [saving, setSaving] = useState(false);
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [loadingSug, setLoadingSug] = useState(false);
    const [sugError, setSugError] = useState<string | null>(null);
    const [liveNotes, setLiveNotes] = useState("");
    const [soapLoading, setSoapLoading] = useState(false);
    const [soapError, setSoapError] = useState<string | null>(null);
    const [soapSections, setSoapSections] = useState<{subjective: string; objective: string; assessment: string; plan: string} | null>(null);
    const isInitialMount = useRef(true);

    useEffect(() => {
        const transcript = sessionStorage.getItem("consultationText") || "";
        const notes = sessionStorage.getItem("consultationLiveNotes") || "";
        console.log("[Review] Loading from sessionStorage:", { transcript: transcript.substring(0, 50), notes: notes.substring(0, 50) });
        setText(transcript);
        try {
            setLiveNotes(notes);
            console.log("[Review] Live notes loaded successfully, length:", notes.length);
        } catch (e) {
            console.error("[Review] Error loading live notes:", e);
            setLiveNotes("");
        }
        const init = async () => {
            const base = process.env.NEXT_PUBLIC_API_BASE_URL!;
            try {
                const res = await fetch(`${base}/patients`, { credentials: 'include' });
                if (res.ok) {
                    const items = await res.json();
                    setPatients(items.map((p:any)=>({id:p.id, name:p.name})));
                    const preset = sessionStorage.getItem('selectedPatientId');
                    if (preset) {
                        const n = Number(preset);
                        if (!Number.isNaN(n)) setPatientId(n);
                    }
                }
            } catch {}
        };
        init();
    }, []);

    useEffect(() => {
        // Skip auto-save on initial mount to prevent overwriting loaded notes
        if (isInitialMount.current) {
            isInitialMount.current = false;
            return;
        }
        try {
            sessionStorage.setItem("consultationLiveNotes", liveNotes);
            console.log("[Review] Auto-saved live notes to sessionStorage, length:", liveNotes.length);
        } catch (e) {
            console.error("[Review] Error auto-saving live notes:", e);
        }
    }, [liveNotes]);

    const soapNote = useMemo(() => {
        if (!soapSections) return "";
        const parts = [
            "Subjective:",
            soapSections.subjective || "—",
            "",
            "Objective:",
            soapSections.objective || "—",
            "",
            "Assessment:",
            soapSections.assessment || "—",
            "",
            "Plan:",
            soapSections.plan || "—",
        ];
        return parts.join("\n").trim();
    }, [soapSections]);

    // Debounced suggestions when text changes
    useEffect(() => {
        const base = process.env.NEXT_PUBLIC_API_BASE_URL!;
        const controller = new AbortController();
        if (!text || !text.trim()) { setSuggestions([]); return; }
        setLoadingSug(true);
        setSugError(null);
        const t = setTimeout(async () => {
            try {
                const res = await fetch(`${base}/suggest_questions`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text, num: 5 }),
                    signal: controller.signal,
                });
                if (res.ok) {
                    const data = await res.json();
                    setSuggestions(Array.isArray(data?.suggestions) ? data.suggestions : []);
                } else {
                    setSugError('Could not load suggestions');
                }
            } catch (e:any) {
                if (e?.name !== 'AbortError') setSugError('Could not load suggestions');
            } finally {
                setLoadingSug(false);
            }
        }, 500);
        return () => { clearTimeout(t); controller.abort(); };
    }, [text]);

    const regenerate = async () => {
        const base = process.env.NEXT_PUBLIC_API_BASE_URL!;
        if (!text || !text.trim()) { setSuggestions([]); return; }
        setLoadingSug(true);
        setSugError(null);
        try {
            const res = await fetch(`${base}/suggest_questions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, num: 5 }),
            });
            if (res.ok) {
                const data = await res.json();
                setSuggestions(Array.isArray(data?.suggestions) ? data.suggestions : []);
            } else {
                setSugError('Could not load suggestions');
            }
        } catch {
            setSugError('Could not load suggestions');
        } finally {
            setLoadingSug(false);
        }
    };

    const runSoapFormatter = async () => {
        const base = process.env.NEXT_PUBLIC_API_BASE_URL;
        if (!base) {
            alert("NEXT_PUBLIC_API_BASE_URL is not set");
            return;
        }
        if (!text.trim() && !liveNotes.trim()) {
            setSoapError("Add transcript or notes before running the formatter.");
            return;
        }
        setSoapLoading(true);
        setSoapError(null);
        try {
            const res = await fetch(`${base}/soap_autofill`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ transcript: text, notes: liveNotes })
            });
            if (!res.ok) {
                let detail = 'Failed to format notes';
                try {
                    const err = await res.json();
                    if (err?.detail) detail = err.detail;
                } catch {}
                throw new Error(detail);
            }
            const data = await res.json();
            setSoapSections({
                subjective: data?.subjective ?? '',
                objective: data?.objective ?? '',
                assessment: data?.assessment ?? '',
                plan: data?.plan ?? '',
            });
        } catch (e:any) {
            setSoapError(e?.message || 'Failed to format notes');
        } finally {
            setSoapLoading(false);
        }
    };

    const applySoapToText = () => {
    if (!soapNote) return;
    const originalTranscript = text;
    const combinedText = originalTranscript.trim()
        ? `${soapNote}\n\n---\n\nOriginal Transcript:\n${originalTranscript}`
        : soapNote;
    setText(combinedText);
};

    const save = async () => {
        const consultation_id = null;
        const base = process.env.NEXT_PUBLIC_API_BASE_URL;
        if (!base) {
            alert("NEXT_PUBLIC_API_BASE_URL is not set");
            return;
        }
        setSaving(true);
        try {
            // Resolve patient selection
            let selectedId = patientId;
            if (!selectedId && newPatient.trim()) {
                const pRes = await fetch(base + "/patients", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    credentials: "include",
                    body: JSON.stringify({ name: newPatient.trim() })
                });
                if (!pRes.ok) {
                    alert("Failed to create patient");
                    return;
                }
                const p = await pRes.json();
                selectedId = p.id;
            }
            // Create consultation first
            const audio_filename = sessionStorage.getItem("consultationAudioFilename") || null;
            const cRes = await fetch(base + "/consultations", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({ patient_id: selectedId, patient_name: (!selectedId && newPatient.trim()) ? newPatient.trim() : null, transcript: text, audio_filename, audio_url: sessionStorage.getItem("consultationAudioUrl") || null })
            });
            if (cRes.status === 401) {
                alert("Please login to save");
                window.location.href = "/login";
                return;
            }
            if (!cRes.ok) {
                alert("Failed to create consultation");
                return;
            }
            const consultation = await cRes.json();
            try { sessionStorage.removeItem('selectedPatientId'); } catch {}
            try { sessionStorage.removeItem('consultationLiveNotes'); } catch {}
            const res = await fetch(base + "/notes", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({ consultation_id: consultation.id, text: (() => {
                    const trimmedNotes = liveNotes.trim();
                    if (!trimmedNotes) return text;
                    const separator = text ? "\n\n" : "";
                    return `${text}${separator}Clinician Notes:\n${trimmedNotes}`;
                })() })
            });
            if (!res.ok) {
                alert("Failed to save note");
                return;
            }
            const data = await res.json();
            alert("Saved note " + data.id);
            window.location.href = "/dashboard";
        } finally {
            setSaving(false);
        }
        };

    return(
        <main className="max-w-2xl mx-auto py-10 px-4 space-y-4">
            <h2 className="text-2xl font-semibold">Review & Save Notes</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                    <label className="text-sm text-gray-700">Select Patient</label>
                    <select className="w-full p-2 border rounded" value={patientId ?? ''} onChange={(e)=>setPatientId(e.target.value ? Number(e.target.value) : null)}>
                        <option value="">-- Choose existing --</option>
                        {patients.map(p => (
                            <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                    </select>
                </div>
                <div>
                    <label className="text-sm text-gray-700">Or add new patient</label>
                    <input className="w-full p-2 border rounded" placeholder="New patient name" value={newPatient} onChange={(e)=>setNewPatient(e.target.value)} />
                </div>
            </div>
            <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">Consultation transcript</label>
                <textarea value={text} onChange={(e) => setText(e.target.value)} rows={10} className="w-full rounded border border-gray-300 p-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200" placeholder="Edit the transcript or paste additional details" />
            </div>
            <div className="space-y-2">
                <div className="flex items-center justify-between">
                    <label className="block text-sm font-medium text-gray-700">Live notes</label>
                    {liveNotes.length > 0 ? (
                        <span className="text-xs text-green-600 font-medium">{liveNotes.length} characters</span>
                    ) : (
                        <span className="text-xs text-gray-500">No notes yet</span>
                    )}
                </div>
                <textarea value={liveNotes} onChange={(e) => setLiveNotes(e.target.value)} rows={6} className="w-full rounded border border-gray-300 p-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200" placeholder="Notes captured during the consultation. These stay synced from the consult page." />
            </div>
            <div className="space-y-2">
                <div className="flex items-center gap-3">
                    <h3 className="text-lg font-semibold">Suggested Next Questions</h3>
                    {loadingSug ? <span className="inline-block h-4 w-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" /> : null}
                    <button type="button" onClick={regenerate} className="text-sm bg-gray-100 text-gray-900 border border-gray-300 rounded px-2 py-1">Regenerate</button>
                </div>
                {sugError ? (
                    <div className="text-sm text-red-700">{sugError}</div>
                ) : null}
                {(!suggestions || suggestions.length === 0) && !loadingSug ? (
                    <p className="text-sm text-gray-600">Type or paste the transcript to see suggestions.</p>
                ) : (
                    <ul className="list-disc pl-5 space-y-1">
                        {suggestions.slice(0,5).map((s, i) => (
                            <li key={i} className="text-sm text-gray-800 flex items-start gap-2">
                                <span className="flex-1">{s}</span>
                                <button type="button" className="text-xs bg-gray-100 text-gray-900 border border-gray-300 rounded px-2 py-0.5" onClick={() => setText(t => (t ? t + "\n" : "") + s)}>Insert</button>
                                <button type="button" className="text-xs text-blue-600 underline" onClick={() => navigator.clipboard?.writeText(s)}>Copy</button>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
            <section className="space-y-3 rounded border border-gray-200 bg-white p-4 shadow-sm">
                <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div>
                        <h3 className="text-lg font-semibold">AI SOAP formatter</h3>
                        <p className="text-sm text-gray-600">Use Gemini to reorganize the transcript and notes into Subjective, Objective, Assessment, and Plan.</p>
                    </div>
                    <button
                        type="button"
                        onClick={runSoapFormatter}
                        disabled={soapLoading}
                        className="rounded border border-blue-600 bg-blue-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {soapLoading ? "Formatting…" : "Format with Gemini"}
                    </button>
                </div>
                {soapError ? <p className="text-sm text-red-700">{soapError}</p> : null}
                {soapSections ? (
                    <div className="space-y-4">
                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="space-y-1">
                                <h4 className="text-sm font-semibold text-gray-800">Subjective</h4>
                                <p className="whitespace-pre-wrap rounded border border-gray-200 bg-gray-50 p-2 text-sm text-gray-800">{soapSections.subjective || '—'}</p>
                            </div>
                            <div className="space-y-1">
                                <h4 className="text-sm font-semibold text-gray-800">Objective</h4>
                                <p className="whitespace-pre-wrap rounded border border-gray-200 bg-gray-50 p-2 text-sm text-gray-800">{soapSections.objective || '—'}</p>
                            </div>
                            <div className="space-y-1">
                                <h4 className="text-sm font-semibold text-gray-800">Assessment</h4>
                                <p className="whitespace-pre-wrap rounded border border-gray-200 bg-gray-50 p-2 text-sm text-gray-800">{soapSections.assessment || '—'}</p>
                            </div>
                            <div className="space-y-1">
                                <h4 className="text-sm font-semibold text-gray-800">Plan</h4>
                                <p className="whitespace-pre-wrap rounded border border-gray-200 bg-gray-50 p-2 text-sm text-gray-800">{soapSections.plan || '—'}</p>
                            </div>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            <button type="button" className="rounded border border-gray-300 px-3 py-1 text-sm text-gray-700 hover:bg-gray-100" onClick={() => { setSoapSections(null); setSoapError(null); }}>Clear</button>
                            <button type="button" className="rounded border border-green-600 bg-green-600 px-3 py-1 text-sm font-medium text-white hover:bg-green-700" onClick={applySoapToText}>Replace transcript with SOAP note</button>
                        </div>
                    </div>
                ) : (
                    <p className="text-sm text-gray-600">Run the formatter to preview SOAP sections you can apply to the note.</p>
                )}
            </section>
            <button onClick={save} disabled={saving} className="rounded bg-black text-white px-4 py-2 disabled:opacity-60">{saving ? 'Saving…' : 'Save note'}</button>
        </main>
    );
}   
