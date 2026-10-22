export const AUTH_COOKIE = "attendance_dashboard_auth";

export function isAuthConfigured(): boolean {
  return Boolean(process.env.DASHBOARD_PASSWORD?.trim());
}

export function checkPassword(password: string): boolean {
  const expected = process.env.DASHBOARD_PASSWORD?.trim();
  if (!expected) return true;
  return password === expected;
}
