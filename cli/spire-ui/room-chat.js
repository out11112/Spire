import { newId } from './ids.js';
import { stripVTControlCharacters } from 'node:util';
import { MUTED, RESET } from './palette.js';

const segments = new Intl.Segmenter('zh-CN', { granularity: 'grapheme' });
const chars = text => [...segments.segment(text)].map(part => part.segment);
const clean = text => stripVTControlCharacters(text)
  .replace(/[\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/g, ' ');
const cellWidth = text => {
  if (/\p{Extended_Pictographic}|\p{Regional_Indicator}|\u20e3/u.test(text)) return 2;
  const cp = text.codePointAt(0);
  if (/^[\p{Mark}\u200d\ufe0f]+$/u.test(text)) return 0;
  return cp >= 0x1100 && (cp <= 0x115f || cp >= 0x2e80 && cp <= 0xa4cf
    || cp >= 0xac00 && cp <= 0xd7a3 || cp >= 0xf900 && cp <= 0xfaff
    || cp >= 0xfe10 && cp <= 0xfe6f || cp >= 0xff00 && cp <= 0xff60
    || cp >= 0xffe0 && cp <= 0xffe6 || cp >= 0x20000 && cp <= 0x3ffff) ? 2 : 1;
};
const width = text => chars(stripVTControlCharacters(text)).reduce((n, c) => n + cellWidth(c), 0);
// Preserve SGR while cutting an underlying game row at a terminal cell boundary.
function prefix(text, limit) {
  let out = '', used = 0;
  for (const token of text.match(/\x1b\[[0-9;]*m|[^\x1b]+/g) ?? []) {
    if (token.startsWith('\x1b')) { out += token; continue; }
    for (const c of chars(token)) {
      if (used + cellWidth(c) > limit) return out + '\x1b[0m' + ' '.repeat(limit - used);
      out += c; used += cellWidth(c);
    }
  }
  return out + '\x1b[0m' + ' '.repeat(Math.max(0, limit - used));
}
// Keep game content and styles to the right of the bounded chat region.
function suffix(text, start) {
  let out = '', used = 0;
  for (const token of text.match(/\x1b\[[0-9;]*m|[^\x1b]+/g) ?? []) {
    if (token.startsWith('\x1b')) { out += token; continue; }
    for (const c of chars(token)) {
      const next = used + cellWidth(c);
      if (used >= start) out += c;
      else if (next > start) out += ' '.repeat(next - start);
      used = next;
    }
  }
  return out;
}
const fit = (text, limit) => {
  let out = '', used = 0;
  for (const c of chars(text)) { if (used + cellWidth(c) > limit) break; out += c; used += cellWidth(c); }
  return out + ' '.repeat(Math.max(0, limit - used));
};
function preview(text, limit) {
  const lines = [''];
  for (const c of chars(clean(text))) {
    if (width(lines.at(-1)) + cellWidth(c) > limit) {
      if (lines.length === 2) { lines[1] = fit(lines[1], limit - 1).trimEnd() + '…'; break; }
      lines.push('');
    }
    lines[lines.length - 1] += c;
  }
  return lines;
}

/** Room-only ephemeral UI. It never reads or writes the host's channel chat. */
export function createRoomChat(ctx, current) {
  let messages = [], seen = new Map(), timer, draft = [], cursor = 0, editing = false;
  let sending = false, pending, error = '', generation = 0, stopped = false;
  let bounds, editScope;
  const redraw = () => { if (!stopped && !ctx.signal.aborted) ctx.redraw(); };
  const supported = () => !!current().roomId && current().available;
  const schedule = () => {
    clearTimeout(timer); timer = undefined;
    if (!messages.length) return;
    timer = setTimeout(() => {
      messages = messages.filter(message => message.expires > Date.now());
      schedule(); redraw();
    }, Math.max(0, Math.min(...messages.map(message => message.expires)) - Date.now()));
    timer.unref?.();
  };
  function accept(event) {
    const room = current();
    if (stopped || ctx.signal.aborted || !room.available || event?.type !== 'ROOM_CHAT'
      || event.roomId !== room.roomId || typeof event.id !== 'string' || event.id.length > 64
      || typeof event.userId !== 'string' || typeof event.name !== 'string'
      || typeof event.content !== 'string' || [...event.content].length > 200) return;
    if (event.userId === ctx.user.id && pending?.messageId === event.id) {
      pending = undefined; draft = []; cursor = 0; editing = false; sending = false; error = '';
    }
    const now = Date.now();
    seen = new Map([...seen].filter(([, expires]) => expires > now));
    const key = `${event.userId}:${event.id}`;
    if (seen.has(key)) return;
    seen.set(key, now + 120_000);
    if (seen.size > 256) seen.delete(seen.keys().next().value);
    messages = [...messages.filter(message => message.expires > now), { ...event, expires: now + 60_000 }].slice(-8);
    schedule(); redraw();
  }
  async function send() {
    const room = current(), content = draft.join('').trim();
    if (!content || sending) return;
    if (!room.online || !room.leaseId) { error = '连接中断，恢复后按 Enter 发送'; redraw(); return; }
    if (content === '/sl' && room.sl?.canReset === false) { error = '多人模式只有房主可以使用 /sl'; redraw(); return; }
    if (content === '/sl' && (!room.sl?.available || !editScope || editScope !== room.sl.token)) { error = '场景已变化或无法 SL，请按 Esc 后重新输入'; redraw(); return; }
    const request = pending?.content === content && pending?.leaseId === room.leaseId
      ? pending : { messageId: newId(), leaseId: room.leaseId, content, ...(content === '/sl' ? { scopeToken: editScope } : {}) };
    pending = request; sending = true; error = ''; const epoch = generation; redraw();
    try {
      const event = await ctx.request(`/api/games/spire/rooms/${room.roomId}/chat`, 'POST', request);
      if (epoch !== generation || stopped) return;
      if (event?.id !== request.messageId || event?.userId !== ctx.user.id || event?.roomId !== room.roomId || event?.type !== 'ROOM_CHAT') throw new Error('消息确认无效');
      accept(event);
    } catch (cause) {
      if (epoch !== generation || stopped || pending !== request) return;
      error = cause?.message ?? '发送结果未确认，按 Enter 重试';
      if (cause?.status >= 400 && cause.status < 500) pending = undefined;
    } finally {
      if (epoch === generation && (!pending || pending === request)) sending = false;
      redraw();
    }
  }
  function insert(text) {
    if (!editing || sending) return;
    const available = 200 - [...draft.join('')].length;
    let count = 0; const addition = [];
    for (const c of chars(clean(text))) { count += [...c].length; if (count > available) break; addition.push(c); }
    const before = draft.slice(0, cursor).join('') + addition.join('');
    draft = chars(before + draft.slice(cursor).join('')); cursor = chars(before).length; error = ''; redraw();
  }
  function open() { if (!supported()) return; editing = true; editScope = current().sl?.token; error = ''; redraw(); }
  function key(key) {
    if (!editing) {
      if (!key.ctrl && !key.meta && key.value?.toLowerCase() === 't' && supported()) { open(); return true; }
      return false;
    }
    const name = key.name;
    if (name === 'escape' || key.ctrl && ['c', 'd'].includes(name)) {
      editing = false; if (!sending) { draft = []; cursor = 0; pending = undefined; } error = ''; redraw(); return true;
    }
    if (sending) return true;
    if (['return', 'enter'].includes(name)) { void send(); return true; }
    if (name === 'left') cursor = Math.max(0, cursor - 1);
    else if (name === 'right') cursor = Math.min(draft.length, cursor + 1);
    else if (name === 'home' || key.ctrl && name === 'a') cursor = 0;
    else if (name === 'end' || key.ctrl && name === 'e') cursor = draft.length;
    else if (name === 'backspace') { if (cursor) draft.splice(--cursor, 1); }
    else if (name === 'delete') draft.splice(cursor, 1);
    else if (key.ctrl && name === 'u') { draft = []; cursor = 0; }
    else if (!key.ctrl && !key.meta && key.value && !['tab', 'up', 'down', 'pageup', 'pagedown'].includes(name)) insert(key.value);
    redraw(); return true;
  }
  const inside = (box, event) => box && event.x >= box.x && event.x < box.x + box.w && event.y >= box.y && event.y < box.y + box.h;
  function mouse(event) {
    return editing || !!inside(bounds, event);
  }
  function paint(frame, columns, rows) {
    bounds = undefined;
    if (!supported()) { editing = false; return frame; }
    if (columns < 20 || rows < 6) return frame;
    const result = frame.map(row => ({ ...row }));
    while (result.length < rows) result.push({ text: '' });
    const put = (y, x, text) => {
      result[y] = { ...result[y], text: prefix(result[y]?.text ?? '', x) + '\x1b[0;90m' + MUTED + text + RESET + suffix(result[y]?.text ?? '', x + width(text)) };
    };
    // Reserve the game's bottom four rows; align chat with the right edge.
    const bottom = rows - 5, rightMargin = 0;
    const boxWidth = Math.min(36, columns - rightMargin - 2), inner = boxWidth;
    const body = messages.filter(message => message.expires > Date.now()).flatMap(message => preview(`${clean(message.name)}：${message.content}`, inner));
    let cursorColumn;
    if (editing) {
      if (sending) body.push('发送中…');
      else if (!current().online) body.push('已离线');
      if (error) body.push(...preview(error, inner));
      let start = cursor;
      while (start > 0 && width(draft.slice(start - 1, cursor).join('')) <= inner - 3) start--;
      cursorColumn = 2 + width(draft.slice(start, cursor).join(''));
      body.push('› ' + draft.slice(start, cursor).join('') + '│' + draft.slice(cursor).join(''));
    }
    if (!body.length) return result;
    const lines = body.slice(-Math.min(8, bottom + 1)).map(line => fit(line, inner));
    bounds = { x: columns - rightMargin - boxWidth, y: bottom + 1 - lines.length, w: boxWidth, h: lines.length };
    lines.forEach((line, i) => put(bounds.y + i, bounds.x, line));
    if (editing && !sending) {
      for (const row of result) delete row.cursorColumn;
      result[bottom].cursorColumn = bounds.x + cursorColumn;
    }
    return result;
  }
  function reset() {
    generation++; clearTimeout(timer); timer = undefined; messages = []; seen.clear();
    draft = []; cursor = 0; editing = sending = false; pending = undefined; error = ''; bounds = undefined;
  }
  function stop() { stopped = true; reset(); ctx.signal.removeEventListener('abort', stop); }
  ctx.signal.addEventListener('abort', stop, { once: true });
  return { accept, key, mouse, paint, paste: insert, reset, stop, composing: () => editing };
}
