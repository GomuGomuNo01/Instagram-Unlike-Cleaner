/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** « true » dans la démo en ligne (npm run build:demo), absent sinon. */
  readonly VITE_DEMO?: string
}
