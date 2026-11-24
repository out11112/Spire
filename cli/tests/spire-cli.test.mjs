import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';

import { SpireStore, normalizeOrigin } from '../dist/config.js';
import { validateSpirePath } from '../dist/host.js';

test('normalizeOrigin allows https and local http, rejects remote http', () => {
  assert.equal(normalizeOrigin('https://spire.linkchat.online/foo'), 'https://spire.linkchat.online');
  assert.equal(normalizeOrigin('http://127.0.0.1:8100'), 'http://127.0.0.1:8100');
  assert.throws(() => normalizeOrigin('http://spire.linkchat.online'), /https/);
});

test('validateSpirePath restricts HTTP and WS paths to /api/games/spire/ and /ws/games/spire/', () => {
  assert.equal(validateSpirePath('/api/games/spire/rooms?limit=10', false), '/api/games/spire/rooms?limit=10');
  assert.equal(validateSpirePath('/ws/games/spire/rooms/abc?roomChat=1', true), '/ws/games/spire/rooms/abc?roomChat=1');
  assert.throws(() => validateSpirePath('/api/users/me', false));
  assert.throws(() => validateSpirePath('https://evil.example/api/games/spire/rooms', false));
});

test('SpireStore saves login and falls back to existing linkchat-cli session', async () => {
  const dir = await mkdtemp(path.join(tmpdir(), 'spire-cli-test-'));
  try {
    const spireDir = path.join(dir, 'spire-cli');
    const linkchatDir = path.join(dir, 'linkchat-cli');
    await mkdir(linkchatDir, { recursive: true });
    await writeFile(
      path.join(linkchatDir, 'auth.json'),
      JSON.stringify({
        'https://linkchat.online': {
          token: 'a'.repeat(32),
          user: { id: '01a167fa-80e1-7633-a178-be5947f60802', username: 'alice@example.com', nickname: 'Alice' },
        },
      }),
    );

    const store = new SpireStore(spireDir, linkchatDir);
    const reused = await store.loadLogin('https://linkchat.online');
    assert.equal(reused?.user.nickname, 'Alice');

    await store.saveLogin('https://linkchat.online', {
      token: 'b'.repeat(32),
      user: { id: '01a167fa-80e1-7633-a178-be5947f60802', username: 'alice@example.com', nickname: 'Alice2' },
    });
    const own = await store.loadLogin('https://linkchat.online');
    assert.equal(own?.token, 'b'.repeat(32));
    assert.equal(own?.user.nickname, 'Alice2');
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});
