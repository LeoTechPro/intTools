import { BaseConnector } from '@inttools/connector-sdk';
import type { ConnectorContext, ConnectorMetadata, HealthCheckResult } from '@inttools/connector-sdk';

export interface AmoCrmConnectorConfig {
  subdomain: string;
  clientId: string;
  clientSecret: string;
  redirectUri: string;
  refreshToken?: string;
}

export type AmoCrmConnectorContext = ConnectorContext & {
  config: AmoCrmConnectorConfig;
};

const AMOCRM_METADATA: ConnectorMetadata = {
  name: 'amoCRM',
  version: '0.1.0',
  slug: 'amocrm',
};

export interface AmoCrmDealPayload extends Record<string, unknown> {
  id: string;
  name: string;
  price?: number;
  pipelineId?: string;
  responsibleUserId?: string;
}

export class AmoCrmConnector extends BaseConnector {
  constructor(context: AmoCrmConnectorContext, metadata: ConnectorMetadata = AMOCRM_METADATA) {
    super(metadata, context);
  }

  private get config(): AmoCrmConnectorConfig {
    return (this.context as AmoCrmConnectorContext).config;
  }

  async initialize(): Promise<void> {
    await super.initialize();
    this.assertConfig(['subdomain', 'clientId', 'clientSecret', 'redirectUri']);
    this.context.logger.info(
      { subdomain: this.config.subdomain },
      'amocrm connector initialised',
    );
  }

  async healthCheck(): Promise<HealthCheckResult> {
    const required = ['subdomain', 'clientId', 'clientSecret', 'redirectUri'] as const;
    const missing = required.filter((key) => !this.config[key]);
    return {
      status: missing.length === 0 ? 'ok' : 'degraded',
      details: {
        subdomain: this.config.subdomain,
        hasRefreshToken: Boolean(this.config.refreshToken),
        missing,
      },
    };
  }

  publishDealCreated(deal: AmoCrmDealPayload): void {
    this.emit({
      type: 'amocrm.deal.created',
      payload: deal,
      occurredAt: new Date(),
    });
  }

  private assertConfig(keys: (keyof AmoCrmConnectorConfig)[]): void {
    const missing = keys.filter((key) => !this.config[key]);
    if (missing.length > 0) {
      throw new Error(`AmoCrmConnector: missing config keys ${missing.join(', ')}`);
    }
  }
}

export function createAmoCrmConnector(
  context: AmoCrmConnectorContext,
  metadata: ConnectorMetadata = AMOCRM_METADATA,
): AmoCrmConnector {
  return new AmoCrmConnector(context, metadata);
}
