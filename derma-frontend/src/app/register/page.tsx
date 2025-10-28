"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const base = process.env.NEXT_PUBLIC_API_BASE_URL!;
      const res = await fetch(`${base}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) throw new Error((await res.json())?.detail || "Registration failed");
      router.replace("/dashboard");
    } catch (e: any) {
      setError(e?.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="max-w-md mx-auto py-10 px-4">
      <h2 className="text-2xl font-semibold mb-4">Register</h2>
      <form onSubmit={submit} className="space-y-4">
        <input className="w-full border p-2 rounded" type="email" placeholder="Email" value={email} onChange={(e)=>setEmail(e.target.value)} required />
        <input className="w-full border p-2 rounded" type="password" placeholder="Password" value={password} onChange={(e)=>setPassword(e.target.value)} required />
        {error ? <p className="text-red-600 text-sm">{error}</p> : null}
        <button disabled={loading} className="rounded bg-black text-white px-4 py-2 w-full">{loading ? "Creating..." : "Create account"}</button>
      </form>
      <p className="text-sm text-gray-600 mt-3">Already have an account? <a className="text-blue-700 underline" href="/login">Login</a></p>
    </main>
  );
}
