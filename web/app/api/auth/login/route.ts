import { NextResponse } from "next/server";
import { AUTH_COOKIE, checkPassword, isAuthConfigured } from "@/lib/auth";

export async function POST(request: Request) {
  if (!isAuthConfigured()) {
    return NextResponse.json({ ok: true, authRequired: false });
  }

  const body = await request.json().catch(() => ({}));
  const password = typeof body.password === "string" ? body.password : "";

  if (!checkPassword(password)) {
    return NextResponse.json({ error: "Invalid password" }, { status: 401 });
  }

  const res = NextResponse.json({ ok: true, authRequired: true });
  res.cookies.set(AUTH_COOKIE, "1", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
  return res;
}

export async function GET() {
  return NextResponse.json({ authRequired: isAuthConfigured() });
}
