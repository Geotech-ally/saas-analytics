/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DJANGO_URL?: string;
  readonly VITE_FASTAPI_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
