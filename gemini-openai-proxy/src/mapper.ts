import { randomUUID } from 'crypto';
import { fetchAndEncode } from './remoteimage';

export class ProxyRequestError extends Error {
  statusCode: number;

  constructor(statusCode: number, message: string) {
    super(message);
    this.name = 'ProxyRequestError';
    this.statusCode = statusCode;
  }
}

type GeminiPart = Record<string, unknown>;
type GeminiContent = { role: 'user' | 'model'; parts: GeminiPart[] };
type OpenAIToolDefinition = {
  name: string;
  description?: string;
  parameters?: Record<string, unknown>;
};
type OpenAIToolCallState = {
  id: string;
  index: number;
  name: string;
  args: Record<string, unknown>;
  emitted: boolean;
};

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function parseJsonOrThrow(value: string, message: string) {
  try {
    return JSON.parse(value);
  } catch {
    throw new ProxyRequestError(400, message);
  }
}

function normalizeToolArguments(value: unknown) {
  if (typeof value !== 'string' || value.trim() === '') {
    return {};
  }

  const parsed = parseJsonOrThrow(
    value,
    'Tool/function arguments must be valid JSON.',
  );

  if (isPlainObject(parsed)) {
    return parsed;
  }

  return { value: parsed };
}

function normalizeToolResponseContent(content: unknown) {
  if (Array.isArray(content)) {
    const text = content
      .map((item) => {
        if (typeof item === 'string') {
          return item;
        }

        if (isPlainObject(item) && typeof item.text === 'string') {
          return item.text;
        }

        return JSON.stringify(item);
      })
      .join('');

    return { output: text };
  }

  if (typeof content === 'string') {
    const trimmed = content.trim();

    if (!trimmed) {
      return { output: '' };
    }

    try {
      const parsed = JSON.parse(trimmed);

      if (isPlainObject(parsed)) {
        return parsed;
      }

      return { output: parsed };
    } catch {
      return { output: content };
    }
  }

  if (isPlainObject(content)) {
    return content;
  }

  return { output: content ?? null };
}

function mergeObjects(
  target: Record<string, unknown>,
  source: Record<string, unknown>,
) {
  const result = { ...target };

  for (const [key, value] of Object.entries(source)) {
    if (isPlainObject(value) && isPlainObject(result[key])) {
      result[key] = mergeObjects(
        result[key] as Record<string, unknown>,
        value,
      );
    } else {
      result[key] = value;
    }
  }

  return result;
}

async function mapContentToParts(content: unknown): Promise<GeminiPart[]> {
  if (content == null) {
    return [];
  }

  if (typeof content === 'string') {
    return [{ text: content }];
  }

  if (!Array.isArray(content)) {
    throw new ProxyRequestError(400, 'Message content must be a string or array.');
  }

  const parts: GeminiPart[] = [];

  for (const item of content) {
    if (!isPlainObject(item)) {
      throw new ProxyRequestError(400, 'Unsupported structured message content.');
    }

    if (item.type === 'text' || item.type === 'input_text') {
      parts.push({ text: String(item.text ?? '') });
      continue;
    }

    if (item.type === 'image_url') {
      const imageUrlValue = item.image_url;
      const imageUrl =
        typeof imageUrlValue === 'string'
          ? imageUrlValue
          : isPlainObject(imageUrlValue) && typeof imageUrlValue.url === 'string'
            ? imageUrlValue.url
            : undefined;

      if (typeof imageUrl !== 'string' || imageUrl.trim() === '') {
        throw new ProxyRequestError(400, 'image_url must include a non-empty url.');
      }

      parts.push({ inlineData: await fetchAndEncode(imageUrl) });
      continue;
    }

    throw new ProxyRequestError(
      400,
      `Unsupported content part type: ${String(item.type)}`,
    );
  }

  return parts;
}

