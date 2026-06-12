import { BaseConnector } from '@inttools/connector-sdk';
import type { ConnectorContext, ConnectorMetadata, HealthCheckResult } from '@inttools/connector-sdk';

export interface Bitrix24ConnectorConfig {
  portalUrl: string;
  authToken: string;
  webhookSecret?: string;
}

export type Bitrix24ConnectorContext = ConnectorContext & {
  config: Bitrix24ConnectorConfig;
};

const BITRIX24_METADATA: ConnectorMetadata = {
  name: 'Bitrix24',
  version: '0.1.0',
  slug: 'bitrix24',
};

export interface Bitrix24LeadPayload extends Record<string, unknown> {
  id: string;
  title: string;
  amount?: number;
  assignedTo?: string;
}

export class Bitrix24Connector extends BaseConnector {
  constructor(context: Bitrix24ConnectorContext, metadata: ConnectorMetadata = BITRIX24_METADATA) {
    super(metadata, context);
  }

  private get config(): Bitrix24ConnectorConfig {
    return (this.context as Bitrix24ConnectorContext).config;
  }

  async initialize(): Promise<void> {
    await super.initialize();
    this.assertConfig(['portalUrl', 'authToken']);
    this.context.logger.info(
      { portalUrl: this.config.portalUrl },
      'bitrix24 connector initialised',
    );
  }

  async healthCheck(): Promise<HealthCheckResult> {
    const hasRequiredConfig = ['portalUrl', 'authToken'].every((key) => Boolean(this.config[key as keyof Bitrix24ConnectorConfig]));
    return {
      status: hasRequiredConfig ? 'ok' : 'degraded',
      details: {
        portalUrl: this.config.portalUrl,
        hasAuthToken: Boolean(this.config.authToken),
      },
    };
  }

  publishLeadCreated(lead: Bitrix24LeadPayload): void {
    this.emit({
      type: 'bitrix24.lead.created',
      payload: lead,
      occurredAt: new Date(),
    });
  }

  private assertConfig(keys: (keyof Bitrix24ConnectorConfig)[]): void {
    const missing = keys.filter((key) => !this.config[key]);
    if (missing.length > 0) {
      throw new Error(`Bitrix24Connector: missing config keys ${missing.join(', ')}`);
    }
  }
}

export function createBitrix24Connector(
  context: Bitrix24ConnectorContext,
  metadata: ConnectorMetadata = BITRIX24_METADATA,
): Bitrix24Connector {
  return new Bitrix24Connector(context, metadata);
}
