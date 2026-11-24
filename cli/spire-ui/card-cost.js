import { BUFF, PILE_EXHAUST, paint } from './palette.js';

export const cardCost = (card, coloured = false) => {
  const free = card.freeThisTurn || card.freeThisCombat;
  const energy = coloured && card.cost === 0 && (card.freeEnergy || free) ? paint(BUFF, '0') : card.cost;
  const stars = coloured && card.starCost === 0 && (card.freeStars || free || card.freeStarsThisTurn) ? paint(BUFF, '0') : card.starCost;
  return `[${energy}${card.starCost === undefined ? '' : `,${stars}`}]`;
};

// Match complete, known annotation clauses; a colon in a card's main effect
// or an unfamiliar rule must never make the effect disappear.
const annotations = [
  // Official enchantment and affliction wording (current servers).
  ['墨影[:：]这张牌造成(\\d+)层虚弱。', (_, n) => `墨影 ${n}`],
  ['播种[:：]你在每场战斗中第一次打出这张牌时，获得(\\d+)能量。(（本场已生效）)?', (_, n, used) => `播种 ${n}${used ? '（已生效）' : ''}`],
  ['黏糊[:：]这张牌获得消耗。当被打出时，这张牌的格挡值永久增加1点。', () => '黏糊'],
  ['克隆[:：]这张牌能在休息处被复制。', () => '克隆'],
  ['本能[:：]这张牌的攻击伤害翻倍。', () => '本能'],
  ['注能[:：]这张牌在每场战斗开始时自动打出。', () => '注能'],
  ['特兹卡塔拉的余烬[:：]费用为0，造成3 点额外伤害，且获得永恒。', () => '特兹卡塔拉的余烬'],
  ['伶俐[:：]获得(\\d+)点格挡。', (_, n) => `伶俐 ${n}`],
  ['动量[:：]在本场战斗中，每次打出就增加这张牌的攻击伤害(\\d+)点。（已增加 (\\d+)）', (_, n, total) => `动量 ${n}（累计 +${total}）`],
  ['王室认证[:：]这张牌拥有固有和保留。', () => '王室认证'],
  ['锋利[:：]这张牌上的伤害值增加(\\d+)点。', (_, n) => `锋利 ${n}`],
  ['迅速[:：]你第一次打出这张牌时，抽(\\d+)张牌。(（本场已使用）)?', (_, n, used) => `迅速 ${n}${used ? '（已用）' : ''}`],
  ['灵巧[:：]这张牌获得的格挡值增加(\\d+)点。', (_, n) => `灵巧 ${n}`],
  ['蛇行[:：]当你抽到这张牌时，使其费用在0到3之间随机变化。', () => '蛇行'],
  ['腐化[:：]造成的伤害增加50%，但会失去2生命。', () => '腐化'],
  ['活力[:：]第一次打出这张牌时，造成(\\d+)点额外伤害。(（本场已使用）)?', (_, n, used) => `活力 ${n}${used ? '（已用）' : ''}`],
  ['华彩[:：]这张牌每场战斗能够重放一次。(（本场已使用）)?', (_, used) => `华彩${used ? '（已用）' : ''}`],
  ['灵魂之力[:：]这张牌失去消耗。', () => '灵魂之力'],
  ['完美契合[:：]每当这张牌要被洗入抽牌堆时，将其放在抽牌堆顶。', () => '完美契合'],
  ['涡旋[:：]这张牌获得重放1。', () => '涡旋'],
  ['稳定[:：]这张牌获得保留。', () => '稳定'],
  ['缠身[:：]能量费用增加1。(（当前未生效）)?', (_, off) => `缠身${off ? '（未生效）' : ''}`],
  ['邪咒[:：]这张牌获得虚无。(（当前未生效）)?', (_, off) => `邪咒${off ? '（未生效）' : ''}`],
  ['昏眩[:：]你在本回合只能打出1张牌。(（当前未生效）)?', (_, off) => `昏眩${off ? '（未生效）' : ''}`],
  ['魂缚[:：]每回合只能打出1张魂缚卡牌。卡牌会在回合结束时失去魂缚。(（当前未生效）)?', (_, off) => `魂缚${off ? '（未生效）' : ''}`],
  ['污染[:：]打出时获得(\\d+)层污染。', (_, n) => `污染 ${n}`],
  ['流电[:：]打出这张牌时受到(\\d+)点伤害。', (_, n) => `流电 ${n}`],
  ['烟雾[:：]你在本回合无法再打出更多技能牌。回合结束时消除。(（当前未生效）)?', (_, off) => `烟雾${off ? '（未生效）' : ''}`],
  // Wording from servers before the official text.
  ['墨影[:：](?:卡牌效果完成后|打出后)施加 1 虚弱', () => '墨影 1'],
  ['播种[:：]每场首次(?:完成卡牌效果后|打出)获得 (\\d+) 能量(（本场已生效）)?', (_, n, used) => `播种 ${n}${used ? '（已生效）' : ''}`],
  ['播种[:：]本场已生效', () => '播种 1（已生效）'],
  ['黏糊[:：]消耗；格挡增加 (-?\\d+)，每次打出永久增加 1', (_, n) => `黏糊 ${Number(n) + 1}`],
  ['克隆[:：]营地复制选项会复制此牌', () => '克隆'],
  ['本能[:：]攻击伤害翻倍', () => '本能'],
  ['注能[:：]位于初始抽牌堆底，首回合自动打出', () => '注能'],
  ['特兹卡塔拉的余烬[:：]基础费用降至 0，攻击伤害增加 3，永恒', () => '特兹卡塔拉的余烬'],
  ['伶俐[:：]每次打出获得 (\\d+) 基础格挡', (_, n) => `伶俐 ${n}`],
  ['动量[:：]每次打出后本场基础伤害增加 (\\d+)（已增加 (\\d+)）', (_, n, total) => `动量 ${n}（累计 +${total}）`],
  ['王室认证[:：]固有、保留', () => '王室认证'],
  ['锋利[:：]攻击基础伤害增加 (\\d+)', (_, n) => `锋利 ${n}`],
  ['迅速[:：]每场首次打出后抽 (\\d+) 张牌(（本场已使用）)?', (_, n, used) => `迅速 ${n}${used ? '（已用）' : ''}`],
  ['灵巧[:：]卡牌每次获得格挡时增加 (\\d+) 点基础格挡', (_, n) => `灵巧 ${n}`],
  ['蛇行[:：]每次抽到并留在手中时，将本场能量费用随机设为 0–3', () => '蛇行'],
  ['腐化[:：]攻击伤害提高 50%，打出后受到 2 点无视格挡的无加成伤害', () => '腐化'],
  ['活力[:：]每场战斗首次打出的攻击伤害增加 (\\d+)(（本场已使用）)?', (_, n, used) => `活力 ${n}${used ? '（已用）' : ''}`],
  ['华彩[:：]每场战斗首次打出时额外重放一次(（本场已使用）)?', (_, used) => `华彩${used ? '（已用）' : ''}`],
  ['灵魂之力[:：]移除消耗关键词', () => '灵魂之力'],
  ['完美契合[:：]战斗中洗牌时置于抽牌堆顶（首次洗牌除外）', () => '完美契合'],
  ['涡旋[:：]每次打出额外重放一次', () => '涡旋'],
  ['稳定[:：]保留', () => '稳定'],
  ['缠身[:：]费用随持有者的缠身层数增加，自己回合结束时清除', () => '缠身'],
  ['缠身[:：]当前不增加费用', () => '缠身（未生效）'],
  ['邪咒[:：]持有者具有邪咒能力时提供虚无', () => '邪咒'],
  ['邪咒[:：]当前不提供虚无', () => '邪咒（未生效）'],
  ['昏眩[:：]本回合打出过任何卡牌后不能打出，自己回合结束时清除', () => '昏眩'],
  ['昏眩[:：]当前不限制出牌', () => '昏眩（未生效）'],
  ['魂缚[:：]每回合只能打出一张魂缚卡牌，自己回合结束前清除附着', () => '魂缚'],
  ['魂缚[:：]当前不限制出牌', () => '魂缚（未生效）'],
  ['污染[:：]打出后受到的每段攻击伤害增加 (\\d+)，持续至敌方回合结束', (_, n) => `污染 ${n}`],
  ['流电[:：]施加者存活时，打出后受到 (\\d+) 点可格挡伤害', (_, n) => `流电 ${n}`],
  ['烟雾[:：]本回合无法打出，自己回合结束清除', () => '烟雾'],
  ['烟雾[:：]当前不限制出牌', () => '烟雾（未生效）'],
  ['永恒[:：]不能移除或变换', () => '永恒'],
  ['奇巧[:：]被主动弃掉时自动打出，回合结束清空手牌不触发', () => '奇巧'],
  ['覆甲[:：]回合结束获得格挡，之后每回合衰减 1 (\\d+)', (_, n) => `覆甲 ${n}`],
].map(([pattern, summary]) => [new RegExp(`(^| · |；)${pattern}(?=$| · |；)`, 'g'), summary]);

