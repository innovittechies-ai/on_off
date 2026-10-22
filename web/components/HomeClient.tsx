"use client";

import { useCallback, useState } from "react";
import { Dashboard } from "@/components/Dashboard";
import { LoginGate } from "@/components/LoginGate";

type Props = {
  collegeName: string;
  initialAuthed: boolean;
  passwordRequired: boolean;
};

export function HomeClient({ collegeName, initialAuthed, passwordRequired }: Props) {
  const [authed, setAuthed] = useState(initialAuthed);
  const onAuthenticated = useCallback(() => setAuthed(true), []);

  if (!authed && passwordRequired) {
    return <LoginGate collegeName={collegeName} onAuthenticated={onAuthenticated} />;
  }

  return <Dashboard collegeName={collegeName} />;
}
