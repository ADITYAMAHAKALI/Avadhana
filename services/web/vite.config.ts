import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Allows access via an ngrok tunnel (or similar) when sharing the
    // local dev server with others outside this machine. Vite blocks
    // unrecognized Host headers by default as a DNS-rebinding
    // protection; this is dev-only config, never shipped in a build.
    allowedHosts: ['bleakish-unionistic-lorraine.ngrok-free.dev'],
  },
})
