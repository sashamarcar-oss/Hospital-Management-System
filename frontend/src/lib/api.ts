import axios, {
  AxiosError,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios";

/**
 * API base URL
 *
 * Local development:
 *   VITE_API_URL is normally not set, so this falls back to /api.
 *   Vite then proxies /api to http://127.0.0.1:8000.
 *
 * Production:
 *   Vercel should have:
 *
 *   VITE_API_URL=https://YOUR-RENDER-BACKEND.onrender.com/api
 */
const rawApiUrl = import.meta.env.VITE_API_URL || "/api";

export const API_URL = rawApiUrl.replace(/\/+$/, "");

export const TOKEN_STORAGE_KEY = "hms_tokens";
export const USER_STORAGE_KEY = "hms_user";

interface TokenPair {
  access: string;
  refresh: string;
}

interface RefreshResponse {
  access: string;
  refresh?: string;
}

interface AuthenticatedRequestConfig
  extends AxiosRequestConfig {
  _retry?: boolean;
}

/**
 * Get stored JWT tokens.
 */
export function getTokens(): TokenPair | null {
  try {
    const raw = localStorage.getItem(TOKEN_STORAGE_KEY);

    if (!raw) {
      return null;
    }

    return JSON.parse(raw) as TokenPair;
  } catch {
    return null;
  }
}

/**
 * Store JWT tokens.
 */
export function setTokens(tokens: TokenPair): void {
  localStorage.setItem(
    TOKEN_STORAGE_KEY,
    JSON.stringify(tokens)
  );
}

/**
 * Remove JWT tokens.
 */
export function clearTokens(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

/**
 * Axios API client.
 */
const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Add access token to every API request.
 */
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const tokens = getTokens();

    if (tokens?.access) {
      config.headers.Authorization = `Bearer ${tokens.access}`;
    }

    return config;
  }
);

/**
 * Prevent multiple requests from refreshing the token
 * at the same time.
 */
let refreshPromise: Promise<string> | null = null;

/**
 * Refresh the access token.
 */
async function refreshAccessToken(
  refreshToken: string
): Promise<string> {
  const response = await axios.post<RefreshResponse>(
    `${API_URL}/auth/refresh/`,
    {
      refresh: refreshToken,
    }
  );

  const newAccessToken = response.data.access;

  const newRefreshToken =
    response.data.refresh ?? refreshToken;

  setTokens({
    access: newAccessToken,
    refresh: newRefreshToken,
  });

  return newAccessToken;
}

/**
 * Handle API responses and automatically refresh
 * expired access tokens.
 */
