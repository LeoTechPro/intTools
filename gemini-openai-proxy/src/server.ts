import http from 'http';
import { getRuntimeStatus, listModels, sendChat, sendChatStream } from './chatwrapper';
import {
  createStreamMapper,
  mapRequest,
  mapResponse,
  ProxyRequestError,
} from './mapper';

const HOST = process.env.HOST ?? '127.0.0.1';
const PORT = Number(process.env.PORT ?? 11434);

function allowCors(res: http.ServerResponse) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
}

function writeJson(
  res: http.ServerResponse,
  statusCode: number,
  payload: Record<string, unknown>,
) {
  res.writeHead(statusCode, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(payload));
}

function readJSON(
  req: http.IncomingMessage,
  res: http.ServerResponse,
): Promise<any | null> {
  return new Promise((resolve) => {
    let data = '';

    req.on('data', (chunk) => {
      data += chunk;
    });

    req.on('end', () => {
      try {
        resolve(data ? JSON.parse(data) : {});
      } catch {
        writeJson(res, 400, {
          error: {
            message: 'Malformed JSON body.',
          },
        });
        resolve(null);
      }
    });
  });
}

function handleProxyError(res: http.ServerResponse, error: unknown) {
  const statusCode =
    error instanceof ProxyRequestError ? error.statusCode : 500;
  const message =
    error instanceof Error ? error.message : 'Unexpected proxy error.';

  writeJson(res, statusCode, {
    error: { message },
  });
}

http
  .createServer(async (req, res) => {
    allowCors(res);

    if (req.method === 'OPTIONS') {
      res.writeHead(204).end();
      return;
    }

    if (req.url === '/healthz' && req.method === 'GET') {
      writeJson(res, 200, {
        status: 'ok',
        host: HOST,
        port: PORT,
        ...getRuntimeStatus(),
      });
      return;
    }

    if (req.url === '/v1/models' && req.method === 'GET') {
      writeJson(res, 200, {
        object: 'list',
        data: listModels(),
      });
      return;
    }

    if (req.url === '/v1/chat/completions' && req.method === 'POST') {
      const body = await readJSON(req, res);

      if (!body) {
        return;
      }

      try {
        const { preferredModel, geminiReq } = await mapRequest(body);

        if (body.stream) {
          const { model, stream } = await sendChatStream({
            preferredModel,
            ...geminiReq,
          });
          const streamMapper = createStreamMapper(model);

          res.writeHead(200, {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            Connection: 'keep-alive',
          });

          for await (const chunk of stream) {
            for (const payload of streamMapper.mapChunk(chunk)) {
              res.write(`data: ${JSON.stringify(payload)}\n\n`);
            }
          }

          for (const payload of streamMapper.finalize()) {
            res.write(`data: ${JSON.stringify(payload)}\n\n`);
          }

          res.end('data: [DONE]\n\n');
          return;
        }

        const { model, response } = await sendChat({
          preferredModel,
          ...geminiReq,
        });
        writeJson(res, 200, mapResponse(response, model));
      } catch (error) {
        console.error('Proxy error:', error);
        handleProxyError(res, error);
      }
      return;
    }

    writeJson(res, 404, {
      error: {
        message: 'Not found.',
      },
    });
  })
  .listen(PORT, HOST, () => {
    const runtime = getRuntimeStatus();

    console.log(
      `OpenAI proxy listening on http://${HOST}:${PORT} (auth=${runtime.authType}, primary=${runtime.primaryModel}, fallbacks=${runtime.fallbackModels.join(' -> ')})`,
    );
  });
