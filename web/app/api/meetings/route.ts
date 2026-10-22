import { NextResponse } from "next/server";
import { fetchMeetingsByDate, getZoomToken } from "@/lib/zoom";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const date = searchParams.get("date");
  if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    return NextResponse.json({ error: "Invalid or missing date (YYYY-MM-DD)" }, { status: 400 });
  }

  const tokenResult = await getZoomToken();
  if ("error" in tokenResult) {
    return NextResponse.json({ error: tokenResult.error }, { status: 502 });
  }

  const result = await fetchMeetingsByDate(tokenResult.token, date);
  if ("error" in result) {
    return NextResponse.json({ error: result.error }, { status: 502 });
  }

  return NextResponse.json({
    meetings: result.meetings,
    warning: result.warning,
  });
}
