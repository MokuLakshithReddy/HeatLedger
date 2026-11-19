import { Language } from "./i18n";

export interface UserSession {
  token: string;
  userId: string;
  fullName: string;
  role: string;
  language: Language;
}

// In-memory session store (Starts strictly null - unauthenticated by default)
let currentSession: UserSession | null = null;
let listeners: Array<(s: UserSession | null) => void> = [];

export const SessionStore = {
  get: (): UserSession | null => currentSession,
  set: (s: UserSession | null) => {
    currentSession = s;
    listeners.forEach((l) => l(currentSession));
  },
  clear: () => {
    currentSession = null;
    listeners.forEach((l) => l(null));
  },
  subscribe: (listener: (s: UserSession | null) => void) => {
    listeners.push(listener);
    return () => {
      listeners = listeners.filter((l) => l !== listener);
    };
  },
};
