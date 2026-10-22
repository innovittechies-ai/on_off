import type { RawParticipant } from "./zoom";

export type StudentRow = {
  name: string;
  email: string;
  joinTimeIst: string;
  leaveTimeIst: string;
  durationMin: number;
  category: AttendanceCategory;
};

export type AttendanceCategory =
  | "Excellent"
  | "Good"
  | "Partial"
  | "At risk";

export function convertToIst(utcTimeStr?: string): string {
  if (!utcTimeStr) return "N/A";
  try {
    const utc = new Date(utcTimeStr.replace("Z", "+00:00"));
    const ist = new Date(utc.getTime() + (5 * 60 + 30) * 60 * 1000);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${ist.getUTCFullYear()}-${pad(ist.getUTCMonth() + 1)}-${pad(ist.getUTCDate())} ${pad(ist.getUTCHours())}:${pad(ist.getUTCMinutes())}:${pad(ist.getUTCSeconds())} IST`;
  } catch {
    return utcTimeStr;
  }
}

function categorize(durationMin: number, sessionLengthMin: number): AttendanceCategory {
  const pct = sessionLengthMin > 0 ? durationMin / sessionLengthMin : 0;
  if (pct >= 0.9 || durationMin >= 90) return "Excellent";
  if (pct >= 0.65 || durationMin >= 60) return "Good";
  if (pct >= 0.35 || durationMin >= 30) return "Partial";
  return "At risk";
}

export function processParticipants(
  participants: RawParticipant[],
  sessionLengthMin = 90
): StudentRow[] {
  const unique = new Map<string, RawParticipant & { duration: number }>();

  for (const p of participants) {
    const email = p.user_email?.trim() || "";
    const name = p.name?.trim() || "Unknown";
    const duration = p.duration ?? 0;
    const key = email && email !== "N/A" ? email : name;

    const existing = unique.get(key);
    if (!existing || duration > existing.duration) {
      unique.set(key, { ...p, duration });
    }
  }

  const rows: StudentRow[] = [];
  for (const p of unique.values()) {
    const durationMin = Math.floor((p.duration ?? 0) / 60);
    rows.push({
      name: p.name?.trim() || "Unknown",
      email: p.user_email?.trim() || "—",
      joinTimeIst: convertToIst(p.join_time),
      leaveTimeIst: convertToIst(p.leave_time),
      durationMin,
      category: categorize(durationMin, sessionLengthMin),
    });
  }

  return rows.sort((a, b) => b.durationMin - a.durationMin);
}

export function rowsToCsv(rows: StudentRow[]): string {
  const header = "Name,Email,Duration (min),Category,Join (IST),Leave (IST)";
  const lines = rows.map(
    (r) =>
      `"${r.name.replace(/"/g, '""')}","${r.email.replace(/"/g, '""')}",${r.durationMin},${r.category},"${r.joinTimeIst}","${r.leaveTimeIst}"`
  );
  return [header, ...lines].join("\n");
}

export function categoryColor(cat: AttendanceCategory): string {
  switch (cat) {
    case "Excellent":
      return "#22c55e";
    case "Good":
      return "#3b82f6";
    case "Partial":
      return "#f59e0b";
    case "At risk":
      return "#ef4444";
  }
}