api.interceptors.response.use(
  (response) => response,

  async (error: AxiosError) => {
    const original = error.config as
      | AuthenticatedRequestConfig
      | undefined;

    const tokens = getTokens();

    /**
     * Handle network errors first.
     */
    if (!error.response) {
      return Promise.reject(error);
    }

    /**
     * Only attempt token refresh for 401 responses.
     */
    if (
      error.response.status === 401 &&
      original &&
      !original._retry &&
      tokens?.refresh
    ) {
      original._retry = true;

      try {
        /**
         * If another request is already refreshing the token,
         * wait for that refresh instead of creating another one.
         */
        if (!refreshPromise) {
          refreshPromise = refreshAccessToken(tokens.refresh);
        }

        const accessToken = await refreshPromise;

        /**
         * Reset the shared refresh promise.
         */
        refreshPromise = null;

        /**
         * Retry the original request with the new token.
         */
        original.headers = {
          ...original.headers,
          Authorization: `Bearer ${accessToken}`,
        };

        return api(original);
      } catch (refreshError) {
        refreshPromise = null;

        /**
         * Refresh token is no longer valid.
         */
        clearTokens();

        /**
         * Notify the application that authentication failed.
         */
        window.dispatchEvent(
          new CustomEvent("hms:unauthorized")
        );

        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

/**
 * Convert API/Axios errors into user-friendly messages.
 */
export function getErrorMessage(
  error: unknown,
  fallback = "Something went wrong. Please try again."
): string {
  /**
   * Axios error
   */
  if (axios.isAxiosError(error)) {
    /**
     * Network error means the browser could not
     * reach the backend at all.
     */
    if (!error.response) {
      if (error.code === "ERR_NETWORK") {
        return "Unable to reach the server. Please check your connection or try again later.";
      }

      return error.message || fallback;
    }

    const data = error.response.data as
      | Record<string, unknown>
      | undefined;

    /**
     * No response body.
     */
    if (!data) {
      if (error.response.status === 401) {
        return "Invalid username or password.";
      }

      if (error.response.status === 403) {
        return "You do not have permission to perform this action.";
      }

      if (error.response.status === 404) {
        return "The requested resource was not found.";
      }

      if (error.response.status >= 500) {
        return "A server error occurred. Please try again later.";
      }

      return error.message || fallback;
    }

    /**
     * Django REST Framework detail message.
     */
    if (typeof data.detail === "string") {
      return data.detail;
    }

    /**
     * Non-field errors.
     */
    if (
      Array.isArray(data.non_field_errors) &&
      data.non_field_errors.length > 0
    ) {
      return String(data.non_field_errors[0]);
    }

    /**
     * Field validation errors.
     */
    const messages: string[] = [];

    for (const [key, value] of Object.entries(data)) {
      if (
        key === "detail" ||
        key === "non_field_errors"
      ) {
        continue;
      }

      if (Array.isArray(value) && value.length > 0) {
        messages.push(`${key}: ${String(value[0])}`);
      } else if (typeof value === "string") {
        messages.push(`${key}: ${value}`);
      }
    }

    if (messages.length > 0) {
      return messages.join(". ");
    }

    /**
     * HTTP status-specific messages.
     */
    if (error.response.status === 400) {
      return "The information provided is invalid. Please check your details.";
    }

    if (error.response.status === 401) {
      return "Invalid username or password.";
    }

    if (error.response.status === 403) {
      return "You do not have permission to perform this action.";
    }

    if (error.response.status === 404) {
      return "The requested record was not found.";
    }

    if (error.response.status >= 500) {
      return "A server error occurred. Please try again later.";
    }

    return fallback;
  }

  /**
   * Standard JavaScript Error.
   */
  if (error instanceof Error) {
    if (error.message === "Network Error") {
      return "Unable to reach the server. Please check your connection or try again.";
    }

    return error.message || fallback;
  }

  return fallback;
}

/**
 * Extract Django REST Framework field errors.
 */
export function getFieldErrors(
  error: unknown
): Record<string, string> {
  if (
    axios.isAxiosError(error) &&
    error.response?.data &&
    typeof error.response.data === "object"
  ) {
    const data = error.response.data as Record<
      string,
      unknown
    >;

    const out: Record<string, string> = {};

    for (const [key, value] of Object.entries(data)) {
      if (
        key === "detail" ||
        key === "non_field_errors"
      ) {
        continue;
      }

      if (Array.isArray(value) && value.length > 0) {
        out[key] = String(value[0]);
      } else if (typeof value === "string") {
        out[key] = value;
      }
    }

    return out;
  }

  return {};
}

/**
 * Download a file from a URL.
 */
export function downloadFile(
  url: string,
  filename: string
): void {
  const a = document.createElement("a");

  a.href = url;
  a.download = filename;

  document.body.appendChild(a);
  a.click();
  a.remove();
}

/**
 * GET request.
 */
export async function apiGet<T = unknown>(
  url: string,
  config?: AxiosRequestConfig
): Promise<T> {
  const { data } = await api.get<T>(url, config);
  return data;
}

/**
 * POST request.
 */
export async function apiPost<T = unknown>(
  url: string,
  body?: unknown,
  config?: AxiosRequestConfig
): Promise<T> {
  const { data } = await api.post<T>(
    url,
    body,
    config
  );

  return data;
}

/**
 * PATCH request.
 */
export async function apiPatch<T = unknown>(
  url: string,
  body?: unknown,
  config?: AxiosRequestConfig
): Promise<T> {
  const { data } = await api.patch<T>(
    url,
    body,
    config
  );

  return data;
}

/**
 * PUT request.
 */
export async function apiPut<T = unknown>(
  url: string,
  body?: unknown,
  config?: AxiosRequestConfig
): Promise<T> {
  const { data } = await api.put<T>(
    url,
    body,
    config
  );

  return data;
}

/**
 * DELETE request.
 */
export async function apiDelete<T = void>(
  url: string,
  config?: AxiosRequestConfig
): Promise<T> {
  const { data } = await api.delete<T>(
    url,
    config
  );

  return data;
}

export { api };