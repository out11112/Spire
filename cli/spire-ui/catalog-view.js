import { ACCENT, TEXT, MUTED, SELECTED, RESET } from './palette.js';
import { panelRule, panelTitle, panelText, searchRow, hintRow } from './panel.js';
import { clean, cut, pad, wrap, textWidth, listWindow, tabStrip } from './ui-layout.js';
export { clean, cut, pad, wrap, textWidth } from './ui-layout.js';

export function filterCatalog(items, query) {
  const tokens = query.normalize('NFC').toLowerCase().trim().split(/\s+/).filter(Boolean);
  return items.filter(item => tokens.every(token => {
    const needle = [...token]; let at = 0;
    for (const char of clean(`${item.id} ${item.name} ${item.group ?? ''} ${item.kind ?? ''} ${item.rarity ?? ''}`).normalize('NFC').toLowerCase()) {
      if (char === needle[at] && ++at === needle.length) return true;
    }
    return false;
  }));
}
/** A panel title and the category tabs below it; the tabs are indented like panel text. */
export function libraryHeader(tabs, group, width, title = 'Spire · 资料库', meta = '') {
  const strip = tabStrip(tabs, group, Math.max(1, width), { selected: SELECTED, text: TEXT });
  return {
    rows: [panelTitle(title, meta, width), { text: strip.text }],
    hits: strip.hits.map(hit => ({ ...hit, x: hit.x, y: 1 })),
  };
}
export const LIBRARY_HINTS = [['Enter', '详情'], ['Tab', '分类'], ['←→', '翻页'], ['输入', '搜索'], ['Esc', '返回']];
/**
 * The library page: rule, title with the position, category tabs, search line,
 * list and preview (side by side from 110 columns, stacked below otherwise),
 * then a note and the keys.
 */
export function renderLibrary({ width, height, tabs, title, group, query, listing, detail, index, offset, top = 0, loading, note, version }) {
  const total = listing?.total ?? 0, items = listing?.items ?? [];
  const position = `${items.length ? offset + index + 1 : 0}/${total} · 第 ${Math.floor(offset / 40) + 1} 页${version && width >= 70 ? ' · 本地资料 ' + version : ''}`;
  const header = libraryHeader(tabs, group, width, title, position);
  const rows = [panelRule(width), ...header.rows, searchRow(query, width, '输入名称搜索…')];
  const hits = header.hits.map(hit => ({ ...hit, y: hit.y + 1 }));
  const footer = [...(note ? panelText(note, width, 1, 'error') : []), hintRow(LIBRARY_HINTS, width)];
  const wide = width >= 110, leftWidth = wide ? Math.floor((width - 3) * .56) : width;
  const detailWidth = wide ? width - leftWidth - 3 : width;
  const preview = (detail ? [detail.name, ...detail.lines] : [loading ? '正在加载详情…' : '选择条目查看详情'])
    .flatMap(line => wrap(line, detailWidth));
  const bodyHeight = Math.max(1, height - rows.length - footer.length);
  const previewRows = wide ? bodyHeight - 1 : Math.min(5, Math.max(3, preview.length), Math.max(1, bodyHeight - 4));
  const listRows = Math.max(1, bodyHeight - 1 - (wide ? 0 : previewRows + 1));
  const groupWidth = leftWidth >= 48 ? 18 : 12, nameWidth = leftWidth - groupWidth - 2;
  top = listWindow(items.length, index, top, listRows);
  rows.push({ text: MUTED + '  ' + pad('名称', nameWidth) + pad('分类', groupWidth) + (wide ? ' │ 条目详情' : '') + RESET });
  for (let i = 0; i < listRows; i++) {
    const at = top + i, item = items[at];
    let left = ' '.repeat(leftWidth);
    if (item) {
      const active = at === index;
      hits.push({ index: at, y: rows.length, x: 0, w: leftWidth });
      left = (active ? ACCENT + '\x1b[1m❯ ' : TEXT + '  ') + pad(item.name, nameWidth) + '\x1b[22m' + MUTED + pad(item.group ?? '', groupWidth) + RESET;
    } else if (!items.length && i === 0) left = MUTED + pad(loading ? '加载中…' : '没有匹配条目', leftWidth) + RESET;
    rows.push({ text: left + (wide ? MUTED + ' │ ' + (i === 0 && detail ? ACCENT + '\x1b[1m' : TEXT) + (preview[i] ?? '') + RESET : '') });
  }
  if (!wide) {
    rows.push({ text: MUTED + '─'.repeat(Math.max(0, width)) + RESET });
    for (let i = 0; i < previewRows; i++) {
      const overflow = i === previewRows - 1 && preview.length > previewRows;
      const line = overflow ? cut(preview[i], detailWidth - textWidth('… Enter 详情')) + '… Enter 详情' : preview[i] ?? '';
      rows.push({ text: line, tone: i === 0 ? 'title' : 'text' });
    }
  }
  while (rows.length < height - footer.length) rows.push({ text: '' });
  rows.splice(height - footer.length);
  rows.push(...footer);
  return { rows: rows.slice(0, height), hits: hits.filter(hit => hit.y < height - footer.length), top };
}
