import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fc from 'fast-check';

import {
  createBitrix24Connector,
  type Bitrix24ConnectorContext,
  type Bitrix24LeadPayload,
  createAmoCrmConnector,
  type AmoCrmConnectorContext,
  type AmoCrmDealPayload,
  createGetCourseConnector,
  type GetCourseConnectorContext,
  type GetCourseEnrollmentPayload,
} from '..';
import type { ConnectorEvent } from '@inttools/connector-sdk';

function createEventCapture(prefix: string): {
  events: ConnectorEvent[];
  logger: {
    info: (obj: unknown, msg?: string) => void;
    warn: (obj: unknown, msg?: string) => void;
    error: (obj: unknown, msg?: string) => void;
    debug: (obj: unknown, msg?: string) => void;
  };
} {
  const events: ConnectorEvent[] = [];
  const collect = (level: string, obj: unknown, msg?: string) => {
    const text = msg ?? '';
    if (process.env.CONNECTOR_SDK_VERBOSE === '1') {
      // eslint-disable-next-line no-console
      console.log({ prefix, level, message: text, details: obj });
    }
    if (typeof obj === 'object' && obj !== null && 'event' in obj) {
      const maybeEvent = (obj as { event?: ConnectorEvent }).event;
      if (maybeEvent) {
        events.push(maybeEvent);
      }
    }
  };

  return {
    events,
    logger: {
      info: (obj, msg) => collect('info', obj, msg),
      warn: (obj, msg) => collect('warn', obj, msg),
      error: (obj, msg) => collect('error', obj, msg),
      debug: (obj, msg) => collect('debug', obj, msg),
    },
  };
}

const bitrixLeadArb: fc.Arbitrary<Bitrix24LeadPayload> = fc.record(
  {
    id: fc.string({ minLength: 1, maxLength: 32 }),
    title: fc.string({ minLength: 1, maxLength: 64 }),
    amount: fc.option(fc.integer({ min: 0, max: 1000000 }), { nil: undefined }),
    assignedTo: fc.option(fc.string({ maxLength: 32 }), { nil: undefined }),
  },
  { requiredKeys: ['id', 'title'] },
);

const amoCrmDealArb: fc.Arbitrary<AmoCrmDealPayload> = fc.record(
  {
    id: fc.string({ minLength: 1, maxLength: 32 }),
    name: fc.string({ minLength: 1, maxLength: 64 }),
    price: fc.option(fc.integer({ min: 0, max: 1000000 }), { nil: undefined }),
    pipelineId: fc.option(fc.string({ maxLength: 32 }), { nil: undefined }),
    responsibleUserId: fc.option(fc.string({ maxLength: 32 }), { nil: undefined }),
  },
  { requiredKeys: ['id', 'name'] },
);

const getCourseEnrollmentArb: fc.Arbitrary<GetCourseEnrollmentPayload> = fc.record(
  {
    userEmail: fc.emailAddress(),
    courseCode: fc.string({ minLength: 1, maxLength: 64 }),
    enrolledAt: fc
      .date({ min: new Date('2020-01-01T00:00:00Z'), max: new Date('2030-01-01T00:00:00Z') })
      .map((d) => d.toISOString()),
    orderId: fc.option(fc.string({ maxLength: 32 }), { nil: undefined }),
  },
  { requiredKeys: ['userEmail', 'courseCode', 'enrolledAt'] },
);

function assertConnectorEvent(event: ConnectorEvent | undefined, expectedType: string): asserts event is ConnectorEvent {
  assert.ok(event, 'event emitted');
  assert.equal(event.type, expectedType);
  assert.ok(event.occurredAt instanceof Date);
}

describe('connector examples fuzz', () => {
  it('Bitrix24 publishLeadCreated preserves payload', async () => {
    await fc.assert(
      fc.asyncProperty(bitrixLeadArb, async (lead) => {
        const capture = createEventCapture('bitrix24');
        const context: Bitrix24ConnectorContext = {
          logger: capture.logger,
          config: {
            portalUrl: 'https://example.bitrix24.ru',
            authToken: 'bitrix-token',
            webhookSecret: 'secret',
          },
        };
        const connector = createBitrix24Connector(context);
        await connector.initialize();

        const leadSnapshot = { ...lead };
        connector.publishLeadCreated(lead);

        const event = capture.events.at(-1);
        assertConnectorEvent(event, 'bitrix24.lead.created');
        assert.deepStrictEqual(event.payload, leadSnapshot);
        assert.deepStrictEqual(lead, leadSnapshot);
      }),
      { numRuns: 50 },
    );
  });

  it('amoCRM publishDealCreated preserves payload', async () => {
    await fc.assert(
      fc.asyncProperty(amoCrmDealArb, async (deal) => {
        const capture = createEventCapture('amocrm');
        const context: AmoCrmConnectorContext = {
          logger: capture.logger,
          config: {
            subdomain: 'example',
            clientId: 'client-id',
            clientSecret: 'client-secret',
            redirectUri: 'https://example.com/oauth',
            refreshToken: 'refresh-token',
          },
        };
        const connector = createAmoCrmConnector(context);
        await connector.initialize();

        const dealSnapshot = { ...deal };
        connector.publishDealCreated(deal);

        const event = capture.events.at(-1);
        assertConnectorEvent(event, 'amocrm.deal.created');
        assert.deepStrictEqual(event.payload, dealSnapshot);
        assert.deepStrictEqual(deal, dealSnapshot);
      }),
      { numRuns: 50 },
    );
  });

  it('GetCourse publishEnrollmentCreated preserves payload', async () => {
    await fc.assert(
      fc.asyncProperty(getCourseEnrollmentArb, async (enrollment) => {
        const capture = createEventCapture('getcourse');
        const context: GetCourseConnectorContext = {
          logger: capture.logger,
          config: {
            accountDomain: 'academy',
            apiKey: 'gc-api-key',
            webhookSecret: 'gc-secret',
          },
        };
        const connector = createGetCourseConnector(context);
        await connector.initialize();

        const enrollmentSnapshot = { ...enrollment };
        connector.publishEnrollmentCreated(enrollment);

        const event = capture.events.at(-1);
        assertConnectorEvent(event, 'getcourse.enrollment.created');
        assert.deepStrictEqual(event.payload, enrollmentSnapshot);
        assert.deepStrictEqual(enrollment, enrollmentSnapshot);
      }),
      { numRuns: 50 },
    );
  });
});
