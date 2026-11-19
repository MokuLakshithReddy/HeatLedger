import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";
import { Language } from "./i18n";

export interface UserSession {
  token: string;
  userId: string;
  fullName: string;
  role: string;
  language: Language;
}

const STORAGE_KEY = "heatledger_user_session";

let currentSession: UserSession | null = null;
let listeners: Array<(s: UserSession | null) => void> = [];

export const SessionStore = {
  get: (): UserSession | null => currentSession,
  
  set: async (s: UserSession | null) => {
    currentSession = s;
    listeners.forEach((l) => l(currentSession));
    try {
      if (s) {
        const json = JSON.stringify(s);
        if (Platform.OS === "web") {
          localStorage.setItem(STORAGE_KEY, json);
        } else {
          await SecureStore.setItemAsync(STORAGE_KEY, json);
        }
      } else {
        if (Platform.OS === "web") {
          localStorage.removeItem(STORAGE_KEY);
        } else {
          await SecureStore.deleteItemAsync(STORAGE_KEY);
        }
      }
    } catch (e) {
      console.warn("Session persistence warning:", e);
    }
  },

  clear: async () => {
    currentSession = null;
    listeners.forEach((l) => l(null));
    try {
      if (Platform.OS === "web") {
        localStorage.removeItem(STORAGE_KEY);
      } else {
        await SecureStore.deleteItemAsync(STORAGE_KEY);
      }
    } catch (e) {
      console.warn("Session clear warning:", e);
    }
  },

  loadStoredSession: async (): Promise<UserSession | null> => {
    try {
      let json: string | null = null;
      if (Platform.OS === "web") {
        json = localStorage.getItem(STORAGE_KEY);
      } else {
        json = await SecureStore.getItemAsync(STORAGE_KEY);
      }
      if (json) {
        currentSession = JSON.parse(json);
        listeners.forEach((l) => l(currentSession));
        return currentSession;
      }
    } catch (e) {
      console.warn("Failed to load stored session:", e);
    }
    return null;
  },

  subscribe: (listener: (s: UserSession | null) => void) => {
    listeners.push(listener);
    return () => {
      listeners = listeners.filter((l) => l !== listener);
    };
  },
};
