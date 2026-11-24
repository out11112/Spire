const cardUnplayable = card => card.unplayable === true || card.cost === '—' || (['status', 'curse', 'quest'].includes(card.kind) && /不能被打出|不可打出/.test(String(card.description ?? '')));
import catalogMetadata from './catalog-data/metadata.json' with { type: 'json' };
import { cardCost, cardDescription, optionLabel, optionCards } from './card-cost.js';
import { newId } from './ids.js';
import { createDelegationPanel } from './delegation.js';
import { createActionQueue } from './action-queue.js';
import { createRoomChat } from './room-chat.js';
import { renderShop, shopGoods, SHOP_GROUPS } from './shop-view.js';
import { createLobby, HELP_GROUPS, HELP_NOTE } from './lobby.js';
import { panelTitle, hintRow } from './panel.js';
import { TEXT, MUTED, ACCENT, DANGER, DANGER_SELECTED, RESET, MAP_FOCUS, MAP_NEXT, MAP_REACHABLE, MAP_IDLE, MAP_VOTES, GOLD, BUFF, DEBUFF, PILE_DRAW, PILE_DISCARD, PILE_EXHAUST, paint } from './palette.js';
import { pileChange, animation, frameAt, FRAME_MS } from './animation.js';
import { wrap as wrapCardText } from './ui-layout.js';
import { powerDescription } from './power-text.js';
const PROTOCOL = 8;
const VERSION_ERROR = 'Spire 客户端与服务器版本不匹配，请配套升级。';
const BASE = '/api/games/spire/rooms';
const hpText = creature => creature.awaitingRevive ? '0（待复活）' : creature.hpDisplay === 'infinite' && creature.hp > 0 ? '∞' : `${creature.hp}/${creature.maxHp}`;
const healthText = creature => `⛨ ${creature.block ?? 0} · HP ${hpText(creature)}`;
export const phases = { lobby: '等待队友', map: '路线投票', combat: '战斗', reward: '战利品', rest: '休息', shop: '商店', event: '事件', treasure: '宝箱', actComplete: '本幕完成', ending: '结局事件', victory: '通关', defeat: '攀登结束', abandoned: '已放弃' };
const tabNames = {action:'行动',deck:'牌组',draw:'抽牌堆',discard:'弃牌堆',exhaust:'消耗牌堆',relics:'遗物',potions:'药水',status:'状态',log:'日志'};
// Official names come from the exported catalog; these few are display-only
// states the game has no status for.
const powerNames = {...catalogMetadata.powerNames, temporaryStrengthDown:'临时力量降低', facingLeft:'当前朝左', facingRight:'当前朝右'};
const powersText = (powers, monologues = []) => Object.entries(powers ?? {}).filter(([,value])=>value!==0).flatMap(([key,value])=>key==='monologue' && monologues.length ? monologues.map(record=>`独白 ${record.applied}`) : [`${powerNames[key] ?? '未知状态'} ${value}`]).join(' · ') || '无';
const resourcesText = (p, showStars = true) => [showStars && (p.character==='regent' || p.stars) ? `辉星 ${p.stars ?? 0}` : '', ...(p.orbs ?? []).map(orb => `${orb.name}${['dark','glass'].includes(orb.kind) ? ` ${orb.charge}` : ''}`), p.osty ? `奥斯提 ${p.osty.hp}/${p.osty.maxHp} HP` : '', ...(p.companions ?? []).map(pet=>pet.name+(pet.cooldown===undefined?'':pet.cooldown>0?` 冷却 ${pet.cooldown}`:' 就绪'))].filter(Boolean).join(' · ');
const terminalPhases = new Set(['victory', 'defeat', 'abandoned']);
// A state whose phase this build does not know is still well formed: the run
// moved on, and the screen has to say so rather than refuse to open. Only the
// phase check is relaxed, and the caller has to ask for that explicitly.
function wellFormed(s, knownPhase) {
  return !!s && s.protocol === PROTOCOL && typeof s.roomId === 'string' && Number.isSafeInteger(s.revision) && Number.isSafeInteger(s.phaseId) && (knownPhase ? Object.hasOwn(phases, s.phase) : typeof s.phase === 'string')
    && Array.isArray(s.players) && s.players.length <= 4 && s.players.every(p => typeof p.id === 'string' && typeof p.name === 'string')
    && Array.isArray(s.enemies) && s.enemies.length <= 12 && s.enemies.every(e => typeof e.id === 'string' && typeof e.name === 'string' && e.intent)
    && (!s.act || Number.isInteger(s.act.index) && s.act.index>=0 && s.act.index<3 && typeof s.act.name==='string')
    && s.self && ['hand', 'deck', 'discard', 'relics', 'potions'].every(k => Array.isArray(s.self[k]) && s.self[k].length <= 1000)
    && ['draw','exhaust'].every(k => s.self[k] === undefined || Array.isArray(s.self[k]) && s.self[k].length <= 1000)
    && (!s.pendingChoice || typeof s.pendingChoice.id === 'string' && typeof s.pendingChoice.title === 'string' && s.players.some(p=>p.id===s.pendingChoice.owner) && Number.isSafeInteger(s.pendingChoice.minimum) && Number.isSafeInteger(s.pendingChoice.maximum) && s.pendingChoice.minimum>=0 && s.pendingChoice.maximum>=s.pendingChoice.minimum && s.pendingChoice.maximum<=1000)
    && (!s.pendingDecision || typeof s.pendingDecision.id==='string' && typeof s.pendingDecision.title==='string' && typeof s.pendingDecision.kind==='string' && s.players.some(p=>p.id===s.pendingDecision.owner) && Number.isSafeInteger(s.pendingDecision.minimum) && Number.isSafeInteger(s.pendingDecision.maximum) && s.pendingDecision.minimum>=0 && s.pendingDecision.maximum>=s.pendingDecision.minimum)
    && s.players.every(p => (p.stars === undefined || Number.isSafeInteger(p.stars) && p.stars>=0) && (p.orbs === undefined || Array.isArray(p.orbs) && p.orbs.length<=10 && p.orbs.every(o=>o && typeof o.name==='string' && typeof o.kind==='string')) && (!p.osty || Number.isSafeInteger(p.osty.hp) && Number.isSafeInteger(p.osty.maxHp)))
    && s.players.every(p=>p.companions===undefined || Array.isArray(p.companions) && p.companions.length<=3 && p.companions.every(pet=>pet && typeof pet.name==='string' && (pet.cooldown===undefined || Number.isSafeInteger(pet.cooldown) && pet.cooldown>=0)))
    && s.players.every(p=>p.monologueInstances===undefined || Array.isArray(p.monologueInstances) && p.monologueInstances.every(record=>record && Number.isSafeInteger(record.strength) && record.strength>0 && Number.isSafeInteger(record.applied) && record.applied>=0))
    && (!s.mapView || typeof s.mapView === 'object' && s.mapView.nodes && s.mapView.nodes.length <= 200 && Array.isArray(s.mapView.nodes) && s.mapView.nodes.every(n => n && typeof n.id === 'string' && Number.isSafeInteger(n.row) && Number.isSafeInteger(n.col) && typeof n.type === 'string' && (n.children === undefined || Array.isArray(n.children))))
    && (!!s.endTurn && typeof s.endTurn === 'object' && typeof s.endTurn.canEndTurn === 'boolean' && typeof s.endTurn.canUndoEndTurn === 'boolean' && typeof s.endTurn.reason === 'string')
    && (!s.eventProgress?.sphere || (Number.isSafeInteger(s.eventProgress.sphere.divinations) && s.eventProgress.sphere.divinations >= 0
        && Number.isSafeInteger(s.eventProgress.sphere.width) && s.eventProgress.sphere.width > 0 && s.eventProgress.sphere.width <= 32
        && Number.isSafeInteger(s.eventProgress.sphere.height) && s.eventProgress.sphere.height > 0 && s.eventProgress.sphere.height <= 32
        && typeof s.eventProgress.sphere.tool === 'string' && typeof s.eventProgress.sphere.finished === 'boolean'
        && Array.isArray(s.eventProgress.sphere.cells) && s.eventProgress.sphere.cells.length <= 1024
        && s.eventProgress.sphere.cells.every(cell => cell && Number.isSafeInteger(cell.x) && Number.isSafeInteger(cell.y)
            && (cell.item === null || cell.item === undefined || typeof cell.item === 'string'))))
    && Array.isArray(s.options) && Array.isArray(s.log) && s.log.every(entry => typeof entry === 'string' || entry && Number.isSafeInteger(entry.id) && typeof entry.text === 'string');
}
export function validState(s) { return wellFormed(s, true); }

// Every intent field the rules can send and what the screen does with it: rendered,
// folded into another line, or internal with a reason. A field that is none of those
// is printed as a raw field, and the acceptance compares this against the backend's
// vocabulary so a new enemy action cannot end up as a blank line.
export const renderedIntentKeys = ['damage', 'hits', 'strength', 'vigor', 'vitalSpark', 'ritual', 'block', 'moveBlock',
  'dexterity', 'status', 'count', 'statusPile', 'statusExtra', 'debuffs', 'knowledge', 'healPerPlayer', 'stunned',
  'sleep', 'revive', 'reviveIllusion', 'summonEnemy', 'bloat', 'ratBackup', 'stealGold', 'wakeGremlin', 'escapeEnemy',
  'soar', 'land', 'fabricate', 'guardFabricator', 'layEggs', 'hatchEgg', 'stealCard', 'flutter', 'teamStrength',
  'reattach', 'liquify', 'hiveSpit', 'thornsBefore', 'thornsAfter', 'plow', 'selfKill', 'intangible', 'beckon',
  'burrowed', 'allyStrength', 'steam'];
export const internalIntentKeys = {
  targets: '目标由服务端按存活玩家生成，界面用「对我／全队受击」表达',
  damageByTarget: '并入攻击数字',
  intensify: '服务端已改写成力量与灼伤，本字段不再单独展示',
  hidden: '引擎不读取，仅数据标记',
  deathBlow: '引擎不读取，仅数据标记',
  sleeping: '引擎以 asleep 力量表示沉睡，本字段是数据标记',
};
const signed = value => `${value > 0 ? '+' : ''}${value}`;
// --- act map (§D) -----------------------------------------------------------
function mapData(view) {
  const nodes = (view?.nodes ?? []).filter(node => node && typeof node.id === 'string');
  const byId = new Map(nodes.map(node => [node.id, node]));
  const rows = new Map();
  for (const node of nodes) {
    if (!rows.has(node.row)) rows.set(node.row, []);
    rows.get(node.row).push(node);
  }
  for (const list of rows.values()) list.sort((left, right) => left.col - right.col);
  return { nodes, byId, rows, keys: [...rows.keys()].sort((left, right) => right - left),
           current: byId.get(view.current), reachable: new Set(view.reachable ?? []), visited: new Set(view.path ?? []) };
}
// Places cells at display columns, so the frame stays aligned whatever the
// terminal's character widths are.
function place(cells, width) {
  let out = '', at = 0;
  const placed = [];
  for (const cell of [...cells].sort((left, right) => left.at - right.at)) {
    if (cell.at < at) continue;
    out += ' '.repeat(cell.at - at) + cell.text;
    placed.push({ ...cell, from: cell.at, width: displayWidth(cell.text) });
    at = cell.at + displayWidth(cell.text);
  }
  return { text: cut(out, width), placed };
}
// One glyph per set of directions, so a corner always joins the lines that meet.
const JOIN = {
  u: '│', d: '│', l: '─', r: '─', ud: '│', ul: '┘', ur: '└', dl: '┐', dr: '┌', lr: '─',
  udl: '┤', udr: '├', ulr: '┴', dlr: '┬', udlr: '┼',
};
const joinGlyph = directions => {
  const set = new Set(directions);
  const key = `${set.has('u') ? 'u' : ''}${set.has('d') ? 'd' : ''}${set.has('l') ? 'l' : ''}${set.has('r') ? 'r' : ''}`;
  return JOIN[key] ?? '─';
};
const mapCode = node => `${String(node.row).padStart(2, '0')}-${String.fromCharCode(65 + node.col)}`;
const mapType = node => node.type === "先古之民" ? "先古" : node.type;
function mapLabel(view, data, node, options) {
  return `${node.id === view.current ? '● ' : data.visited.has(node.id) ? '✓ ' : ''}[${mapType(node)}]`;
}
function mapPaint(view, data, node, label, focus) {
  const child = data.byId.get(focus)?.children?.includes(node.id);
  const colour = node.id === focus ? MAP_FOCUS : child ? MAP_NEXT : node.id === view.current ? ACCENT : data.reachable.has(node.id) ? MAP_REACHABLE : MAP_IDLE;
  return `${colour}${label}${RESET}`;
}
function mapVotes(node, players) {
  const seats = (players ?? []).filter(player => player.vote === node.id).length;
  return seats ? { text: `${MAP_VOTES}${seats}${RESET}`, width: 1 } : { text: '', width: 0 };
}
function drawMap(view, width, session = {}) {
  const data = mapData(view), layers = [...data.rows.keys()].sort((a,b) => a-b);
  const focus = data.byId.has(session.focus) ? session.focus : view.current;
  const codeLabel = n => mapCode(n);
  const labels = new Map(data.nodes.map(n => [n.id, mapLabel(view, data, n, session.options)]));
  const cols = Math.max(6, ...data.nodes.map(n => n.col)) + 1;
  // An 80-column terminal gives the extension 75 columns after host margins.
  // Reserve only measured text plus a separator before falling back to a table.
  const needed = Math.max(8, ...data.nodes.map(n => displayWidth(labels.get(n.id)) + mapVotes(n, session.players).width + 1));
  const slot = Math.max(needed, width >= cols * 12 ? 12 : 6);
  const unsafeGap = layers.some((layer,i)=>{
    const rooms=data.rows.get(layer), next=data.rows.get(layers[i+1])??[];
    const edges=rooms.flatMap(n=>(n.children??[]).map(id=>[n,data.byId.get(id)]).filter(([,kid])=>kid));
    return edges.some(([a,b])=>b.row!==layers[i+1] || (Math.abs(a.col-b.col)>1 && rooms.length>1 && next.length>1)) ||
      edges.some(([a,b])=>edges.some(([c,d])=>(a.col-c.col)*(b.col-d.col)<0));
  });
  const compact = session.full || cols * slot > width || (session.height??24)<7 || unsafeGap;
  const blocks = [];
  const cell = (n, col, text) => ({id:n.id, row:0, col, width:displayWidth(text), height:1});
  const plainRow = text => ({text, cells:[], tone:'muted'});
  for (let i=0; i<layers.length; i++) {
    const rooms = data.rows.get(layers[i]), block = [];
    if (compact) {
      for (const n of rooms) {
        const label = `${codeLabel(n)} ${labels.get(n.id)}`;
        const kids = (n.children ?? []).map(id => data.byId.get(id)).filter(Boolean);
        const targets=kids.length ? kids.map(k=>`${mapCode(k)}[${mapType(k)}]`) : ['终点'];
        let suffix='';
        const emit=()=>block.push({text:mapPaint(view,data,n,label,focus)+mapVotes(n,session.players).text+suffix,cells:[cell(n,0,label)],tone:'text'});
        for(const target of targets){
          const next=`${suffix?' ·':' →'} ${target}`;
          if(suffix && displayWidth(label+suffix+next)+mapVotes(n,session.players).width>width){emit();suffix='';}
          suffix+=`${suffix?' ·':' →'} ${target}`;
        }
        emit();
      }
    } else {
      for (const codes of [true,false]) {
        const pieces = rooms.map(n => {
          const text = codes ? codeLabel(n) : labels.get(n.id);
          return {at:n.col*slot, text:mapPaint(view,data,n,text,focus)+(codes?'':mapVotes(n,session.players).text), node:n, plain:text};
        });
        const placed = place(pieces,width);
        block.push({text:placed.text,tone:'text',cells:placed.placed.map(e=>cell(e.node,e.from,e.plain))});
      }
      if (i+1<layers.length) {
        const ink = Array.from({length:3},()=>new Map());
        const put=(y,x,dirs,owner)=>{
          let c=ink[y].get(x); if(!c){c={dirs:new Set(),owners:new Set()};ink[y].set(x,c);}
          for(const d of dirs)c.dirs.add(d);c.owners.add(owner);
        };
        const horizontal=(y,a,b,owner)=>{
          for(let x=Math.min(a,b);x<=Math.max(a,b);x++)put(y,x,`${x>Math.min(a,b)?'l':''}${x<Math.max(a,b)?'r':''}`,owner);
        };
        const edges=rooms.flatMap(n=>(n.children??[]).map(id=>[n,data.byId.get(id)]).filter(([,kid])=>kid));
        // Original noncrossing edges use separate midpoint tracks. Branches
        // share the source row; merges share only the destination row.
        for(const [n,kid] of edges){
          const a=n.col*slot+2,b=kid.col*slot+2,m=Math.round((a+b)/2);
          horizontal(0,a,m,n.id);put(0,a,'u',n.id);put(0,m,'d',n.id);
          put(1,m,'ud',n.id);
          horizontal(2,m,b,n.id);put(2,m,'u',n.id);put(2,b,'d',n.id);
        }
        for(const row of ink){
          const pieces=[...row].map(([at,c])=>({at,text:`${c.owners.has(focus)?MAP_FOCUS:MAP_IDLE}${joinGlyph(c.dirs)}${RESET}`}));
          block.push(plainRow(place(pieces,width).text));
        }
      }
    }
    blocks.push(block);
  }
  const budget=Math.max(3,session.height??24);
  const anchor=data.byId.get(session.anchor)??data.current;
  const home=Math.max(0,layers.indexOf(anchor?.row));
  let from=Math.max(0,Math.min(blocks.length-1,session.scroll??Math.max(0,home-1)));
  let lines=[],span=0;
  // Scroll offsets count from the bottom (the beginning of the act).
  // Reverse layers, but keep same-layer rooms and wrapped targets in reading order.
  if(compact){
    const all=[...blocks].reverse().flat();
    const focusId=session.anchor??anchor?.id;
    const focusEnd=all.findLastIndex(line=>line.cells.some(c=>c.id===focusId));
    const offset=Math.max(0,Math.min(Math.max(0,all.length-budget),session.scroll??(focusEnd>=0?all.length-focusEnd-1:0)));
    const start=Math.max(0,all.length-budget-offset);
    lines=all.slice(start,start+budget);
    return {lines,from:offset,span:lines.length,total:all.length,height:lines.length,compact:true};
  }
  // Show the focused layer even if the preceding layer uses the whole budget.
  if(session.scroll===undefined && from<home && blocks[from].length+2>budget)from=home;
  for(let i=from;i<blocks.length;i++){
    const last=i===blocks.length-1;
    if(lines.length+blocks[i].length>budget){
      if(lines.length+2<=budget){lines.push(...blocks[i].slice(0,2));span++;}
      break;
    }
    lines.push(...blocks[i]);span++;
    if(last)break;
  }
  // Remove dangling connectors at the viewport boundary.
  while(lines.length && !lines.at(-1).cells.length)lines.pop();
  // Reflect the geometry vertically, including each connector's directions.
  // Labels remain code-above-type; neither text nor ANSI escapes are mirrored.
  const mirror={'┌':'└','└':'┌','┐':'┘','┘':'┐','┬':'┴','┴':'┬'};
  lines.reverse();
  for(let i=0;i<lines.length;i++){
    if(lines[i].cells.length){
      [lines[i],lines[i+1]]=[lines[i+1],lines[i]];
      i++;
    }else lines[i]={...lines[i],text:lines[i].text.replace(/[┌└┐┘┬┴]/g,ch=>mirror[ch])};
  }
  return {lines,from,span,total:layers.length,height:lines.length,compact:false};
}

