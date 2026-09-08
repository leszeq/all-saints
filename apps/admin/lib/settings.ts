export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  status: string;
  roles: string[];
  permissions: string[];
  preferred_language: string;
  last_login_at?: string | null;
}

export interface ApplicationSettings {
  app_name: string;
  app_version: string;
  environment: string;
  docs_url?: string | null;
  redoc_url?: string | null;
  openapi_url?: string | null;
  features: {
    ai_search: boolean;
    maps: boolean;
    timeline: boolean;
    exports: boolean;
  };
  ai: {
    provider: string;
    openai_configured: boolean;
    embedding_model: string;
    completion_model: string;
    ollama_base_url?: string | null;
    ollama_embedding_model: string;
    ollama_llm_model: string;
    embedding_dimensions: number;
  };
  storage: {
    backend: string;
    images_bucket: string;
    documents_bucket: string;
    exports_bucket: string;
    public_endpoint?: string | null;
  };
  security: {
    access_token_minutes: number;
    refresh_token_days: number;
    secure_cookies: boolean;
    cors_origins: string[];
    docs_enabled: boolean;
  };
}
