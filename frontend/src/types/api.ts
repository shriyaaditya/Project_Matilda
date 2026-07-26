export interface HealthResponse {
  status: string;
  app_name: string;
  environment: string;
  version: string;
}

export interface ApiErrorResponse {
  error: {
    code: number;
    message: string;
    details?: unknown;
    path: string;
  };
}
