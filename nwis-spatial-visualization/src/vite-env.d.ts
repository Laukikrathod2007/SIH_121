/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_VISUALIZATION_PROVIDER?: 'nwis' | 'volve';
  readonly VITE_GOOGLE_MAPS_3D_KEY?: string;
  readonly VITE_CESIUM_ION_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
