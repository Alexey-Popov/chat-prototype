/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CORE_URL: string;
  readonly VITE_DEV_MOCK_USER: string;
  readonly VITE_DEV_DEFAULT_EMAIL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
