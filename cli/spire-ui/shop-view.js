import { cardCost, cardDescription } from './card-cost.js';
import { libraryHeader, clean, cut, pad, wrap, textWidth } from './catalog-view.js';

import { TEXT, MUTED, ERROR, ACCENT, RESET } from './palette.js';
import { hintRow } from './panel.js';
export const SHOP_GROUPS = [['', '全部'], ['card', '卡牌'], ['relic', '遗物'], ['potion', '药水'], ['removal', '删牌']];
const KINDS = { attack: '攻击', skill: '技能', power: '能力', status: '状态', curse: '诅咒', relic: '遗物', potion: '药水', removal: '服务' };
export const shopGoods = (options, group = '') => options.filter(row => row.shop && (!group || row.shop.kind === group));
/** Same tabs, columns and selection colours as the library; all offers are server data. */
export function renderShop({ width, height, options, group = '', selected, top = 0, note = '', hints = [], focused = true, unaffordableIds = new Set(), gold, potionCount = 0, potionCapacity = 3 }) {
  const goods = shopGoods(options, group), leave = options.find(row => row.action?.type === 'continue');
  const row = goods.find(item => item.id === selected), item = row?.shop;
  const tabs = SHOP_GROUPS.map(([id, name]) => ({ id, name: `${name} ${shopGoods(options, id).length}` }));
  const header = libraryHeader(tabs, group, width, '');
  const rows = header.rows.slice(1), hits = header.hits.map(hit => ({ kind: 'shopTab', id: hit.group, row: hit.y - 1, col: hit.x, width: hit.w, height: 1 }));
  const wide = width >= 110, leftWidth = wide ? Math.floor((width - 3) * .56) : width;
  const detailWidth = wide ? width - leftWidth - 3 : width;
  const description = item ? String(item.kind === 'card' ? cardDescription(item, true) : item.description ?? '').split('\n').flatMap(line => wrap(line, detailWidth)) : [];
  const footerHeight = 2;
  const bodyHeight = Math.max(1, height - rows.length - footerHeight);
  // Short descriptions use only the rows they need; the rest belongs to stock.
  const previewHeight = wide ? bodyHeight - 1 : Math.min(item ? description.length + 2 : 2, Math.max(3, Math.floor(bodyHeight * .4)));
  const listHeight = Math.max(1, wide ? bodyHeight - 1 : bodyHeight - previewHeight - 2);
  const index = goods.findIndex(row => row.id === selected);
  if (index >= 0) { if (index < top) top = index; if (index >= top + listHeight) top = index - listHeight + 1; }
  top = Math.max(0, Math.min(top, Math.max(0, goods.length - listHeight)));
  const nameWidth = leftWidth - 22;
  const columns = (name, kind, price, sale) => pad(name, nameWidth) + pad(kind, 9) + pad(price, 7) + pad(sale, 6);
  const preview = [];
  if (item) {
    preview.push({ text: cut(item.name, detailWidth), tone: 'title' });
    const restriction = Number.isFinite(gold) && item.price > gold ? ' · 金币不足' : item.kind === 'potion' && potionCount >= potionCapacity ? ' · 药水栏已满' : '';
    preview.push({ text: cut(`${KINDS[item.type] ?? item.type ?? ''}${item.cost === undefined ? '' : ` · 费用 ${cardCost(item)}`}${item.sale ? ' · 半价' : ''}${restriction}`, detailWidth), tone: 'muted' });
    const descriptionHeight = Math.max(1, previewHeight - 2);
    for (let i = 0; i < descriptionHeight; i++) {
      let text = description[i] ?? '';
      if (i === descriptionHeight - 1 && description.length > descriptionHeight) text = cut(text, detailWidth - 1) + '…';
      preview.push({ text, tone: 'text' });
    }
  } else {
    preview.push({ text: leave?.id === selected ? '离开商店' : '商品详情', tone: 'title' });
    preview.push({ text: cut(goods.length ? '选择商品查看效果与价格。' : '该分类已售罄，可切换分类。', detailWidth), tone: 'muted' });
  }
  rows.push({ text: MUTED + columns('  商品', '类型/费', '金币', '折扣') + (wide ? ' │ 商品详情' : '') + RESET });
  for (let i = 0; i < listHeight; i++) {
    const current = goods[top + i], active = current?.id === selected && focused;
    let text = ' '.repeat(leftWidth);
    if (current) {
      const shop = current.shop;
      hits.push({ kind: 'item', id: current.id, row: rows.length, col: 0, width: leftWidth, height: 1 });
      const kind = `${KINDS[shop.type] ?? shop.type ?? ''}${shop.cost === undefined ? '' : ` ${cardCost(shop)}`}`;
      text = (active ? '\x1b[1m' : '') + (unaffordableIds.has(current.id) ? ERROR : active ? ACCENT : TEXT) + columns('  ' + clean(shop.name), kind, String(shop.price), shop.sale ? '半价' : '') + RESET;
    } else if (!goods.length && i === 0) text = MUTED + pad('  该分类已售罄', leftWidth) + RESET;
    const detail = preview[i];
    rows.push({ text: text + (wide ? MUTED + ' │ ' + (detail?.tone === 'muted' ? MUTED : TEXT) + (detail?.text ?? '') + RESET : '') });
  }
  if (!wide) {
    rows.push({ text: '─'.repeat(width), tone: 'muted' });
    for (let i = 0; i < previewHeight; i++) {
      rows.push(preview[i] ?? { text: '' });
    }
  }
  while (rows.length < height - footerHeight) rows.push({ text: '' });
  rows.push({ text: cut(note, width), tone: 'muted' });
  // The way out shares the last row with the keys.
  const label = leave ? (leave.id === selected && focused ? '[Enter 确认]' : '[E 离开商店]') : '';
  if (leave) hits.push({ kind: 'item', id: leave.id, confirm: label === '[Enter 确认]', row: rows.length, col: 0, width: textWidth(label), height: 1 });
  const keys = hintRow(hints, Math.max(0, width - textWidth(label) - 2), label ? 2 : 0).text;
  rows.push({ text: (label === '[Enter 确认]' ? ACCENT + '\x1b[1m' : TEXT) + label + RESET + keys });
  return { rows: rows.slice(0, height), hits: hits.filter(hit => hit.row < height), top, listHeight };
}
