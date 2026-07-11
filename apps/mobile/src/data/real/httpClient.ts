import * as SecureStore from 'expo-secure-store';

const TOKEN_STORAGE_KEY = 'avadhana_token';

/**
 * Typed error surfaced from the backend's `{error, message}` JSON error shape
 * (see API contract: SLOT_LIMIT_EXCEEDED, ALREADY_COMMITTED, NOT_COMMITTED, etc).
 * Mirrors services/web/src/data/real/httpClient.ts's ApiError so error-handling
 * code reads the same way on both clients.
 */
export class ApiError extends Error {
  readonly status: number;
  /** Machine-readable error code from the backend, e.g. "SLOT_LIMIT_EXCEEDED". Undefined if the body didn't match the {error, message} shape. */
  readonly code?: string;
  /** Raw parsed JSON body, in case a caller needs contract-specific fields (e.g. `used`/`total` on SLOT_LIMIT_EXCEEDED). */
  readonly body?: unknown;

  constructor(status: number, message: string, code?: string, body?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.body = body;
  }
}

/** Raised when a 401 forces a logout mid-request, so callers can distinguish "session expired" from other failures. */
export class SessionExpiredError extends Error {
  constructor() {
    super('Session expired. Please log in again.');
    this.name = 'SessionExpiredError';
  }
}

function getBaseUrl(): string {
  return process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';
}

/**
 * expo-secure-store persists to the iOS Keychain / Android Keystore rather
 * than plain storage — deliberately not AsyncStorage. Matches the lesson from
 * the 2026-07-10 security audit's "JWT in localStorage" finding on web: a
 * mobile client shouldn't repeat that mistake by using an unencrypted store.
 */
export async function getStoredToken(): Promise<string | null> {
  return SecureStore.getItemAsync(TOKEN_STORAGE_KEY);
}

export async function setStoredToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_STORAGE_KEY, token);
}

export async function clearStoredToken(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_STORAGE_KEY);
}

/**
 * Called whenever a request gets a 401. Wired by AuthContext on startup so the
 * whole app can react (clear token, flip to logged-out state) without every
 * call site needing to know about auth plumbing.
 */
let onSessionExpired: (() => void) | null = null;

export function registerSessionExpiredHandler(handler: () => void): void {
  onSessionExpired = handler;
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  /** Attach the bearer token if present. Defaults to true; set false for PUBLIC endpoints that should work logged-out. */
  auth?: boolean;
}

/**
 * Shared fetch wrapper: base URL, bearer auth, JSON parsing, and typed error
 * surfacing. On 401 it clears the stored token and notifies the registered
 * session-expired handler before throwing, so callers can just `catch (e)`.
 */
export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, auth = true } = options;

  const headers: Record<string, string> = {};
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  if (auth) {
    const token = await getStoredToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  let response: Response;
  try {
    response = await fetch(`${getBaseUrl()}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (cause) {
    throw new ApiError(0, 'Could not reach the server. Check your connection and try again.', 'NETWORK_ERROR', cause);
  }

  if (response.status === 401) {
    await clearStoredToken();
    onSessionExpired?.();
    throw new SessionExpiredError();
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  const data: unknown = text ? JSON.parse(text) : undefined;

  if (!response.ok) {
    // FastAPI's HTTPException wraps whatever `detail=` payload the backend
    // raises inside a top-level `detail` key — e.g.
    // `{"detail": {"error": "SLOT_LIMIT_EXCEEDED", "message": "..."}}`,
    // not a flat `{error, message}` body. Unwrap `detail` when present so
    // callers still get the real backend-authored `error`/`message`.
    const rawBody = data as { detail?: unknown; error?: string; message?: string } | undefined;
    const errorBody =
      (rawBody?.detail as { error?: string; message?: string } | undefined) ?? rawBody;
    const message = errorBody?.message ?? `Request failed with status ${response.status}`;
    throw new ApiError(response.status, message, errorBody?.error, errorBody ?? data);
  }

  return data as T;
}