// The package ships without dependencies, so the tab strip is measured here.
// Its labels are tabNames (CJK), pile counts in fullwidth parens, brackets.
const wideChar = character => { const code = character.codePointAt(0); return code >= 0x1100 && (code <= 0x115f || (code >= 0x2e80 && code <= 0xa4cf && code !== 0x303f) || (code >= 0xac00 && code <= 0xd7a3) || (code >= 0xf900 && code <= 0xfaff) || (code >= 0xfe30 && code <= 0xfe6f) || (code >= 0xff00 && code <= 0xff60) || (code >= 0xffe0 && code <= 0xffe6)); };
// A coloured digit is zero columns wide: measuring and cutting step over the
// escape sequences instead of counting their characters.
const ESCAPE_END = /[a-zA-Z]/;
const displayWidth = text => {
  let width = 0, escape = false;
  for (const character of String(text)) {
    if (escape) { if (ESCAPE_END.test(character)) escape = false; continue; }
    if (character === '\x1b') { escape = true; continue; }
    width += wideChar(character) ? 2 : 1;
  }
  return width;
};
const pad = (text, width) => text + ' '.repeat(Math.max(0, width - displayWidth(text)));
function cut(text, width) {
  let out = '', used = 0, escape = false, trimmed = false;
  for (const character of text) {
    if (escape) { out += character; if (ESCAPE_END.test(character)) escape = false; continue; }
    if (character === '\x1b') { out += character; escape = true; continue; }
    const size = wideChar(character) ? 2 : 1;
    if (used + size > width) { trimmed = true; break; }
    out += character; used += size;
  }
  return trimmed && out.includes('\x1b') ? `${out}\x1b[0m` : out;
}
export function createScreen(ctx, navigation = {}) {
  let connectionGeneration = 0;
  let state, roomId, leaseId, connection, online = false, synced = false, rooms = [], loading = true, busy = false, closed = false;
  let ascension = 0;
  // Official ascension titles and descriptions, exported with the catalog.
  const ascensionNames = catalogMetadata.ascensions.map(row => row.name);
  const ascensionDescriptions = catalogMetadata.ascensions.map(row => row.description);
  let tab = 0, selected = 'create', index = 0, modal, note = '', columns = 80, height = 24, serverProtocol = undefined, unsupported;
  // Frame row -> what that row means, rebuilt by every render.
  let hits = [];
  let targeting;
  let expandedUnit;
  let enemyPage = 0;              // the enemy block page the battlefield is showing
  let shopGroup = '', shopTop = 0;
  const unaffordableShopIds = new Set();
  const shopPositions = new Map();
  let listPage = 0;               // the 1-9/0 page of the item list
  let pageSize = 10;              // how many items a page holds at the current size
  let mapBudget = 10;
  let mapScroll;                  // the map row the view starts at (undefined follows the anchor)
  let mapAnchor;                  // the room the viewport is parked on (a click or arrow navigation)
  let mapFocus;                   // the node being looked at on the map, never a submitted route
  let chain;                      // §G: the claim that follows this player's own treasure pick
  let rewardLog = new Map();      // §F reward id -> claimed / skipped; display only, never a receipt
  let rewardOpen;                 // §F the card reward whose candidates are expanded
  let rewardPick = new Map();     // §F the candidate chosen in each card reward
  let skipArmed = false;          // 跳过剩余奖励并离开 shows [Enter 跳过] and the next confirm skips
  let skipQueue = [];             // §F the server skip rows still to run, in reward order
  let skipKnown = new Set();      // §F the rows that existed when the skip was confirmed
  const picked = new Set(); let choiceReturn;
  const changed = () => { if (!closed && !ctx.signal.aborted) ctx.redraw(); };
  // Piles whose size changed are marked for a moment with where they came from.
  // Games opened from the lobby always show it; any key or click ends it early.
  const animate = navigation.animate === true;
  let motion, motionTimer;
  function stopMotion() { if (motionTimer) clearInterval(motionTimer); motionTimer = undefined; motion = undefined; }
  function startMotion(change) {
    motion = animation(change, Date.now());
    if (motionTimer) return;
    motionTimer = setInterval(() => { if (!frameAt(motion, Date.now())) stopMotion(); changed(); }, FRAME_MS);
    motionTimer.unref?.();
  }
  const actionQueue = createActionQueue({
    send: value => connection?.send(value) ?? false,
    state: (snapshot, action) => { if (action?.type === 'character') { characterConfirmed = true; mapOpen = undefined; } accept(snapshot); },
    note: value => { note = value; }, changed, lease: () => leaseId,
    reconnect: () => connection?.reconnect(),
    timing: sample => ctx.recordTiming?.(sample),
  });
  const queueStatus = () => actionQueue.blocked ? '正在核对操作结果 · R 查看进度' : '';
  const chat = createRoomChat(ctx, () => ({ roomId, leaseId, available: state?.features?.roomChat === true, online: online && synced, sl: state?.sl }));
  const errorText = e => e instanceof Error ? e.message : '游戏请求失败。';
  const seatId = () => state?.self.id ?? ctx.user.id;
  const me = () => state?.players.find(p => p.id === seatId());
  const delegation = createDelegationPanel(ctx, { snapshot: () => state, room: () => roomId, reconnect: () => connect(roomId), redraw: changed });
  let characterConfirmed=false, mapOpen, mapReturnTab=0;
  const needsCharacterChoice=()=>!characterConfirmed && !state?.paused && ['lobby','map'].includes(state?.phase) && state?.options.some(row=>row.action?.type==='character');
  let pileView, pileReturn, focusRegion='action', focusIndex=0, hovered, focusControl;
  const equipmentOffset={relics:0,potions:0};
  const activeTab = () => pileView ?? 'action';
  function closePile() {
    pileView=undefined;
    if(pileReturn){({index,selected,listPage,focusRegion,focusIndex,mapOpen}=pileReturn);pileReturn=undefined;}
    changed();
  }
  function openPile(key) {
    if(!state || modal || (key!=='deck' && state.phase!=='combat'))return;
    if(pileView===key){closePile();return;}
    if(!pileView)pileReturn={index,selected,listPage,focusRegion,focusIndex,mapOpen};
    pileView=key;mapOpen=false;focusRegion='action';hovered=undefined;index=0;selected=undefined;listPage=0;changed();
  }
  const regionItems = region => !state ? [] : region==='relics' ? state.self.relics.map(r=>({...r,id:r.id??r.key})) :
    region==='potions' ? Array.from({length:state.self.potionCapacity??3},(_,i)=>state.self.potions[i]??{id:`empty:${i}`,name:'空槽',description:'没有药水',empty:true}) :
    region==='units' ? [...state.players,...state.enemies.filter(e=>e.hp>0||e.awaitingRevive)] :
    region==='entries' ? [{id:'deck',name:`[D 牌组 ${state.self.deck.length}]`,description:'查看永久总牌组 · U 升级预览'}] : [];
  function controlItem(hit){
    if(!hit)return;
    const labels={endTurn:endTurnLabel(),pile:{draw:'抽牌堆',discard:'弃牌堆',exhaust:'消耗牌堆'}[hit.id],inspect:'查看队友'};
    return {id:focusKey(hit),name:labels[hit.kind]??'操作',description:'Enter 操作'};
  }
  function focusItem(){return focusRegion==='controls'?controlItem(currentHit()):regionItems(focusRegion)[focusIndex];}
  function pointsAt(region,id){
    if(modal)return false;
    if(targeting)return region==='units' && String(id)===String(targeting.id);
    const active=hovered ?? {region:focusRegion,row:focusRegion==='action'?items()[index]:focusItem()};
    return active.region===region && String(active.row?.id)===String(id);
  }
  function targetCardDescription(card, targetId, full = false){
    const description=cardDescription(card ?? {}, true, full);
    const preview=card?.damagePreview, value=preview?.byTarget?.[String(targetId)];
    if(preview?.basis!=='currentStateBeforeBlock'||!Number.isSafeInteger(value?.damage)||value.damage<0||!Number.isSafeInteger(value?.hits)||value.hits<0)return description;
    const damage=value.hits===0?0:value.damage;
    // Replace only the primary attack clause, never self-damage or a bonus value.
    const primary=/(^|；)((?:对所有敌人|对随机敌人)?伤害)\s*\d+/;
    return primary.test(description)
      ? description.replace(primary,(_,start,label)=>`${start}${label} ${damage}`)
      : `伤害 ${damage}${description?`；${description}`:''}`;
  }
  // Alone at a chest, a count of who picked what says nothing.
  function soloLabel(label){return state?.players?.length===1 && state.phase==='treasure' ? label.replace(/（\d+ 人选择）$/,'') : label;}
  function detailText(full = false){
    if(targeting?.action?.type==='play'){
      const card=state?.self.hand.find(card=>card.id===targeting.action.card);
      if(card)return [card.name,targeting.arena==='enemy'?targetCardDescription(card,targeting.id,full):cardDescription(card, true, full)].filter(Boolean).join(' · ');
    }

    const row=(targeting ? regionItems('units').find(row=>String(row.id)===String(targeting.id)) : undefined) ?? hovered?.row ?? (focusRegion==='action' ? items()[index] : focusItem());
    if(!row)return state?.phase==='defeat' ? '攀登结束 · Esc 返回主界面' : '';
    if(row.hp!==undefined)return [row.name,healthText(row),row.intent?intentLines(row.intent,row,state,true).join('+'):resourcesText(row),powersText(row.powers,row.monologueInstances)].filter(Boolean).join(' · ');
    if (optionCards(row)) return optionLabel(row, full);
    return [row.name??row.card?.name,row.card ? cardDescription(row.card, true, full) : row.description??(row.label===undefined?undefined:soloLabel(full ? row.fullLabel??row.label : row.label)),
      row.counter!==undefined?`当前计数 ${row.counter}`:'',row.usage==='Automatic'?'自动触发，不能主动使用':'',
      (hovered?.region??focusRegion)==='potions' && state?.self.potionsLocked?'事件锁定：不能使用或丢弃':''].filter(Boolean).join(' · ');
  }
  function potionMenu(potion){
    if(!potion || potion.empty)return;
    const id=potion.id;
    choose(`${potion.name} · 药水操作`,[{id:'use',label:'使用'},{id:'drop',label:'丢弃'},{id:'back',label:'返回'}],answer=>{
      const current=state.self.potions.find(p=>p.id===id);
      if(!current){note='这瓶药水已不在栏中。';changed();return;}
      if(answer.id==='back'){changed();return;}
      if(state.self.potionsLocked){note='事件锁定：不能使用或丢弃药水。';changed();return;}
      if(!canAct())return;
      if(answer.id==='drop'){
        choose('丢弃这瓶药水？',[{id:'no',label:'保留'},{id:'yes',label:'丢弃'}],row=>{if(row.id==='yes')void submit({type:'dropPotion',potion:id});else changed();});return;
      }
      if(current.usage==='Automatic'){note='这瓶药水会自动触发，不能主动使用。';changed();return;}
      if(state.paused || (state.phase==='combat'?me()?.done:current.usage!=='AnyTime')){note='当前不能使用这瓶药水。';changed();return;}
      const action={type:'potion',potion:id,phaseId:state.phaseId,label:current.name};
      if(current.target==='AnyEnemy'||current.key==='FirePotion')beginTargeting(action,'enemy','选择药水目标');
      else if(current.target==='AnyPlayer'&&state.players.filter(p=>p.hp>0).length>1)beginTargeting(action,'ally','选择药水目标');
      else {delete action.label;void submit(action);}
    });
  }
  async function openLog(cursor={},atEnd=false){
    if(!state || !roomId)return;
    const battle=state.battleLog?.battleId, originRoom=roomId, generation=connectionGeneration;
    if(!battle){note='当前没有战斗日志。';changed();return;}
    const previous=modal?.battleLog ? {selected:modal.previousSelected,index:modal.previousIndex,page:modal.previousPage} : {selected,index,page:listPage};
    await guard(async()=>{
      const pageCursor=Object.keys(cursor).length?cursor:{before:String((state.battleLog?.last??Number.MAX_SAFE_INTEGER-1)+1)};
      const query=new URLSearchParams({battleId:String(battle),limit:'100',...pageCursor});
      const body=await ctx.request(`${BASE}/${originRoom}/logs?${query}`);
      if(closed || generation!==connectionGeneration || roomId!==originRoom || state?.battleLog?.battleId!==battle)return;
      const rows=[];let turn;
      for(const entry of [...body.entries].reverse().filter(entry=>entry.kind!=='pile')){
        if(entry.turn!==turn){turn=entry.turn;rows.push({id:`turn:${entry.id}`,label:`── 回合 ${turn} ──`,separator:true});}
        rows.push({id:String(entry.id),label:`${entry.id}. ${entry.text}${entry.source?.name?` [${entry.source.name}]`:''}`});
      }
      choose('战斗日志',rows.length?rows:[{id:'empty',label:'暂无记录'}],()=>changed(),
        {battleLog:body,meta:`${body.total} 条${body.incomplete?' · 早期记录可能不完整':''}`,previousSelected:previous.selected,previousIndex:previous.index,previousPage:previous.page});
      if(atEnd)moveTo(rows.length-1);
    });
  }
  const logItems = () => state.log.map((entry, i) => typeof entry === 'string' ? {id:String(i),label:entry} : {id:String(entry.id),label:entry.text});
  // A phase this build cannot render stays read only, so nothing is submitted.
  const canAct = () => !!state && online && synced && !busy && !unsupported && !state.readOnly && !actionQueue.blocked;
  const cardItem = c => ({ id: c.id, label: `${c.name}  ${cardCost(c, true)}  ${cardDescription(c, true)}`, card: c });
  // In the room lobby the ready row names the character that will embark.
  const lobbyReady = row => row.id === 'ready' && state?.phase === 'lobby' && me()?.characterName ? { ...row, label: `${row.label}（${me().characterName}）` } : row;
  const optionItem = raw => { const row = lobbyReady(raw); return { ...row, fullLabel: row.label, label: optionLabel(row) }; };
  function items() {
    if (modal) return modal.items;
    if (!roomId) return [{ id: 'create', label: '创建合作房间（2–4 人）' }, {id:'solo',label:rooms.some(r=>r.mode==='solo') ? `继续单人攀登 · A${rooms.find(r=>r.mode==='solo').ascension ?? 0}` : '单人攀登 · 开始'}, {id:'ascension',label:`新局难度 · A${ascension} ${ascensionNames[ascension]}（全部开放）`}, ...rooms.filter(r=>r.mode!=='solo').map(r => ({ id: r.id, room: r, label: `${r.players.some(p => p.id === ctx.user.id) ? '继续' : '加入'} · ${r.players.map(p => p.name).join(' / ')} · A${r.ascension ?? 0} · ${r.players.length}/4 · ${phases[r.phase] ?? r.phase}${r.paused ? ' · 已暂停' : ''}${r.compatible === false ? ' · 版本不兼容' : ''}` }))];
    if (!state) return [];
    if(needsCharacterChoice())return [{id:'keepCharacter',label:`使用当前角色：${me()?.characterName??me()?.character??'铁甲战士'}`},...state.options.filter(row=>row.action?.type==='character')];
    if (['deck','draw','discard','exhaust'].includes(activeTab())) return (state.self[activeTab()] ?? []).map(cardItem);

    if (state.readOnly) return state.phase === 'combat' ? state.self.hand.map(cardItem) : [];
    const groups = rewardGroups();
    const eventRewards = ['event', 'ending'].includes(state.phase) && groups.some(group => group.kind === 'card');
    if (state.pendingChoice && !state.paused) return state.options.map(optionItem).map(row => row.pick ? {...row,label:`${picked.has(row.pick) ? '[x]' : '[ ]'} ${row.label}`} : row.id === 'confirmChoice' ? {...row,label:`确认选择（${picked.size}/${state.pendingChoice.maximum}）`} : row);
    if (state.pendingDecision && !state.paused && !eventRewards) {
      const decision = state.pendingDecision;
      if (decision.maximum > 1) {
        const candidates = decision.options ?? state.options.filter(row => row.action?.selections?.length === 1).map(row => ({ id: row.action.selections[0], label: row.label }));
        const rows = candidates.map(item => ({ ...item, id: item.id, label: `${picked.has(item.id) ? '[x]' : '[ ]'} ${optionLabel(item)}`, pick: item.id }));
        // Whatever the server offers beyond single candidates is the way out.
        rows.push(...state.options.filter(row => (row.action?.selections ?? []).length !== 1));
        rows.push({ id: 'confirmDecision', label: `确认选择（${picked.size}/${decision.maximum}）`,
                    action: { type: 'decide', decisionId: decision.id, selections: [...picked] } });
        return rows;
      }
      return state.options.map(optionItem);
    }
    if (state.phase === 'combat' && !state.paused && !state.self.pendingCardRewards) return state.self.hand.map(cardItem);
    if (state.phase === 'shop' && !state.paused) return shopRows();
    if ((state.phase === 'reward' || eventRewards) && !state.paused) {
      const rows = [];
      for (const group of groups) {
        const status = rewardStatus(group);
        if (status === '已领取' || status === '已跳过') {
          const goldClaim = status === '已领取' && group.claims.some(row => row.action?.type === 'goldReward');
          rows.push({ id: `done:${group.key}`, label: goldClaim ? group.title : `${group.title}  ${status}` });
          continue;
        }
        if (group.kind !== 'card') {
          // §F: a reward with nothing to choose is claimed by its own row; the
          // claim button is the confirmation, so there is no second dialog.
          const claim = group.claims[0] ?? group.others[0];
          const lead = claim ?? group.skips[0];
          rows.push({ id: `claim:${group.key}`, label: group.title, action: lead?.action, group: group.key, skipped: !claim && Boolean(group.skips[0]) });
          for (const row of group.others.slice(claim === group.others[0] ? 1 : 0)) rows.push({ ...row, label: `　${row.label}`, group: group.key });
          continue;
        }
        const open = rewardOpen === group.key;
        rows.push({ id: group.key, label: `${open ? '▾' : '▸'} ${group.title}`, group: group.key, open });
        if (!open) continue;
        // Picking the card is the claim: no separate 领取 row, and the way past a
        // card reward is 跳过剩余奖励并离开 at the end of the list.
        for (const row of group.candidates) rows.push({ ...row, fullLabel: row.label, label: `　${optionLabel(row).replace(/^奖励 \d+：/, '')}`, candidate: true, group: group.key });
        for (const row of group.others) rows.push({ ...row, label: `　${row.label}`, group: group.key });
      }
      if (eventRewards) rows.push(...state.options.filter(row => !REWARD_TYPES.includes(row.action?.type) && !nestedCardReward(row)));
      if (!eventRewards || groups.some(group => group.skips.length)) {
        rows.push(rows.length ? { id: 'skipAll', label: '跳过剩余奖励并离开' }
          : { id: 'rewardDone', label: state.players.length > 1 ? '奖励已结算 · 等待队友' : '奖励已结算 · 等待继续' });
      }
      return rows;
    }
    if(state.phase==='map' && !state.paused && state.mapView?.nodes?.length)return [{id:'openMap',label:'打开地图'}];
    return state.options.map(optionItem);
  }
  function anchor() {
    const rows = items(), at = rows.findIndex(row => row.id === selected);
    index = at >= 0 ? at : Math.max(0, Math.min(Number.isFinite(index) ? index : 0, rows.length - 1)); selected = rows[index]?.id;
  }
  function accept(s) {
    if (closed) return;
    if (actionQueue.accept(s)) return;
    if (s?.type === 'ROOM_CHAT') { chat.accept(s); return; }
    // A phase this build does not know means the server moved ahead of the
    // extension: open it read only instead of refusing the whole state.
    const unknownPhase = typeof s?.phase === 'string' && !Object.hasOwn(phases, s.phase);
    if (s?.protocol !== PROTOCOL) { synced=false; note=VERSION_ERROR; changed(); throw new Error(VERSION_ERROR); }
    if (s.features?.actionSync !== true) throw new Error('服务器不支持动作核对，请升级 Spire 后端。');
    if (!wellFormed(s, !unknownPhase) || !(s.self.id === ctx.user.id || s.features?.delegation === true && s.actorId === ctx.user.id && s.delegation?.status === 'active' && s.delegation.delegateId === ctx.user.id && s.delegation.ownerId === s.self.id) || s.roomId !== roomId) { synced=false; throw new Error('游戏状态与客户端不兼容。'); }
    // An older snapshot must not clear the read-only guard before it is discarded:
    // check the revision first, then update anything derived from the state.
    if (state && s.revision < state.revision) return;
    unsupported = unknownPhase ? s.phase : undefined;
    if ((state?.pendingChoice?.id ?? state?.pendingDecision?.id) !== (s.pendingChoice?.id ?? s.pendingDecision?.id)) {
      picked.clear();
      if (s.pendingChoice || s.pendingDecision) {
        choiceReturn ??= {selected,index,tab}; selected=undefined;index=0;tab=0;
      } else {
        if (choiceReturn && s.phase==='combat' && state?.phaseId===s.phaseId) ({selected,index,tab}=choiceReturn);
        choiceReturn=undefined;
      }
    }
    if (s.pendingChoice) {
      const candidates = new Set(s.options.map(row => row.pick).filter(Boolean));
      for (const id of picked) if (!candidates.has(id)) picked.delete(id);
      while (picked.size > s.pendingChoice.maximum) picked.delete([...picked].at(-1));
    }
    if (s.pendingDecision) {
      const candidates = new Set(s.options.flatMap(row => row.action?.selections ?? []));
      for (const id of picked) if (!candidates.has(id)) picked.delete(id);
    }
    if (state?.mapView?.current !== s.mapView?.current || state?.act?.index !== s.act?.index) {
      mapFocus=undefined; mapAnchor=undefined; mapScroll=undefined;
    }
    if (state?.phaseId !== s.phaseId || state?.phase !== s.phase) { shopGroup = ''; shopTop = 0; shopPositions.clear(); unaffordableShopIds.clear(); }
    if (state?.phaseId !== s.phaseId || state?.paused !== s.paused) {
      targeting = undefined; modal = undefined; mapOpen=undefined; pileView=undefined;pileReturn=undefined;focusRegion='action';focusIndex=0;hovered=undefined; selected = undefined; index = 0; tab = 0;
      rewardLog = new Map(); rewardOpen = undefined; rewardPick = new Map(); skipQueue = []; skipKnown = new Set(); skipArmed = false;
    }
    if (s.leaseId) { leaseId = s.leaseId; synced = true; }
    const revisionChanged=state?.revision!==s.revision;
    const moved = animate && revisionChanged ? pileChange(state, s) : undefined;
    state = s; loading = false;
    if (s.readOnly) note = '旁观模式 · Esc → 存档托管，可收回控制权';
    else if (s.delegation) note = '代玩模式 · 操作原角色，Esc → 存档托管';
    if (moved) startMotion(moved); else if (s.phase !== 'combat') stopMotion();
    if(revisionChanged){hovered=undefined;}
    focusIndex=Math.max(0,Math.min(focusIndex,regionItems(focusRegion).length-1));
    if(!['action','controls'].includes(focusRegion)&&!regionItems(focusRegion).length)focusRegion='action';
    if(modal?.upgradePicker && revisionChanged)void hoverUpgrade();
    if (modal?.validFor && !modal.validFor(s)) { modal=undefined; selected=undefined; index=0; note='奖励已失效，请重新选择。'; }
    if (note.startsWith('已连接') || note.startsWith('连接中断')) note = '';
    // The chained claim waits for the pick to be confirmed, then submits the exact
    // queued reward. It runs after this state settles, so it never races the lease.
    const next = chainStep(s);
    const generation = connectionGeneration;
    if (next) setTimeout(() => { if (!closed && generation === connectionGeneration) void submit(next); }, 0);
    if (skipQueue.length || skipKnown.size) setTimeout(() => { if (closed || generation !== connectionGeneration) return; const step = skipStep(state); if (step) void submit(step); else changed(); }, 0);
    // A mark is display only: a reward the server still offers is not settled, so
    // a failed claim or skip corrects itself on the next state.
    if (rewardLog.size) for (const group of rewardGroups()) if (rewardLog.has(group.key)) rewardLog.delete(group.key);
    anchor(); changed(); actionQueue.ready();
  }
  async function guard(fn) {
    if (busy || closed || ctx.signal.aborted) return;
    const generation = connectionGeneration;
    busy = true; changed();
    try { await fn(); }
    catch (e) { if (!closed && !ctx.signal.aborted && generation === connectionGeneration) note = errorText(e); }
    finally { if (!closed && generation === connectionGeneration) { busy = false; loading = false; changed(); } }
  }
  async function loadRooms() {
    const generation = connectionGeneration;
    loading = true;
    let result;
    try { result = await ctx.request(BASE); }
    catch (e) { if (e?.status === 404) throw new Error('服务器尚未安装或启用 Spire 后端模块。'); throw e; }
    if (closed || generation !== connectionGeneration) return;
    if (result?.protocol !== PROTOCOL) { synced=false; serverProtocol=undefined; throw new Error(VERSION_ERROR); }
    if (!Array.isArray(result.rooms)) throw new Error('游戏房间列表无效。');
    serverProtocol = result.protocol; rooms = result.rooms; anchor(); loading = false;
  }
  function connect(id) {
    if (closed || ctx.signal.aborted) return;
    const generation = ++connectionGeneration;
    busy = false;
    actionQueue.stop(); chat.reset(); connection?.close(); characterConfirmed=!!navigation.configured;mapOpen=undefined; roomId = id; state = undefined; leaseId = undefined; synced = false; loading = true; tab = 0; selected = undefined;
    connection = ctx.connect(`/ws/games/spire/rooms/${id}?roomChat=1`, value => { if (!closed && generation === connectionGeneration) accept(value); }, connected => {
      if (closed || generation !== connectionGeneration) return;
      online = connected; synced = false;
      if (!connected) { actionQueue.disconnect(); note = '连接中断，正在重连；操作已暂停。'; }
      else note = '已连接，等待服务器状态。';
      changed();
    }, { onReplaced() {
      if (closed || generation !== connectionGeneration) return false;
      if (!state?.delegation && !delegation.pending()) return false;
      actionQueue.stop();
      if (!delegation.pending()) {
        if (navigation.onHome) void leaveToHome();
        else { note = '控制权已变化，请退出后重新进入。'; changed(); }
      }
      return true;
    } });
  }
  async function submit(action) {
    if (!canAct() || !leaseId || !roomId) return;
    if (actionQueue.enqueue({ ...action, phaseId: action.phaseId ?? state.phaseId })) modal = undefined;
  }
  async function leaveToHome() {
    stopGame();
    // Closing the controller pauses the room on the server.
    await navigation.onHome?.();
  }
  // The shortcut table by topic, as rows of a list: topic names, then key and meaning.
  function helpLines() {
    const keyWidth = Math.max(...HELP_GROUPS.flatMap(([, rows]) => rows.map(([key]) => displayWidth(key)))) + 2;
    return [...HELP_GROUPS.flatMap(([name, rows]) => [{ label: paint(ACCENT, name, TEXT), separator: true },
      ...rows.map(([key, text]) => ({ label: '  ' + paint('\x1b[1m', pad(key, keyWidth), '\x1b[22m') + text }))]),
      ...wrapCardText(HELP_NOTE, Math.max(1, columns - 4)).map(label => ({ label, separator: true }))].map((row, i) => ({ id: `help${i}`, ...row }));
  }
  /** The keys of the screen as it is now, for the hint row at the bottom. */
  function hintPairs() {
    if (chat.composing()) return [['Enter', '发送'], ['Esc', '取消'], ['/sl', '恢复场景']];
    if (targeting) return [['Enter', '确认目标'], ['←→', '切换'], ['Esc', '取消']];
    if (modal?.battleLog) return [['←→', '翻页'], ['↑↓', '浏览'], ['Esc', '返回']];
    if (modal?.shortcuts) return [['↑↓', '浏览'], ['Esc', '返回']];
    if (modal?.textDetail || modal?.detail) return [['↑↓', '浏览'], ['Esc', '返回']];
    if (modal?.upgradePicker) return [['Enter', '确认'], ['↑↓', '选择'], ['?', '说明'], ['Esc', '返回']];
    if (modal) return [['Enter', '确认'], ['↑↓', '选择'], ['Esc', '返回']];
    if (pileView) return [['↑↓', '浏览'], ['Esc', '返回']];
    if (!state) return [['Enter', '确认'], ['R', '刷新'], ['Esc', '返回']];
    if (mapNavigation()) return [[state.phase === 'map' ? 'Enter' : 'M', state.phase === 'map' ? '投票' : '收起'], ['方向键', '移动'], ['?', '快捷键'], ['Esc', '收起']];
    if (state.readOnly) return [['D', '牌组'], ['V', '日志'], ['T', '聊天'], ['Esc', '托管菜单']];
    if (state.phase === 'defeat' && !state.delegation) return [['Esc', '返回主界面']];
    if (shopView()) return [['Enter', '购买'], ['Tab', '分类'], ['?', '快捷键'], ['Esc', '菜单']];
    const picking = items().some(row => row.pick);
    const keys = state.phase === 'combat' ? [['Enter', '打出'], ['方向键', '移动'], ['E', '结束回合']]
      : picking ? [['空格', '勾选'], ['Enter', '确认'], ['方向键', '移动']]
      : [['Enter', '确认'], ['方向键', '移动'], ...(state.phase === 'lobby' || state.paused ? [['T', '聊天']] : state.mapView?.nodes?.length ? [['M', '地图']] : [])];
    return [...keys, ['?', '快捷键'], ['Esc', '菜单']];
  }
  function choose(title, candidates, acceptChoice, options = {}) {
    // Topic rows are headings, so the cursor starts on the first real row.
    const first = Math.max(0, candidates.findIndex(row => !row.separator));
    modal = { title, items: candidates, accept: acceptChoice, previousSelected: selected, previousIndex: index, previousPage: listPage, ...options }; listPage = 0; index = first; selected = candidates[first]?.id; changed();
  }
  function upgradePreview(cardId, source) {
    const preview = state?.upgradePreviews?.[source]?.[cardId];
    if (!preview) throw new Error('这张牌不能升级。');
    return preview;
  }
  function hoverUpgrade() {
    if (!modal?.upgradePicker) return;
    const row=items()[index]; if (!row?.card) return;
    const body=state?.upgradePreviews?.deck?.[row.id];
    modal.upgradeDetail=body ? `升级前：${body.before.name} ${cardCost(body.before)} ${body.before.description}\n升级后：${body.after.name} ${cardCost(body.after)} ${body.after.description}` : '这张牌不能升级。';
    changed();
  }
  function deckChoice(mode, callback) {
    const cards = state.self.deck.filter(c => mode === 'deckUpgrade' ? (!c.upgraded && !['status', 'curse', 'quest'].includes(c.kind)) : mode === 'deckEnchant' ? (c.canSown !== false && !c.sown && !c.inky && !c.enchantment && !['status', 'curse', 'quest'].includes(c.kind)) : c.removable !== false);
    if (!cards.length) { note = '没有符合条件的牌。'; changed(); return; }
    choose('选择牌组中的牌', cards.map(cardItem), row => {
      if (mode === 'deckUpgrade') { callback(row.id); return; }
      callback(row.id);
    }, { upgradePicker: mode === 'deckUpgrade', upgradeDetail: mode === 'deckUpgrade' ? '正在读取升级预览…' : undefined });
    if(mode==='deckUpgrade')void hoverUpgrade();
  }
  function previewUpgrade(cardId, source) {
    if (!roomId || !canAct() || !cardId) return;
    try {
      const body = upgradePreview(cardId, source);
      const line = card => `${card.name}  ${cardCost(card)}  ${card.description}`;
      const rows = [
        { id:'before', label:`升级前：${line(body.before)}` },
        { id:'after', label:`升级后：${line(body.after)}` },
        { id:'back', label:'返回' },
      ];
      choose('升级预览', rows, () => {
        modal=undefined; anchor(); changed();
      });
    } catch (error) { note=errorText(error); changed(); }
  }
  function cardAction(c) {
    if (!canAct() || state.paused || me()?.done || me()?.hp <= 0) return;
    const action = { type: 'play', card: c.id, phaseId: state.phaseId };
    const send = () => {
      // A single target is picked on the battlefield itself, never from a list.
      if (c.target === 'enemy') beginTargeting({ ...action, label: c.name }, 'enemy');
      else if (c.target === 'ally') beginTargeting({ ...action, label: c.name }, 'ally');
      else void submit(action);
    };
    const eligible = state.self.hand.filter(x => x.id !== c.id && (c.choice !== 'upgrade' || (!x.upgraded && !['status', 'curse', 'quest'].includes(x.kind))));
    if (c.choice && eligible.length) choose(c.choice === 'upgrade' ? '选择升级的手牌' : '选择消耗的手牌', eligible.map(cardItem), row => {
      action.choice = row.id;
      send();
    });
    else send();
  }
  // The keyboard branches and clicks move the same state through these, so the
  // two input paths cannot drift apart.
  const navKinds=new Set(['item','equipment','entry','entity','pile','endTurn','inspect','node']);
  function focusKey(hit){return `${hit.kind}:${hit.region??''}:${hit.id}`;}
  function currentHit(){
    if(focusRegion==='action')return hits.find(h=>mapNavigation()?h.kind==='node'&&h.id===(mapFocus??state.mapView.current):h.kind==='item'&&h.id===items()[index]?.id);
    if(focusRegion==='units')return hits.find(h=>h.kind==='entity'&&String(h.id)===String(focusItem()?.id));
    if(focusRegion==='entries')return hits.find(h=>h.kind==='entry'&&h.id===focusItem()?.id);
    if(focusRegion==='controls')return hits.find(h=>focusKey(h)===focusControl);
    return hits.find(h=>h.kind==='equipment'&&h.region===focusRegion&&h.index===focusIndex);
  }
  function selectHit(hit){
    hovered=undefined;
    if(hit.kind==='item'){focusRegion='action';moveTo(items().findIndex(row=>row.id===hit.id));}
    else if(hit.kind==='node'){focusRegion='action';mapFocus=hit.id;mapAnchor=hit.id;mapScroll=undefined;}
    else if(hit.kind==='equipment'){focusRegion=hit.region;focusIndex=hit.index;}
    else if(hit.kind==='entity'){focusRegion='units';focusIndex=regionItems('units').findIndex(row=>String(row.id)===String(hit.id));}
    else if(hit.kind==='entry'){focusRegion='entries';focusIndex=regionItems('entries').findIndex(row=>row.id===hit.id);}
    else{focusRegion='controls';focusControl=focusKey(hit);}
    changed();
  }
  function spatialMove(direction,skipLocal=false){
    hovered=undefined;
    screen.render(columns,height);
    if(!skipLocal && focusRegion==='action' && !mapNavigation() && ['up','down'].includes(direction)){
      const next=index+(direction==='up'?-1:1);
      if(next>=0&&next<items().length){moveTo(next);return;}
    }
    if(['relics','potions'].includes(focusRegion)&&['left','right'].includes(direction)){
      const next=focusIndex+(direction==='left'?-1:1);
      if(next>=0&&next<regionItems(focusRegion).length){focusIndex=next;changed();return;}
    }
    const adjacentEquipment=focusRegion==='relics'&&direction==='down'?'potions':focusRegion==='potions'&&direction==='up'?'relics':undefined;
    if(adjacentEquipment && regionItems(adjacentEquipment).length){
      focusRegion=adjacentEquipment;focusIndex=Math.min(focusIndex,regionItems(adjacentEquipment).length-1);changed();return;
    }
    if(focusRegion==='units'){
      const enemies=state.enemies.filter(e=>e.hp>0||e.awaitingRevive),at=enemies.findIndex(e=>String(e.id)===String(focusItem()?.id));
      const vertical=true;
      if(at>=0 && (vertical?['up','down']:['left','right']).includes(direction)){
        const next=at+(['up','left'].includes(direction)?-1:1);
        if(next>=0&&next<enemies.length){focusIndex=regionItems('units').findIndex(row=>String(row.id)===String(enemies[next].id));changed();return;}
      }
    }
    const current=currentHit()??hits.find(h=>navKinds.has(h.kind));
    if(!current)return;
    const vertical=['up','down'].includes(direction);
    // Vertical navigation follows the left edge of the content, not the centre
    // of a wide hit area. Otherwise short potion/pile labels lose to farther rows.
    const point=h=>({x:vertical?h.col:h.col+Math.min(Number.isFinite(h.width)?h.width:columns,24)/2,y:h.row+(h.height-1)/2});
    const origin=point(current),sign=['up','left'].includes(direction)?-1:1;
    let candidates=hits.filter(h=>navKinds.has(h.kind)&&h!==current&&!(h.kind==='item'&&items().find(r=>r.id===h.id)?.separator));
    if(focusRegion==='action' && (skipLocal||['up','down'].includes(direction)))candidates=candidates.filter(h=>h.kind!==(mapNavigation()?'node':'item'));
    const score=h=>{const p=point(h),forward=sign*(vertical?p.y-origin.y:p.x-origin.x),cross=Math.abs(vertical?p.x-origin.x:p.y-origin.y);return {h,forward,cross,score:forward+cross*(vertical?1:100)};};
    const choices=candidates.map(score).filter(p=>p.forward>0).sort((a,b)=>a.score-b.score);
    if(choices.length){selectHit(choices[0].h);return;}
    // A boundary wraps to the opposite edge, keeping every region reachable.
    const wrap=candidates.map(score).sort((a,b)=>a.forward-b.forward||a.cross-b.cross);
    if(wrap.length)selectHit(wrap[0].h);
  }
  function showFocusedDetail(){
    const text=detailText(true),title=focusItem()?.name??'详情';
    choose(title,wrapText(text,Math.max(1,columns-4)).map((label,i)=>({id:String(i),label})),()=>changed());
  }
  function activateFocus(){
    if(focusRegion==='action'){confirm();return;}
    const row=focusItem(),hit=currentHit();
    if(focusRegion==='potions')potionMenu(row);
    else if(focusRegion==='entries')openPile('deck');
    else if(focusRegion==='units' && state?.phase==='combat')toggleUnit(row?.id);
    else if(focusRegion==='units')showFocusedDetail();
    else if(focusRegion==='relics')showFocusedDetail();
    else if(hit?.kind==='pile')openPile(hit.id);
    else if(hit?.kind==='endTurn')endTurn();
    else if(hit?.kind==='inspect')void inspectPlayer(hit.id);
  }
  function paintFocus(frame){
    if(targeting){
      const target=hits.find(h=>h.kind==='entity'&&String(h.id)===String(targeting.id));
      if(target&&frame[target.row])frame[target.row].focusColumn=target.col;
      return;
    }
    const hit=modal ? hits.find(h=>h.kind==='item'&&h.id===items()[index]?.id) : hovered ? hits.find(h=>hovered.region==='units'?h.kind==='entity'&&String(h.id)===String(hovered.row.id):hovered.region==='controls'?focusKey(h)===hovered.row.id:hovered.region==='entries'?h.kind==='entry'&&h.id===hovered.row.id:h.region===hovered.region&&h.id===hovered.row.id) : currentHit();if(!hit||!frame[hit.row])return;
    frame[hit.row].focusColumn=hit.col;
    if(!modal&&!hovered&&focusRegion==='action'&&mapNavigation())return;
    // Highlight the selected hit rectangle, leaving all content positions fixed.
    // A unit's unfolded status rows stay in their own colours; only its name row is highlighted.
    const last=hit.kind==='entity' ? hit.row+1 : hit.row+(hit.height??1);
    for(let row=hit.row;row<Math.min(frame.length,last);row++){
      const text=frame[row].text;
      // cut() closes a trimmed coloured span with a reset the source text does not
      // have; drop it so the slices below line up with the original text.
      let left=cut(text,hit.col); if(!text.startsWith(left))left=left.slice(0,-RESET.length);
      const rest=text.slice(left.length); let body=cut(rest,Math.min(hit.width,columns)); if(!rest.startsWith(body))body=body.slice(0,-RESET.length);
      const restore=frame[row].tone==='muted'?MUTED:TEXT;
      // The focus colour replaces the row's own colours except buff / debuff
      // statuses, which keep theirs and hand back to the focus colour.
      const focus=frame[row].dim ? MUTED : items()[index]?.danger ? DANGER+DANGER_SELECTED : ACCENT;
      const shown=body.replace(/\x1b\[[0-9;]*m/g,code=>code===BUFF||code===DEBUFF?code:focus);
      frame[row].text=left+focus+'\x1b[1m'+shown+'\x1b[22m'+restore+rest.slice(body.length);
    }
  }
  // Moving never arms 跳过剩余奖励并离开; only its first confirm does.
  function moveTo(next) { const list = items(); index = Math.max(0, Math.min(Number.isFinite(next) ? next : 0, list.length - 1)); selected = list[index]?.id; skipArmed = false; changed();if(modal?.upgradePicker)void hoverUpgrade(); }
  function pageDetail(delta) { modal.detailOffset = Math.max(0, (modal.detailOffset ?? 0) + delta); changed(); }
  function clickRow(id) {
    focusRegion='action';hovered=undefined;
    const list = items(), at = list.findIndex(row => row.id === id);
    // A pushed state can replace the list under a click: re-anchor and never let
    // the cursor clamp confirm a row the player never saw.
    if (at < 0) { anchor(); changed(); return; }
    index = at; selected = id;
    confirm();
  }
  function intentLines(v, enemy, state, compact = false) {
    const symbols={attack:'ATK',defend:'⛨',buff:'↑',debuff:'↓',status:'↓',cardDebuff:'↓',heal:'+',summon:'⊕',sleep:'zZ',stun:'…',escape:'↗',unknown:'?',deathBlow:'ATK'};
    // Official intent titles (intents.json).
    const names={attack:'攻势',defend:'守势',buff:'强化',debuff:'策略',status:'策略',cardDebuff:'恶意',heal:'回复',summon:'召唤',sleep:'沉睡',stun:'击晕',escape:'懦弱',unknown:'未知',deathBlow:'濒死一击'};
    const declared=enemy.intentDisplay ?? (v?.damage?[{type:'attack',damage:v.damageByTarget?.[seatId()]??v.damage,hits:v.hits??1}]:[{type:v?.sleep?'sleep':'unknown'}]);
    if (compact) return declared.map(part=>part.type==='hidden'?'?':`${part.type==='attack'?'ATK':names[part.type]??'未知'}${part.damage!==undefined?` ${part.damage}${(part.hits??1)>1?`×${part.hits}`:''}`:''}${part.count!==undefined?` ${part.count}`:''}`);
    return declared.map(part=>part.type==='hidden'?'?':`${symbols[part.type]??'?'}${part.type==='attack'?'':' '}${part.type==='attack'?'':names[part.type]??'未知'}${part.damage!==undefined?` ${part.damage}${(part.hits??1)>1?`×${part.hits}`:''}`:''}${part.count!==undefined?` ${part.count}`:''}`);
  }

  function hoverRow(id) {
    focusRegion='action';
    const at = items().findIndex(row => row.id === id);
    if (at >= 0) moveTo(at);
  }
  // --- battlefield ------------------------------------------------------------
  // One list row per creature is the only battlefield layout.
  const debuffPowers = new Set(['weak', 'vulnerable', 'frail', 'poison', 'doom', 'constrict', 'hang', 'ringing', 'hex',
    'dampen', 'tangled', 'noDraw', 'noBlock', 'slow', 'smoggy', 'chainsOfBinding', 'shrink', 'paperCuts', 'sandpit',
    'slowCards', 'battlewornDummyTimeLimit', 'steamEruption', 'witheringCounters']);
  function splitPowers(powers) {
    const buffs = [], debuffs = [];
    for (const [key, value] of Object.entries(powers ?? {})) {
      if (!value) continue;
      const name = powerNames[key] ?? '未知状态';
      const signed = ['strength', 'dexterity', 'focus'].includes(key) ? (value > 0 ? `+${value}` : String(value)) : String(value);
      (debuffPowers.has(key) ? debuffs : buffs).push(`${name} ${signed}`);
    }
    return [buffs, debuffs];
  }
  // Official wording, one sentence per instance the server details (bombs, boulders, …).
  function describePower(creature, key, amount, values = {}) {
    const context = { amount, owner: creature.name, isPlayer: state?.players.includes(creature), multiplayer: (state?.players.length ?? 1) > 1 };
    const rows = creature.powerDetails?.[key]?.length ? creature.powerDetails[key] : [{}];
    const texts = rows.map(row => powerDescription(catalogMetadata.powerDescriptions, key, { ...context, values: { ...values, ...row } })).filter(Boolean);
    return texts.length ? texts.join('') : undefined;
  }
  function powerEntries(creature) {
    const monologues = creature.monologueInstances ?? [];
    return Object.entries(creature.powers ?? {}).filter(([, value]) => value !== 0).flatMap(([key, value]) =>
      key === 'monologue' && monologues.length
        ? monologues.map(record => ({ key, text: `独白 ${record.applied}`,
          description: describePower(creature, key, record.applied, { StrengthPower: record.strength, StrengthApplied: record.applied }) }))
        : [{ key, text: `${powerNames[key] ?? '未知状态'} ${value}`, description: describePower(creature, key, value) }]);
  }
  // A block wraps rather than cuts: several intent fields join to a line longer
  // than any column, and the plan asks for every field to stay readable.
  function hardSplit(text, width) {
    const out = []; let line = '';
    for (const character of text) {
      if (displayWidth(line) + (wideChar(character) ? 2 : 1) > width) { out.push(line); line = ''; }
      line += character;
    }
    if (line) out.push(line);
    return out;
  }
  function wrapText(text, width) {
    const lines = []; let line = '';
    for (const part of String(text).split(' · ')) {
      for (const piece of displayWidth(part) > width ? hardSplit(part, width) : [part]) {
        if (!line) line = piece;
        else if (displayWidth(line) + 3 + displayWidth(piece) <= width) line += ' · ' + piece;
        else { lines.push(line); line = piece; }
      }
    }
    if (line) lines.push(line);
    return lines.length ? lines : [''];
  }
  function showPowerDetail(creature) {
    const entries = powerEntries(creature);
    const lines = entries.length ? entries.map(entry => entry.text + (entry.description ? `：${entry.description}` : '')) : ['无状态'];
    const rows = lines.flatMap(line => wrapCardText(line, Math.max(1, columns - 4)));
    choose(`${creature.name} · 状态详情`,
      rows.map((label, i) => ({ id: `status${i}`, label })), () => { anchor(); changed(); }, { textDetail: { lines, width: columns } });
  }
  function showCardDetail(row) {
    const cards = row.card ? [row.card] : optionCards(row);
    const text = cards ? cards.map(card => `${card.name} ${cardCost(card)} · ${cardDescription(card, true, true)}`).join('\n') : optionLabel(row, true);
    const lines = String(text).split('\n');
    const rows = lines.flatMap(line => wrapCardText(line, Math.max(1, columns - 4)));
    const previousModal = modal;
    choose(`${cards?.[0]?.name ?? '卡牌'} · 详情`,
      rows.map((label, i) => ({ id: `detail${i}`, label })), () => { modal = previousModal; anchor(); changed(); },
      { previousModal, textDetail: { lines, width: columns, card: true } });
  }
  function toggleUnit(id) {
    expandedUnit = expandedUnit === String(id) ? undefined : String(id);
    changed();
  }
  function compactLines(creature, arena, width, room = 1) {
    const head = creature.name + (arena === 'ally' && creature.characterName ? ' · ' + creature.characterName : '') + (creature.done ? ' ✓' : '');
    const intent = arena === 'enemy' ? intentLines(creature.intent, creature, state, true).join('+') : '';
    const entries = powerEntries(creature);
    const resources = arena === 'ally' ? resourcesText(creature, creature.id !== seatId()) : '';
    const summary = [head, healthText(creature), intent, resources].filter(Boolean).join(' · ');
    const inline = entries.length > 0 && displayWidth(summary + ' · ' + entries.map(entry => entry.text).join(' · ')) <= width;
    const stateLabel = inline
      ? entries.map(entry => paint(debuffPowers.has(entry.key) ? DEBUFF : BUFF, entry.text)).join(' · ')
      : entries.length ? '状态 ' + entries.length + ' 项' : '';
    const full = [summary, stateLabel].filter(Boolean).join(' · ');
    let line = full;
    if (displayWidth(full) > width) {
      // Reserve the creature's health and attack before shortening its name.
      const stats = 'HP' + hpText(creature) + ' ⛨' + (creature.block ?? 0);
      const stateRoom = stateLabel ? displayWidth(stateLabel) + 3 : 0;
      const minimumName = Math.min(6, displayWidth(creature.name));
      const tail = intent ? cut(intent, Math.max(0, width - displayWidth(stats) - stateRoom - minimumName - 4)) : '';
      const nameRoom = Math.max(1, width - displayWidth(stats) - displayWidth(tail) - stateRoom - (tail ? 4 : 1));
      line = cut(creature.name, nameRoom) + ' ' + stats + (tail ? ' · ' + tail : '');
      if (stateLabel) line += ' · ' + stateLabel;
      if (resources && displayWidth(line + ' · ' + resources) <= width) line += ' · ' + resources;
    }
    const lines = [cut(line, width)];
    if (!inline && entries.length && expandedUnit === String(creature.id) && room > 1) {
      const detail = wrapText(entries.map(entry => entry.text).join(' · ') || '无状态', Math.max(1, width - 2));
      const visible = detail.slice(0, room - 1);
      if (detail.length > visible.length) visible[visible.length - 1] = cut(visible.at(-1), Math.max(1, width - 3)) + '…';
      const colours = new Map(entries.map(entry => [entry.text, debuffPowers.has(entry.key) ? DEBUFF : BUFF]));
      const tint = line => line.split(' · ').map(piece => colours.has(piece.replace(/…$/, '')) ? paint(colours.get(piece.replace(/…$/, '')), piece) : piece).join(' · ');
      lines.push(...visible.map((line, i) => (i ? '  ' : '└ ') + tint(line)));
    }
    return lines;
  }
  function allyBlock(player, width) {
    const resources = resourcesText(player);
    return [`${player.name}${player.characterName ? ` · ${player.characterName}` : ''}${player.done ? ' ✓' : ''}`,
            ...statLines(player, resources ? [resources] : [], width)];
  }
  function mapDetailText(view, data) {
    const node = data.byId.get(mapFocus ?? view.current);
    return node ? '选中：' + node.type + ' · ' + mapCode(node) : '';
  }
  // The dedicated shop never hides a forced choice or a nested reward.
  const shopOffers = () => state?.phase === 'shop' && !state.paused && !state.pendingChoice && !state.pendingDecision
    && state.options.every(row => row.shop || row.action?.type === 'continue');
  const shopView = () => shopOffers() && !modal && !pileView && !targeting && !mapNavigation();
  function shopRows() {
    if (!shopOffers()) return state.options;
    return [...shopGoods(state.options, shopGroup), ...state.options.filter(row => row.action?.type === 'continue')];
  }
  function switchShop(group) {
    if (!shopView() || !SHOP_GROUPS.some(([id]) => id === group)) return;
    shopPositions.set(shopGroup, { selected, index, top: shopTop });
    shopGroup = group;
    const position = shopPositions.get(group);
    selected = position?.selected; index = position?.index ?? 0; shopTop = position?.top ?? 0;
    focusRegion = 'action'; hovered = undefined; note = ''; anchor(); changed();
  }
  function shopDetail() {
    const row = items()[index];
    if (!row?.shop) return;
    const item = row.shop;
    choose(item.name, [{ id: 'back', label: '返回商店' }], () => changed(), {
      shopDetail: true, detailOffset: 0,
      detail: `${item.description}\n售价：${item.price} 金币${item.sale ? ' · 半价' : ''}\n当前金币：${me()?.gold ?? 0}`,
    });
  }
  // --- rewards (§F) -----------------------------------------------------------
  const REWARD_TYPES = ['reward', 'customReward', 'customRelicReward', 'goldReward', 'claimPotion', 'skipPotion', 'rewardRemove', 'skipRemoval'];
  function nestedCardReward(row, snapshot = state) {
    const decision = snapshot?.pendingDecision, action = row.action;
    if (decision?.kind !== 'rewardSet' || decision.maximum !== 1 || action?.type !== 'decide'
        || action.decisionId !== decision.id || action.selections?.length !== 1) return;
    const identity = /^(reward:\d+):(.+)$/.exec(action.selections[0]);
    if (identity) return { reward: identity[1], card: identity[2], decision: decision.id };
  }
  function rewardGroups() {
    const groups = new Map();
    for (const row of state.options ?? []) {
      const action = row.action ?? {};
      const type = action.type;
      const nested = nestedCardReward(row);
      if (!REWARD_TYPES.includes(type) && !nested) continue;
      const key = nested ? nested.decision + ':' + nested.reward : action.reward ?? action.potion ?? (type === 'reward' ? 'reward:phase' : type === 'rewardRemove' || type === 'skipRemoval' ? 'removal' : row.id);
      if (!groups.has(key)) groups.set(key, { key, claims: [], skips: [], others: [], candidates: [] });
      const group = groups.get(key);
      const card = nested?.card ?? action.card;
      const skip = type === 'skipPotion' || type === 'skipRemoval' || card === 'skip' || action.choice === 'skip';
      const alternative = card === 'reroll' || card === 'sacrifice';
      if ((type === 'reward' || type === 'customReward' || nested) && !skip && !alternative) group.candidates.push(row);
      else if (skip) group.skips.push(row);
      else if (action.choice === 'claim' || action.card === 'claim' || type === 'rewardRemove') group.claims.push(row);
      else group.others.push(row);
    }
    for (const group of groups.values()) {
      group.title = group.candidates.length ? '卡牌奖励'
        : (group.claims[0] ?? group.others[0] ?? group.skips[0] ?? { label: group.key }).label;
      group.kind = group.candidates.length ? 'card' : 'other';
    }
    return [...groups.values()];
  }
  function rewardStatus(group) {
    const logged = rewardLog.get(group.key);
    if (logged) return logged;
    return group.kind === 'card' ? '待选择' : '待领取';
  }
  // Skipping the rest runs the server's own skip rows in order. A row that is gone
  // was already handled; a reward that was not in the confirmed list stops the
  // queue, because skipping something new is exactly what must not happen.
  function skipStep(snapshot) {
    const rows = snapshot.options ?? [];
    const fresh = rows.filter(row => (REWARD_TYPES.includes(row.action?.type) || nestedCardReward(row, snapshot)) && !skipKnown.has(row.id));
    if (fresh.length) { skipQueue = []; skipKnown = new Set(); note = '奖励清单有变化，请重新查看后再跳过。'; return undefined; }
    while (skipQueue.length) {
      const row = skipQueue.shift();
      const current = rows.find(option => option.id === row.id);
      if (!current) continue;
      return { ...current.action, phaseId: snapshot.phaseId };
    }
    return undefined;
  }
  // --- chest claim chain (§G) --------------------------------------------------
  const claimRows = snapshot => (snapshot?.options ?? [])
    .filter(row => row.action?.type === 'customRelicReward' && row.action.card === 'claim');
  // The next step of a single player's chest claim: exactly the reward the pick
  // just queued. Anything else — none, or several — ends the chain with a note
  // instead of a guess.
  function chainStep(snapshot) {
    if (!chain) return undefined;
    if (snapshot.phaseId !== chain.phaseId) { chain = undefined; return undefined; }
    const queued = claimRows(snapshot).filter(row => !chain.before.has(row.id));
    if (!queued.length) { chain = undefined; return undefined; }
    if (queued.length > 1) { chain = undefined; note = '宝箱奖励需要自行确认，请选择要领取的遗物。'; return undefined; }
    chain = undefined;
    return { ...queued[0].action, phaseId: snapshot.phaseId };
  }
  function hitAt(x, y) {
    return hits.filter(hit => hit.row <= y && y < hit.row + hit.height && hit.col <= x && x < hit.col + hit.width)
      .sort((left, right) => left.width * left.height - right.width * right.height)[0];
  }
  // The divination board. The server sends only the cells a player has looked
  // at, so the client cannot draw what it has not earned and has no layout of
  // its own to keep in step.
  let sphereCursor = { x: 5, y: 5 };
  function sphereView() { return state?.eventProgress?.sphere; }
  function sphereGlyph(cell) {
    if (!cell) return '·';
    if (cell.item === 'Relic') return 'R';
    if (cell.item === 'Potion') return 'P';
    if (cell.item === 'CardReward') return 'C';
    if (cell.item === 'Gold') return '$';
    if (cell.item === 'Curse') return '!';
    return 'o';
  }
  function sphereAt(view, x, y) {
    return (view.cells ?? []).find(cell => cell.x === x && cell.y === y);
  }
  function sphereLines(view) {
    const header = '    ' + Array.from({ length: view.width }, (_, x) => String(x % 10)).join(' ');
    const lines = [header];
    for (let y = 0; y < view.height; y += 1) {
      const cells = [];
      for (let x = 0; x < view.width; x += 1) {
        const here = x === sphereCursor.x && y === sphereCursor.y;
        const glyph = sphereGlyph(sphereAt(view, x, y));
        cells.push(here ? `[${glyph}` : ` ${glyph}`);
      }
      lines.push(`${String(y).padStart(2, ' ')}  ${cells.join('').slice(1)}`);
    }
    return lines;
  }
  function sphereMove(dx, dy) {
    const view = sphereView(); if (!view) return;
    if((dx<0&&sphereCursor.x===0)||(dx>0&&sphereCursor.x===view.width-1)||(dy<0&&sphereCursor.y===0)||(dy>0&&sphereCursor.y===view.height-1)){spatialMove(dx<0?'left':dx>0?'right':dy<0?'up':'down',true);return;}
    sphereCursor = { x: Math.max(0, Math.min(view.width - 1, sphereCursor.x + dx)),
                     y: Math.max(0, Math.min(view.height - 1, sphereCursor.y + dy)) };
    changed();
  }
  function sphereUse() {
    const view = sphereView(); if (!view || view.finished) return;
    void submit({ type: 'sphere', op: 'use', x: sphereCursor.x, y: sphereCursor.y });
  }
  function sphereTool() {
    const view = sphereView(); if (!view || view.finished) return;
    void submit({ type: 'sphere', op: 'tool', tool: view.tool === 'Big' ? 'Small' : 'Big' });
  }
  // Teammate detail. Read only, and paged on the server: the client asks for a
  // page and shows what comes back, so it never holds a second copy of anyone's
  // deck and never has to keep one in step.
  async function inspectPlayer(id, page = 0, atEnd=false) {
    if (!roomId || !canAct()) return;
    await guard(async () => {
      const generation = connectionGeneration;
      const body = await ctx.request(`${BASE}/${roomId}/players/${id}/inspection?page=${page}`);
      if (closed || generation !== connectionGeneration) return;
      const rows = body.rows ?? [];
      const first = body.total === 0 ? 0 : page * (body.pageSize ?? 40) + 1;
      const last = page * (body.pageSize ?? 40) + rows.length;
      const pages = Math.max(1, Math.ceil(body.total / (body.pageSize ?? 40)));
      const previous = modal?.inspection ? {previousSelected:modal.previousSelected, previousIndex:modal.previousIndex, previousPage:modal.previousPage} : undefined;
      choose(`${body.name} · ${first}-${last}/${body.total} · 第 ${page + 1}/${pages} 页`,
        rows.map((row, i) => ({ id: `i${i}`, label: `${row.pile === 'status' ? powerNames[row.key] ?? '未知状态' : row.name ?? row.key}${row.amount !== undefined ? ` ${row.amount}` : ''}${row.description ? `：${row.description}` : ''}${row.upgraded ? ' +' : ''}` })),
        () => { anchor(); changed(); }, { ...previous, inspection: {id,page,pages,total:body.total} });
      if(atEnd)moveTo(modal.items.length-1);
      changed();
    });
  }
  function endTurnState() {
    return state.endTurn;
  }
  // One key, three states. The server decides which applies and why, so the
  // client never has to infer "the turn is resolving" from the phase.
  function endTurn() {
    if (modal || !canAct() || state?.phase !== 'combat' || state.paused) return;
    const control = endTurnState();
    if (control.canUndoEndTurn) { void submit({ type: 'undoEnd', turn: state.turn }); return; }
    if (!control.canEndTurn) return;
    void submit({ type: 'end' });
  }
  function endTurnLabel() {
    const own = me();
    if ((own?.hp ?? 0) <= 0) return `[已倒下 ${state.turn}]`;
    if (state?.phase !== 'combat') return '';
    const control = endTurnState();
    if (control.canUndoEndTurn) return `[E 撤销结束回合 ${state.turn}]`;
    if (control.canEndTurn) return state.paused ? `[等待继续 ${state.turn}]` : `[E 结束回合 ${state.turn}]`;
    return state.paused ? `[等待继续 ${state.turn}]` : `[${control.reason || '等待结算'} ${state.turn}]`;
  }
  function inspectEntity(id) {
    const enemy = (state.enemies ?? []).find(entry => entry.id === id);
    const player = (state.players ?? []).find(entry => String(entry.id) === id);
    if (enemy) choose(enemy.name, [intentLines(enemy.intent, enemy, state, true).join('+') || '（本回合无行动）', `${healthText(enemy)} · ${powersText(enemy.powers)}`].map((label, index) => ({ id: `detail${index}`, label })), () => { anchor(); changed(); });
    else if (player) choose(player.name, [`${healthText(player)} · ${powersText(player.powers)}`].map((label, index) => ({ id: `detail${index}`, label })), () => { anchor(); changed(); });
  }
  // Only the currently aimed entity is emphasized.
  const TINTS = { enemy: 91, ally: 94 };
  const targetTint = arena => `\x1b[${TINTS[arena]}m`;
  const tint = (lines, colour) => lines.map(line=>`${colour}\x1b[1m${line}\x1b[22m\x1b[0m`);
  function framed(lines, width, style) {
    const [left, right] = style === 'current' ? ['║', '║'] : ['│', '│'];
    const [topLeft, topRight, bottomLeft, bottomRight, bar] = style === 'current' ? ['╔', '╗', '╚', '╝', '═'] : ['┌', '┐', '└', '┘', '─'];
    const head = topLeft + bar.repeat(Math.max(0, width - 2)) + topRight;
    const body = lines.map(line => left + pad(cut(line, width - 2), width - 2) + right);
    return [head, ...body, bottomLeft + bar.repeat(Math.max(0, width - 2)) + bottomRight];
  }
  // The pointer and the keyboard move the same target cursor.
  function targetIndex() {
    if (!targeting) return -1;
    const ids = targetIds();
    return Math.max(0, ids.indexOf(targeting.id));
  }
  // AnyPlayer potions include the owner; ally-only cards still exclude self.
  const playerTargets = action => (state.players ?? []).filter(p => p.hp > 0
    && (action?.type === 'potion' || String(p.id) !== String(seatId())));
  function targetIds() {
    if (!targeting) return [];
    return targeting.action && targeting.arena === 'enemy'
      ? (state.enemies ?? []).filter(e => e.hp > 0).map(e => e.id)
      : playerTargets(targeting.action).map(p => String(p.id));
  }
  function beginTargeting(action, arena, title = '选择目标') {
    // Outside combat nothing is drawn to click, and a potion may still be used
    // there, so the list stays the surface for that case alone.
    if (state?.phase !== 'combat') {
      const rows = arena === 'enemy'
        ? (state?.enemies ?? []).filter(e => e.hp > 0).map(e => ({ id: e.id, label: `${e.name} · ${healthText(e)}` }))
        : playerTargets(action).map(p => ({ id: String(p.id), playerId: p.id, label: `${p.name} · ${healthText(p)}` }));
      if (!rows.length) { note = arena === 'enemy' ? '没有可攻击的敌人。' : '没有存活的其他队友。'; changed(); return; }
      choose(title, rows, row => void submit({ ...payloadOf(action), target: arena === 'ally' ? row.playerId : row.id }));
      return;
    }
    const ids = arena === 'enemy'
      ? (state.enemies ?? []).filter(e => e.hp > 0).map(e => e.id)
      : playerTargets(action).map(p => String(p.id));
    if (!ids.length) { note = arena === 'enemy' ? '没有可攻击的敌人。' : '没有存活的其他队友。'; changed(); return; }
    // The banner names the card or potion being aimed.
    targeting = { action, arena, id: ids[0], label: action.label };
    changed();
  }
  function cancelTargeting() { targeting = undefined; changed(); }
  // The banner label is client side only: the action keeps its wire shape.
  function payloadOf(action) { const { label, ...rest } = action; return rest; }
  function submitTarget(id) {
    if (!targeting || !targetIds().includes(id)) return;
    const { action, arena } = targeting;
    targeting = undefined;
    void submit({ ...payloadOf(action), target: id });
  }
  function confirm() {
    if (busy || modal?.battleLog) return;
    anchor(); const row = items()[index]; if (!row) return;
    if (modal) { const current = modal; modal = undefined; selected = current.previousSelected; index = current.previousIndex; listPage = current.previousPage ?? 0; current.accept(row); return; }
    if (!roomId) {
      if (row.id === 'ascension') { choose('进阶难度 · 效果逐级叠加 · 创建后固定', ascensionNames.map((name, level)=>({id:String(level), label:`A${level} · ${name}：${ascensionDescriptions[level]}${level===ascension ? ' ✓' : ''}`})), choice=>{ascension=Number(choice.id);changed();});return; }
      void guard(async () => {
        const generation = connectionGeneration;
        const current = () => !closed && !ctx.signal.aborted && generation === connectionGeneration;
        if(serverProtocol!==PROTOCOL)throw new Error(VERSION_ERROR);
        if (row.id === 'create' || row.id === 'solo') {
          const existing = row.id === 'solo' && rooms.find(r=>r.mode==='solo');
          if (existing) { if(existing.compatible===false)throw new Error('该存档需要对应版本的后端游戏模块。'); await ctx.request(`${BASE}/${existing.id}/join`, 'POST');if(current())connect(existing.id);return; }
          const result = await ctx.request(BASE, 'POST', { ascension, requestId: newId(),mode:row.id==='solo'?'solo':'coop' }); if(current())connect(result.id);
        } else {
          if (row.room.compatible === false) throw new Error('该存档需要对应版本的后端游戏模块。');
          await ctx.request(`${BASE}/${row.id}/join`, 'POST'); if(current())connect(row.id);
        }
      }); return;
    }
    if (!canAct()) return;
    if (row.shop) {
      if (row.shop.price > (me()?.gold ?? 0)) { unaffordableShopIds.add(row.id); note = ''; changed(); return; }
      if (row.shop.kind === 'potion' && state.self.potions.length >= (state.self.potionCapacity ?? 3)) { focusRegion = 'potions'; focusIndex = 0; changed(); return; }
      unaffordableShopIds.delete(row.id);
    }
    if(row.id==='keepCharacter'){characterConfirmed=true;mapOpen=undefined;selected=undefined;index=0;changed();return;}
    if(row.id==='openMap'){mapOpen=true;mapReturnTab=tab;tab=0;changed();return;}
    if (tab === 0 && row.pick) {
      const limit = state.pendingChoice?.maximum ?? state.pendingDecision?.maximum ?? 1;
      if (picked.has(row.pick)) picked.delete(row.pick);
      else if (picked.size < limit) picked.add(row.pick);
      else note=`最多选择 ${limit} 张牌。`;
      changed();return;
    }
    if (tab === 0 && !pileView && row.card) { cardAction(row.card); return; }
    if (tab === 0 && row.group && row.id === row.group) { if (row.open) rewardPick.delete(row.group); rewardOpen = row.open ? undefined : row.group; changed(); return; }
    if (tab === 0 && row.candidate && row.action) {
      // Picking a card reward's card is the deliberate claim.
      const action = { ...row.action, phaseId: state.phaseId };
      rewardLog.set(row.group, '已领取');
      void submit(action);
      return;
    }
    if (tab === 0 && row.group && row.id.startsWith('claim:')) {
      // §F: the deliberate claim: a card reward claims the chosen candidate, any
      // other reward claims by its own row.
      const group = rewardGroups().find(item => item.key === row.group);
      const chosen = group?.candidates.find(candidate => candidate.id === rewardPick.get(row.group))
        ?? group?.candidates.find(candidate => candidate.id === selected)
        ?? (group?.candidates.length === 1 ? group.candidates[0] : undefined);
      if (group?.kind === 'card' && !chosen) { note = '先选择一张卡牌再领取。'; changed(); return; }
      const action = chosen?.action ?? row.action;
      if (!action) { note = '这项奖励不能在这里领取。'; changed(); return; }
      rewardLog.set(row.group, '已领取');
      void submit({ ...action, phaseId: state.phaseId });
      return;
    }   // §F: a candidate is chosen, never claimed
    if (tab === 0 && row.id === 'skipAll') {
      // Two steps: the first click or Enter turns the row into [Enter 跳过],
      // the second one skips.
      if (!skipArmed) { skipArmed = true; changed(); return; }
      skipArmed = false;
      const groups = rewardGroups();
      skipKnown = new Set((state.options ?? []).map(option => option.id));
      skipQueue = groups.flatMap(group => group.skips);
      const forced = groups.filter(group => !group.skips.length);
      if (forced.length) note = `规则强制的奖励不能跳过：${forced.map(group => group.title).join('、')}`;
      const step = skipStep(state);
      if (step) void submit(step); else changed();
      return;
    }
    if (tab === 0 && row.action) {
      if (row.action.type === 'choose' && state.pendingChoice?.maximum > 1) {
        if (picked.size < state.pendingChoice.minimum || picked.size > state.pendingChoice.maximum) {
          note=`请选择 ${state.pendingChoice.minimum}–${state.pendingChoice.maximum} 张牌后确认。`;changed();return;
        }
        void submit({...row.action,cards:[...picked]});
      }
      else if (row.action.type === 'treasurePick') {
        // §G: the row itself is the confirmation. A single player's pick then
        // claims the matching reward; a party votes and claims in two steps.
        const action = { ...row.action, phaseId: state.phaseId };
        const valid = snapshot => snapshot.phaseId === action.phaseId && snapshot.options.some(option => option.id === row.id && option.action?.type === 'treasurePick' && option.action.index === action.index);
        if (!valid(state)) { note = '宝箱内容已变化，请重新选择。'; changed(); return; }
        if (state.players.length === 1 && action.index !== null) chain = { phaseId: state.phaseId, before: new Set(claimRows(state).map(row => row.id)) };
        void submit(action);
      }
      // A multi-select decision has its own confirm row and an explicit cancel row;
      // neither should open the generic confirmation after the fact.
      else if (row.action.type === 'decide' && !(state.pendingDecision?.maximum > 1 && ['confirmDecision','decideCancel'].includes(row.id))) {
        const action={...row.action,phaseId:state.phaseId};
        const valid=s=>s.phaseId===action.phaseId && s.pendingDecision?.id===action.decisionId && s.options.some(o=>o.id===row.id);
        choose('确认选择？',[{id:'no',label:'返回'},{id:'yes',label:'确认选择'}],answer=>{
          if(answer.id==='yes' && valid(state)) void submit(action);else changed();
        }, { detail: row.label, detailOffset: 0, validFor: valid });
      }
      else if (row.action.type === 'customRelicReward') {
        // §G: allocated or offered directly, the claim row is the deliberate claim.
        const action = { ...row.action, phaseId: state.phaseId };
        const valid = snapshot => snapshot.phaseId === action.phaseId && snapshot.options.some(option =>
          option.action?.type === 'customRelicReward' && option.action.reward === action.reward && option.action.card === action.card);
        if (!valid(state)) { note = '奖励已失效，请重新选择。'; changed(); return; }
        void submit(action);
      }
      else if (row.group) {
        if (row.skipped) rewardLog.set(row.group, '已跳过'); else if (row.action) rewardLog.set(row.group, '已领取');
        if (row.action) void submit({ ...row.action, phaseId: state.phaseId });
        else changed();
        return;
      }
      else if (['reward','customReward'].includes(row.action.type)) {
        // §F: the row is the confirmation. A reward the server no longer offers is
        // refused here rather than confirmed twice.
        const action = { ...row.action, phaseId: state.phaseId };
        const offered = (state.options ?? []).some(option => option.action?.type === action.type && option.action.reward === action.reward && option.action.card === action.card);
        if (!offered) { note = '奖励已失效，请重新选择。'; changed(); return; }
        void submit(action);
      }
      else if (row.action.type === 'decide' && state.pendingDecision?.maximum > 1 && row.id === 'confirmDecision') {
        const decision = state.pendingDecision;
        if (picked.size < decision.minimum || picked.size > decision.maximum) {
          note = `请选择 ${decision.minimum}–${decision.maximum} 张牌后确认。`; changed(); return;
        }
        void submit({ ...row.action, selections: [...picked] });
      }
      else if (row.action.type === 'buy') {
        // §E: the row is the purchase; the price and the balance were on screen.
        const price = row.shop?.price ?? 0;
        if (price > (me()?.gold ?? 0)) { note = ''; changed(); return; }
        void submit(row.action);
      }
      else if (row.choice) deckChoice(row.choice, id => {
        if (row.action.type !== 'removeCard') { void submit({ ...row.action, choice: id }); return; }
        // §E: the removal service names the card and the cost before charging.
        const card = (state.self.deck ?? []).find(item => item.id === id);
        const price = row.shop?.price ?? 0;
        choose(`确认移除「${card?.name ?? id}」？`, [{ id: 'no', label: '返回' }, { id: 'yes', label: `确认移除 · ${price} 金币` }], answer => {
          if (answer.id === 'yes') void submit({ ...row.action, choice: id }); else changed();
        }, { detail: `费用：${price} 金币\n移除后余额：${(me()?.gold ?? 0) - price} 金币`, detailOffset: 0 });
      });
      else if (row.action.type === 'abandon') choose('确认放弃本局？', [{ id: 'no', label: '返回' }, { id: 'yes', label: '确认放弃', danger: true }], answer => { if (answer.id === 'yes') void submit(row.action); else changed(); });
      else void submit(row.action);
    }
  }
  // The drawing reads the view state and the party; this supplies both.
  const mapLines = (view, width) => drawMap(view, width,
    { scroll: mapScroll, anchor: mapAnchor, focus:mapFocus, height:mapBudget, players: state?.players, options: state?.options });
  const mapNavigation = () => !modal && !targeting && !pileView && !needsCharacterChoice() && tab===0 && (mapOpen??state?.phase==='map') && !state?.paused && !state.pendingChoice && !state.pendingDecision && Boolean(state.mapView?.nodes?.length);
  const screen = {
    render(width, rows) {
      columns = width; height = rows; hits = [];
      const frame = [], add = (text, tone = 'text') => frame.push({ text, tone });
      const mark = hit => hits.push({ row: frame.length, col: 0, width: Infinity, height: 1, ...hit });
      if (width < 40 || rows < ((mapNavigation() || modal?.shortcuts)?12:20)) { add(`请扩大终端至至少 40 列、${mapNavigation()?12:20} 行。`, 'title'); add('Ctrl+C / Ctrl+D 返回聊天', 'muted'); return frame; }
      if (modal?.textDetail && modal.textDetail.width !== width) {
        modal.items = modal.textDetail.lines.flatMap(line => (modal.textDetail.card ? wrapCardText : wrapText)(line, Math.max(1, width - 4)))
          .map((label, i) => ({ id: `status${i}`, label }));
        modal.textDetail.width = width; index = 0; selected = modal.items[0]?.id;
      }
      if (state?.phase !== 'combat') expandedUnit = undefined;
      const own = me();
      const heading = needsCharacterChoice() ? '选择初始角色' : state?.phase === 'shop' && width < 70 ? `商店 · 第 ${state.floor} 层` : state ? `A${state.ascension ?? 0} · ${state.act ? `第 ${state.act.index + 1} 幕 ${state.act.name} · ` : ''}第 ${state.floor} 层 · ${phases[state.phase]}${state.paused ? ' · 暂停' : ''}` : 'Spire · 合作房间';
      const waiting = busy ? '处理中…' : state && !synced ? '等待服务器确认…' : '';
      const status = state ? `${waiting ? paint(MUTED, waiting + ' · ', ACCENT) : ''}${paint(GOLD, `金币 ${own?.gold ?? 0}`, ACCENT)} · 药水 ${state.self.potions.length}/${state.self.potionCapacity ?? 3}` : waiting;
      add(status ? pad(cut(heading, Math.max(8, width - displayWidth(status) - 2)), width - displayWidth(status)) + status : cut(heading, width), 'title');
      if(state){
        const entries=regionItems('entries'), labels=entries.map((row,i)=>`${row.name}`);
        const deckLabel=labels[0]??'', deckAt=Math.max(0,width-displayWidth(deckLabel));
        // One equipment line per region. The relics line shares the first row
        // with the deck entry, so it wraps at the deck label instead of the frame.
        const equipmentRow=(region,avail)=>{
          const list=regionItems(region);let from=Math.min(equipmentOffset[region],Math.max(0,list.length-1));
          const wanted=focusRegion===region?Math.max(0,Math.min(focusIndex,list.length-1)):from;
          if(wanted<from)from=wanted;
          const label=row=>`${row.name}${row.counter!==undefined?`(${row.counter})`:''}`;
          while(from<wanted && displayWidth(list.slice(from,wanted+1).map(row=>' '+label(row)).join(' · '))>avail-14)from++;
          equipmentOffset[region]=Math.max(0,from);
          let text=(region==='relics'?'遗物':'药水')+' ';let shown=0;
          for(let i=from;i<list.length;i++){
            const part=cut(`${label(list[i])}`,Math.max(4,avail-14));
            if(displayWidth(text+' '+part)>avail-5)break;
            const col=displayWidth(text);mark({kind:'equipment',region,id:list[i].id,index:i,col,width:displayWidth(part)});
            text+=part+' · ';shown++;
          }
          if(!list.length)text+='无';
          if(from>0||from+shown<list.length){
            mark({kind:'equipmentPage',region,delta:-1,col:avail-5,width:2});
            mark({kind:'equipmentPage',region,delta:1,col:avail-2,width:2});
            text=pad(cut(text,avail-5),avail-5)+'‹  ›';
          }
          return cut(text,avail);
        };
        const relicsText=equipmentRow('relics',Math.max(8,deckAt-2));
        mark({kind:'entry',id:'deck',col:deckAt,width:displayWidth(deckLabel)});
        add(pad(cut(relicsText,deckAt),deckAt)+deckLabel,'muted');
        add(equipmentRow('potions',width),'muted');
      }
      if(mapNavigation()) {
        const view=state.mapView;
        frame.push(panelTitle('路线 · ' + (state?.act?.name ?? view.act?.name ?? ''), state.phase !== 'map' ? '仅查看' : '', width, 0));
        mapBudget=Math.max(3,rows-frame.length-2);
        const drawn=mapLines(view,width);
        for(const line of drawn.lines){
          const row=frame.length;add(line.text,line.tone);
          for(const cell of line.cells)hits.push({kind:'node',id:cell.id,row,col:cell.col,width:cell.width,height:1});
        }
        while(frame.length<rows-2)add('');
        const message=actionQueue.size?(queueStatus()+' '+note).trim():note;
        add(cut(message||(focusRegion==='action'&&!hovered?mapDetailText(view,mapData(view)):detailText()),width),'muted');
        frame.push(hintRow(hintPairs(),width,0));
        hits=hits.filter(hit=>hit.row<rows);
        paintFocus(frame);return frame.slice(0,rows);
      }
      if (shopView()) {
        add(cut((state.players ?? []).map(player => `${player.name} ${hpText(player)} HP${player.done ? ' · 已完成' : ''}`).join(' · '), width), 'muted');
        anchor();
        for (const id of unaffordableShopIds) {
          if (!state.options.some(row => row.id === id && row.shop?.price > (me()?.gold ?? 0))) unaffordableShopIds.delete(id);
        }
        const rendered = renderShop({ width, height: rows - frame.length, options: state.options, group: shopGroup, selected, top: shopTop,
          unaffordableIds: unaffordableShopIds,
          gold: own?.gold, potionCount: state.self.potions.length, potionCapacity: state.self.potionCapacity ?? 3,
          focused: focusRegion === 'action' && !hovered, hints: hintPairs(),
          note: actionQueue.size ? (queueStatus() + ' ' + note).trim() : note });
        shopTop = rendered.top; pageSize = rendered.listHeight;
        const start = frame.length;
        for (const hit of rendered.hits) hits.push({ ...hit, row: start + hit.row, revision: state.revision });
        frame.push(...rendered.rows);
        if (focusRegion !== 'action' || hovered) paintFocus(frame);
        else { const hit = currentHit(); if (hit) frame[hit.row].focusColumn = hit.col; }
        return frame;
      }
      if (unsupported) add(`此扩展版本不认识该阶段「${unsupported}」，请在更新扩展后继续（当前只读）。`, 'error');
      if (state?.partyRequirement && !state.partyRequirement.canReady && (state.phase === 'lobby' || state.paused)) add(`等待队友：${state.partyRequirement.online}/${state.partyRequirement.minimum} 人在线，至少两人才能开始 / 继续`, 'muted');
      if (state) {
        if (state.phase === 'combat') {
          const alive = state.enemies.filter(e => e.hp > 0 || e.awaitingRevive);
          const chosen = focusRegion==='units'&&!targeting?alive.findIndex(e=>String(e.id)===String(focusItem()?.id)):targetIndex();
          const party = [own, ...state.players.filter(p => p.id !== seatId())];
          const legalEnemy = enemy => Boolean(targeting && enemy && targeting.arena === 'enemy' && targetIds().includes(enemy.id));
          const legalAlly = id => Boolean(targeting && targeting.arena === 'ally' && targetIds().includes(id));
          {
            // Reserve a usable hand, resources, page hint and bottom details.
            const minimumHand = rows >= 24 && width >= 80 ? 5 : 3;
            const budget = Math.max(party.length + 2, rows - frame.length - minimumHand - 8);
            const room = Math.max(expandedUnit ? 2 : 1, budget - party.length - alive.length + 1);
            // Expanded statuses stay below their creature and share the arena budget.
            const allies = party.map(player => compactLines(player, 'ally', width, room));
            const used = allies.reduce((total, lines) => total + lines.length, 0);
            const enemyLines = alive.map(enemy => compactLines(enemy, 'enemy', width, room));
            const enemyHeight = enemyLines.reduce((n, lines) => n + lines.length, 0);
            // Reserve a page hint when the enemy list exceeds the arena height.
            const perPage = enemyHeight <= budget - used ? Math.max(1, alive.length) : Math.max(1, budget - used - 1 - enemyLines.reduce((n, lines) => n + lines.length - 1, 0));
            const pages = Math.max(1, Math.ceil(alive.length / perPage));
            if (chosen >= 0) enemyPage = Math.floor(chosen / perPage);
            enemyPage = Math.max(0, Math.min(pages - 1, enemyPage ?? 0));
            const shown = alive.slice(enemyPage * perPage, enemyPage * perPage + perPage);
            const section = [
              ...party.map((player, index) => ({ id: String(player?.id), legal: legalAlly(String(player?.id)), lines: allies[index] })),
              ...shown.map(enemy => ({ id: enemy.id, legal: legalEnemy(enemy), lines: compactLines(enemy, 'enemy', width, room) })),
            ];
            for (const [sectionIndex, entry] of section.entries()) {
              if (sectionIndex === party.length && section.reduce((total, unit) => total + unit.lines.length, 0) + (pages > 1 ? 1 : 0) < budget) add('');
              const top = frame.length;
              const shownLines = entry.legal && entry.id === targeting.id ? tint(entry.lines, targetTint(targeting.arena)) : entry.lines;
              for (const line of shownLines) add(line, 'text');
              hits.push({ kind: 'entity', id: entry.id, row: top, col: 0, width, height: shownLines.length });
            }
            if (pages > 1) add(`敌人 ${enemyPage + 1}/${pages} 页 · 共 ${alive.length} 名`, 'muted');
          }
          const usable = own?.energy ?? 0;
          const capacity = own?.energyCapacity ?? usable;
          const iconLimit = 5;
          const filled = Math.min(iconLimit, Math.max(0, usable));
          const empty = Math.min(iconLimit - filled, Math.max(0, capacity - usable));
          const orbs = '●'.repeat(filled) + '○'.repeat(empty) + (Math.max(usable, capacity) > iconLimit ? '...' : '');
          const button = endTurnLabel();
          // §2: the Regent's stars are a resource of the same row as the energy.
          const starCount = own?.stars ?? 0;
          const stars = own?.character === 'regent' || starCount > 0 ? `${starCount ? '★'.repeat(Math.min(iconLimit, starCount)) : '☆'}${starCount > iconLimit ? '...' : ''} ${starCount}` : '';
          const energy = `能量 ${orbs ? `${orbs} ` : ''}${usable}/${capacity}${stars ? `   ${stars}` : ''}`;
          // Right-aligned with 弃牌堆 and 牌组 below and above it.
          const buttonAt = Math.max(8, width - displayWidth(button));
          if (!modal) mark({ kind: 'endTurn', id: 'endTurn', col: buttonAt, width: displayWidth(button) });
          add(pad(energy, buttonAt) + button, 'text');
          const piles=[['draw','A','抽牌堆',state.self.draw?.length??state.self.drawCount??0],
            ['exhaust','X','消耗牌堆',state.self.exhaust?.length??state.self.exhaustCount??0],
            ['discard','S','弃牌堆',state.self.discard.length]];
          // A pile whose count just changed lights its number in the pile's colour;
          // the button keeps its text and width. Narrow screens shorten the names.
          const moving=frameAt(motion,Date.now()), pileColour={draw:PILE_DRAW,discard:PILE_DISCARD,exhaust:PILE_EXHAUST};
          const pileName=name=>width<44?name.slice(0,2):name;
          const pileLabels=piles.map(([,key,name,count])=>`[${key} ${pileName(name)} ${count}]`);
          const pileTexts=piles.map(([id,key,name,count],i)=>moving?.changed.has(id)?`[${key} ${pileName(name)} ${paint(pileColour[id],`${count}`,MUTED)}]`:pileLabels[i]);
          // 抽牌堆 stays at the left edge and 弃牌堆 at the right edge; 消耗牌堆 sits
          // directly left of 弃牌堆 instead of centred between them.
          const discardAt=Math.max(0,width-displayWidth(pileLabels[2]));
          const positions=[0,Math.max(displayWidth(pileLabels[0])+1,discardAt-displayWidth(pileLabels[1])-1),discardAt];
          if(!modal)for(let i=0;i<piles.length;i++)mark({kind:'pile',id:piles[i][0],col:positions[i],width:displayWidth(pileLabels[i])});
          add(place(pileTexts.map((text,i)=>({at:positions[i],text})),width).text,'muted');
        } else {
          // The title row already carries this player's gold; teammates keep theirs.
          if (state.event) add(state.event, 'title');
          // §2: outside combat there is no battlefield, so the party, its health
          // and who is ready stay on screen in a compact line each.
          for (const player of state.players ?? []) {
            const here = state.online?.includes(player.id);
            const flag = !here ? '离线' : state.paused || state.phase === 'lobby' ? (player.ready ? '已准备' : '') : player.done ? '已完成' : '';
            const gold = player.id === seatId() ? '' : ` · 金币 ${player.gold ?? 0}`;
            const rowText = cut(`${player.name}${player.characterName ? ` · ${player.characterName}` : ''} ${hpText(player)} HP${gold}${flag ? ` · ${flag}` : ''}${player.vote ? ` · 已投票 ${player.vote}` : ''}`, width);
            // Clicking a teammate is the same act as pressing P on them. The
            // mark is taken before the line is pushed, while the row still is
            // the one it will land on.
            if (!modal) mark({ kind: 'entity', id: String(player.id), width: displayWidth(rowText) });
            add(rowText, 'text');
          }
          if (['event', 'ending', 'victory'].includes(state.phase) && state.eventProgress?.description) {
            // The story wraps instead of running off the edge; a long one keeps
            // its opening and ends in an ellipsis.
            const story = String(state.eventProgress.description).split('\n').flatMap(line => line ? hardSplit(line, width) : []);
            const room = Math.max(2, Math.floor(rows / 4));
            if (story.length > room) story.splice(room - 1, Infinity, cut(story[room - 1], Math.max(1, width - 1)) + '…');
            for (const line of story) add(line, 'muted');
          }
          const sphere = sphereView();
          if (sphere && !modal) {
            const left = sphere.divinations;
            add(`占卜剩余 ${left} 次 · 工具：${sphere.tool === 'Big' ? '大（3×3）' : '小（1 格）'} · 方向键移动，空格揭开，G 换工具`,
                left ? 'title' : 'muted');
            for (const line of sphereLines(sphere)) add(line, 'text');
            add('R 遗物 · P 药水 · C 卡牌奖励 · $ 金币 · ! 诅咒 · o 空 · · 未揭开', 'muted');
          }

        }
        const choosing = (state.choiceStatus ?? []).filter(row => row.status === 'choosing' && row.id !== state.self.id);
        if (tab === 0 && !modal && !pileView && choosing.length) {
          const names = choosing.map(row => state.players.find(player => player.id === row.id)?.name ?? String(row.id)).join('、');
          const done = state.choiceStatus?.find(row => row.id === state.self.id)?.status === 'done';
          add(done ? `你已完成，等待${names}` : `${names}正在选择`, 'muted');
        }
        const decision = state.pendingChoice ?? state.pendingDecision;
        const panelHead=(title,meta='')=>{frame.push(panelTitle(title,meta,width,0));};
        if(modal || (tab===0 && decision))panelHead(modal?.title ?? `${decision.owner===seatId()?'':'等待队友 · '}${decision.title}`,modal?.meta ?? '');
        else if(pileView)panelHead(tabNames[pileView],`${items().length} 张`);
        if (modal?.detail) {
          const lines = ctx.wrap(modal.detail, Math.max(1, width - 2));
          const count = Math.max(1, Math.min(6, rows - frame.length - 9));
          modal.detailOffset = Math.min(modal.detailOffset ?? 0, Math.max(0, lines.length - count));
          mark({ kind: 'detail' });
          for (const line of lines.slice(modal.detailOffset, modal.detailOffset + count)) add(line);
          if (lines.length > count) add('↑↓ 浏览 · 到边缘继续滚动说明', 'muted');
        }
      } else add('频道成员可加入 · R 刷新房间列表', 'muted');
      if (loading) add('正在加载…', 'muted');
      const detailRows=state && (!modal || modal.upgradePicker) ? 3 : 1;
      const footerRows=1+detailRows;
      if (state && state.phase!=='combat') add('');                                          // breathing room above the list
      anchor(); const list = items(), available = Math.max(1, rows - frame.length - footerRows - 1);
      pageSize = available;
      listPage=Math.floor(Math.max(0,index)/available);
      const maxPage = Math.max(0, Math.ceil(list.length / available) - 1);
      listPage = Math.max(0, Math.min(maxPage, listPage));
      const start = listPage * available;
      const cards=list.filter(row=>row.card).map(row=>row.card);
      const cardNameWidth=Math.min(Math.max(4,...cards.map(card=>displayWidth(card.name))),Math.max(8,Math.floor(width*.4)));
      const cardCostWidth=Math.max(3,...cards.map(card=>displayWidth(`${cardCost(card)}`)));
      // A hand card the player cannot pay for right now is dimmed as a whole; the
      // server still decides, so the row stays selectable.
      const inHand=state?.phase==='combat' && !modal && !pileView;
      const unaffordable=card=>inHand && (cardUnplayable(card) || Number.isInteger(card.cost) && card.cost>(own?.energy??0) || Number.isInteger(card.starCost) && card.starCost>(own?.stars??0));
      const rowLabel=row=>{
        if(row.card){
          const label=`${pad(cut(row.card.name,cardNameWidth),cardNameWidth)}  ${pad(`${cardCost(row.card, true)}`,cardCostWidth)}  ${cardDescription(row.card, true)}`;
          return unaffordable(row.card) ? paint(MUTED,label) : label;
        }
        // Like the shop's leave button, the focused way out turns into its key.
        if(row.id==='skipAll' && skipArmed && focusRegion==='action' && !hovered && items()[index]?.id==='skipAll')return '[Enter 跳过]';
        const bundle=optionCards(row);
        if (bundle?.length > 1) {
          // Keep every bundle cost on screen; its full descriptions remain below
          // and in the scrollable explanation opened with ?.
          const prefix=(row.pick ? `${picked.has(row.pick) ? '[x]' : '[ ]'} ` : '')+(row.displayPrefix ?? '');
          const costs=bundle.map(card=>cardCost(card,true));
          const fixed=displayWidth(prefix)+costs.reduce((sum,cost)=>sum+displayWidth(cost)+1,0)+2*(bundle.length-1);
          const nameWidth=Math.max(0,Math.floor((width-fixed)/bundle.length));
          return prefix+bundle.map((card,i)=>`${cut(card.name,nameWidth)} ${costs[i]}`).join('；');
        }
        const label=soloLabel(row.label);
        // Loot reads "name：description"; the name is what the player scans for.
        const at=['reward','treasure'].includes(state?.phase) && !row.separator ? label.indexOf('：') : -1;
        return at>0 && at<24 ? paint(GOLD,label.slice(0,at))+label.slice(at) : label;
      };
      if (!list.length && !loading) add(pileView ? `${tabNames[pileView]}为空。` : state?.readOnly ? '旁观模式 · 当前没有可展示的手牌。' : state?.phase === 'combat' && !state.paused ? '没有手牌。按 E 结束回合。' : state?.phase === 'defeat' ? '攀登结束。按 Esc 返回主界面。' : '等待队友。', 'muted');
      for (let i = start; i < Math.min(list.length, start + available); i++) {
        mark({ kind: 'item', id: list[i].id });
        add(list[i].danger ? `${DANGER}${rowLabel(list[i])}${RESET}` : rowLabel(list[i]), list[i].separator ? 'muted' : 'text');
        // An unplayable card stays grey under the cursor, so no card looks playable that is not.
        if (list[i].card && unaffordable(list[i].card)) frame.at(-1).dim = true;
      }
      if (maxPage > 0) add(`第 ${listPage + 1}/${maxPage + 1} 页 · 共 ${list.length} 项`, 'muted');
      while (frame.length < rows - footerRows) add('');
      {
        const message = actionQueue.size ? (queueStatus()+' '+note).trim() : note;
        const target = targeting && regionItems('units').find(row=>String(row.id)===String(targeting.id));
        const description = !state || modal && !modal.upgradePicker ? '' : targeting ? `选择目标：${target?.name??targeting.id} · ${targeting.action.type!=='play' ? `${targeting.label} · ` : ''}${detailText()}` : modal?.upgradeDetail??detailText();
        const detail=[...(message?[message]:[]), ...wrapCardText(description,width)].slice(0,detailRows);
        for(let i=detail.length;i<detailRows;i++)add('');
        for(const line of detail)add(cut(line,width),'muted');
        frame.push(hintRow(hintPairs(),width,0));
      }
      if(frame.length>rows){const tail=frame.splice(-footerRows);frame.splice(rows-footerRows);frame.push(...tail);}
      const visible = Math.min(rows, frame.length); hits = hits.filter(hit => hit.row < visible);
      paintFocus(frame);return frame.slice(0, rows);
    },
    key(key) {
      if (key.ctrl && ['c', 'd'].includes(key.name)) { stopGame(); ctx.closeScreen(); return; }
      if (motion) stopMotion();
      if (delegation.active()) { delegation.key(key); return; }
      if (chat.key(key)) return;
      const name = key.name, value = key.value?.toLowerCase();
      if (name === 'escape' && state?.phase === 'defeat' && !state?.delegation && navigation.onHome) { void leaveToHome(); return; }
      if (shopView() && columns >= 40 && height >= 20 && name === 'tab') {
        const at = SHOP_GROUPS.findIndex(([id]) => id === shopGroup);
        switchShop(SHOP_GROUPS[(at + (key.shift ? -1 : 1) + SHOP_GROUPS.length) % SHOP_GROUPS.length][0]); return;
      }
      if (modal?.shopDetail && ['pageup', 'pagedown'].includes(name)) { pageDetail(name === 'pageup' ? -5 : 5); return; }
      if (shopView() && value === 'e' && !key.ctrl) {
        const leave = items().findIndex(row => row.action?.type === 'continue');
        if (leave >= 0) { focusRegion = 'action'; hovered = undefined; moveTo(leave); }
        return;
      }
      if (shopView() && value === 'i' && !key.ctrl) { shopDetail(); return; }
      if (modal?.textDetail && ['pageup', 'pagedown'].includes(name)) {
        moveTo(index + (name === 'pageup' ? -1 : 1) * Math.max(1, pageSize)); return;
      }
      if(['tab','pageup','pagedown'].includes(name))return;
      if(['up','down','left','right','home','end'].includes(name))hovered=undefined;
      if(value==='i' && !key.ctrl && !targeting && state && columns>=40 && height>=20 && !modal?.textDetail){
        const creature = !modal && hovered?.region==='units' ? hovered.row : !modal && focusRegion==='units' ? focusItem() : undefined;
        const row = hovered?.region==='action' && !modal ? hovered.row : items()[index];
        if(creature)showPowerDetail(creature);
        else if(row?.card || optionCards(row) || ['reward', 'customReward', 'choose'].includes(row?.action?.type))showCardDetail(row);
        return;
      }
      if(!modal && !targeting && state){
        if(value==='d' && !key.ctrl){openPile('deck');return;}
        if(value==='v'){void openLog();return;}
        if(name==='escape' && pileView){closePile();return;}
        if(focusRegion!=='action' && ['home','end'].includes(name)){focusIndex=name==='home'?0:Math.max(0,regionItems(focusRegion).length-1);hovered=undefined;changed();return;}
        if(focusRegion!=='action' && ['return','enter'].includes(name)){activateFocus();return;}
      }
      if(modal?.battleLog && ['left','right'].includes(name)){
        const cursor=name==='left'?modal.battleLog.after:modal.battleLog.before;
        if(cursor!=null)void openLog({[name==='left'?'after':'before']:String(cursor)});
        return;
      }
      if (targeting) {
        const ids = targetIds();
        if (name === 'escape') { cancelTargeting(); return; }
        if (['left', 'right', 'up', 'down'].includes(name)) {
          const at = Math.max(0, ids.indexOf(targeting.id));
          const step = name === 'left' || name === 'up' ? -1 : 1;
          targeting.id = ids[(at + step + ids.length) % ids.length];
          changed(); return;
        }
        if (name === 'return' || name === 'enter') { submitTarget(targeting.id); return; }
        if (value === 'e') { cancelTargeting(); return; }
      }
      if(value==='m' && state?.mapView?.nodes?.length && !modal && !targeting && !state.paused && !needsCharacterChoice() && !state.pendingChoice && !state.pendingDecision){
        if(mapNavigation()){mapOpen=false;tab=mapReturnTab;}
        else{mapReturnTab=tab;tab=0;mapOpen=true;}
        changed();return;
      }
      if (mapNavigation()) {
        if (name === 'escape') { mapOpen=false; tab=mapReturnTab; changed(); return; }
        if(focusRegion==='action' && tab===0 && ['left','right','up','down'].includes(name)) {
          const data=mapData(state.mapView), here=data.byId.get(mapFocus)??data.current??data.nodes[0];
          const candidates=data.nodes.filter(n=> name==='left'? n.row===here.row&&n.col<here.col : name==='right'? n.row===here.row&&n.col>here.col : name==='up'?n.row>here.row:n.row<here.row);
          candidates.sort((a,b)=>Math.abs(a.row-here.row)-Math.abs(b.row-here.row)||Math.abs(a.col-here.col)-Math.abs(b.col-here.col));
          if(candidates[0]){mapFocus=candidates[0].id;mapAnchor=mapFocus;mapScroll=undefined;}else spatialMove(name,true);
          changed();return;
        }
        if(focusRegion==='action' && ['return','enter'].includes(name)){
          const row=state.phase==='map' && state.options.find(row=>row.action?.type==='vote' && row.action.node===(mapFocus??state.mapView.current));
          if(row)void submit({...row.action,phaseId:state.phaseId});
          return;
        }
      }
      if(mapNavigation() && ['a','s','x','e',' '].includes(value))return;
      if(!modal && !targeting && state?.phase==='combat' && ['a','s','x'].includes(value)){openPile({a:'draw',s:'discard',x:'exhaust'}[value]);return;}
      if(name==='escape' && pileView && !modal){closePile();return;}
      // The board takes the arrows before the option list does, or moving on
      // the grid would scroll the rows underneath it.
      if (focusRegion==='action' && columns>=40 && height>=20 && sphereView() && !sphereView().finished && tab===0 && !pileView && !modal && !targeting) {
        if (name === 'up') { sphereMove(0, -1); return; }
        if (name === 'down') { sphereMove(0, 1); return; }
        if (name === 'left') { sphereMove(-1, 0); return; }
        if (name === 'right') { sphereMove(1, 0); return; }
        if (value === 'h') { sphereMove(-1, 0); return; }
        if (value === 'l') { sphereMove(1, 0); return; }
        if (value === 'k') { sphereMove(0, -1); return; }
        if (value === 'j') { sphereMove(0, 1); return; }
        if (value === ' ' || name === 'space' || name === 'return' || name === 'enter') { sphereUse(); return; }
        if (value === 'g' && !key.ctrl && !key.meta) { sphereTool(); return; }
      }
      if(!modal && !targeting && state && ['up','down','left','right'].includes(name)){spatialMove(name);return;}
      if (value === ' ' && !modal && !targeting) {
        const row = items()[index];
        if (row?.pick) {
          const limit = state.pendingChoice?.maximum ?? state.pendingDecision?.maximum ?? 1;
          if (picked.has(row.pick)) picked.delete(row.pick);
          else if (picked.size < limit) picked.add(row.pick);
          else note = `最多选择 ${limit} 张牌。`;
          changed();
        }
        return;
      }
      if (name === 'escape' || (value === '?' && modal?.shortcuts)) {
        if (modal) { selected = modal.previousSelected; index = modal.previousIndex; listPage = modal.previousPage ?? 0; modal = modal.previousModal; anchor(); changed(); }
        else if (navigation.onHome) {
          choose('游戏菜单', [{id:'continue',label:'继续游戏'},...(state?.features?.delegation && (state.ownerId===ctx.user.id || state.delegation) ? [{id:'delegation',label:'存档托管 · 代玩 / 回档 / 收回'}] : []),...(state?.mode==='coop' && !state.readOnly && state.ownerId===ctx.user.id && !['victory','defeat','abandoned'].includes(state.phase) ? [{id:'abandon',label:'放弃当前存档',danger:true}] : []),{id:'settings',label:'设置 · 查看快捷键'},{id:'home',label:'退出游戏'}], row => {
            modal=undefined;
            if(row.id==='delegation') {
              if (ctx.supportsControlHandoff) delegation.open();
              else note = '请先将 CLI 主程序升级至 0.13.1，再管理托管。';
            }
            else if(row.id==='settings') openSettings();
            else if(row.id==='home') void leaveToHome();
            else if(row.id==='abandon') choose('确认放弃本局？', [{id:'no',label:'返回'},{id:'yes',label:'确认放弃',danger:true}], answer => { if(answer.id==='yes') void submit({type:'abandon'}); else changed(); });
            changed();
          });
        }
        else if(focusRegion!=='action'){focusRegion='action';hovered=undefined;changed();}
        return;
      }
      if (columns < 40 || height < ((mapNavigation() || modal?.shortcuts)?12:20)) return;
      if (value === '?' && (!modal || modal.upgradePicker)) {
        const previousPicker=modal?.upgradePicker?modal:undefined;
        const description = modal?.upgradeDetail ?? detailText(true);
        const lines = [...(description ? [{ id: 'about', label: paint(ACCENT, '当前项目', TEXT), separator: true }, ...wrapCardText(description, Math.max(1, columns - 4)).map((label, i) => ({ id: `about${i}`, label }))] : []), ...helpLines()];
        choose('快捷键与说明', lines, () => {if(previousPicker)modal=previousPicker;anchor(); changed(); }, {shortcuts:true,previousModal:previousPicker});return;
      }
      if (value === 'r' && !busy) {
        if (actionQueue.size || actionQueue.blocked) { if (online && synced) actionQueue.reconcile(); else { note = '正在重新连接，取得状态后自动核对。'; changed(); } return; }
        void guard(async () => { const generation = connectionGeneration; if (roomId) { const snapshot = await ctx.request(`${BASE}/${roomId}`); if (!closed && generation === connectionGeneration) accept(snapshot); } else await loadRooms(); });
        return;
      }
      // The key and the button share one entry point.
      if (value === 'e' && !modal && !targeting) { endTurn(); return; }
      if (value === 'p' && !modal && !targeting && state) {
        const others = (state.players ?? []).filter(player => player.id !== seatId());
        if (!others.length) { note = '没有队友可查看。'; changed(); return; }
        if (others.length === 1) { void inspectPlayer(others[0].id); return; }
        choose('查看队友', others.map(player => ({ id: String(player.id), player: player.id, label: `${player.name} · ${player.characterName ?? ''}` })),
               row => { void inspectPlayer(row.player ?? row.id); });
        return;
      }
      if (value === 'u' && !modal && !targeting && state) {
        const row=items()[index];
        const cardId=row?.card?.id ?? row?.shop?.cardId ??
          (['reward','customReward'].includes(row?.action?.type) && !['skip','reroll','sacrifice'].includes(row.action.card) ? row.action.card : undefined);
        if (cardId) {
          const source=row?.shop ? 'shop' : ['reward','customReward'].includes(row?.action?.type) ? 'reward' : ['deck','draw','discard','exhaust'].includes(activeTab()) ? activeTab() : 'hand';
          void previewUpgrade(cardId,source);
        }
        else { note='当前项目没有可预览的升级。';changed(); }
        return;
      }
      if (name === 'space' && !modal && tab===0 && state?.pendingChoice?.maximum>1) { confirm();return; }
      if(modal && ['up','down'].includes(name)){
        // Headings are not stops: the edge is the last real row in that direction.
        const step=name==='up'?-1:1,list=items();let next=index+step;
        while(list[next]?.separator)next+=step;
        const boundary=next<0||next>=list.length;
        if(boundary && modal.battleLog){
          const cursor=step<0?modal.battleLog.after:modal.battleLog.before;
          if(cursor!=null&&!busy)void openLog({[step<0?'after':'before']:String(cursor)},step<0);
          return;
        }
        if(boundary && modal.inspection){const view=modal.inspection,page=view.page+step;if(page>=0&&page<view.pages)void inspectPlayer(view.id,page,step<0);return;}
        if(modal.detail && boundary){pageDetail(step);return;}
      }
      if (['up', 'down', 'home', 'end'].includes(name)) {
        const list = items();
        moveTo(name === 'home' ? 0 : name === 'end' ? list.length - 1 : index + (name === 'up' ? -1 : 1));
        listPage = Math.floor(Math.max(0, Math.min(index, Math.max(0, list.length - 1))) / pageSize);
        return;
      }
      if (name === 'return' || name === 'enter') confirm();
    },
    mouse(event) {
      if (motion && event.action === 'press') stopMotion();
      if (chat.mouse(event)) return;
      if (columns < 40 || height < ((mapNavigation() || modal?.shortcuts)?12:20)) return;
      if(!modal && !targeting){
        const hit=hitAt(event.x,event.y);
        if(event.action==='move'){
          let next;
          if(hit?.kind==='equipment')next={region:hit.region,row:regionItems(hit.region).find(row=>row.id===hit.id)};
          else if(hit?.kind==='entry')next={region:'entries',row:regionItems('entries').find(row=>row.id===hit.id)};
          else if(hit && ['pile','endTurn','inspect'].includes(hit.kind))next={region:'controls',row:controlItem(hit)};
          else if(hit?.kind==='entity')next={region:'units',row:regionItems('units').find(row=>String(row.id)===String(hit.id))};
          if(hovered?.region!==next?.region || hovered?.row?.id!==next?.row?.id){hovered=next;changed();}
          if(next)return;
        }
        if(event.action==='press' && event.button==='left'){
          if(hit?.kind==='entry'){if(hit.id==='deck')openPile('deck');else void openLog();return;}
          if(hit?.kind==='equipmentPage'){
            equipmentOffset[hit.region]=Math.max(0,Math.min(regionItems(hit.region).length-1,equipmentOffset[hit.region]+hit.delta));
            focusRegion=hit.region;focusIndex=equipmentOffset[hit.region];hovered=undefined;changed();return;
          }
          if(hit?.kind==='equipment'){
            focusRegion=hit.region;focusIndex=hit.index;hovered=undefined;
            if(hit.region==='potions')potionMenu(focusItem());else changed();return;
          }
        }
      }
      if (event.action === 'move') {
        // Hover lights a row, or shows which target the pointer is on.
        const pointed = hitAt(event.x, event.y);
        if (targeting && pointed?.kind === 'entity' && targetIds().includes(pointed.id)) {
          if (targeting.id !== pointed.id) { targeting.id = pointed.id; changed(); }
          return;
        }
        // §D: hovering a map node looks at it; pointing never submits.
        if (pointed?.kind === 'node') {
          focusRegion='action';
          if (mapFocus !== pointed.id) { mapFocus = pointed.id; changed(); }
          return;
        }
        if (pointed?.kind === 'item' && (pointed.id !== selected || focusRegion!=='action')) hoverRow(pointed.id);
        return;
      }
      if (event.action !== 'press') return;
      if (event.button === 'left') {
        const hit = hitAt(event.x, event.y);
        if (hit?.kind === 'node') {
          focusRegion='action';
          // §D: clicking a room you can travel to is the vote itself; any other
          // room is only looked at, and parks the view there.
          mapFocus = hit.id; mapAnchor = hit.id; mapScroll = undefined;
          const row = state.phase==='map' && state.options.find(row => row.action?.type === 'vote' && row.action.node === hit.id);
          if (row) { void submit({ ...row.action, phaseId: state.phaseId }); return; }
          changed();
          return;
        }
        if(hit?.kind==='enemyPage' && !targeting && !modal){enemyPage=(enemyPage+1)%hit.pages;changed();return;}
        if (hit?.kind === 'inspect') {void inspectPlayer(hit.id);return;}
        if (hit?.kind === 'pile') {openPile(hit.id);return;}
        if (hit?.kind === 'shopTab' && shopView()) { switchShop(hit.id); return; }
        if (hit?.kind === 'endTurn') { endTurn(); return; }
        if (hit?.kind === 'entity') {
          // With an action armed a click picks the target; otherwise it only looks.
          if (targeting) { if (targetIds().includes(hit.id)) submitTarget(hit.id); return; }
          if(state.phase==='combat'){selectHit(hit);toggleUnit(hit.id);}else inspectEntity(hit.id); return;
        }
      }
      if (event.button === 'wheel-up' || event.button === 'wheel-down') {
        const step = event.button === 'wheel-up' ? -1 : 1;
        // An open detail pane pages first, before moving the option list.
        if (modal?.detail) { pageDetail(step * 3); return; }
        // §D: on the map the wheel looks around the act instead of moving the cursor.
        if (mapNavigation()) {
          const drawn = mapLines(state.mapView, columns);
          mapScroll = Math.max(0, Math.min(Math.max(0, drawn.total - drawn.span), (mapScroll ?? drawn.from) - step));
          changed(); return;
        }
        moveTo(index + step);
        return;
      }
      if (event.button !== 'left') return;
      const hit = hitAt(event.x, event.y);
      if (!hit) return;
      if (hit.kind === 'item') {
        if (shopView()) {
          // Prices and stock may change between painting and clicking.
          if (hit.revision !== state.revision) { changed(); return; }
          const row = items().find(row => row.id === hit.id);
          if (row?.shop && ['buy', 'removeCard'].includes(row.action?.type)) clickRow(hit.id);
          else if (row?.action?.type === 'continue' && hit.confirm && selected === hit.id) clickRow(hit.id);
          else hoverRow(hit.id);
          return;
        }
        clickRow(hit.id); return;
      }

    },
  };
  const renderGame = screen.render;
  screen.render = (width, rows) => delegation.active() ? delegation.render(width, rows) : chat.paint(renderGame(width, rows), width, rows);
  screen.paste = text => delegation.active() ? delegation.paste(text) : chat.paste(text);
  const gameMouse = screen.mouse;
  screen.mouse = event => delegation.active() ? delegation.mouse(event) : gameMouse(event);
  // Settings list the shortcuts, one per row.
  function openSettings(){
    choose('快捷键', helpLines(), ()=>{}, {shortcuts:true});
  }
  function stopGame() { stopMotion(); closed = true; connectionGeneration++; actionQueue.stop(); chat.stop(); connection?.close(); }
  return { screen, open: connect, start: () => guard(loadRooms), stop: stopGame, accept };
}
export async function run(context) {
  const game = createLobby(context, createScreen);
  try { const page = context.openScreen(game.screen); void game.start(); await page; }
  finally { game.stop(); }
}


// Exported so a test can read a drawn act back the way a player does.
export { drawMap };
