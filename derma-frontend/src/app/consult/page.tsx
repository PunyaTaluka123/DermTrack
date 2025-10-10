"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useSpeechRecognition } from "@/lib/useSpeechRecognition";

export default function Consult() {
  const [recording, setRecording] = useState(false);
  const [status, setStatus] = useState("Idle");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const router = useRouter();

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
    return () => {
      mediaRecorderRef.current?.stream.getTracks().forEach((t) => t.stop());
      stopSpeech();
    };
  }, [stopSpeech]);

  const startRecording = async () => {
    // Prefer Web Speech API if supported
    if (speechSupported) {
      resetSpeech();
      setRecording(true);
      setStatus("Listening...");
      startSpeech();
      return;
    }

    // Fallback to MediaRecorder + backend transcription
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
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
      try {
        const base = process.env.NEXT_PUBLIC_API_BASE_URL;
        if (!base) throw new Error("NEXT_PUBLIC_API_BASE_URL not set");
        const res = await fetch(`${base}/transcribe`, { method: "POST", body: form });
        if (!res.ok) throw new Error(`Transcribe failed: ${res.status}`);
        const data = await res.json();
        const text = data?.text ?? "";
        sessionStorage.setItem("consultationText", text);
        router.push("/review");
      } catch (e: any) {
        setStatus("Transcription failed");
        alert(e?.message || "Transcription failed");
      }
    };
    mr.start();
    mediaRecorderRef.current = mr;
    setRecording(true);
    setStatus("Recording...");
  };

  const stopRecording = () => {
    if (speechSupported && listening) {
      stopSpeech();
      setRecording(false);
      setStatus("Processing...");
      const finalText = [transcript, interimTranscript].filter(Boolean).join(" ").trim();
      sessionStorage.setItem("consultationText", finalText);
      router.push("/review");
      return;
    }
    mediaRecorderRef.current?.stop();
    setRecording(false);
    setStatus("Processing...");
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
          <button className="rounded bg-red-600 text-white px-4 py-2" onClick={stopRecording}>
            Stop {speechSupported ? "Listening" : "Recording"}
          </button>
        ) : (
          <button className="rounded bg-blue-600 text-white px-4 py-2" onClick={startRecording}>
            Start {speechSupported ? "Listening" : "Recording"}
          </button>
        )}
        <span className="self-center text-gray-600">{status}</span>
      </div>

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
