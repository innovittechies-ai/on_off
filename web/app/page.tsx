import { cookies } from "next/headers";
import { HomeClient } from "@/components/HomeClient";
import { AUTH_COOKIE, isAuthConfigured } from "@/lib/auth";

export default function Home() {
  const collegeName =
    process.env.NEXT_PUBLIC_COLLEGE_NAME?.trim() || "Student Attendance Dashboard";
  const passwordRequired = isAuthConfigured();
  const cookieStore = cookies();
  const initialAuthed =
    !passwordRequired || cookieStore.get(AUTH_COOKIE)?.value === "1";

  return (
    <HomeClient
      collegeName={collegeName}
      initialAuthed={initialAuthed}
      passwordRequired={passwordRequired}
    />
  );
}
