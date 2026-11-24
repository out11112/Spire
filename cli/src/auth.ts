import readline from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';
import type { SavedAuth, SavedUser } from './config.js';

function extractSessionCookie(headers: Headers): string | undefined {
  const cookies: string[] = typeof (headers as any).getSetCookie === 'function'
    ? (headers as any).getSetCookie()
    : [headers.get('set-cookie') ?? ''];
  for (const raw of cookies) {
    const match = /(?:^|;\s*)linkchat_session=([^;]+)/.exec(raw);
    if (match?.[1]) return match[1].trim();
  }
  return undefined;
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json() as any;
    return data?.message || data?.detail || data?.error?.message || `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
}

export async function verifySession(authOrigin: string, token: string): Promise<SavedUser | undefined> {
  const response = await fetch(`${authOrigin}/api/users/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401 || response.status === 403) return undefined;
  if (!response.ok) throw new Error(`验证登录失败：${await readErrorMessage(response)}`);
  const user = await response.json() as any;
  return {
    id: String(user.id),
    username: String(user.username ?? user.id),
    nickname: String(user.nickname ?? user.username ?? user.id),
  };
}

export async function loginWithPassword(authOrigin: string, username: string, password: string): Promise<SavedAuth> {
  const response = await fetch(`${authOrigin}/api/users/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) throw new Error(await readErrorMessage(response));
  const token = extractSessionCookie(response.headers);
  if (!token) throw new Error('登录响应未返回会话凭据');
  const user = await response.json() as any;
  return {
    token,
    user: {
      id: String(user.id),
      username: String(user.username ?? username),
      nickname: String(user.nickname ?? user.username ?? username),
    },
  };
}

export async function requestRegisterEmailCode(authOrigin: string, email: string): Promise<void> {
  const response = await fetch(`${authOrigin}/api/users/register/email-code`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  if (!response.ok) throw new Error(await readErrorMessage(response));
}

export async function registerAccount(
  authOrigin: string,
  payload: { email: string; emailCode: string; nickname: string; password: string },
): Promise<SavedAuth> {
  const response = await fetch(`${authOrigin}/api/users/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await readErrorMessage(response));
  const token = extractSessionCookie(response.headers);
  if (!token) throw new Error('注册响应未返回会话凭据');
  const user = await response.json() as any;
  return {
    token,
    user: {
      id: String(user.id),
      username: String(user.username ?? payload.email),
      nickname: String(user.nickname ?? payload.nickname),
    },
  };
}

export async function logoutSession(authOrigin: string, token: string): Promise<void> {
  try {
    await fetch(`${authOrigin}/api/users/logout`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    // Best-effort server logout.
  }
}

async function promptSecret(prompt: string): Promise<string> {
  if (!input.isTTY) {
    const rl = readline.createInterface({ input, output });
    try {
      return (await rl.question(prompt)).trim();
    } finally {
      rl.close();
    }
  }
  output.write(prompt);
  return await new Promise<string>((resolve, reject) => {
    let value = '';
    const wasRaw = input.isRaw;
    input.setRawMode(true);
    input.resume();
    const cleanup = () => {
      input.off('data', onData);
      input.setRawMode(Boolean(wasRaw));
    };
    const onData = (chunk: Buffer) => {
      const str = chunk.toString('utf8');
      for (const ch of str) {
        if (ch === '\r' || ch === '\n') {
          cleanup();
          output.write('\n');
          resolve(value);
          return;
        }
        if (ch === '\x03') {
          cleanup();
          output.write('\n');
          reject(new Error('已取消登录'));
          return;
        }
        if (ch === '\x7f' || ch === '\b') {
          if (value.length > 0) value = value.slice(0, -1);
          continue;
        }
        if (ch >= ' ') value += ch;
      }
    };
    input.on('data', onData);
  });
}

export async function interactiveAuth(authOrigin: string): Promise<SavedAuth> {
  output.write(`\nSpire 账号与 LinkChat 互通（认证地址：${authOrigin}）\n`);
  while (true) {
    const rl = readline.createInterface({ input, output });
    let mode = '';
    try {
      mode = (await rl.question('请选择 [1] 登录已有账号  [2] 注册新账号（默认 1）：')).trim() || '1';
    } finally {
      rl.close();
    }

    if (mode === '2') {
      const rlReg = readline.createInterface({ input, output });
      try {
        const email = (await rlReg.question('邮箱：')).trim();
        await requestRegisterEmailCode(authOrigin, email);
        output.write('验证码已发送到邮箱，请查收。\n');
        const emailCode = (await rlReg.question('邮箱验证码：')).trim();
        const nickname = (await rlReg.question('昵称（1-32 字符）：')).trim();
        rlReg.close();
        const password = await promptSecret('密码（至少 6 位，不含汉字）：');
        return await registerAccount(authOrigin, { email, emailCode, nickname, password });
      } catch (error) {
        rlReg.close();
        output.write(`注册失败：${error instanceof Error ? error.message : String(error)}\n\n`);
      }
      continue;
    }

    const rlLogin = readline.createInterface({ input, output });
    try {
      const username = (await rlLogin.question('用户名或邮箱：')).trim();
      rlLogin.close();
      const password = await promptSecret('密码：');
      return await loginWithPassword(authOrigin, username, password);
    } catch (error) {
      rlLogin.close();
      output.write(`登录失败：${error instanceof Error ? error.message : String(error)}\n\n`);
    }
  }
}
