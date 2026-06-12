import { ConnectorContext, ConnectorLifecycle, ConnectorMetadata, ConnectorEvent, HealthCheckResult } from './types';

export abstract class BaseConnector implements ConnectorLifecycle {
  protected readonly context: ConnectorContext;

  protected readonly metadata: ConnectorMetadata;

  protected constructor(metadata: ConnectorMetadata, context: ConnectorContext) {
    this.metadata = metadata;
    this.context = context;
  }

  get info(): ConnectorMetadata {
    return this.metadata;
  }

  async initialize(): Promise<void> {
    this.context.logger.info({ name: this.metadata.name, version: this.metadata.version }, 'connector initialize');
  }

  async healthCheck(): Promise<HealthCheckResult> {
    return { status: 'ok' };
  }

  async shutdown(): Promise<void> {
    this.context.logger.info({ name: this.metadata.name }, 'connector shutdown');
  }

  protected emit(event: ConnectorEvent): void {
    this.context.logger.debug({ event }, 'connector event');
  }
}
