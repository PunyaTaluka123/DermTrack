"use client";
/* eslint-disable @typescript-eslint/no-explicit-any -- the Web Speech API has no TypeScript DOM types */

import { useCallback, useEffect, useRef, useState } from "react";

type Recognition = InstanceType<any> | null;

export function useSpeechRecognition(options?: { lang?: string }) {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<Recognition>(null);

  const getCtor = () => {
    if (typeof window === "undefined") return null;
    // Vendor prefixed support
    return (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition || null;
  };

  useEffect(() => {
    setSupported(!!getCtor());
  }, []);

  const reset = useCallback(() => {
    setTranscript("");
    setInterimTranscript("");
    setError(null);
  }, []);

  const stop = useCallback(() => {
    try {
      (recognitionRef.current as any)?.stop?.();
    } catch (_) {
      // no-op
    } finally {
      setListening(false);
    }
  }, []);

  const start = useCallback(() => {
    const Ctor = getCtor();
    if (!Ctor) {
      setError("SpeechRecognition not supported in this browser");
      return;
    }
    // Clean previous
    try {
      (recognitionRef.current as any)?.abort?.();
    } catch (_) {}

    const recognition = new Ctor();
    recognition.lang = options?.lang || "en-US";
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onstart = () => {
      setListening(true);
      setError(null);
    };

    recognition.onerror = (event: any) => {
      const msg = event?.error || "unknown_error";
      setError(String(msg));
      setListening(false);
    };

    recognition.onend = () => {
      setListening(false);
    };

    recognition.onresult = (event: any) => {
      // Aggregate results
      let finalText = "";
      let interimText = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const res = event.results[i];
        const text = res[0]?.transcript || "";
        if (res.isFinal) {
          finalText += text + " ";
        } else {
          interimText += text + " ";
        }
      }
      if (finalText) setTranscript((prev) => (prev + " " + finalText).trim());
      setInterimTranscript(interimText.trim());
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch (e) {
      setError("Failed to start recognition");
    }
  }, [options?.lang]);

  return {
    supported,
    listening,
    transcript,
    interimTranscript,
    error,
    start,
    stop,
    reset,
  } as const;
}