function collectToolDefinitions(body: any) {
  const definitions: OpenAIToolDefinition[] = [];

  if (Array.isArray(body.functions)) {
    for (const fn of body.functions) {
      if (!isPlainObject(fn) || typeof fn.name !== 'string') {
        throw new ProxyRequestError(400, 'Each function must include a name.');
      }

      definitions.push({
        name: fn.name,
        description: typeof fn.description === 'string' ? fn.description : undefined,
        parameters: isPlainObject(fn.parameters) ? fn.parameters : undefined,
      });
    }
  }

  if (Array.isArray(body.tools)) {
    for (const tool of body.tools) {
      if (!isPlainObject(tool) || tool.type !== 'function' || !isPlainObject(tool.function)) {
        throw new ProxyRequestError(
          400,
          'Each tool must be of type "function" and include a function payload.',
        );
      }

      if (typeof tool.function.name !== 'string') {
        throw new ProxyRequestError(400, 'Each tool function must include a name.');
      }

      definitions.push({
        name: tool.function.name,
        description:
          typeof tool.function.description === 'string'
            ? tool.function.description
            : undefined,
        parameters: isPlainObject(tool.function.parameters)
          ? tool.function.parameters
          : undefined,
      });
    }
  }

  return definitions;
}

function buildToolConfig(body: any, toolNames: string[]) {
  if (!toolNames.length) {
    return undefined;
  }

  const explicitChoice = body.tool_choice ?? body.function_call;

  if (explicitChoice === undefined || explicitChoice === 'auto') {
    return {
      functionCallingConfig: {
        mode: 'AUTO',
      },
    };
  }

  if (explicitChoice === 'none') {
    return {
      functionCallingConfig: {
        mode: 'NONE',
      },
    };
  }

  if (explicitChoice === 'required') {
    return {
      functionCallingConfig: {
        mode: 'ANY',
      },
    };
  }

  if (isPlainObject(explicitChoice)) {
    const functionName =
      typeof explicitChoice.name === 'string'
        ? explicitChoice.name
        : explicitChoice.type === 'function' &&
            isPlainObject(explicitChoice.function) &&
            typeof explicitChoice.function.name === 'string'
          ? explicitChoice.function.name
          : undefined;

    if (!functionName) {
      throw new ProxyRequestError(400, 'tool_choice/function_call name is missing.');
    }

    if (!toolNames.includes(functionName)) {
      throw new ProxyRequestError(
        400,
        `Requested tool "${functionName}" is not present in tools/functions.`,
      );
    }

    return {
      functionCallingConfig: {
        mode: 'ANY',
        allowedFunctionNames: [functionName],
      },
    };
  }

  throw new ProxyRequestError(400, 'Unsupported tool_choice/function_call value.');
}

async function mapMessages(messages: any[]) {
  if (!Array.isArray(messages) || messages.length === 0) {
    throw new ProxyRequestError(400, 'messages must be a non-empty array.');
  }

  const contents: GeminiContent[] = [];
  const systemParts: GeminiPart[] = [];
  const toolNamesById = new Map<string, string>();

  for (const message of messages) {
    if (!isPlainObject(message) || typeof message.role !== 'string') {
      throw new ProxyRequestError(400, 'Each message must include a role.');
    }

    if (message.role === 'system') {
      const parts = await mapContentToParts(message.content);
      systemParts.push(...parts);
      continue;
    }

    if (message.role === 'user') {
      contents.push({
        role: 'user',
        parts: await mapContentToParts(message.content),
      });
      continue;
    }

    if (message.role === 'assistant') {
      const parts = await mapContentToParts(message.content);

      if (Array.isArray(message.tool_calls)) {
        for (const toolCall of message.tool_calls) {
          if (
            !isPlainObject(toolCall) ||
            toolCall.type !== 'function' ||
            !isPlainObject(toolCall.function) ||
            typeof toolCall.function.name !== 'string'
          ) {
            throw new ProxyRequestError(
              400,
              'assistant.tool_calls must contain function calls.',
            );
          }

          const toolCallId =
            typeof toolCall.id === 'string' && toolCall.id.trim() !== ''
              ? toolCall.id
              : `call_${randomUUID()}`;

          toolNamesById.set(toolCallId, toolCall.function.name);
          parts.push({
            functionCall: {
              id: toolCallId,
              name: toolCall.function.name,
              args: normalizeToolArguments(toolCall.function.arguments),
            },
          });
        }
      }

      contents.push({
        role: 'model',
        parts,
      });
      continue;
    }

    if (message.role === 'tool') {
      if (typeof message.tool_call_id !== 'string' || message.tool_call_id.trim() === '') {
        throw new ProxyRequestError(
          400,
          'tool messages must include a non-empty tool_call_id.',
        );
      }

      const toolName =
        typeof message.name === 'string' && message.name.trim() !== ''
          ? message.name
          : toolNamesById.get(message.tool_call_id);

      if (!toolName) {
        throw new ProxyRequestError(
          400,
          `Unable to resolve tool name for tool_call_id "${message.tool_call_id}".`,
        );
      }

      contents.push({
        role: 'user',
        parts: [
          {
            functionResponse: {
              id: message.tool_call_id,
              name: toolName,
              response: normalizeToolResponseContent(message.content),
            },
          },
        ],
      });
      continue;
    }

    if (message.role === 'function') {
      if (typeof message.name !== 'string' || message.name.trim() === '') {
        throw new ProxyRequestError(400, 'function messages must include a name.');
      }

      contents.push({
        role: 'user',
        parts: [
          {
            functionResponse: {
              name: message.name,
              response: normalizeToolResponseContent(message.content),
            },
          },
        ],
      });
      continue;
    }

    throw new ProxyRequestError(400, `Unsupported message role: ${message.role}`);
  }

  if (!contents.length) {
    throw new ProxyRequestError(400, 'No user/assistant/tool messages to forward.');
  }

  return {
    contents,
    systemInstruction: systemParts.length
      ? ({
          role: 'user',
          parts: systemParts,
        } as GeminiContent)
      : undefined,
  };
}

