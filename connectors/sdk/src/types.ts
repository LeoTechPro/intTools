export interface ConnectorMetadata {
  /** Human-readable name, e.g. "Bitrix24" */
  name: string;
  /** Semantic version of the connector implementation */
  version: string;
  /** Optional unique identifier used in registry */
  slug?: string;
}

export interface ConnectorContext {
  /** Structured logger (pino-compatible) */
  logger: {
    info: (obj: unknown, msg?: string) => void;
    warn: (obj: unknown, msg?: string) => void;
    error: (obj: unknown, msg?: string) => void;
    debug: (obj: unknown, msg?: string) => void;
  };
  /** Shared configuration resolved from environment or secrets store */
  config: Record<string, unknown>;
}

export interface HealthCheckResult {
  status: 'ok' | 'degraded' | 'error';
  details?: Record<string, unknown>;
}

export interface ConnectorLifecycle {
  initialize(): Promise<void>;
  healthCheck(): Promise<HealthCheckResult>;
  shutdown(): Promise<void>;
}

export interface ConnectorEvent<TPayload = Record<string, unknown>> {
  type: string;
  payload: TPayload;
  occurredAt: Date;
}
