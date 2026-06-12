import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  Bitrix24Connector,
  createBitrix24Connector,
  type Bitrix24ConnectorContext,
  AmoCrmConnector,
  createAmoCrmConnector,
  type AmoCrmConnectorContext,
  GetCourseConnector,
  createGetCourseConnector,
  type GetCourseConnectorContext,
} from '..';

interface TestLogger {
  events: string[];
  logger: {
    info: (obj: unknown, msg?: string) => void;
    warn: (obj: unknown, msg?: string) => void;
    error: (obj: unknown, msg?: string) => void;
    debug: (obj: unknown, msg?: string) => void;
  };
}

function createTestLogger(prefix: string): TestLogger {
  const events: string[] = [];
  const log = (level: string, obj: unknown, msg?: string) => {
    const text = msg ?? '';
    if (process.env.CONNECTOR_SDK_VERBOSE === '1') {
      // eslint-disable-next-line no-console
      console.log({ prefix, level, message: text, details: obj });
    }
    if (typeof obj === 'object' && obj !== null && 'event' in obj) {
      const event = (obj as { event?: { type?: string } }).event;
      if (event?.type) {
        events.push(event.type);
      }
    }
  };

  return {
    events,
    logger: {
      info: (obj, msg) => log('info', obj, msg),
      warn: (obj, msg) => log('warn', obj, msg),
      error: (obj, msg) => log('error', obj, msg),
      debug: (obj, msg) => log('debug', obj, msg),
    },
  };
}

describe('connector examples', () => {
  it('initialises Bitrix24 connector and emits lead events', async () => {
    const { logger, events } = createTestLogger('bitrix24');
    const context: Bitrix24ConnectorContext = {
      logger,
      config: {
        portalUrl: 'https://example.bitrix24.ru',
        authToken: 'bitrix-token',
        webhookSecret: 'secret',
      },
    };

    const connector: Bitrix24Connector = createBitrix24Connector(context);
    await connector.initialize();
    const health = await connector.healthCheck();
    connector.publishLeadCreated({ id: '123', title: 'New lead', amount: 1000 });

    assert.equal(health.status, 'ok');
    assert.ok(events.includes('bitrix24.lead.created'));
  });

  it('initialises amoCRM connector and emits deal events', async () => {
    const { logger, events } = createTestLogger('amocrm');
    const context: AmoCrmConnectorContext = {
      logger,
      config: {
        subdomain: 'example',
        clientId: 'client-id',
        clientSecret: 'client-secret',
        redirectUri: 'https://example.com/oauth',
        refreshToken: 'refresh-token',
      },
    };

    const connector: AmoCrmConnector = createAmoCrmConnector(context);
    await connector.initialize();
    const health = await connector.healthCheck();
    connector.publishDealCreated({ id: 'deal-42', name: 'New deal', price: 2500 });

    assert.equal(health.status, 'ok');
    assert.ok(events.includes('amocrm.deal.created'));
  });

  it('initialises GetCourse connector and emits enrollment events', async () => {
    const { logger, events } = createTestLogger('getcourse');
    const context: GetCourseConnectorContext = {
      logger,
      config: {
        accountDomain: 'academy',
        apiKey: 'gc-api-key',
        webhookSecret: 'gc-secret',
      },
    };

    const connector: GetCourseConnector = createGetCourseConnector(context);
    await connector.initialize();
    const health = await connector.healthCheck();
    connector.publishEnrollmentCreated({
      userEmail: 'student@example.com',
      courseCode: 'intro-101',
      enrolledAt: new Date().toISOString(),
    });

    assert.equal(health.status, 'ok');
    assert.ok(events.includes('getcourse.enrollment.created'));
  });
});
