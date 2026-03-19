import { randomUUID } from 'crypto';
import {
  AuthType,
  createContentGenerator,
  createContentGeneratorConfig,
} from '@google/gemini-cli-core/dist/src/core/contentGenerator.js';

const DEFAULT_PRIMARY_MODEL = 'gemini-3-flash-preview';
const DEFAULT_FALLBACK_CHAIN = [
  'gemini-2.5-pro',
  'gemini-2.5-flash',
  'gemini-2.5-flash-lite',
];
const DEFAULT_AUTH_TYPE = 'oauth-personal';

type RuntimeState = {
  model: string;
  sessionId: string;
  generatorPromise: Promise<any> | null;
  initialized: boolean;
  lastInitError: string | null;
  contentGeneratorConfig: Record<string, unknown>;
  creditsNotificationShown: boolean;
  latestApiRequest: Record<string, unknown> | undefined;
};

const primaryModel = process.env.MODEL?.trim() || DEFAULT_PRIMARY_MODEL;
const fallbackModels = (process.env.MODEL_FALLBACK_CHAIN ?? DEFAULT_FALLBACK_CHAIN.join(','))
  .split(',')
  .map((value) => value.trim())
  .filter(Boolean);
const authType = (process.env.AUTH_TYPE?.trim() || DEFAULT_AUTH_TYPE) as AuthType;
const runtimeStates = new Map<string, RuntimeState>();

function getSessionId(model: string) {
  return `openai-proxy-${model}-${randomUUID()}`;
}

function createRuntimeState(model: string): RuntimeState {
  return {
    model,
    sessionId: getSessionId(model),
    generatorPromise: null,
    initialized: false,
    lastInitError: null,
    contentGeneratorConfig: { authType },
    creditsNotificationShown: false,
    latestApiRequest: undefined,
  };
}

function getRuntimeState(model: string) {
  const cached = runtimeStates.get(model);

  if (cached) {
    return cached;
  }

  const state = createRuntimeState(model);
  runtimeStates.set(model, state);

  return state;
}

function createConfigShim(state: RuntimeState) {
  return {
    fakeResponses: undefined,
    recordResponses: undefined,
    getModel: () => state.model,
    getActiveModel: () => state.model,
    setModel: (_value: string) => {},
    getProxy: () => undefined,
    getUsageStatisticsEnabled: () => false,
    getGemini31Launched: async () => false,
    getGemini31LaunchedSync: () => false,
    getContentGeneratorConfig: () => state.contentGeneratorConfig,
    getValidationHandler: () => undefined,
    isBrowserLaunchSuppressed: () => process.env.NO_BROWSER === 'true',
    getAcpMode: () => false,
    getBillingSettings: () => ({ overageStrategy: 'ask' }),
    getCreditsNotificationShown: () => state.creditsNotificationShown,
    setCreditsNotificationShown: (value: boolean) => {
      state.creditsNotificationShown = value;
    },
    refreshUserQuotaIfStale: async () => undefined,
    refreshAvailableCredits: async () => {},
    getQuotaRemaining: () => undefined,
    getQuotaLimit: () => undefined,
    getQuotaResetTime: () => undefined,
    getUserTier: () => undefined,
    getUserTierName: () => undefined,
    getUserPaidTier: () => undefined,
    setQuota: (
      _remaining: number | undefined,
      _limit: number | undefined,
      _modelId?: string,
    ) => {},
    getExperimentsAsync: async () => undefined,
    setLatestApiRequest: (request: Record<string, unknown>) => {
      state.latestApiRequest = request;
    },
    getLatestApiRequest: () => state.latestApiRequest,
  };
}

async function initializeGenerator(state: RuntimeState) {
  const configShim = createConfigShim(state);
  const generatorConfig = await createContentGeneratorConfig(
    configShim as any,
    authType,
  );

  state.contentGeneratorConfig = generatorConfig as Record<string, unknown>;

  return createContentGenerator(generatorConfig, configShim as any, state.sessionId);
}

async function ensureGenerator(model: string) {
  const state = getRuntimeState(model);

  if (!state.generatorPromise) {
    state.generatorPromise = initializeGenerator(state)
      .then((generator) => {
        state.initialized = true;
        state.lastInitError = null;

        return generator;
      })
      .catch((error: Error) => {
        state.initialized = false;
        state.lastInitError = error.message;
        state.generatorPromise = null;
        throw error;
      });
  }

  return {
    generator: await state.generatorPromise,
    state,
  };
}

function createPromptId() {
  return `proxy-${randomUUID()}`;
}

function isFallbackableError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);

  return /requested entity was not found|quota|capacity|reset after|rateLimitExceeded|too many requests/i.test(
    message,
  );
}

function dedupeModels(models: string[]) {
  return [...new Set(models.filter(Boolean))];
}

function getModelChain(preferredModel?: string) {
  return dedupeModels([
    preferredModel?.trim() || primaryModel,
    primaryModel,
    ...fallbackModels,
  ]);
}

async function runWithFallback<T>(
  preferredModel: string | undefined,
  execute: (args: { generator: any; model: string }) => Promise<T>,
) {
  const attempts: { model: string; reason: string }[] = [];
  let lastError: unknown;

  for (const model of getModelChain(preferredModel)) {
    try {
      const { generator } = await ensureGenerator(model);

      return await execute({ generator, model });
    } catch (error) {
      lastError = error;
      attempts.push({
        model,
        reason: error instanceof Error ? error.message : String(error),
      });

      if (!isFallbackableError(error)) {
        throw error;
      }
    }
  }

  if (lastError instanceof Error) {
    lastError.message = `${lastError.message} (attempted models: ${attempts
      .map((item) => item.model)
      .join(' -> ')})`;
  }

  throw lastError;
}

export async function sendChat({
  preferredModel,
  contents,
  config = {},
}: {
  preferredModel?: string;
  contents: any[];
  config?: Record<string, unknown>;
}) {
  return runWithFallback(preferredModel, async ({ generator, model }) => ({
    model,
    response: await generator.generateContent(
      {
        model,
        contents,
        config,
      },
      createPromptId(),
      'user',
    ),
  }));
}

export async function sendChatStream({
  preferredModel,
  contents,
  config = {},
}: {
  preferredModel?: string;
  contents: any[];
  config?: Record<string, unknown>;
}) {
  return runWithFallback(preferredModel, async ({ generator, model }) => {
    const stream = await generator.generateContentStream(
      {
        model,
        contents,
        config,
      },
      createPromptId(),
      'user',
    );

    return { model, stream };
  });
}

export function listModels() {
  return dedupeModels([primaryModel, ...fallbackModels]).map((model) => ({
    id: model,
    object: 'model',
    owned_by: 'google',
  }));
}

export function getRuntimeStatus() {
  return {
    authType,
    primaryModel,
    fallbackModels,
    models: Array.from(runtimeStates.values()).map((state) => ({
      model: state.model,
      initialized: state.initialized,
      lastInitError: state.lastInitError,
      sessionId: state.sessionId,
    })),
  };
}
