"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type ConsentLog = {
  id: number;
  consultation_id: number;
  user_id: number;
  patient_id?: number | null;
  patient_name?: string | null;
  consent_given: boolean;
  consent_timestamp: string;
  consent_method: string;
  ip_address?: string | null;
  withdrawn: boolean;
};

export default function AdminConsentLogs() {
  const router = useRouter();
  const base = process.env.NEXT_PUBLIC_API_BASE_URL!;

  const [loading, setLoading] = useState(true);
  const [logs, setLogs] = useState<ConsentLog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    const loadLogs = async () => {
      setLoading(true);
      setError(null);
      try {
        // Verify authentication
        const meRes = await fetch(`${base}/me`, { credentials: "include" });
        if (meRes.status === 401) {
          router.replace("/login");
          return;
        }

        // Fetch all consent logs (admin endpoint)
        const res = await fetch(`${base}/admin/consent-logs`, {
          credentials: "include",
        });

        if (res.status === 401) {
          router.replace("/login");
          return;
        }

        if (!res.ok) {
          throw new Error("Failed to load consent logs");
        }

        const data = await res.json();
        setLogs(data);
      } catch (e) {
        setError((e as Error)?.message || "Failed to load consent logs");
      } finally {
        setLoading(false);
      }
    };

    loadLogs();
  }, [base, router]);

  const filteredLogs = logs.filter((log) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      log.patient_name?.toLowerCase().includes(term) ||
      log.consultation_id.toString().includes(term) ||
      log.user_id.toString().includes(term) ||
      log.ip_address?.toLowerCase().includes(term)
    );
  });

  if (loading) {
    return (
      <main className="max-w-6xl mx-auto py-10 px-4">
        <h1 className="text-3xl font-bold mb-6">Admin - Consent Logs</h1>
        <p className="text-gray-600">Loading consent logs...</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="max-w-6xl mx-auto py-10 px-4">
        <h1 className="text-3xl font-bold mb-6">Admin - Consent Logs</h1>
        <div className="bg-red-50 border border-red-200 rounded p-4 text-red-800">
          {error}
        </div>
      </main>
    );
  }

  return (
    <main className="max-w-6xl mx-auto py-10 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Admin - Consent Logs</h1>
        <button
          onClick={() => router.push("/dashboard")}
          className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
        >
          Back to Dashboard
        </button>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded p-4">
        <h2 className="font-semibold text-blue-900 mb-2">About Consent Logs</h2>
        <p className="text-sm text-blue-800">
          This page displays all patient consent records across all doctors in the system.
          Each entry logs when a doctor confirmed they obtained patient consent before
          recording a consultation, including timestamp, IP address, and consent method.
        </p>
      </div>

      <div className="bg-white border rounded p-4">
        <div className="flex gap-4 items-center mb-4">
          <input
            type="text"
            placeholder="Search by patient name, consultation ID, user ID, or IP..."
            className="flex-1 px-3 py-2 border rounded"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <div className="text-sm text-gray-600">
            Showing {filteredLogs.length} of {logs.length} records
          </div>
        </div>

        {filteredLogs.length === 0 ? (
          <p className="text-gray-600 text-center py-8">No consent logs found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left p-3">ID</th>
                  <th className="text-left p-3">Consultation</th>
                  <th className="text-left p-3">Doctor ID</th>
                  <th className="text-left p-3">Patient</th>
                  <th className="text-left p-3">Consent Status</th>
                  <th className="text-left p-3">Method</th>
                  <th className="text-left p-3">Timestamp</th>
                  <th className="text-left p-3">IP Address</th>
                  <th className="text-left p-3">Withdrawn</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="p-3 font-mono text-xs">{log.id}</td>
                    <td className="p-3 font-mono text-xs">{log.consultation_id}</td>
                    <td className="p-3 font-mono text-xs">{log.user_id}</td>
                    <td className="p-3">{log.patient_name || "—"}</td>
                    <td className="p-3">
                      <span
                        className={`inline-block px-2 py-1 rounded text-xs font-semibold ${
                          log.consent_given
                            ? "bg-green-100 text-green-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {log.consent_given ? "✓ Given" : "✗ Not Given"}
                      </span>
                    </td>
                    <td className="p-3 capitalize">{log.consent_method}</td>
                    <td className="p-3 text-xs">
                      {new Date(log.consent_timestamp).toLocaleString()}
                    </td>
                    <td className="p-3 font-mono text-xs">{log.ip_address || "—"}</td>
                    <td className="p-3">
                      {log.withdrawn ? (
                        <span className="text-red-600 font-semibold">Yes</span>
                      ) : (
                        <span className="text-green-600">No</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded p-4">
        <h3 className="font-semibold text-amber-900 mb-2">Compliance Notes</h3>
        <ul className="text-sm text-amber-800 space-y-1 list-disc list-inside">
          <li>All consent records are immutable and cannot be edited or deleted</li>
          <li>IP addresses are logged for audit trail purposes</li>
          <li>Consent timestamps are recorded in UTC</li>
          <li>This data should be retained per HIPAA requirements (7 years minimum)</li>
        </ul>
      </div>
    </main>
  );
}
