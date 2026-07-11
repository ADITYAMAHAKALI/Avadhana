# Avadhana Mobile

Expo (React Native, managed workflow) client for Avadhana. Own `package.json`, doesn't touch `services/web/`. See epic [#87](https://github.com/ADITYAMAHAKALI/Avadhana/issues/87) and its sub-issues for scope and sequencing.

## Get started

1. Point at a running `services/backend-api` instance:

   ```bash
   cp .env.example .env
   # edit EXPO_PUBLIC_API_BASE_URL if the backend isn't on localhost:8000
   ```

2. Install dependencies and start the dev server:

   ```bash
   npm install
   npx expo start
   ```

   From the CLI output you can open the app in a development build, an Android emulator, an iOS simulator, [Expo Go](https://expo.dev/go), or a browser (`npx expo start --web`).

## Structure

- `src/app/` — file-based routes (Expo Router): `login.tsx`, `signup.tsx`, `(tabs)/` (dashboard/discover/profile), `problems/[problemId].tsx`.
- `src/data/` — HTTP client + typed API calls against `services/backend-api`, mirroring the ports pattern in `services/web/src/data/`. JWT is stored via `expo-secure-store` (iOS Keychain / Android Keystore), not `AsyncStorage` — see the 2026-07-10 security audit's localStorage-JWT finding for why that distinction matters.
- `src/context/AuthContext.tsx` — session state (bootstrap from stored token, login, signup, logout).
- `src/components/` — themed primitives (`ThemedText`, `ThemedView`) carried over from the Expo template.

## What's built vs. what's next

Auth, dashboard ("your focus"), discover, and a read-only problem detail + feed view are wired to the real backend. Commit modal, checkpoint flow, gated feed writes (post/comment/like), and push notifications are tracked as separate sub-issues of #87 — see the "Mobile App" section in the repo root `TODO.md`.