const enchantmentNames = new Set(['墨影', '播种', '黏糊', '克隆', '本能', '注能', '特兹卡塔拉的余烬',
  '伶俐', '动量', '王室认证', '锋利', '迅速', '灵巧', '蛇行', '腐化', '活力', '华彩', '灵魂之力', '完美契合', '涡旋', '稳定']);
export const compactCardText = (text, coloured = false, full = false) => annotations.reduce((result, [pattern, summary]) =>
  result.replace(pattern, (match, prefix, ...args) => {
    const original = match.slice(prefix.length), name = original.split(/[:：]/, 1)[0];
    const replacement = full ? original : summary(match, ...args.slice(0, -2));
    return prefix + (coloured && enchantmentNames.has(name) ? paint(PILE_EXHAUST, name) + replacement.slice(name.length) : replacement);
  }), String(text ?? ''));
export const cardDescription = (card, coloured = false, full = false) => compactCardText(card.description, coloured, full);

const validCost = cost => Number.isSafeInteger(cost) && cost >= 0 || cost === 'X' || cost === '—';
const validDisplay = card => card && typeof card.id === 'string' && typeof card.name === 'string'
  && typeof card.description === 'string' && validCost(card.cost)
  && (card.starCost === undefined || Number.isSafeInteger(card.starCost) && card.starCost >= 0 || card.starCost === 'X')
  && ['freeEnergy', 'freeStars'].every(key => card[key] === undefined || typeof card[key] === 'boolean');

// Presentation metadata never turns a choice row into a playable hand card.
export const optionCards = row => Array.isArray(row.displayCards) && row.displayCards.length > 0
  && row.displayCards.length <= 1000 && row.displayCards.every(validDisplay)
  && (row.displayPrefix === undefined || typeof row.displayPrefix === 'string') ? row.displayCards : undefined;

export const optionLabel = (row, full = false) => {
  if (optionCards(row)) return (row.displayPrefix ?? '') + row.displayCards
    .map(card => `${card.name} ${cardCost(card, true)} ${cardDescription(card, true, full)}`).join('；');
  const label = row.fullLabel ?? row.label;
  if (!['choose', 'reward', 'customReward'].includes(row.action?.type)) return label;
  return label.replace(/^(.+?\[[0-9X—,]+\]\s+)([\s\S]*)$/, (_, prefix, text) => prefix + compactCardText(text, true, full));
};
