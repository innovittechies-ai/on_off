import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { AUTH_COOKIE } from "@/lib/auth";

export function middleware(request: NextRequest) {
  const password = process.env.DASHBOARD_PASSWORD?.trim();
  if (!password) return NextResponse.next();

  const isApi = request.nextUrl.pathname.startsWith("/api/");
  const isLoginApi = request.nextUrl.pathname === "/api/auth/login";

  if (isLoginApi) return NextResponse.next();

  if (isApi) {
    const authed = request.cookies.get(AUTH_COOKIE)?.value === "1";
    if (!authed) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/api/meetings", "/api/participants"],
};
