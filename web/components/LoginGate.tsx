"use client";

import { GraduationCap, Lock } from "lucide-react";
import { useEffect, useState } from "react";

type Props = {
  collegeName: string;
  onAuthenticated: () => void;
};

export function LoginGate({ collegeName, onAuthenticated }: Props) {
  const [authRequired, setAuthRequired] = useState<boolean | null>(null);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("/api/auth/login")
      .then((r) => r.json())
      .then((d) => setAuthRequired(Boolean(d.authRequired)))
      .catch(() => setAuthRequired(true));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    setLoading(false);
    if (!res.ok) {
      setError("Incorrect password. Contact your IT admin.");
      return;
    }
    onAuthenticated();
  }

  if (authRequired === null) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="h-10 w-10 rounded-full border-2 border-accent border-t-transparent animate-spin" />
      </div>
    );
  }

  if (!authRequired) return null;

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="glass-strong shadow-glow max-w-md w-full rounded-2xl p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-3 rounded-xl bg-accent/20 text-accent">
            <GraduationCap className="w-8 h-8" />
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-slate-400">Director access</p>
            <h1 className="font-display text-2xl font-semibold text-white">{collegeName}</h1>
          </div>
        </div>
        <p className="text-slate-400 text-sm mb-6">
          Enter the dashboard password to view student attendance and download reports.
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Dashboard password"
              className="w-full pl-10 pr-4 py-3 rounded-xl bg-ink-900/80 border border-surface-border text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-accent/50"
              autoFocus
            />
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading || !password}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-accent to-accent-light text-ink-950 font-semibold hover:opacity-95 disabled:opacity-50 transition"
          >
            {loading ? "Signing in…" : "Open dashboard"}
          </button>
        </form>
      </div>
    </div>
  );
}
