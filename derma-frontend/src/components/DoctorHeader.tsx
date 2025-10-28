"use client";

import {usePathname, useRouter} from "next/navigation";

const HIDDEN_PATH_PREFIXES = ["/login", "/register"];

export default function DoctorHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const base = process.env.NEXT_PUBLIC_API_BASE_URL;

  const goToConsult = () => {
    router.push("/consult");
  };

  const handleLogout = async () => {
    try {
      if (!base) {
        console.error("NEXT_PUBLIC_API_BASE_URL not configured");
        router.push("/login");
        return;
      }
      const res = await fetch(`${base}/auth/logout`, {method: "POST", credentials: "include"});
      if (!res.ok) {
        console.warn("Logout request failed");
      }
    } catch (err) {
      console.error("Logout error", err);
    } finally {
      router.replace("/login");
    }
  };

  if (!pathname || pathname === "/" || HIDDEN_PATH_PREFIXES.some((p) => pathname.startsWith(p))) {
    return null;
  }

  return (
    <header className="sticky top-0 z-40 border-b border-gray-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500">DermaTrack</p>
          <h1 className="text-lg font-semibold text-gray-900">Doctor Dashboard</h1>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={goToConsult}
            className="rounded-md border border-blue-600 bg-blue-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-blue-700"
          >
            Start Transcription
          </button>
          <button
            type="button"
            onClick={handleLogout}
            className="text-sm font-medium text-gray-600 underline hover:text-gray-800"
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
