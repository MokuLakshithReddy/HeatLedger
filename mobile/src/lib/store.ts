import { useState, useEffect } from "react";
import { Language } from "./i18n";

export interface UserSession {
  token: string;
  userId: string;
  fullName: string;
  role: string;
  language: Language;
}

// In-memory / persistent session store for React Native
let currentSession: UserSession | null = {
  token: "mock-worker-token",
  userId: "demo-worker-id",
  fullName: "Raju K. (Swiggy Partner)",
  role: "worker",
  language: "te", // Default Telugu
};

export const SessionStore = {
  get: () => currentSession,
  set: (s: UserSession | null) => {
    currentSession = s;
  },
};
