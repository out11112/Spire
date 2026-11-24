import { newId } from './ids.js';

/** Ordered intents only; no game rules or predicted state live here. */
export function createActionQueue({ send, state, note, changed, lease, reconnect = () => {}, timing = () => {} }) {
  const entries = [];
  let uncertain = false, halted = false, recovering = false, timer, sync, generation = 0;
  const completed = new Set();
  const remember = id => { completed.add(id); if (completed.size > 64) completed.delete(completed.values().next().value); };
  const notify = () => { changed(); };
  const arm = () => {
    clearTimeout(timer);
    if (entries.length && !uncertain) {
      const current = generation;
      timer = setTimeout(() => { if (current === generation) reconcile(); }, 10_000);
      timer.unref?.();
    }
  };
  const disconnect = () => {
    clearTimeout(timer);
    sync = undefined; recovering = false;
    if (entries.length) {
      uncertain = true;
      note('队列结果待确认，重连后自动核对；不会自动重打。');
      notify();
    }
  };
  function report(entry, outcome, server) {
    timing({ actionId: entry.body.actionId, totalMs: performance.now() - entry.started,
      serverMs: server?.total, outcome });
  }
  function enqueue(action) {
    if (uncertain || recovering || halted) return false;
    if (entries.length && (!['play', 'potion', 'end'].includes(action.type)
      || entries.some(e => !['play', 'potion'].includes(e.body.action.type)))) {
      note('请等待前序动作确认。'); notify(); return false;
    }
    if (entries.length >= 8) { note('待执行队列已满（最多 8 个动作）。'); notify(); return false; }
    if (entries.some(e => (action.type === 'play' && e.body.action.type === 'play' && e.body.action.card === action.card)
      || (action.type === 'potion' && e.body.action.type === 'potion' && e.body.action.potion === action.potion))) {
      note('该卡牌或药水已在队列中。'); notify(); return false;
    }
    const entry = { body: { actionId: newId(), leaseId: lease(), action: { ...action } }, started: performance.now() };
    const previous = entries.at(-1);
    entries.push(entry);
    if (!send({ type: 'ACTION', ...entry.body, ...(previous ? { afterActionId: previous.body.actionId } : {}) })) {
      entries.pop();
      disconnect();
      note('连接不可用，操作未发送。'); notify();
      if (entries.length) reconcile();
      return false;
    }
    if (entries.length === 1) arm();
    note(''); notify(); return true;
  }
  function accept(event) {
    if (event?.type === 'SYNC_RESULT') {
      if (!sync || event.requestId !== sync.requestId || event.leaseId !== lease()) return true;
      if (!event.state || (event.state.leaseId !== undefined && event.state.leaseId !== event.leaseId) || !Array.isArray(event.results) || event.results.length !== sync.actionIds.length
        || sync.actionIds.some(id => event.results.filter(r => r?.actionId === id && ['committed', 'not_committed'].includes(r.status)).length !== 1)) {
        note('核对协议错误，正在重新连接。'); reconnect(); return true;
      }
      state(event.state);
      for (const entry of entries) { remember(entry.body.actionId); report(entry, 'reconciled'); }
      entries.splice(0); clearTimeout(timer); sync = undefined;
      uncertain = false; recovering = false; halted = false;
      note(event.results.some(r => r.status === 'not_committed') ? '部分动作未提交，已同步最新状态，请重新选择操作。' : '核对完成。');
      notify(); return true;
    }
    if (!['ACTION_RESULT', 'ACTION_ERROR'].includes(event?.type)) return false;
    if (completed.has(event.actionId)) return true;
    if (recovering || uncertain) {
      const pending = entries.find(e => e.body.actionId === event.actionId);
      if (pending) pending.receipt = event;
      else note(event.error?.message || '收到无法关联的动作回执，正在核对。');
      return true;
    }
    const entry = entries[0];
    if (!entry || event.actionId !== entry.body.actionId) {
      note(event.error?.message || '动作协议错误，正在核对。');
      reconcile();
      return true;
    }
    if (event.type === 'ACTION_ERROR' && !(event.error?.status >= 400 && event.error?.status < 500)) {
      reconcile();
      return true;
    }
    if (event.type === 'ACTION_RESULT') state(event.state, entry.body.action);
    entries.shift(); remember(entry.body.actionId);
    if (event.type === 'ACTION_ERROR') {
      if (!halted) note(event.error?.message || '动作失败，后续队列已停止。');
      halted = true;
    } else if (event.stopQueue && entries.length) {
      halted = true;
      note('需要新选择或阶段已变化，后续队列已停止。');
    }
    if (!entries.length) { uncertain = false; halted = false; }
    arm(); notify();
    report(entry, event.type === 'ACTION_RESULT' ? 'ok' : 'rejected', event.timing);
    return true;
  }
  function reconcile() {
    if (recovering) { note('正在核对动作结果，请稍候。'); notify(); return; }
    uncertain = true; recovering = true; clearTimeout(timer);
    sync = { type: 'SYNC', requestId: newId(), leaseId: lease(), actionIds: entries.map(e => e.body.actionId) };
    note('正在核对动作结果；不会自动重打。'); notify();
    if (!send(sync)) { recovering = false; sync = undefined; reconnect(); return; }
    const current = generation;
    timer = setTimeout(() => {
      if (current !== generation) return;
      recovering = false; sync = undefined;
      note('核对超时，正在重新连接后自动核对。'); notify(); reconnect();
    }, 10_000);
    timer.unref?.();
  }
  return { enqueue, accept, disconnect, reconcile,
    ready() { if (uncertain && !recovering) reconcile(); },
    get size() { return entries.length; },
    get blocked() { return uncertain || recovering || halted; },
    get pendingActions() { return entries.map(e => e.body.action); },
    stop() { generation++; clearTimeout(timer); entries.splice(0); completed.clear(); sync = undefined; recovering = false; uncertain = false; halted = false; },
  };
}
