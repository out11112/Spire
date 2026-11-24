import { newId } from './ids.js';
import { panelRule, panelTitle, panelText, optionRow, hintRow } from './panel.js';

/** A retained request body makes a lost response safe to retry. */
export function createDelegationPanel(ctx, { snapshot, room, reconnect, redraw }) {
  let opened = false, busy = false, target = '', allowSl = true, selected = 0, pending, note = '', hits = [];
  const grant = () => snapshot()?.delegation;
  const owner = () => snapshot()?.ownerId === ctx.user.id;
  function entries() {
    if (pending) return [{ id: 'submit', label: '确认 / 重试', danger: true }, { id: 'cancel', label: '取消' }];
    if (!grant()) return owner() ? [
      { id: 'target', label: `指定账号 ID：${target || '留空为公开邀请'}` },
      { id: 'sl', label: `允许回档：${allowSl ? '是' : '否'}` },
      { id: 'open', label: '开放存档托管…' }, { id: 'back', label: '返回' },
    ] : [{ id: 'back', label: '返回' }];
    return [
      ...(grant().canRestoreBefore ? [{ id: 'restore-before', label: '恢复托管前快照…', danger: true }] : []),
      ...(owner() ? [{ id: 'revoke', label: '收回控制，保留当前进度…' }, { id: 'revoke-restore', label: '收回控制，恢复托管前…', danger: true }] : []),
      { id: 'back', label: '返回' },
    ];
  }
  async function submit() {
    if (busy || !pending) return;
    busy = true; note = '处理中…'; redraw();
    try {
      await ctx.request(pending.path, 'POST', pending.body);
      opened = false; pending = undefined; reconnect();
    } catch (error) {
      note = error?.message ?? '结果未确认，请重试同一请求。';
      if (error?.status >= 400 && error.status < 500) {
        pending = undefined;
        note += ' 请返回游戏刷新状态后重新确认。';
      }
    } finally { busy = false; redraw(); }
  }
  function activate(row) {
    if (!row || busy) return;
    if (row.id === 'back') { opened = false; redraw(); return; }
    if (row.id === 'cancel') { pending = undefined; selected = 0; redraw(); return; }
    if (row.id === 'submit') { void submit(); return; }
    if (row.id === 'target') { note = '输入账号 UUIDv7；清空为公开邀请。'; redraw(); return; }
    if (row.id === 'sl') { allowSl = !allowSl; redraw(); return; }
    const state = snapshot(), base = `/api/games/spire/rooms/${room()}/delegation`;
    if (row.id === 'open') {
      const inviteeId = target || null;
      if (target && (!(/^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/).test(inviteeId) || inviteeId === ctx.user.id)) { note = '请输入其他账号的有效 UUIDv7。'; redraw(); return; }
      pending = { path: base, body: { requestId: newId(), revision: state.revision, inviteeId, allowSl },
        message: `${target ? '授权账号 ' + target : '公开邀请：任意存档外账号均可首先接管'}。你将变为旁观者，可随时收回。回档权限：${allowSl ? '允许' : '禁止'}。` };
    } else {
      const restore = row.id !== 'revoke';
      pending = { path: `${base}/${grant().id}/${row.id === 'restore-before' ? row.id : 'revoke'}`,
        body: row.id === 'restore-before' ? { requestId: newId(), revision: state.revision } : { revision: state.revision, restoreBefore: restore },
        message: restore ? '恢复整局到托管前，覆盖托管后的进度；多人模式影响整队。' : '收回控制权并保留当前进度，代玩者将断开连接。' };
    }
    selected = 0; note = ''; redraw();
  }
  function edit(value) { if (!busy && !pending && !grant() && selected === 0) { target = value.toLowerCase().replace(/[^0-9a-f-]/g, '').slice(0, 36); redraw(); } }
  return {
    active: () => opened,
    pending: () => busy || !!pending,
    open() { opened = true; selected = 0; pending = undefined; note = ''; redraw(); },
    render(width, height) {
      const state = snapshot(), g = grant();
      const summary = g ? `${g.status === 'open' ? '等待接管' : '托管中'} · ${state.readOnly ? '你正在旁观' : '你正在代玩'} · 回档${g.allowSl ? '允许' : '禁止'}` : '代玩者操作原角色，存档及奖励仍归原账号。';
      const rows = [panelRule(width), panelTitle('存档托管', '', width, 0), ...panelText(pending?.message ?? summary, width, 3)];
      hits = [];
      entries().forEach((row, i) => { hits.push({ y: rows.length, row, i }); rows.push(optionRow(row, { selected: selected === i, width })); });
      rows.push(...panelText(note, width, 2));
      return [...rows.slice(0, Math.max(0, height - 1)), hintRow([['↑↓', '选择'], ['Enter', '确认'], ['Esc', '返回']], width, 0)];
    },
    key(key) {
      if (busy) return;
      if (key.name === 'escape') { if (pending) pending = undefined; else opened = false; selected = 0; redraw(); return; }
      if (key.ctrl && key.name === 'u') { edit(''); return; }
      if (key.name === 'backspace') { edit(target.slice(0, -1)); return; }
      if (key.name === 'up') selected = Math.max(0, selected - 1);
      else if (key.name === 'down') selected = Math.min(entries().length - 1, selected + 1);
      else if (['return', 'enter'].includes(key.name)) activate(entries()[selected]);
      else if (!key.ctrl && !key.meta && /^[0-9a-f-]+$/i.test(key.value ?? '')) edit(target + key.value);
      redraw();
    },
    paste(text) { edit(target + text); },
    mouse(event) { if (event.action !== 'press' || event.button !== 'left') return; const hit = hits.find(h => h.y === event.y); if (hit) { selected = hit.i; activate(hit.row); } },
  };
}
