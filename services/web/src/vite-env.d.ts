/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Base URL of the backend API, e.g. http://localhost:8000. When unset,
   * the app falls back to mock data (see src/data/index.ts) so `npm run dev`
   * keeps working without a live backend.
   */
  readonly VITE_API_BASE_URL?: string;
  /**
   * Force mock data even if VITE_API_BASE_URL is set. Accepts "true"/"false".
   * Mainly useful for local UI work against fixtures while still testing
   * against a real backend in other tabs/terminals.
   */
  readonly VITE_USE_MOCK_DATA?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
