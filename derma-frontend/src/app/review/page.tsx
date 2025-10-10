"use client";
import { useEffect, useState } from "react";

export default function Review() {
    const [text, setText] = useState("");
    useEffect(() => { setText(sessionStorage.getItem("consultationText") || ""); }, []);

    const save = async () => {
        const consultation_id = "demo_consultation_id";
        const base = process.env.NEXT_PUBLIC_API_BASE_URL;
        if (!base) {
            alert("NEXT_PUBLIC_API_BASE_URL is not set");
            return;
        }
        const res = await fetch(base + "/notes", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            credentials: "include",
                body: JSON.stringify({ consultation_id, text }),
            });
            if (res.status === 401) {
                alert("Please login to save notes");
                window.location.href = "/login";
                return;
            }
            if (!res.ok) {
                alert("Failed to save");
                return;
            }
            const data = await res.json();
            alert("Saved note " + data.id);
            window.location.href = "/notes";
        };

    return(
        <main className="max-w-2xl mx-auto py-10 px-4 space-y-4">
            <h2 className="text-2xl font-semibold">Review & Save Notes</h2>
            <textarea value={text} onChange={(e) => setText(e.target.value)} rows={10} className="w-full p-2 border border-gray-300 rounded" placeholder="TRANSCRIPT HERE" />
            <button onClick={save} className="rounded bg-black text-white px-4 py-2">Save note</button>
        </main>
    );
}   
