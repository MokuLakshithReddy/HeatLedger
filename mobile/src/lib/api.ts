// In mobile environments, standard localhost points to emulator/device localhost (10.0.2.2 on Android emulator)
// or local LAN IP. Fallback to http://10.0.2.2:8000 or http://localhost:8000
export const API_BASE = "http://10.0.2.2:8000/api/v1";

export async function mobileApiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  // Try standard backend URL, fallback to localhost if 10.0.2.2 fails
  const urls = [
    `${API_BASE}${endpoint}`,
    `http://localhost:8000/api/v1${endpoint}`,
  ];

  let lastError: any = null;
  for (const url of urls) {
    try {
      const response = await fetch(url, { ...options, headers });
      if (!response.ok) {
        let errMessage = "Request failed";
        try {
          const json = await response.json();
          errMessage = json.detail || JSON.stringify(json);
        } catch {}
        throw new Error(errMessage);
      }
      return await response.json();
    } catch (e) {
      lastError = e;
    }
  }
  throw lastError;
}
