import { chmod, mkdir, readFile, rename, rm, writeFile } from 'node:fs/promises';
import { homedir } from 'node:os';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

export const DEFAULT_SPIRE_URL = 'https://spire.linkchat.online';
export const DEFAULT_AUTH_URL = 'https://linkchat.online';

export interface SavedUser {
  id: string;
  username: string;
  nickname: string;
}

export interface SavedAuth {
  token: string;
  user: SavedUser;
}

export function normalizeOrigin(raw: string): string {
  const url = new URL(raw);
  if (url.protocol !== 'https:' && url.protocol !== 'http:') {
    throw new Error('服务地址必须使用 http 或 https');
  }
  if (url.protocol === 'http:' && !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)) {
    throw new Error('跨主机连接必须使用 https');
  }
  return url.origin;
}

export function spireConfigDir(platform = process.platform, home = homedir(), env = process.env): string {
  const { join } = platform === 'win32' ? path.win32 : path.posix;
  if (platform === 'darwin') return join(home, 'Library', 'Application Support', 'spire-cli');
  if (platform === 'win32') return join(env.LOCALAPPDATA || join(home, 'AppData', 'Local'), 'spire-cli');
  return join(env.XDG_CONFIG_HOME || join(home, '.config'), 'spire-cli');
}

export function linkchatConfigDir(platform = process.platform, home = homedir(), env = process.env): string {
  const { join } = platform === 'win32' ? path.win32 : path.posix;
  if (platform === 'darwin') return join(home, 'Library', 'Application Support', 'linkchat-cli');
  if (platform === 'win32') return join(env.LOCALAPPDATA || join(home, 'AppData', 'Local'), 'linkchat-cli');
  return join(env.XDG_CONFIG_HOME || join(home, '.config'), 'linkchat-cli');
}

async function readJsonFile(file: string): Promise<Record<string, any>> {
  try {
    const raw = await readFile(file, 'utf8');
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function parseSavedAuth(entry: any): SavedAuth | undefined {
  if (!entry || typeof entry !== 'object') return undefined;
  const token = entry.token;
  const user = entry.user;
  if (typeof token !== 'string' || !/^[A-Za-z0-9_-]{20,256}$/.test(token)) return undefined;
  if (!user || typeof user.id !== 'string' || typeof user.nickname !== 'string') return undefined;
  return {
    token,
    user: {
      id: user.id,
      username: typeof user.username === 'string' ? user.username : user.id,
      nickname: user.nickname,
    },
  };
}

export class SpireStore {
  constructor(
    readonly dir = spireConfigDir(),
    readonly linkchatDir = linkchatConfigDir(),
  ) {}

  private authFile() {
    return path.join(this.dir, 'auth.json');
  }

  async loadLogin(authOrigin: string): Promise<SavedAuth | undefined> {
    const own = await readJsonFile(this.authFile());
    const found = parseSavedAuth(own[authOrigin]);
    if (found) return found;
    // Reuse an existing linkchat-cli session on the same machine if present.
    const linkchat = await readJsonFile(path.join(this.linkchatDir, 'auth.json'));
    return parseSavedAuth(linkchat[authOrigin]);
  }

  async saveLogin(authOrigin: string, auth: SavedAuth): Promise<void> {
    await mkdir(this.dir, { recursive: true, mode: 0o700 });
    const data = await readJsonFile(this.authFile());
    data[authOrigin] = auth;
    const temp = path.join(this.dir, '.auth.' + randomUUID());
    try {
      await writeFile(temp, JSON.stringify(data, null, 2) + '\n', { mode: 0o600 });
      await rename(temp, this.authFile());
      if (process.platform !== 'win32') await chmod(this.authFile(), 0o600);
    } finally {
      await rm(temp, { force: true });
    }
  }

  async clearLogin(authOrigin: string): Promise<void> {
    const data = await readJsonFile(this.authFile());
    if (!(authOrigin in data)) return;
    delete data[authOrigin];
    await mkdir(this.dir, { recursive: true, mode: 0o700 });
    const temp = path.join(this.dir, '.auth.' + randomUUID());
    try {
      await writeFile(temp, JSON.stringify(data, null, 2) + '\n', { mode: 0o600 });
      await rename(temp, this.authFile());
      if (process.platform !== 'win32') await chmod(this.authFile(), 0o600);
    } finally {
      await rm(temp, { force: true });
    }
  }
}