function buildRequestConfig(body: any, systemInstruction?: GeminiContent) {
  const config: Record<string, unknown> = {};

  if (typeof body.temperature === 'number') {
    config.temperature = body.temperature;
  }

  if (typeof body.top_p === 'number') {
    config.topP = body.top_p;
  }

  if (typeof body.max_tokens === 'number') {
    config.maxOutputTokens = body.max_tokens;
  }

  if (isPlainObject(body.generationConfig)) {
    Object.assign(config, body.generationConfig);
  }

  if (body.include_reasoning === true) {
    config.thinkingConfig = {
      includeThoughts: true,
      thinkingBudget:
        typeof body.thinking_budget === 'number' ? body.thinking_budget : 2048,
    };
  }

  if (systemInstruction) {
    config.systemInstruction = systemInstruction;
  }

  return config;
}

function extractParts(response: any): any[] {
  return response?.candidates?.[0]?.content?.parts ?? [];
}

function mapUsage(usage: any) {
  return {
    prompt_tokens: usage?.promptTokenCount ?? 0,
    completion_tokens: usage?.candidatesTokenCount ?? 0,
    total_tokens: usage?.totalTokenCount ?? 0,
  };
}

function mapFinishReason(candidate: any, hasToolCalls: boolean) {
  if (hasToolCalls) {
    return 'tool_calls';
  }

  switch (candidate?.finishReason) {
    case 'MAX_TOKENS':
      return 'length';
    case 'STOP':
    case undefined:
      return 'stop';
    default:
      return 'stop';
  }
}

function buildToolCallPayload(toolCall: any, index: number) {
  const id =
    typeof toolCall?.id === 'string' && toolCall.id.trim() !== ''
      ? toolCall.id
      : `call_${randomUUID()}`;

  return {
    id,
    index,
    type: 'function',
    function: {
      name: String(toolCall?.name ?? ''),
      arguments: JSON.stringify(toolCall?.args ?? {}),
    },
  };
}

export async function mapRequest(body: any) {
  const toolDefinitions = collectToolDefinitions(body);
  const { contents, systemInstruction } = await mapMessages(body.messages);
  const config = buildRequestConfig(body, systemInstruction);

  if (toolDefinitions.length) {
    config.tools = [
      {
        functionDeclarations: toolDefinitions.map((tool) => ({
          name: tool.name,
          description: tool.description,
          parametersJsonSchema: tool.parameters ?? {
            type: 'object',
            properties: {},
          },
        })),
      },
    ];

    config.toolConfig = buildToolConfig(
      body,
      toolDefinitions.map((tool) => tool.name),
    );
  }

  return {
    preferredModel:
      typeof body.model === 'string' && body.model.trim() !== ''
        ? body.model.trim()
        : undefined,
    geminiReq: {
      contents,
      config,
    },
  };
}

