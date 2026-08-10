import axios, { AxiosError, type AxiosRequestConfig } from "axios";

export const API_URL = "/api";

export const TOKEN_STORAGE_KEY = "hms_tokens";
export const USER_STORAGE_KEY = "hms_user";

interface TokenPair {
  access: string;
  refresh: string;
}

export function getTokens(): TokenPair | null {
  try {
    const raw = localStorage.getItem(TOKEN_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as TokenPair) : null;
  } catch {
    return null;
  }
}

export function setTokens(tokens: TokenPair) {
  localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens));
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const tokens = getTokens();
  if (tokens?.access) {
    config.headers.Authorization = `Bearer ${tokens.access}`;
  }
  return config;
});

let refreshPromise: Promise<string> | null = null;

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (AxiosRequestConfig & { _retry?: boolean }) | undefined;
    const tokens = getTokens();

    if (error.response?.status === 401 && original && !original._retry && tokens?.refresh) {
      original._retry = true;
      try {
        const refresh = async () => {
          const { data } = await axios.post(`${API_URL}/auth/refresh/`, {
            refresh: tokens.refresh,
          });
          setTokens({ access: data.access, refresh: data.refresh ?? tokens.refresh });
          return data.access as string;
        };
        refreshPromise = refreshPromise ?? refresh();
        const access = await refreshPromise;
        refreshPromise = null;
        original.headers = { ...original.headers, Authorization: `Bearer ${access}` };
        return api(original);
      } catch (refreshError) {
        refreshPromise = null;
        clearTokens();
        window.dispatchEvent(new CustomEvent("hms:unauthorized"));
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

export function getErrorMessage(error: unknown, fallback = "Something went wrong. Please try again."): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as Record<string, unknown> | undefined;
    if (!data) return error.message || fallback;
    if (typeof data.detail === "string") return data.detail;
    if (data.non_field_errors && Array.isArray(data.non_field_errors)) {
      return data.non_field_errors[0] as string;
    }
    const messages: string[] = [];
    for (const [key, value] of Object.entries(data)) {
      if (key === "detail" || key === "non_field_errors") continue;
      if (Array.isArray(value)) {
        messages.push(`${key}: ${value[0]}`);
      } else if (typeof value === "string") {
        messages.push(`${key}: ${value}`);
      }
    }
    if (messages.length) return messages.join(". ");
    if (error.response?.status === 401) return "Your session has expired. Please sign in again.";
    if (error.response?.status === 403) return "You do not have permission to perform this action.";
    if (error.response?.status === 404) return "The requested record was not found.";
    if (error.response && error.response.status >= 500) {
      return "A server error occurred. Please try again later.";
    }
  }
  if (error instanceof Error && error.message === "Network Error") {
    return "Unable to reach the server. Please check your connection.";
  }
  return fallback;
}

export function getFieldErrors(error: unknown): Record<string, string> {
  if (axios.isAxiosError(error) && error.response?.data && typeof error.response.data === "object") {
    const data = error.response.data as Record<string, unknown>;
    const out: Record<string, string> = {};
    for (const [key, value] of Object.entries(data)) {
      if (key === "detail" || key === "non_field_errors") continue;
      if (Array.isArray(value)) out[key] = String(value[0]);
      else if (typeof value === "string") out[key] = value;
    }
    return out;
  }
  return {};
}

export function downloadFile(url: string, filename: string) {
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

export async function apiGet<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const { data } = await api.get<T>(url, config);
  return data;
}

export async function apiPost<T>(url: string, body?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const { data } = await api.post<T>(url, body, config);
  return data;
}

export async function apiPatch<T>(url: string, body?: unknown): Promise<T> {
  const { data } = await api.patch<T>(url, body);
  return data;
}

export async function apiPut<T>(url: string, body?: unknown): Promise<T> {
  const { data } = await api.put<T>(url, body);
  return data;
}

export async function apiDelete<T = void>(url: string): Promise<T> {
  const { data } = await api.delete<T>(url);
  return data;
}

export { api };
