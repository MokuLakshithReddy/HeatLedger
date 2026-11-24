import { Platform } from "react-native";
import Constants from "expo-constants";
import { SessionStore } from "./store";

/**
 * Dynamically resolves the appropriate backend API URL:
 * 1. EXPO_PUBLIC_API_URL environment variable if set (e.g. for custom LAN or production URL).
 * 2. Auto-detected workstation LAN IP from Metro hostUri for physical Android/iOS devices running Expo Go.
 * 3. 10.0.2.2 for Android Studio emulators.
 * 4. localhost for iOS Simulators and Web browser debugging.
 */
function resolveApiBase(): string {
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL.replace(/\/+$/, "");
  }

  try {
    const hostUri =
      Constants.expoConfig?.hostUri ||
      (Constants as any).manifest2?.extra?.expoClient?.hostUri ||
      (Constants as any).manifest?.debuggerHost;
    if (hostUri) {
      const hostIp = hostUri.split(":")[0];
      if (hostIp && hostIp !== "localhost" && hostIp !== "127.0.0.1") {
        return `http://${hostIp}:8000/api/v1`;
      }
    }
  } catch {
    // Proceed to platform defaults
  }

  if (Platform.OS === "android") {
    return "http://10.0.2.2:8000/api/v1";
  }

  return "http://localhost:8000/api/v1";
}

export const API_BASE = resolveApiBase();

export async function mobileApiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
  explicitToken?: string
): Promise<T> {
  const token = explicitToken || SessionStore.get()?.token;
  const headers = new Headers(options.headers || {});
  
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  // Deduplicated candidate URLs starting with the dynamically resolved API_BASE
  const urls: string[] = [
    `${API_BASE}${endpoint}`,
    `http://localhost:8000/api/v1${endpoint}`,
    `http://127.0.0.1:8000/api/v1${endpoint}`,
  ];
  if (Platform.OS === "android" && API_BASE !== "http://10.0.2.2:8000/api/v1") {
    urls.push(`http://10.0.2.2:8000/api/v1${endpoint}`);
  }
  const candidateUrls = Array.from(new Set(urls));

  let lastError: any = null;
  for (const url of candidateUrls) {
    try {
      const response = await fetch(url, { ...options, headers });
      if (!response.ok) {
        let errMessage = `HTTP ${response.status}`;
        try {
          const json = await response.json();
          errMessage = json.detail || JSON.stringify(json);
        } catch {
          errMessage = await response.text();
        }
        throw new Error(errMessage);
      }
      return await response.json();
    } catch (e: any) {
      lastError = e;
      // If error is 4xx/5xx from actual response, do not retry other URLs
      if (e.message && !e.message.includes("Network request failed") && !e.message.includes("Failed to fetch")) {
        throw e;
      }
    }
  }
  throw lastError;
}
