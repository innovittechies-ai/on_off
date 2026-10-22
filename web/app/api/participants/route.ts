import { NextResponse } from "next/server";
import { processParticipants } from "@/lib/attendance";
import { fetchMeetingParticipants, getZoomToken } from "@/lib/zoom";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const meetingId = searchParams.get("meetingId")?.trim();
  const sessionLength = Number(searchParams.get("sessionLength") || "90");

  if (!meetingId) {
    return NextResponse.json({ error: "Missing meetingId" }, { status: 400 });
  }

  const tokenResult = await getZoomToken();
  if ("error" in tokenResult) {
    return NextResponse.json({ error: tokenResult.error }, { status: 502 });
  }

  const result = await fetchMeetingParticipants(tokenResult.token, meetingId);
  if ("error" in result) {
    return NextResponse.json({ error: result.error }, { status: 502 });
  }

  const students = processParticipants(result.participants, sessionLength);
  return NextResponse.json({ students, rawCount: result.participants.length });
}
