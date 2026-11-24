import { newId } from './ids.js';
import { localCatalog } from './local-catalog.js';
import manifest from './package.json' with { type: 'json' };
import { clean, cut, pad, wrap, textWidth, libraryHeader, renderLibrary, filterCatalog } from './catalog-view.js';
import { TEXT, MUTED } from './palette.js';
import { panelRule, panelTitle, panelText, optionRow, searchRow, toggleRow, hintRow } from './panel.js';

const BASE = '/api/games/spire';
const PHASES = { lobby:'等待开始',map:'路线选择',combat:'战斗',reward:'战利品',rest:'火堆',shop:'商店',event:'事件',treasure:'宝箱',actComplete:'本幕完成',ending:'结局事件' };
// The shortcuts by topic: the key, then what it does.
export const HELP_GROUPS = [
  ['通用', [['方向键', '移动'], ['Enter', '确认'], ['Esc', '返回；游戏中打开菜单，失败后返回主界面'], ['Ctrl+C / Ctrl+D', '返回聊天频道'], ['T', '房间聊天'], ['/sl', '在房间聊天中输入，恢复当前场景初始状态'], ['R', '刷新 / 重试'], ['?', '快捷键与当前项目说明']]],
  ['战斗', [['E', '结束回合 / 取消选择目标'], ['D', '永久牌组'], ['A', '抽牌堆'], ['S', '弃牌堆'], ['X', '消耗牌堆'], ['V', '战斗日志'], ['P', '查看队友'], ['I', '状态、卡牌或商品详情'], ['U', '卡牌升级预览'], ['空格', '勾选多选项']]],
  ['地图与事件', [['M', '展开 / 收起地图'], ['Esc', '先收起地图，再按打开菜单'], ['HJKL', '球体棋盘移动（也可用方向键）'], ['G', '球体棋盘换工具']]],
  ['商店', [['Tab / Shift+Tab', '切换分类'], ['E', '选中离开，再按 Enter 确认']]],
  ['大厅与资料库', [['输入', '多人房间、资料库直接搜索'], ['Ctrl+U', '清空搜索'], ['Ctrl+R', '刷新'], ['←→', '资料库翻页；详情中切换进阶'], ['↑↓', '详情中选择关联条目'], ['PgUp / PgDn', '滚动详情']]],
];
export const HELP_NOTE = '返回主界面会保留存档；多人 SL 由房主或获授权的代玩者触发，事件战斗也恢复到事件节点开头；聊天消息显示 60 秒，最多保留 8 条。';
/** The same shortcuts as plain lines, for the in-game help list. */
export const HELP = [...HELP_GROUPS.flatMap(([, rows]) => rows.map(([key, text]) => `${key}  ${text}`)), '说明：' + HELP_NOTE];

