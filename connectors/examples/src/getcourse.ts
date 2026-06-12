import { BaseConnector } from '@inttools/connector-sdk';
import type { ConnectorContext, ConnectorMetadata, HealthCheckResult } from '@inttools/connector-sdk';

export interface GetCourseConnectorConfig {
  accountDomain: string;
  apiKey: string;
  webhookSecret?: string;
}

export type GetCourseConnectorContext = ConnectorContext & {
  config: GetCourseConnectorConfig;
};

const GETCOURSE_METADATA: ConnectorMetadata = {
  name: 'GetCourse',
  version: '0.1.0',
  slug: 'getcourse',
};

export interface GetCourseEnrollmentPayload extends Record<string, unknown> {
  userEmail: string;
  courseCode: string;
  enrolledAt: string;
  orderId?: string;
}

export class GetCourseConnector extends BaseConnector {
  constructor(context: GetCourseConnectorContext, metadata: ConnectorMetadata = GETCOURSE_METADATA) {
    super(metadata, context);
  }

  private get config(): GetCourseConnectorConfig {
    return (this.context as GetCourseConnectorContext).config;
  }

  async initialize(): Promise<void> {
    await super.initialize();
    this.assertConfig(['accountDomain', 'apiKey']);
    this.context.logger.info(
      { accountDomain: this.config.accountDomain },
      'getcourse connector initialised',
    );
  }

  async healthCheck(): Promise<HealthCheckResult> {
    const hasConfig = Boolean(this.config.accountDomain && this.config.apiKey);
    return {
      status: hasConfig ? 'ok' : 'degraded',
      details: {
        accountDomain: this.config.accountDomain,
        hasWebhookSecret: Boolean(this.config.webhookSecret),
      },
    };
  }

  publishEnrollmentCreated(enrollment: GetCourseEnrollmentPayload): void {
    this.emit({
      type: 'getcourse.enrollment.created',
      payload: enrollment,
      occurredAt: new Date(),
    });
  }

  private assertConfig(keys: (keyof GetCourseConnectorConfig)[]): void {
    const missing = keys.filter((key) => !this.config[key]);
    if (missing.length > 0) {
      throw new Error(`GetCourseConnector: missing config keys ${missing.join(', ')}`);
    }
  }
}

export function createGetCourseConnector(
  context: GetCourseConnectorContext,
  metadata: ConnectorMetadata = GETCOURSE_METADATA,
): GetCourseConnector {
  return new GetCourseConnector(context, metadata);
}