export function mapResponse(gResp: any, model: string) {
  const candidate = gResp?.candidates?.[0];

  if (!candidate) {
    const reason = gResp?.promptFeedback?.blockReason ?? 'No candidates returned.';
    throw new Error(String(reason));
  }

  const parts = extractParts(gResp);
  const contentParts: string[] = [];
  const toolCalls = parts
    .filter((part) => part?.functionCall)
    .map((part, index) => buildToolCallPayload(part.functionCall, index));

  for (const part of parts) {
    if (typeof part?.text === 'string') {
      contentParts.push(part.thought === true ? `<think>${part.text}` : part.text);
    }
  }

  return {
    id: `chatcmpl-${randomUUID()}`,
    object: 'chat.completion',
    created: Math.floor(Date.now() / 1000),
    model,
    choices: [
      {
        index: 0,
        message: {
          role: 'assistant',
          content: contentParts.length ? contentParts.join('') : null,
          ...(toolCalls.length ? { tool_calls: toolCalls } : {}),
        },
        finish_reason: mapFinishReason(candidate, toolCalls.length > 0),
      },
    ],
    usage: mapUsage(gResp?.usageMetadata),
  };
}

function createStreamPayload(model: string, completionId: string, created: number, choice: any) {
  return {
    id: completionId,
    object: 'chat.completion.chunk',
    created,
    model,
    choices: [choice],
  };
}

export function createStreamMapper(model: string) {
  const completionId = `chatcmpl-${randomUUID()}`;
  const created = Math.floor(Date.now() / 1000);
  const toolCalls = new Map<string, OpenAIToolCallState>();
  let nextToolIndex = 0;
  let sentRole = false;
  let sawToolCalls = false;

  const buildDelta = (delta: Record<string, unknown>, finishReason?: string) =>
    createStreamPayload(model, completionId, created, {
      index: 0,
      delta,
      ...(finishReason ? { finish_reason: finishReason } : {}),
    });

  return {
    mapChunk(chunk: any) {
      const payloads: any[] = [];
      const parts = extractParts(chunk);
      let text = '';

      for (const part of parts) {
        if (typeof part?.text === 'string') {
          text += part.thought === true ? `<think>${part.text}` : part.text;
          continue;
        }

        if (!part?.functionCall) {
          continue;
        }

        const incoming = part.functionCall;
        const key =
          typeof incoming.id === 'string' && incoming.id.trim() !== ''
            ? incoming.id
            : String(incoming.name ?? `tool-${nextToolIndex}`);
        const previous = toolCalls.get(key);
        const current: OpenAIToolCallState = previous ?? {
          id:
            typeof incoming.id === 'string' && incoming.id.trim() !== ''
              ? incoming.id
              : `call_${randomUUID()}`,
          index: previous?.index ?? nextToolIndex++,
          name: String(incoming.name ?? ''),
          args: {},
          emitted: false,
        };

        if (isPlainObject(incoming.args)) {
          current.args = mergeObjects(current.args, incoming.args);
        }

        if (typeof incoming.name === 'string' && incoming.name.trim() !== '') {
          current.name = incoming.name;
        }

        toolCalls.set(key, current);

        if (incoming.willContinue === true || current.emitted) {
          continue;
        }

        sawToolCalls = true;
        current.emitted = true;

        const delta: Record<string, unknown> = {
          tool_calls: [
            {
              index: current.index,
              id: current.id,
              type: 'function',
              function: {
                name: current.name,
                arguments: JSON.stringify(current.args),
              },
            },
          ],
        };

        if (!sentRole) {
          delta.role = 'assistant';
          sentRole = true;
        }

        payloads.push(buildDelta(delta));
      }

      if (text) {
        const delta: Record<string, unknown> = { content: text };

        if (!sentRole) {
          delta.role = 'assistant';
          sentRole = true;
        }

        payloads.push(buildDelta(delta));
      }

      return payloads;
    },

    finalize() {
      const payloads: any[] = [];

      for (const toolCall of toolCalls.values()) {
        if (toolCall.emitted) {
          continue;
        }

        sawToolCalls = true;
        toolCall.emitted = true;

        const delta: Record<string, unknown> = {
          tool_calls: [
            {
              index: toolCall.index,
              id: toolCall.id,
              type: 'function',
              function: {
                name: toolCall.name,
                arguments: JSON.stringify(toolCall.args),
              },
            },
          ],
        };

        if (!sentRole) {
          delta.role = 'assistant';
          sentRole = true;
        }

        payloads.push(buildDelta(delta));
      }

      const finalDelta: Record<string, unknown> = {};

      if (!sentRole) {
        finalDelta.role = 'assistant';
      }

      payloads.push(
        buildDelta(finalDelta, sawToolCalls ? 'tool_calls' : 'stop'),
      );

      return payloads;
    },
  };
}
