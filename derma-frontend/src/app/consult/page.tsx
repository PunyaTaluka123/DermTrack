"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useSpeechRecognition } from "@/lib/useSpeechRecognition";

export default function Consult() {
  const [recording, setRecording] = useState(false);
  const [status, setStatus] = useState("Idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [checkingAudio, setCheckingAudio] = useState(false);
  const [audioVerified, setAudioVerified] = useState(false);
  const [elapsed, setElapsed] = useState(0); // seconds
  const [liveNotes, setLiveNotes] = useState("");
  const timerRef = useRef<number | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const router = useRouter();
  const search = useSearchParams();

  const {
    supported: speechSupported,
    listening,
    transcript,
    interimTranscript,
    error: speechError,
    start: startSpeech,
    stop: stopSpeech,
    reset: resetSpeech,
  } = useSpeechRecognition({ lang: "en-US" });

  // Visualizer removed per request

  useEffect(() => {
    // Require login before allowing transcription
    const checkAuth = async () => {
      try {
        const base = process.env.NEXT_PUBLIC_API_BASE_URL!;
        const res = await fetch(`${base}/me`, { credentials: 'include' });
        if (res.status === 401) router.replace('/login');
      } catch {
        // if request fails, send to login to be safe
        router.replace('/login');
      }
    };
    checkAuth();
    // Capture patient_id from query and stash for review preselect
    const pid = search?.get('patient_id');
    if (pid) {
      try { sessionStorage.setItem('selectedPatientId', String(parseInt(pid, 10))); } catch {}
    }
    return () => {
      mediaRecorderRef.current?.stream.getTracks().forEach((t) => t.stop());
      stopSpeech();
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [stopSpeech, search]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const stored = sessionStorage.getItem("consultationLiveNotes");
      if (stored) setLiveNotes(stored);
    } catch {
      // ignore storage errors
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      sessionStorage.setItem("consultationLiveNotes", liveNotes);
      console.log("[Consult] Saved live notes to sessionStorage, length:", liveNotes.length);
    } catch (e) {
      console.error("[Consult] Error saving live notes:", e);
    }
  }, [liveNotes]);

  const ensureAudioAccess = useCallback(async () => {
    if (audioVerified) return true;
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setErrorMsg("Microphone access is not supported on this device.");
      return false;
    }
    setCheckingAudio(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());
      setAudioVerified(true);
      setErrorMsg(null);
      return true;
    } catch (err) {
      console.error("Microphone preflight failed", err);
      setErrorMsg("Microphone check failed. Please allow browser access to your microphone.");
      return false;
    } finally {
      setCheckingAudio(false);
    }
  }, [audioVerified]);

  const startRecording = async () => {
    setErrorMsg(null);
    setStatus("Checking microphone…");
    const ready = await ensureAudioAccess();
    if (!ready) {
      setStatus("Idle");
      return;
    }
    // Prefer Web Speech API if supported
    if (speechSupported) {
      resetSpeech();
      setRecording(true);
      setStatus("Listening...");
      setElapsed(0);
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = (setInterval(() => setElapsed((s) => s + 1), 1000) as unknown) as number;
      startSpeech();
      return;
    }

    // Fallback to MediaRecorder + backend transcription
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e: any) {
      setErrorMsg("Microphone access denied or unavailable.");
      setStatus("Idle");
      return;
    }
    const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
    chunksRef.current = [];
    mr.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };
    mr.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      const form = new FormData();
      form.append("audio", blob, "consult.webm");
      setStatus("Transcribing...");
      setErrorMsg(null);
      try {
        const base = process.env.NEXT_PUBLIC_API_BASE_URL;
        if (!base) throw new Error("NEXT_PUBLIC_API_BASE_URL not set");
        const res = await fetch(`${base}/transcribe`, { method: "POST", body: form });
        if (!res.ok) throw new Error(`Transcribe failed: ${res.status}`);
        const data = await res.json();
        const text = data?.text ?? "";
        const audioFilename = data?.audio_filename || "";
        const audioUrl = data?.audio_url || "";
        sessionStorage.setItem("consultationText", text);
        sessionStorage.setItem("consultationAudioFilename", audioFilename);
        if (audioUrl) sessionStorage.setItem("consultationAudioUrl", audioUrl);
        // Read live notes from sessionStorage to get the latest value (avoiding stale closure)
        try {
          const currentLiveNotes = sessionStorage.getItem("consultationLiveNotes") || "";
          console.log("[Consult] MediaRecorder stop - live notes in sessionStorage:", currentLiveNotes.substring(0, 50), "length:", currentLiveNotes.length);
          sessionStorage.setItem("consultationLiveNotes", currentLiveNotes);
        } catch {}
        router.push("/review");
      } catch (e: any) {
        setStatus("Transcription failed");
        setErrorMsg(e?.message || "Transcription failed");
      }
    };
    mr.start();
    mediaRecorderRef.current = mr;
    setRecording(true);
    setStatus("Recording...");
    setElapsed(0);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = (setInterval(() => setElapsed((s) => s + 1), 1000) as unknown) as number;
  };

  const stopRecording = () => {
    if (speechSupported && listening) {
      stopSpeech();
      setRecording(false);
      setStatus("Processing...");
      if (timerRef.current) clearInterval(timerRef.current);
      const finalText = [transcript, interimTranscript].filter(Boolean).join(" ").trim();
      sessionStorage.setItem("consultationText", finalText);
      sessionStorage.removeItem("consultationAudioFilename");
      sessionStorage.removeItem("consultationAudioUrl");
      // Read live notes from sessionStorage to ensure we have the latest value
      try {
        const currentLiveNotes = sessionStorage.getItem("consultationLiveNotes") || "";
        console.log("[Consult] Stop recording - live notes in sessionStorage:", currentLiveNotes.substring(0, 50), "length:", currentLiveNotes.length);
        sessionStorage.setItem("consultationLiveNotes", currentLiveNotes);
      } catch {}
      router.push("/review");
      return;
    }
    mediaRecorderRef.current?.stop();
    setRecording(false);
    setStatus("Processing...");
    if (timerRef.current) clearInterval(timerRef.current);
  };

  const combinedTranscript = [transcript, interimTranscript].filter(Boolean).join(" ");

  return (
    <main className="max-w-xl mx-auto py-10 px-4 space-y-6">
      <h2 className="text-2xl font-semibold">Consultation</h2>
      <p className="text-gray-600">
        Describe your skin concerns and symptoms. Click "Start Recording" to begin.
      </p>

      {speechSupported ? (
        <p className="text-sm text-green-700">Browser speech recognition available.</p>
      ) : (
        <p className="text-sm text-amber-700">
          Browser speech recognition not supported. Falling back to audio upload.
        </p>
      )}

      {speechError ? (
        <p className="text-sm text-red-700">Speech error: {speechError}</p>
      ) : null}

      <div className="flex gap-3">
        {recording ? (
          <button className="rounded bg-red-600 px-4 py-2 text-white" onClick={stopRecording}>
            Stop {speechSupported ? "Listening" : "Recording"}
          </button>
        ) : (
          <button
            className="rounded bg-blue-600 px-4 py-2 text-white disabled:cursor-not-allowed disabled:opacity-60"
            onClick={startRecording}
            disabled={checkingAudio}
          >
            {checkingAudio ? "Checking devices…" : `Start ${speechSupported ? "Listening" : "Recording"}`}
          </button>
      )}
      <span className="self-center text-gray-600">{status}</span>
      {recording ? (
        <span className="self-center text-gray-800 font-mono">
          {String(Math.floor(elapsed / 60)).padStart(2, '0')}:{String(elapsed % 60).padStart(2, '0')}
        </span>
      ) : null}
    </div>

      {audioVerified ? (
        <p className="text-xs text-green-700">Microphone check passed.</p>
      ) : (
        <p className="text-xs text-gray-500">We’ll verify your microphone before recording begins.</p>
      )}

      <div className="space-y-2 rounded-md border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-700">Live notes</label>
          {recording ? <span className="text-xs text-blue-600">Recording in progress</span> : null}
        </div>
        <textarea
          className="h-32 w-full rounded border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
          value={liveNotes}
          onChange={(e) => setLiveNotes(e.target.value)}
          placeholder="Jot down findings, reminders, or follow-ups while the transcript builds."
        />
        <p className="text-xs text-gray-500">Notes save automatically and carry over to the review page.</p>
      </div>

      {status === 'Transcribing...' ? (
        <div className="flex items-center gap-2 text-gray-700">
          <span className="inline-block h-4 w-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
          <span>Transcribing…</span>
        </div>
      ) : null}

      {errorMsg ? (
        <div className="text-red-700 text-sm">{errorMsg}</div>
      ) : null}

      {/* Waveform removed */}

      {/* Live transcript preview when using Web Speech */}
      {speechSupported && (transcript || interimTranscript) ? (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Live transcript</label>
          <textarea
            className="w-full p-2 border border-gray-300 rounded h-36"
            value={combinedTranscript}
            readOnly
          />
        </div>
      ) : null}
    </main>
  );
}
