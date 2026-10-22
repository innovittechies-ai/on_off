"use client";

import {
  BarChart3,
  Calendar,
  Copy,
  Download,
  GraduationCap,
  Search,
  Users,
  Video,
} from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  categoryColor,
  rowsToCsv,
  type StudentRow,
} from "@/lib/attendance";
import type { ZoomMeeting } from "@/lib/zoom";

type Props = {
  collegeName: string;
};

function yesterdayIso() {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

function formatMeetingStart(iso?: string) {
  if (!iso) return "—";
  try {
    const utc = new Date(iso.replace("Z", "+00:00"));
    const ist = new Date(utc.getTime() + (5 * 60 + 30) * 60 * 1000);
    return ist.toLocaleString("en-IN", {
      timeZone: "UTC",
      dateStyle: "medium",
      timeStyle: "short",
    }) + " IST";
  } catch {
    return iso;
  }
}

export function Dashboard({ collegeName }: Props) {
  const [date, setDate] = useState(yesterdayIso());
  const [meetings, setMeetings] = useState<ZoomMeeting[]>([]);
  const [meetingsLoading, setMeetingsLoading] = useState(false);
  const [meetingsError, setMeetingsError] = useState("");
  const [meetingsWarning, setMeetingsWarning] = useState("");

  const [selectedMeeting, setSelectedMeeting] = useState<ZoomMeeting | null>(null);
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState("");
  const [search, setSearch] = useState("");
  const [copied, setCopied] = useState<string | null>(null);

  const sessionLength = selectedMeeting?.duration ?? 90;

  const loadMeetings = useCallback(async () => {
    setMeetingsLoading(true);
    setMeetingsError("");
    setMeetingsWarning("");
    setSelectedMeeting(null);
    setStudents([]);
    const res = await fetch(`/api/meetings?date=${date}`);
    const data = await res.json();
    setMeetingsLoading(false);
    if (!res.ok) {
      setMeetingsError(data.error || "Failed to load sessions");
      setMeetings([]);
      return;
    }
    setMeetings(data.meetings || []);
    if (data.warning) setMeetingsWarning(data.warning);
  }, [date]);

  const loadReport = useCallback(
    async (meeting: ZoomMeeting, idOrUuid: string) => {
      setSelectedMeeting(meeting);
      setReportLoading(true);
      setReportError("");
      setStudents([]);
      const len = meeting.duration ?? 90;
      const res = await fetch(
        `/api/participants?meetingId=${encodeURIComponent(idOrUuid)}&sessionLength=${len}`
      );
      const data = await res.json();
      setReportLoading(false);
      if (!res.ok) {
        setReportError(data.error || "Failed to load report");
        return;
      }
      setStudents(data.students || []);
    },
    []
  );

  const filtered = useMemo(() => {
    if (!search.trim()) return students;
    const q = search.toLowerCase();
    return students.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.email.toLowerCase().includes(q)
    );
  }, [students, search]);

  const stats = useMemo(() => {
    if (!students.length) return null;
    const avg =
      students.reduce((a, s) => a + s.durationMin, 0) / students.length;
    const max = Math.max(...students.map((s) => s.durationMin));
    const cats = students.reduce(
      (acc, s) => {
        acc[s.category] = (acc[s.category] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );
    return { avg: Math.round(avg), max, cats, total: students.length };
  }, [students]);

  const pieData = stats
    ? Object.entries(stats.cats).map(([name, value]) => ({ name, value }))
    : [];

  const barData = filtered.slice(0, 15).map((s) => ({
    name: s.name.split(" ")[0],
    fullName: s.name,
    minutes: s.durationMin,
  }));

  function copyText(label: string, text: string) {
    navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(null), 2000);
  }

  function downloadCsv() {
    const csv = rowsToCsv(filtered);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `attendance-${date}-${selectedMeeting?.id ?? "session"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="min-h-screen pb-16">
      <header className="border-b border-white/10 bg-ink-950/40 backdrop-blur-md sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-accent/15 text-accent shadow-glow">
              <GraduationCap className="w-7 h-7" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                Leadership portal
              </p>
              <h1 className="font-display text-xl sm:text-2xl font-semibold text-white">
                {collegeName}
              </h1>
            </div>
          </div>
          <p className="text-sm text-slate-400 max-w-xs text-right hidden sm:block">
            Track live-class attendance, spot at-risk learners, export CSV for records.
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        {/* Step 1 — Sessions */}
        <section className="glass rounded-2xl p-6 shadow-card">
          <div className="flex flex-wrap items-end gap-4 justify-between mb-6">
            <div>
              <h2 className="font-display text-lg font-semibold flex items-center gap-2">
                <Calendar className="w-5 h-5 text-accent" />
                Find class sessions
              </h2>
              <p className="text-sm text-slate-400 mt-1">
                Pick a date to list Zoom sessions hosted by your college account.
              </p>
            </div>
            <div className="flex flex-wrap gap-3 items-center">
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="px-4 py-2.5 rounded-xl bg-ink-900/80 border border-surface-border text-white focus:outline-none focus:ring-2 focus:ring-accent/40"
              />
              <button
                type="button"
                onClick={loadMeetings}
                disabled={meetingsLoading}
                className="px-5 py-2.5 rounded-xl bg-accent text-ink-950 font-semibold hover:bg-accent-light disabled:opacity-50 transition flex items-center gap-2"
              >
                <Search className="w-4 h-4" />
                {meetingsLoading ? "Searching…" : "Search sessions"}
              </button>
            </div>
          </div>

          {meetingsWarning && (
            <p className="text-amber-300/90 text-sm mb-4 bg-amber-500/10 border border-amber-500/20 rounded-lg px-4 py-2">
              {meetingsWarning}
            </p>
          )}
          {meetingsError && (
            <p className="text-red-400 text-sm mb-4">{meetingsError}</p>
          )}

          {meetings.length > 0 && (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {meetings.map((m, i) => (
                <article
                  key={`${m.id}-${m.uuid ?? i}`}
                  className={`glass-strong rounded-xl p-4 transition hover:border-accent/30 ${
                    selectedMeeting?.uuid === m.uuid && selectedMeeting?.id === m.id
                      ? "ring-2 ring-accent/50"
                      : ""
                  }`}
                >
                  <div className="flex items-start gap-2 mb-2">
                    <Video className="w-4 h-4 text-accent shrink-0 mt-1" />
                    <h3 className="font-medium text-white line-clamp-2">
                      {m.topic || "Untitled session"}
                    </h3>
                  </div>
                  <p className="text-xs text-slate-500 mb-3">{formatMeetingStart(m.start_time)}</p>
                  <p className="text-xs text-slate-400 mb-1">
                    Duration: <span className="text-slate-200">{m.duration ?? "—"} min</span>
                  </p>
                  <div className="flex flex-wrap gap-2 mt-3">
                    <button
                      type="button"
                      onClick={() => copyText(`id-${m.id}`, String(m.id))}
                      className="text-xs px-2 py-1 rounded-lg bg-white/5 hover:bg-white/10 flex items-center gap-1"
                    >
                      <Copy className="w-3 h-3" />
                      {copied === `id-${m.id}` ? "Copied" : "ID"}
                    </button>
                    {m.uuid && (
                      <button
                        type="button"
                        onClick={() => copyText(`uuid-${m.uuid}`, m.uuid!)}
                        className="text-xs px-2 py-1 rounded-lg bg-white/5 hover:bg-white/10 flex items-center gap-1"
                      >
                        <Copy className="w-3 h-3" />
                        {copied === `uuid-${m.uuid}` ? "Copied" : "UUID"}
                      </button>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => loadReport(m, m.uuid || String(m.id))}
                    disabled={reportLoading}
                    className="mt-4 w-full py-2 rounded-lg bg-white/10 hover:bg-white/15 text-sm font-medium transition"
                  >
                    View attendance
                  </button>
                </article>
              ))}
            </div>
          )}

          {!meetingsLoading && meetings.length === 0 && !meetingsError && (
            <p className="text-slate-500 text-sm text-center py-8">
              Select a date and search to see sessions.
            </p>
          )}
        </section>

        {/* Step 2 — Report */}
        {(reportLoading || students.length > 0 || reportError) && (
          <section className="glass rounded-2xl p-6 shadow-card">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
              <div>
                <h2 className="font-display text-lg font-semibold flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-accent" />
                  Student performance
                </h2>
                {selectedMeeting && (
                  <p className="text-sm text-slate-400 mt-1 line-clamp-1">
                    {selectedMeeting.topic}
                  </p>
                )}
              </div>
              {students.length > 0 && (
                <button
                  type="button"
                  onClick={downloadCsv}
                  className="px-4 py-2 rounded-xl bg-emerald-600/90 hover:bg-emerald-500 text-white font-medium flex items-center gap-2 text-sm"
                >
                  <Download className="w-4 h-4" />
                  Download CSV
                </button>
              )}
            </div>

            {reportLoading && (
              <div className="flex justify-center py-16">
                <div className="h-10 w-10 rounded-full border-2 border-accent border-t-transparent animate-spin" />
              </div>
            )}
            {reportError && <p className="text-red-400 text-sm">{reportError}</p>}

            {stats && !reportLoading && (
              <>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                  <Metric icon={Users} label="Students tracked" value={String(stats.total)} />
                  <Metric icon={BarChart3} label="Avg. time in class" value={`${stats.avg} min`} />
                  <Metric icon={Video} label="Longest stay" value={`${stats.max} min`} />
                  <Metric
                    icon={Users}
                    label="At risk"
                    value={String(stats.cats["At risk"] ?? 0)}
                    accent="text-red-400"
                  />
                </div>

                <div className="grid lg:grid-cols-2 gap-6 mb-8">
                  <div className="glass-strong rounded-xl p-4 h-72">
                    <p className="text-sm text-slate-400 mb-2">Top attendance (minutes)</p>
                    <ResponsiveContainer width="100%" height="90%">
                      <BarChart data={barData}>
                        <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                        <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                        <Tooltip
                          contentStyle={{
                            background: "#1e293b",
                            border: "1px solid rgba(255,255,255,0.1)",
                            borderRadius: 8,
                          }}
                          formatter={(v: number) => [`${v} min`, "Duration"]}
                          labelFormatter={(_, payload) =>
                            payload?.[0]?.payload?.fullName ?? ""
                          }
                        />
                        <Bar dataKey="minutes" fill="#c9a227" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="glass-strong rounded-xl p-4 h-72">
                    <p className="text-sm text-slate-400 mb-2">Performance mix</p>
                    <ResponsiveContainer width="100%" height="90%">
                      <PieChart>
                        <Pie
                          data={pieData}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          innerRadius={50}
                          outerRadius={80}
                          paddingAngle={2}
                        >
                          {pieData.map((entry) => (
                            <Cell
                              key={entry.name}
                              fill={categoryColor(entry.name as StudentRow["category"])}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            background: "#1e293b",
                            border: "1px solid rgba(255,255,255,0.1)",
                            borderRadius: 8,
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="relative mb-4 max-w-md">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    type="search"
                    placeholder="Search by name or email…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-ink-900/80 border border-surface-border text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-accent/40"
                  />
                </div>

                <div className="overflow-x-auto rounded-xl border border-surface-border">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-white/5 text-slate-400 uppercase text-xs tracking-wider">
                      <tr>
                        <th className="px-4 py-3">Student</th>
                        <th className="px-4 py-3">Email</th>
                        <th className="px-4 py-3">Duration</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3 hidden md:table-cell">Joined (IST)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {filtered.map((s) => (
                        <tr key={`${s.email}-${s.name}`} className="hover:bg-white/[0.03]">
                          <td className="px-4 py-3 font-medium text-white">{s.name}</td>
                          <td className="px-4 py-3 text-slate-400">{s.email}</td>
                          <td className="px-4 py-3">{s.durationMin} min</td>
                          <td className="px-4 py-3">
                            <span
                              className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium"
                              style={{
                                background: `${categoryColor(s.category)}22`,
                                color: categoryColor(s.category),
                              }}
                            >
                              {s.category}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-slate-500 hidden md:table-cell text-xs">
                            {s.joinTimeIst}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </section>
        )}
      </main>

      <footer className="text-center text-xs text-slate-600 py-6">
        Powered by Zoom Reports · Times shown in IST
      </footer>
    </div>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  accent,
}: {
  icon: typeof Users;
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div className="glass-strong rounded-xl p-4">
      <Icon className="w-4 h-4 text-accent mb-2" />
      <p className="text-xs text-slate-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-semibold mt-1 ${accent ?? "text-white"}`}>{value}</p>
    </div>
  );
}
