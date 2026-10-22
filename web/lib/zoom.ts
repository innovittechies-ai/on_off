function zoomErrorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object") {
    const o = body as Record<string, string>;
    return o.message || o.reason || fallback;
  }
  return fallback;
}

export function getZoomEnv() {
  return {
    accountId: process.env.ZOOM_ACCOUNT_ID?.trim() || "",
    clientId: process.env.ZOOM_CLIENT_ID?.trim() || "",
    clientSecret: process.env.ZOOM_CLIENT_SECRET?.trim() || "",
    userEmail: process.env.ZOOM_USER_EMAIL?.trim() || "",
    userId: process.env.ZOOM_USER_ID?.trim() || "",
  };
}

export function encodeMeetingIdForUrl(meetingId: string): string {
  const id = meetingId.trim();
  if (!id) return id;
  if (id.startsWith("/") || id.includes("//")) {
    return encodeURIComponent(encodeURIComponent(id));
  }
  return encodeURIComponent(id);
}

export async function getZoomToken(): Promise<{ token: string } | { error: string }> {
  const { accountId, clientId, clientSecret } = getZoomEnv();
  if (!accountId || !clientId || !clientSecret) {
    return { error: "Server missing ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, or ZOOM_CLIENT_SECRET." };
  }

  const basic = Buffer.from(`${clientId}:${clientSecret}`).toString("base64");
  const res = await fetch("https://zoom.us/oauth/token", {
    method: "POST",
    headers: {
      Authorization: `Basic ${basic}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      grant_type: "account_credentials",
      account_id: accountId,
    }),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    return {
      error: `Authentication failed (${res.status}): ${zoomErrorMessage(data, res.statusText)}`,
    };
  }
  return { token: (data as { access_token: string }).access_token };
}

async function resolveReportUser(token: string): Promise<{ userId: string; warning?: string } | { error: string }> {
  const { userEmail, userId } = getZoomEnv();
  if (userId) return { userId };
  if (userEmail) return { userId: userEmail };

  const res = await fetch("https://api.zoom.us/v2/users?page_size=1", {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    return {
      error: `Could not list users (${res.status}): ${zoomErrorMessage(data, res.statusText)}`,
    };
  }
  const users = (data as { users?: { id?: string; email?: string }[] }).users || [];
  if (!users.length) {
    return { error: "No users on account. Set ZOOM_USER_EMAIL in Vercel env." };
  }
  const u = users[0];
  const id = u.id || u.email;
  if (!id) return { error: "Could not resolve Zoom user. Set ZOOM_USER_EMAIL." };
  return {
    userId: id,
    warning: "ZOOM_USER_EMAIL not set — using first account user. Set it in Vercel for accurate sessions.",
  };
}

export type ZoomMeeting = {
  id: number | string;
  uuid?: string;
  topic?: string;
  start_time?: string;
  duration?: number;
};

export async function fetchMeetingsByDate(
  token: string,
  targetDate: string
): Promise<{ meetings: ZoomMeeting[]; warning?: string } | { error: string }> {
  const user = await resolveReportUser(token);
  if ("error" in user) return user;

  const encodedUser = encodeURIComponent(user.userId);
  const all: ZoomMeeting[] = [];
  let nextPageToken: string | undefined;

  do {
    const params = new URLSearchParams({
      from: targetDate,
      to: targetDate,
      page_size: "300",
    });
    if (nextPageToken) params.set("next_page_token", nextPageToken);

    const res = await fetch(
      `https://api.zoom.us/v2/report/users/${encodedUser}/meetings?${params}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return {
        error: `Meetings API (${res.status}): ${zoomErrorMessage(data, res.statusText)}`,
      };
    }
    const page = data as { meetings?: ZoomMeeting[]; next_page_token?: string };
    all.push(...(page.meetings || []));
    nextPageToken = page.next_page_token;
  } while (nextPageToken);

  return { meetings: all, warning: user.warning };
}

export type RawParticipant = {
  name?: string;
  user_email?: string;
  join_time?: string;
  leave_time?: string;
  duration?: number;
};

export async function fetchMeetingParticipants(
  token: string,
  meetingId: string
): Promise<{ participants: RawParticipant[] } | { error: string }> {
  const encoded = encodeMeetingIdForUrl(meetingId);
  const all: RawParticipant[] = [];
  let nextPageToken: string | undefined;

  do {
    const params = new URLSearchParams({ page_size: "300" });
    if (nextPageToken) params.set("next_page_token", nextPageToken);

    const res = await fetch(
      `https://api.zoom.us/v2/report/meetings/${encoded}/participants?${params}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return {
        error: `Participants API (${res.status}): ${zoomErrorMessage(data, res.statusText)}`,
      };
    }
    const page = data as { participants?: RawParticipant[]; next_page_token?: string };
    all.push(...(page.participants || []));
    nextPageToken = page.next_page_token;
  } while (nextPageToken);

  if (!all.length) {
    return {
      error:
        "No participants returned. Use Meeting ID or UUID; reports need 2+ attendees. For recurring classes, use the session UUID.",
    };
  }
  return { participants: all };
}