/** The lobby owns navigation; the battle screen remains a separately disposable child. */
export function createLobby(ctx, createGame, catalog = localCatalog) {
  let view = 'main', selected = 0, meta, libraryMeta, rooms = [], note = '', busy = false, stopped = false;
  let game, poll, width = 80, height = 24, hits = [], setup, confirm, confirmIndex = 0, previous = 'main';
  let catalogData, metaRequest, roomsRequest, roomsLoadedAt = 0, delegationSupported;
  let groupOptions = [], catalogTop = 0, catalogLoading = false, navigation = 0;
  let category, query = '', group = '', offset = 0, listing, detail, detailCategory, upgraded = false, level = 0, scroll = 0;
  let listVersion = 0, detailVersion = 0, detailBack = [], createRequest, passwordPrompt;
  const redraw = () => { if (!stopped && !ctx.signal.aborted) ctx.redraw(); };
  const fetch = (path, params = {}) => ctx.request(`${BASE}/${path}${Object.keys(params).length ? '?' + new URLSearchParams(params) : ''}`);
  function move(next) { view = next; selected = 0; scroll = 0; catalogTop = 0; confirm = undefined; note = ''; redraw(); }
  async function guard(work) {
    if (busy || stopped) return;
    busy = true; redraw();
    try { await work(); } catch (error) { if (!stopped) note = error?.message ?? '请求失败，按 R 重试'; }
    finally { busy = false; redraw(); }
  }
  function loadMeta() {
    if (meta) return Promise.resolve(meta);
    return metaRequest ??= fetch('catalog').then(result => {
      if (!stopped) meta = result;
      return result;
    }).catch(error => {
      if (error?.status === 404) throw new Error('服务器需要更新 Spire 后端才能使用新大厅。');
      throw error;
    }).finally(() => { metaRequest = undefined; });
  }
  function loadRooms(cached = false) {
    if (cached && roomsLoadedAt && Date.now() - roomsLoadedAt < 5000) return Promise.resolve();
    return roomsRequest ??= fetch('rooms').then(result => {
      if (stopped) return;
      if (result.protocol !== 8 || !Array.isArray(result.rooms)) throw new Error('服务器与游戏版本不兼容');
      const id = entries()[selected]?.id;
      delegationSupported = result.features?.delegation === true; rooms = result.rooms; roomsLoadedAt = Date.now();
      const index = entries().findIndex(row => row.id === id);
      if (index >= 0) selected = index;
      else selected = Math.min(selected, Math.max(0, entries().length - 1));
      redraw();
    }).finally(() => { roomsRequest = undefined; });
  }
  function prefetch() {
    // Background failures are retried by the next explicit entry; never block the menu.
    void Promise.allSettled([loadMeta(), loadRooms()]);
  }
  async function home() {
    game?.stop(); game = undefined; createRequest = undefined; roomsLoadedAt = 0; move('main'); prefetch();
  }
  function play(id) {
    if (stopped) return;
    game?.stop();
    game = createGame(ctx, { onHome: home, configured: true, animate: true });
    game.open(id); redraw();
  }
  async function configure(mode) {
    await Promise.all([loadMeta(), loadRooms(true)]);
    if (stopped) return;
    setup = { mode, character: 0, ascension: 0, passwordEnabled: false, password: '' };
    createRequest = undefined; move('setup');
  }
  const savedSolo = () => rooms.find(room => room.mode === 'solo' && room.ownerId === ctx.user.id);
  // As in the original lobby, a joining player starts as the Ironclad and
  // picks a character inside the room before readying up.
  async function join(room, password) {
    const result = await ctx.request(`${BASE}/rooms/${room.id}/join`, 'POST', ...(password === undefined ? [] : [{ password }]));
    passwordPrompt = undefined; view = 'rooms';
    play(result.id);
  }
  async function startGame(replace) {
    if (setup.mode === 'coop' && setup.passwordEnabled && !setup.password) throw new Error('请先设置房间密码');
    const body = { ...(setup.mode === 'coop' && setup.passwordEnabled ? { password: setup.password } : {}), mode: setup.mode, ascension: setup.ascension, character: meta.characters[setup.character].id,
      ...(replace ? { replaceRoomId: replace.id, replaceRevision: replace.revision } : {}) };
    const signature = JSON.stringify(body);
    if (createRequest?.signature !== signature) createRequest = { signature, requestId: newId() };
    const result = await ctx.request(`${BASE}/rooms`, 'POST', { ...body, requestId: createRequest.requestId });
    setup.password = ''; createRequest = undefined;
    play(result.id);
  }
  async function resume(room) {
    if (!room.compatible) throw new Error('存档版本不兼容，请使用对应版本处理存档');
    // Existing members are authenticated again by the game socket.
    play(room.id);
  }
  function promptPassword(room) {
    passwordPrompt = { room, selected, value: '' };
    move('password');
  }
  function editPassword(value) {
    // Room passwords are exactly six ASCII digits; other input is ignored.
    passwordPrompt.value = clean(value).replace(/[^0-9]/g, '').slice(0, 6);
    note = ''; redraw();
  }
  function cancelPassword() {
    const prompt = passwordPrompt; passwordPrompt = undefined;
    move(prompt.room ? 'rooms' : 'setup'); selected = prompt.selected; redraw();
  }
  async function submitPassword() {
    if (passwordPrompt.value.length !== 6) throw new Error('请输入 6 位数字密码');
    if (passwordPrompt.room) await join(passwordPrompt.room, passwordPrompt.value);
    else { setup.password = passwordPrompt.value; cancelPassword(); }
  }
  const categoryName = () => libraryMeta?.categories.find(row => row.id === category)?.name ?? '资料库';
  function orderedGroups(groups) {
    const preferred = category === 'monsters' ? ['普通', '精英', '首领', '特殊'] : [...(libraryMeta?.characters ?? []).map(row => row.name), '通用', '无色', '状态', '诅咒', '特殊'];
    return [...new Set((groups ?? []).filter(value => value && value !== '全部'))].sort((a, b) => {
      const rank = value => preferred.includes(value) ? preferred.indexOf(value) : preferred.length;
      return rank(a) - rank(b) || a.localeCompare(b, 'zh-CN');
    });
  }
  const groupTabs = () => groupOptions.map(value => ({ id: value, name: value }));
  async function switchCategory(id) {
    if (stopped || !libraryMeta?.categories.some(row => row.id === id)) return;
    const request = ++navigation;
    listVersion++; detailVersion++; category = id; group = query = ''; offset = 0;
    catalogData = listing = detail = undefined; groupOptions = []; detailBack = []; upgraded = false; level = 0;
    move('catalog'); catalogLoading = true; redraw();
    try { await loadList(); }
    catch (error) { if (request === navigation && !stopped) note = error?.message ?? '加载失败，按 Ctrl+R 重试'; }
    finally { if (request === navigation) { catalogLoading = false; redraw(); } }
  }
  async function switchGroup(value) {
    if (stopped || !groupTabs().some(row => row.id === value)) return;
    const request = ++navigation;
    listVersion++; detailVersion++; group = value; offset = 0;
    // The old list and detail stay up until the new ones arrive, so switching
    // never blanks the panes for a moment.
    catalogData = undefined; detailBack = []; upgraded = false; level = 0;
    view = 'catalog'; selected = scroll = catalogTop = 0; confirm = undefined; note = '';
    catalogLoading = true;
    try { await loadList(); }
    catch (error) { if (request === navigation && !stopped) note = error?.message ?? '加载失败，按 Ctrl+R 重试'; }
    finally { if (request === navigation) { catalogLoading = false; redraw(); } }
  }
  function nextGroup(delta) {
    const tabs = groupTabs(), index = Math.max(0, tabs.findIndex(row => row.id === group));
    if (tabs.length > 1) void switchGroup(tabs[(index + delta + tabs.length) % tabs.length].id);
  }
  function applyCatalogFilter() {
    if (!catalogData) return;
    const items = filterCatalog(catalogData.items, query);
    offset = Math.min(offset, Math.max(0, Math.ceil(items.length / 40) - 1) * 40);
    listing = { ...catalogData, items: items.slice(offset, offset + 40), total: items.length };
    selected = Math.min(selected, Math.max(0, listing.items.length - 1));
  }
  async function loadList() {
    const version = ++listVersion, savedCategory = category, savedGroup = group;
    const current = () => !stopped && version === listVersion && savedCategory === category && savedGroup === group && view === 'catalog';
    if (!catalogData) {
      const data = await catalog.list(savedCategory, savedGroup);
      if (!current()) return;
      groupOptions = orderedGroups(data.groups);
      if (!savedGroup && groupOptions.length) {
        group = groupOptions[0];
        catalogData = { ...data, items: data.items.filter(item => item.group === group) };
      } else catalogData = data;
    }
    applyCatalogFilter();
    // The new list shows together with its first detail, not one frame before it.
    if (!listing.items.length) { detail = undefined; redraw(); }
    await preview();
  }
  function editCatalogQuery(value) {
    query = value.slice(0, 200); offset = selected = catalogTop = 0; detailVersion++; detail = undefined;
    applyCatalogFilter(); redraw();
    if (!catalogLoading) void preview().catch(error => { note = error.message; redraw(); });
  }
  async function getDetail(kind, id) {
    return catalog.detail(kind, id, { ascension: level, upgraded });
  }
  async function preview() {
    const row = listing?.items[selected], version = ++detailVersion;
    if (!row) { detail = undefined; return; }
    // The previous entry stays up until this one arrives, so the pane never
    // blanks for a moment between two entries.
    const data = await getDetail(category, row.id);
    if (stopped || version !== detailVersion || view !== 'catalog') return;
    detail = data; detailCategory = category; redraw();
  }
  async function refreshDetail() {
    const version = ++detailVersion, data = await getDetail(detailCategory, detail.id);
    if (version === detailVersion && !stopped && view === 'detail') { detail = data; redraw(); }
  }
  function entries() {
    if (view === 'main') return [
      { id: 'solo', label: '单人模式', hint: '选择角色与进阶，独自攀登尖塔' },
      { id: 'coop', label: '多人联机', hint: '全站房间，与任何人一起攀登' },
      { id: 'library', label: '资料库', hint: '卡牌、怪物、遗物、药水与角色' },
      { id: 'settings', label: '设置', hint: '查看快捷键' },
      { id: 'delegations', label: '托管存档', hint: delegationSupported === undefined ? '正在检查服务器支持，可选择后等待加载' : delegationSupported ? '接管邀请、继续代玩或管理自己的托管' : '服务器尚不支持，请更新后端' },
      { id: 'exit', label: '退出', hint: '返回聊天' },
    ];
    if (view === 'delegations') return rooms.filter(room => room.delegation).map(room => ({ id: room.id, room, label: `${room.canClaimDelegation ? '接管' : room.ownerId === ctx.user.id ? '旁观 / 收回' : '继续代玩'} · ${room.ownerName ?? '房主'} · ${room.mode === 'solo' ? '单人' : '多人'} · ${room.floor} 层 · ${room.delegation.allowSl ? '允许回档' : '禁止回档'}` }));
    if (view === 'rooms') return [{ id: 'create', label: '创建多人房间' }, ...rooms.filter(room => room.mode === 'coop' && (!query || `${room.id} ${room.players.map(p => p.name).join(' ')}`.toLowerCase().includes(query.toLowerCase()))).map(room => ({
      id: room.id, room, label: roomLabel(room),
    }))];
    if (view === 'setup') {
      const saved = setup.mode === 'solo' ? savedSolo() : undefined;
      return [...(saved ? [{ id: 'resume', label: `继续存档 · A${saved.ascension} · ${saved.floor} 层`, room: saved }, { id: 'abandon', label: '放弃当前存档', room: saved, danger: true }] : []),
        { id: 'character', toggle: '角色', value: meta.characters[setup.character].name },
        { id: 'ascension', toggle: '进阶', value: `A${setup.ascension} · ${meta.ascensions[setup.ascension].name}` },
        ...(setup.mode === 'coop' ? [{ id: 'passwordEnabled', toggle: '密码', value: setup.passwordEnabled ? '开启' : '关闭' },
          ...(setup.passwordEnabled ? [{ id: 'password', label: setup.password ? '修改密码 · 已设置' : '设置房间密码' }] : [])] : []),
        { id: 'start', label: setup.mode === 'coop' ? '创建房间 · 等待队友' : saved ? '开始新旅程…' : '开始旅程' }];
    }
    if (view === 'categories') return libraryMeta.categories.map(row => ({ id: row.id, label: row.name, hint: `${row.count} 项` }));
    if (view === 'catalog') return listing?.items.map(row => ({ ...row, label: `${row.name} · ${row.group}` })) ?? [];
    return [];
  }
  async function activate(row) {
    if (!row) return;
    if (view === 'main') {
      if (row.id === 'exit') ctx.closeScreen();
      else if (row.id === 'solo') await configure('solo');
      else if (row.id === 'delegations') {
        await loadRooms(true);
        if (!delegationSupported) throw new Error('服务器尚不支持存档托管，请更新 Spire 后端。');
        move('delegations');
      }
      else if (row.id === 'coop') { query = ''; move('rooms'); await loadRooms(); }
      else if (row.id === 'library') { libraryMeta = await catalog.metadata(); move('categories'); }
      else if (row.id === 'settings') { previous = 'main'; move('settings'); }
    } else if (view === 'delegations') {
      if (!row.room.compatible) throw new Error('存档版本不兼容');
      if (row.room.canClaimDelegation) { confirm = { ...row.room, claim: true }; confirmIndex = 0; redraw(); }
      else await resume(row.room);
    } else if (view === 'rooms') {
      if (row.id === 'back') move('main');
      else if (row.id === 'create') await configure('coop');
      else if (!row.room.compatible) throw new Error('房间存档版本不兼容');
      else if (row.room.canClaimDelegation) { confirm = { ...row.room, claim: true }; confirmIndex = 0; redraw(); }
      else if (row.room.delegation?.delegateId === ctx.user.id) await resume(row.room);
      else if (row.room.ownerId === ctx.user.id || row.room.players.some(p => p.id === ctx.user.id)) await resume(row.room);
      else if (row.room.phase !== 'lobby' || row.room.players.length >= 4) throw new Error('房间已开始或已满，只能由原成员继续');
      else if (row.room.hasPassword) promptPassword(row.room);
      else await join(row.room);
    } else if (view === 'setup') {
      if (row.id === 'back') move(setup.mode === 'solo' ? 'main' : 'rooms');
      else if (row.id === 'resume') await resume(row.room);
      else if (row.id === 'abandon') { confirm = { ...row.room, abandon: true }; confirmIndex = 0; redraw(); }
      else if (row.id === 'passwordEnabled') { setup.passwordEnabled = !setup.passwordEnabled; if (!setup.passwordEnabled) setup.password = ''; redraw(); }
      else if (row.id === 'password') promptPassword();
      else if (row.id === 'start') {
        const saved = setup.mode === 'solo' ? savedSolo() : undefined;
        if (saved) { confirm = saved; confirmIndex = 0; redraw(); }
        else await startGame();
      } else if (row.id === 'character') { setup.character = (setup.character + 1) % meta.characters.length; redraw(); }
    } else if (view === 'categories') {
      await switchCategory(row.id);
    } else if (view === 'catalog') {
      const data = await getDetail(category, row.id); detailBack = []; move('detail'); detail = data; detailCategory = category;
    }
  }
  async function confirmAction() {
    if (confirm.claim) {
      await ctx.request(`${BASE}/rooms/${confirm.id}/delegation/${confirm.delegation.id}/claim`, 'POST', {});
      const id = confirm.id; confirm = undefined; play(id); return;
    }
    if (!confirm.abandon) return startGame(confirm);
    await ctx.request(`${BASE}/rooms/${confirm.id}/abandon`, 'POST', { revision: confirm.revision });
    rooms = rooms.filter(room => room.id !== confirm.id); confirm = undefined; selected = 0;
    await loadRooms();
  }
  function back() {
    if (view === 'password') { cancelPassword(); return; }
    if (confirm) { confirm = undefined; redraw(); return; }
    if (view === 'detail' && detailBack.length) { ({ detail, detailCategory, level, upgraded, scroll, selected } = detailBack.pop()); redraw(); return; }
    if (view === 'detail') { move('catalog'); selected = Math.max(0, listing?.items.findIndex(row => row.id === detail?.id) ?? 0); void guard(preview); }
    else if (view === 'catalog') { move('categories'); selected = Math.max(0, libraryMeta.categories.findIndex(row => row.id === category)); }
    else if (view === 'setup') move(setup.mode === 'solo' ? 'main' : 'rooms');
    else if (view === 'settings') move(previous);
    else if (view === 'main') ctx.closeScreen();
    else move('main');
  }
  // Every lobby page is one panel: rule, title, body, then a note and the keys at the bottom.
  const titles = () => ({ main: '主菜单', rooms: '多人联机', delegations: '托管存档', setup: setup?.mode === 'solo' ? '单人模式' : '多人联机 · 创建房间', categories: '资料库', settings: '设置 · 快捷键' });
  function hints() {
    if (view === 'password') return [['Enter', passwordPrompt.room ? '加入' : '保存'], ['Esc', '取消'], ['Ctrl+U', '清空']];
    if (confirm) return [['Enter', '确认'], ['Esc', '取消'], ['1-2', '选择']];
    if (view === 'main') return [['Enter', '确认'], ['Esc', '返回聊天'], ['↑↓', '选择']];
    if (view === 'delegations') return [['Enter', '接管 / 进入'], ['R', '刷新'], ['Esc', '返回']];
    if (view === 'rooms') return [['Enter', '进入'], ['输入', '搜索'], ['Ctrl+R', '刷新'], ['Esc', '返回']];
    if (view === 'setup') return [['Enter', '确认'], ['←→', '切换'], ['Esc', '返回']];
    if (view === 'categories') return [['Enter', '进入'], ['Esc', '返回'], ['↑↓', '选择']];
    if (view === 'settings') return [['↑↓', '滚动'], ['Esc', '返回']];
    if (view === 'detail') return [['Esc', '返回'], ...(detail?.links?.length ? [['Enter', '查看关联'], ['↑↓', '选择']] : [['↑↓', '滚动']]),
      ...(detailCategory === 'cards' ? [['U', upgraded ? '查看原版' : '查看升级']] : []), ...(detailCategory === 'monsters' ? [['←→', '进阶']] : []), ['Tab', '分类']];
    return [['Esc', '返回']];
  }
  const roomColumns = () => width < 60 ? [4, 8, 4] : [6, 16, 6];
  function roomLabel(room) {
    const owner = room.ownerName ?? room.players.find(p => p.id === room.ownerId)?.name ?? '未知房主';
    const [a, o, n] = roomColumns();
    const progress = width < 60 ? `${room.act ?? 1}幕${room.floor}层 ${PHASES[room.phase] ?? room.phase}` : `第 ${room.act ?? 1} 幕 · ${room.floor} 层 · ${PHASES[room.phase] ?? room.phase}`;
    return `${room.hasPassword ? '[加密] ' : ''}${pad(`A${room.ascension}`, a)}${pad(owner + (room.ownerId === ctx.user.id ? '（我）' : ''), o)}${pad(`${room.players.length}/4`, n)}${progress}${room.paused ? ' · 暂停' : ''}`;
  }
  function settingsRows() {
    const keyWidth = Math.max(...HELP_GROUPS.flatMap(([, rows]) => rows.map(([key]) => textWidth(key)))) + 2;
    return HELP_GROUPS.flatMap(([name, rows], i) => [...(i ? [{ text: '' }] : []), { text: name, tone: 'title' },
      ...rows.flatMap(([key, text]) => wrap(text, Math.max(1, width - keyWidth - 2)).map((line, j) =>
        ({ text: '  ' + (j ? ' '.repeat(keyWidth) : TEXT + '\x1b[1m' + pad(key, keyWidth) + '\x1b[22m' + MUTED) + line, tone: 'muted' })))])
      .concat([{ text: '' }], panelText(HELP_NOTE, width, 4));
  }
  const screen = {
    header() {
      if (game) return game.screen.header?.();
      return { title: 'Spire', version: manifest.version, subtitle: '单人 · 多人 · 资料库' };
    },
    render(columns, rows) {
      width = columns; height = rows;
      if (game) return game.screen.render(columns, rows);
      hits = [];
      const frame = [], push = (...parts) => { for (const part of parts.flat()) frame.push(part); };
      if (width < 40 || height < 12) return [{ text: cut('请扩大终端至至少 40 列、12 行', width), tone: 'title' }, { text: 'Ctrl+C / Ctrl+D 返回聊天', tone: 'muted' }];
      if (view === 'password') {
        const masked = '*'.repeat([...passwordPrompt.value].length);
        push(panelRule(width), panelTitle(passwordPrompt.room ? '输入房间密码' : '设置房间密码', '', width, 0), { text: '' },
          ...panelText(passwordPrompt.room ? '该房间已加密，输入 6 位数字密码后加入。' : '6 位数字，加入房间的玩家需要输入此密码。', width, 2),
          { text: cut('密码：' + masked, width), cursorColumn: Math.min(width - 1, 6 + masked.length) });
        if (note) push(...panelText(note, width, 2, 'error'));
        while (frame.length < height - 1) push({ text: '' });
        return [...frame.slice(0, height - 1), hintRow(hints(), width, 0)];
      }
      if (view === 'catalog') {
        selected = Math.max(0, Math.min(selected, (listing?.items.length ?? 1) - 1));
        const rendered = renderLibrary({ width, height: rows, tabs: groupTabs(), title: `资料库 › ${categoryName()}`, group, query, listing, detail,
          index: selected, offset, top: catalogTop, version: libraryMeta?.revision?.slice(0, 8), loading: busy || catalogLoading, note });
        hits = rendered.hits; catalogTop = rendered.top; return rendered.rows;
      }
      // The detail page keeps its own selection: the related entries, not the list's rows.
      const items = entries(); if (view !== 'detail') selected = Math.min(selected, Math.max(0, items.length - 1));
      const footer = () => [...(note || busy ? [note ? panelText(note, width, 1, 'error')[0] : { text: '加载中…', tone: 'muted' }] : []), hintRow(hints(), width, 0)];
      const option = (row, i, number) => {
        hits.push({ y: frame.length, index: i });
        if (row.toggle) push(toggleRow(row.toggle, row.value, { active: i === selected && !confirm, width, labelWidth: 4 }));
        else push(optionRow({ label: row.label, hint: row.hint, danger: row.danger }, { selected: i === selected && !confirm, number, width, indent: 0 }));
      };
      if (view === 'detail') {
        const meta = detailCategory === 'cards' ? (upgraded ? '已升级' : '') : detailCategory === 'monsters' ? `A${level}` : '';
        const header = libraryHeader(groupTabs(), group, width, `资料库 › ${categoryName()} › ${detail?.name ?? ''}`, meta);
        push(panelRule(width), header.rows); hits.push(...header.hits.map(hit => ({ ...hit, y: hit.y + 1 })));
        const body = (detail?.lines ?? []).flatMap(line => wrap(line, width)).map(line => ({ text: line }));
        const links = detail?.links ?? [];
        const room = Math.max(1, height - frame.length - footer().length);
        const linkRows = links.length ? 1 + links.length : 0;
        scroll = Math.min(scroll, Math.max(0, body.length + linkRows - room));
        const lines = [...body, ...(links.length ? [{ text: '关联条目', tone: 'title', link: -1 }] : []), ...links.map((row, i) => ({ link: i, row }))];
        for (const line of lines.slice(scroll, scroll + room)) {
          if (line.row) { push(optionRow({ label: line.row.name }, { selected: line.link === selected, width })); }
          else push(line);
        }
      } else {
        const counts = { rooms: `${rooms.filter(room => room.mode === 'coop').length} 个房间`, categories: libraryMeta?.revision ? `本地资料 ${libraryMeta.revision.slice(0, 8)}` : '' };
        push(panelRule(width), panelTitle(titles()[view] ?? '', counts[view] ?? '', width, 0));
        if (view === 'rooms') {
          push(panelText('房主在线、尚未开始的房间对所有人可见；已开始的房间仅原成员可继续。', width, 2), searchRow(query, width, '搜索房主或成员…'));
          const [a, o, n] = roomColumns();
          push({ text: '  ' + pad('进阶', a) + pad('房主', o) + pad('人数', n) + '进度', tone: 'muted' });
        } else push({ text: '' });
        if (view === 'settings') {
          const all = settingsRows(), room = Math.max(1, height - frame.length - footer().length);
          scroll = Math.min(scroll, Math.max(0, all.length - room));
          push(all.slice(scroll, scroll + room));
        } else {
          const numbered = ['main', 'categories'].includes(view) && items.length <= 9;
          const reserve = footer().length + (confirm ? 6 : view === 'setup' ? 6 : 0);
          const budget = Math.max(1, height - frame.length - reserve), first = Math.floor(selected / budget) * budget;
          items.slice(first, first + budget).forEach((row, i) => option(row, first + i, numbered && !row.toggle ? first + i + 1 : undefined));
          if (!items.length) push({ text: busy ? '加载中…' : '没有匹配的房间', tone: 'muted' });
          if (items.length > budget) push({ text: `第 ${Math.floor(first / budget) + 1}/${Math.ceil(items.length / budget)} 页 · 共 ${items.length} 项`, tone: 'muted' });
          if (view === 'setup' && !confirm) {
            const character = meta.characters[setup.character];
            push({ text: '' }, panelText([`${character.name} · ${meta.ascensions[setup.ascension].description}`, character.lines[0], character.lines.at(-1), '初始牌组：' + character.lines.slice(2, -1).join(' · ')].join('\n'), width, Math.max(0, height - frame.length - footer().length - 1)));
          }
          if (confirm) {
            const abandon = !!confirm.abandon;
            push({ text: '' }, panelRule(width), panelTitle(confirm.claim ? '接受存档托管？' : abandon ? '放弃当前存档？' : '替换当前单人存档？', '', width),
              panelText(`A${confirm.ascension} · ${confirm.floor} 层 · ${confirm.players.map(p => p.name).join(' / ')}\n${confirm.claim ? '操作房主原角色，不新增角色；存档及奖励仍属于原账号。' : abandon ? '当前旅程将结束，无法继续此存档。' : '旧旅程将结束，新旅程创建成功后才会替换。'}`, width, 2));
            [confirm.claim ? '接受托管' : abandon ? '放弃存档' : '开始新旅程', '取消'].forEach((label, i) => { hits.push({ y: frame.length, confirm: i }); push(optionRow({ label, danger: i === 0 }, { selected: confirmIndex === i, number: i + 1, width })); });
          }
        }
      }
      const tail = footer();
      while (frame.length < height - tail.length) push({ text: '' });
      return [...frame.slice(0, height - tail.length), ...tail];
    },
    key(key) {
      if (key.ctrl && ['c', 'd'].includes(key.name)) { ctx.closeScreen(); return; }
      if (game) { game.screen.key(key); return; }
      const name = key.name, value = key.value?.toLowerCase();
      if (name === 'tab' && ['catalog', 'detail'].includes(view)) { nextGroup(key.shift ? -1 : 1); return; }
      if (view === 'catalog') {
        if (name === 'escape') { navigation++; listVersion++; detailVersion++; catalogLoading = false; back(); return; }
        if (key.ctrl && name === 'u') { editCatalogQuery(''); return; }
        if (name === 'backspace') { editCatalogQuery([...new Intl.Segmenter('zh-CN', { granularity: 'grapheme' }).segment(query)].slice(0, -1).map(row => row.segment).join('')); return; }
        if (key.ctrl && name === 'r') { if (!busy && !catalogLoading) { catalogData = undefined; void guard(loadList); } return; }
        if (!key.ctrl && !key.meta && key.value && !['tab', 'left', 'right', 'up', 'down', 'home', 'end', 'pageup', 'pagedown', 'return', 'enter'].includes(name)) { editCatalogQuery(query + clean(key.value)); return; }
      }
      if (busy || catalogLoading) return;
      if (view === 'password') {
        if (name === 'escape') cancelPassword();
        else if (['return', 'enter'].includes(name)) void guard(submitPassword);
        else if (key.ctrl && name === 'u') editPassword('');
        else if (name === 'backspace') editPassword([...passwordPrompt.value].slice(0, -1).join(''));
        else if (!key.ctrl && !key.meta && key.value && !['tab', 'left', 'right', 'up', 'down', 'home', 'end', 'pageup', 'pagedown'].includes(name)) editPassword(passwordPrompt.value + key.value);
        return;
      }
      if (name === 'escape') { back(); return; }
      if (confirm) {
        if (['up', 'down'].includes(name)) confirmIndex = name === 'up' ? 0 : 1;
        if (['1', '2'].includes(value)) confirmIndex = Number(value) - 1;
        if (['return', 'enter'].includes(name) || ['1', '2'].includes(value)) {
          if (confirmIndex === 1) confirm = undefined;
          else { void guard(confirmAction); return; }
        }
        redraw(); return;
      }
      // The room list filters as you type, like the library and the chat's pages.
      if (view === 'rooms' && !(key.ctrl && name === 'r')) {
        const typed = !key.ctrl && !key.meta && key.value && !['tab', 'left', 'right', 'up', 'down', 'home', 'end', 'pageup', 'pagedown', 'return', 'enter'].includes(name);
        if (key.ctrl && name === 'u' || name === 'backspace' || typed) {
          query = key.ctrl ? '' : name === 'backspace' ? [...query].slice(0, -1).join('') : (query + clean(key.value)).slice(0, 100);
          selected = 0; redraw(); return;
        }
      }
      // Short menus take their number, as the chat's menus do.
      if (['main', 'categories'].includes(view) && /^[1-9]$/.test(value ?? '') && !key.ctrl && !key.meta && Number(value) <= entries().length) {
        selected = Number(value) - 1; void guard(() => activate(entries()[selected])); return;
      }
      if (value === 'r' || key.ctrl && name === 'r') {
        if (view === 'detail') void guard(refreshDetail);
        else if (view === 'categories') void guard(async () => { libraryMeta = await catalog.metadata(); });
        else if (['main', 'rooms', 'delegations', 'setup'].includes(view)) void guard(loadRooms);
        return;
      }
      if (view === 'settings' || view === 'detail') {
        const selectingLinks = view === 'detail' && detail?.links?.length;
        if (!selectingLinks && name === 'up') scroll = Math.max(0, scroll - 1);
        if (!selectingLinks && name === 'down') scroll++;
        if (name === 'pageup') scroll = Math.max(0, scroll - 10);
        if (name === 'pagedown') scroll += 10;
        if (view === 'detail') {
          if (selectingLinks && (['up', 'down', 'home', 'end'].includes(name) || ['[', ']'].includes(value))) {
            const delta = name === 'up' || value === '[' ? -1 : 1;
            selected = name === 'home' ? 0 : name === 'end' ? detail.links.length - 1 : Math.max(0, Math.min(detail.links.length - 1, selected + delta));
            scroll = [...detail.lines, '关联条目（Enter 查看选中条目）：', ...detail.links.slice(0, selected).map(row => `  ${row.name}`)].flatMap(line => wrap(line, width)).length;
          }
          if (value === 'u' && detailCategory === 'cards') { upgraded = !upgraded; void guard(refreshDetail); }
          if (['left', 'right'].includes(name) && detailCategory === 'monsters') { level = Math.max(0, Math.min(10, level + (name === 'right' ? 1 : -1))); void guard(refreshDetail); }
          if (['return', 'enter'].includes(name) && detail?.links?.[selected]) void guard(async () => {
            const row = detail.links[selected], data = await getDetail(row.category, row.id);
            detailBack.push({ detail, detailCategory, level, upgraded, scroll, selected });
            detail = data; detailCategory = row.category; scroll = selected = 0;
          });
        }
        redraw(); return;
      }
      const items = entries();
      if (name === 'up') selected = Math.max(0, selected - 1);
      if (name === 'down') selected = Math.min(items.length - 1, selected + 1);
      if (name === 'home') selected = 0;
      if (name === 'end') selected = Math.max(0, items.length - 1);
      if (view === 'setup' && ['left', 'right'].includes(name)) {
        const delta = name === 'right' ? 1 : -1;
        if (items[selected]?.id === 'character') setup.character = (setup.character + delta + meta.characters.length) % meta.characters.length;
        if (items[selected]?.id === 'passwordEnabled') { setup.passwordEnabled = !setup.passwordEnabled; if (!setup.passwordEnabled) setup.password = ''; }
        if (items[selected]?.id === 'ascension') setup.ascension = Math.max(0, Math.min(10, setup.ascension + delta));
      }
      if (view === 'catalog') {
        if (['left', 'right'].includes(name)) { offset = Math.max(0, Math.min(Math.max(0, Math.ceil((listing?.total ?? 0) / 40) - 1) * 40, offset + (name === 'right' ? 40 : -40))); selected = 0; void guard(loadList); }

        else if (['up', 'down', 'home', 'end'].includes(name)) void preview().catch(error => { note = error.message; redraw(); });
      }
      if (['return', 'enter'].includes(name)) void guard(() => activate(items[selected]));
      redraw();
    },
    paste(text) { if (view === 'password') { if (!busy) editPassword(passwordPrompt.value + text); return; } if (game) game.screen.paste?.(text); else if (view === 'catalog') editCatalogQuery(query + clean(text)); else if (view === 'rooms') { query = (query + clean(text)).slice(0, 100); selected = 0; redraw(); } },
    mouse(event) { if (game) { game.screen.mouse?.(event); return; } const hit = hits.find(row => row.y === event.y && (row.x === undefined || event.x >= row.x && event.x < row.x + row.w));
      // Pointing at a row lights it like keyboard focus; only a click acts.
      if (event.action === 'move') {
        if (hit?.index === undefined || hit.index === selected) return;
        selected = hit.index; redraw();
        // The library's detail pane follows the pointer as it follows the arrows.
        if (view === 'catalog' && !catalogLoading) void preview().catch(error => { note = error.message; redraw(); });
        return;
      }
      if (event.action !== 'press' || event.button && event.button !== 'left') return; if (hit?.group !== undefined) { void switchGroup(hit.group); return; }
      if (hit?.confirm !== undefined) { confirmIndex = hit.confirm; if (confirmIndex === 1) { confirm = undefined; redraw(); } else void guard(confirmAction); return; } if (busy || catalogLoading) return; if (hit) { selected = hit.index; void guard(() => activate(entries()[selected])); } },
  };
  return { screen, start: async () => {
    if (stopped) return;
    prefetch();
    poll = setInterval(() => { if (!game && ['rooms', 'delegations'].includes(view) && !busy) void guard(loadRooms); }, 5000); poll.unref?.();
  }, stop: () => { stopped = true; navigation++; listVersion++; detailVersion++; clearInterval(poll); passwordPrompt = createRequest = undefined; if (setup) setup.password = ''; game?.stop(); } };
}
