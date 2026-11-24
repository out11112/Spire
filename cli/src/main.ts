#!/usr/bin/env node
import { DEFAULT_AUTH_URL, DEFAULT_SPIRE_URL, SpireStore, normalizeOrigin } from './config.js';
import { interactiveAuth, logoutSession, verifySession } from './auth.js';
import { runStandaloneSpire } from './host.js';

function printHelp() {
  process.stdout.write(`Spire CLI — 独立合作爬塔卡牌终端客户端（账号与 LinkChat 互通）

用法:
  spire                          启动 Spire（未登录时自动引导登录/注册）
  spire login                    登录或注册 LinkChat 账号
  spire logout                   退出当前登录
  spire --help                   显示帮助

选项:
  --server <url>                 Spire 服务地址（默认 ${DEFAULT_SPIRE_URL}，或环境变量 SPIRE_URL）
  --auth <url>                   LinkChat 账号服务地址（默认 ${DEFAULT_AUTH_URL}，或环境变量 LINKCHAT_AUTH_URL）
`);
}

function parseArgs(argv: string[]) {
  let command: 'run' | 'login' | 'logout' | 'help' = 'run';
  let serverRaw = process.env.SPIRE_URL || DEFAULT_SPIRE_URL;
  let authRaw = process.env.LINKCHAT_AUTH_URL || DEFAULT_AUTH_URL;

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]!;
    if (arg === '-h' || arg === '--help') {
      command = 'help';
    } else if (arg === 'login' || arg === 'logout') {
      command = arg;
    } else if (arg === '--server' && argv[i + 1]) {
      serverRaw = argv[++i]!;
    } else if (arg === '--auth' && argv[i + 1]) {
      authRaw = argv[++i]!;
    } else {
      throw new Error(`未知参数：${arg}（运行 spire --help 查看用法）`);
    }
  }
  return {
    command,
    spireOrigin: normalizeOrigin(serverRaw),
    authOrigin: normalizeOrigin(authRaw),
  };
}

async function main() {
  const { command, spireOrigin, authOrigin } = parseArgs(process.argv.slice(2));
  if (command === 'help') {
    printHelp();
    return;
  }

  const store = new SpireStore();

  if (command === 'logout') {
    const saved = await store.loadLogin(authOrigin);
    if (saved) await logoutSession(authOrigin, saved.token);
    await store.clearLogin(authOrigin);
    process.stdout.write('已退出登录。\n');
    return;
  }

  if (command === 'login') {
    const fresh = await interactiveAuth(authOrigin);
    await store.saveLogin(authOrigin, fresh);
    process.stdout.write(`登录成功：${fresh.user.nickname}（${fresh.user.username}）\n`);
    return;
  }

  let auth = await store.loadLogin(authOrigin);
  if (auth) {
    try {
      const verified = await verifySession(authOrigin, auth.token);
      if (verified) {
        auth = { token: auth.token, user: verified };
        await store.saveLogin(authOrigin, auth);
      } else {
        auth = undefined;
      }
    } catch (error) {
      process.stderr.write(`校验登录状态失败：${error instanceof Error ? error.message : String(error)}\n`);
      process.exitCode = 1;
      return;
    }
  }

  if (!auth) {
    auth = await interactiveAuth(authOrigin);
    await store.saveLogin(authOrigin, auth);
  }

  const controller = new AbortController();
  const onSignal = () => controller.abort();
  process.on('SIGINT', onSignal);
  process.on('SIGTERM', onSignal);
  try {
    await runStandaloneSpire({ spireOrigin, auth, signal: controller.signal });
  } finally {
    process.off('SIGINT', onSignal);
    process.off('SIGTERM', onSignal);
  }
}

main().catch(error => {
  process.stderr.write(`错误：${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 1;
});
