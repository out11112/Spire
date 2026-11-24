import { pathToFileURL } from 'node:url';
import path from 'node:path';
import WebSocket from 'ws';
import type { ExtensionContext, ExtensionModule } from './extension-api.js';
import type { SavedAuth } from './config.js';
import { StandaloneTerminal } from './terminal.js';

const PROTOCOL_VERSION = 8;
const SUBPROTOCOL = 'linkchat-game-v8';

export function validateSpirePath(route: string, socket: boolean): string {
  const base = socket ? '/ws/games/spire/' : '/api/games/spire/';
  const url = new URL(route, 'https://spire.invalid');
  if (
    url.origin !== 'https://spire.invalid'
    || !url.pathname.startsWith(base)
    || url.hash
    || route.includes('\\')
    || route.split(/[?#]/, 1)[0]!.includes('%')
  ) {
    throw new Error('请求超出 Spire 接口范围');
  }
  return url.pathname + url.search;
}

export async function runStandaloneSpire(options: {
  spireOrigin: string;
  auth: SavedAuth;
  signal: AbortSignal;
}): Promise<void> {
  const { spireOrigin, auth, signal } = options;
  const entry = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', 'spire-ui', 'index.js');
  const mod = (await import(pathToFileURL(entry).href)) as ExtensionModule;
  const terminal = new StandaloneTerminal();
  const controller = new AbortController();
  const lifetime = AbortSignal.any([signal, controller.signal]);
  const sockets = new Set<() => void>();
  const close = () => terminal.closeScreen();
  lifetime.addEventListener('abort', close, { once: true });

  const request = async (route: string, method: 'GET' | 'POST' = 'GET', body?: unknown) => {
    const clean = validateSpirePath(route, false);
    const headers: Record<string, string> = {
      Authorization: `Bearer ${auth.token}`,
    };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const response = await fetch(new URL(clean, spireOrigin), {
      method,
      headers,
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      signal: lifetime,
    });
    const text = await response.text();
    let parsed: any = undefined;
    if (text) {
      try { parsed = JSON.parse(text); } catch { parsed = text; }
    }
    if (!response.ok) {
      const msg = parsed?.error?.message || parsed?.message || parsed?.detail || `HTTP ${response.status}`;
      const err = new Error(msg) as Error & { status?: number; code?: string };
      err.status = response.status;
      err.code = parsed?.error?.code;
      throw err;
    }
    return parsed;
  };

  const context: ExtensionContext = {
    user: { id: auth.user.id, name: auth.user.nickname },
    signal: lifetime,
    supportsControlHandoff: true,
    request,
    openScreen: screen => lifetime.aborted ? Promise.resolve() : terminal.openScreen(screen),
    closeScreen: close,
    wrap: (text, width) => terminal.wrapText(text, width),
    redraw: () => { if (!lifetime.aborted) terminal.refreshScreen(); },
    connect(route, event, status, connectOptions) {
      const url = new URL(validateSpirePath(route, true), spireOrigin);
      url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
      let ws: WebSocket | undefined;
      let retry: NodeJS.Timeout | undefined;
      let heartbeat: NodeJS.Timeout | undefined;
      let firstState: NodeJS.Timeout | undefined;
      let stopped = false;
      let pong = 0;
      let attempt = 0;
      let validSince = 0;
      let retryAfter = 0;

      const start = () => {
        if (stopped || lifetime.aborted) return;
        const socket = new WebSocket(url, [SUBPROTOCOL], {
          headers: { Authorization: `Bearer ${auth.token}` },
          handshakeTimeout: 10_000,
          maxPayload: 4 * 1024 * 1024,
          perMessageDeflate: { clientNoContextTakeover: true, serverNoContextTakeover: true, threshold: 1024 },
        });
        ws = socket;
        const current = () => !stopped && !lifetime.aborted && ws === socket;
        validSince = 0;
        retryAfter = 0;

        socket.on('open', () => {
          if (!current()) return;
          if (socket.protocol !== SUBPROTOCOL) { socket.close(1002); return; }
          pong = Date.now();
          status(true);
          firstState = setTimeout(() => { if (current() && !validSince) socket.terminate(); }, 10_000);
          heartbeat = setInterval(() => {
            if (!current()) return;
            if (validSince && Date.now() - validSince >= 30_000) attempt = 0;
            if (Date.now() - pong > 45_000) socket.terminate();
            else if (socket.readyState === WebSocket.OPEN) socket.send('PING');
          }, 15_000);
        });

        socket.on('message', data => {
          if (!current()) return;
          if (data.toString() === 'PONG') { pong = Date.now(); return; }
          try {
            const value = JSON.parse(data.toString());
            event(value);
            if (!validSince && (value?.protocol === PROTOCOL_VERSION || value?.state?.protocol === PROTOCOL_VERSION)) {
              validSince = Date.now();
              clearTimeout(firstState);
            }
          } catch (error) {
            stopped = true;
            socket.close(1002);
            terminal.closeScreen(error instanceof Error ? error : new Error('游戏状态与客户端版本不兼容'));
          }
        });

        socket.on('error', (error: Error & { code?: string }) => {
          if (current() && error.code === 'WS_ERR_UNSUPPORTED_MESSAGE_LENGTH') {
            stopped = true;
            terminal.closeScreen(new Error('游戏消息超过 4 MiB'));
          }
        });

        socket.on('unexpected-response', (_, response) => {
          if (!current()) { response.resume(); return; }
          const code = response.statusCode ?? 0;
          if (code >= 400 && code < 500 && ![408, 429].includes(code)) {
            stopped = true;
            terminal.closeScreen(new Error(`连接被服务器拒绝（HTTP ${code}），请重新登录或检查版本`));
          }
          if (code === 429) {
            const raw = response.headers['retry-after'];
            if (typeof raw === 'string') {
              const delay = /^\d+$/.test(raw) ? Number(raw) * 1000 : Date.parse(raw) - Date.now();
              if (Number.isFinite(delay) && delay >= 0) retryAfter = Math.min(delay, 2_147_483_647);
            }
          }
          response.resume();
          socket.terminate();
        });

        socket.on('close', code => {
          if (!current()) return;
          clearInterval(heartbeat);
          clearTimeout(firstState);
          status(false);
          if (code === 4001 && connectOptions?.onReplaced?.()) { stopped = true; return; }
          if ([1008, 1009, 4001].includes(code)) {
            stopped = true;
            terminal.closeScreen(new Error(
              code === 1009 ? '游戏消息超过 4 MiB'
                : code === 4001 ? '游戏已在另一个终端打开'
                : '登录已失效，请重新运行 spire login',
            ));
            return;
          }
          const delay = Math.max(retryAfter, Math.min(1000 * 2 ** Math.min(attempt++, 4), 15_000) * (0.8 + Math.random() * 0.2));
          retry = setTimeout(start, delay);
        });
      };

      const stop = () => {
        stopped = true;
        clearTimeout(retry);
        clearInterval(heartbeat);
        clearTimeout(firstState);
        ws?.close();
        sockets.delete(stop);
      };
      sockets.add(stop);
      start();

      return {
        close: stop,
        reconnect() {
          if (stopped || lifetime.aborted) return;
          const previous = ws;
          ws = undefined;
          clearTimeout(retry);
          clearInterval(heartbeat);
          clearTimeout(firstState);
          previous?.terminate();
          status(false);
          start();
        },
        send(value: unknown) {
          if (stopped || lifetime.aborted || ws?.readyState !== WebSocket.OPEN || ws.bufferedAmount > 64 * 1024) return false;
          const encoded = JSON.stringify(value);
          if (Buffer.byteLength(encoded) > 16 * 1024) return false;
          try { ws.send(encoded); return true; } catch { return false; }
        },
      };
    },
  };

  try {
    if (!lifetime.aborted) await mod.run(context);
  } finally {
    controller.abort();
    for (const stop of sockets) stop();
    lifetime.removeEventListener('abort', close);
    terminal.closeScreen();
  }
}
