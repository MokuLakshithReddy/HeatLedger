import { SessionStore } from "./store";

// In mobile environments, standard localhost points to device localhost.
// Android emulator uses 10.0.2.2. Production uses configured environment URL.
export const API_BASE =
  process.env.EXPO_PUBLIC_API_URL || "http://10.0.2.2:8000/api/v1";

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

  // Primary URL, with fallback to localhost:8000 for web/desktop debugging
  const urls = [
    `${API_BASE}${endpoint}`,
    `http://localhost:8000/api/v1${endpoint}`,
  ];

  let lastError: any = null;
  for (const url of urls) {
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
