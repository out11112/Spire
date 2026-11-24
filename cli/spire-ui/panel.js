// The host's panel parts (src/panel.ts), drawn as extension rows so Spire
// screens look like the chat's menus, forms and pages. Same characters, same
// colours; tests/spire-panel.test.mjs compares the two.
import { ACCENT, TEXT, MUTED, ERROR, DANGER, RESET } from './palette.js';
import { clean, cut, textWidth } from './ui-layout.js';

const BOLD = '\x1b[1m', NORMAL = '\x1b[22m';
const reset = NORMAL + MUTED;
const segmenter = new Intl.Segmenter('zh-CN', { granularity: 'grapheme' });
const chars = text => [...segmenter.segment(text)].map(part => part.segment);
/** Plain text cut to `width` cells, ending in … when it had to be cut. */
export function clip(text, width, padded = false) {
  text = clean(text); width = Math.max(0, Math.floor(width));
  const truncated = textWidth(text) > width;
  let result = truncated ? cut(text, Math.max(0, width - 1)) + (width ? '…' : '') : text;
  return result + (padded ? ' '.repeat(Math.max(0, width - textWidth(result))) : '');
}
const row = (text, tone = 'muted') => ({ text, tone });

/** An accent rule across the width, optionally with a section name and right-hand text inside it. */
export function panelRule(width, label = '', right = '') {
  width = Math.max(0, width);
  if (!label && !right) return row(ACCENT + '─'.repeat(width) + RESET);
  const left = label ? `── ${clip(label, Math.max(0, width - 8))} ` : '';
  const end = right ? ` ${clip(right, Math.max(0, width - textWidth(left) - 6))} ──` : '';
  const fill = Math.max(0, width - textWidth(left) - textWidth(end));
  return row(ACCENT + left + '─'.repeat(fill) + end + RESET);
}
/**
 * Bold accent title with grey text on the right, as `panelTitle` in the host. Game
 * screens and lobby panels draw from column 0 within the host's content inset.
 */
export function panelTitle(title, meta, width, indent = 0) {
  const right = clip(meta ?? '', Math.max(0, width - 6));
  const left = clip(' '.repeat(indent) + title, Math.max(0, width - (right ? textWidth(right) + 2 : 0)));
  return row(ACCENT + BOLD + left + reset + ' '.repeat(Math.max(0, width - textWidth(left) - textWidth(right))) + right);
}
/** Grey description text wrapped below a title, at most `maxRows` rows. */
export function panelText(text, width, maxRows = 2, tone = 'muted') {
  const rows = [], room = Math.max(0, width);
  if (!room || maxRows < 1) return [];
  for (const line of String(text ?? '').split(/\r?\n/)) {
    let current = '', size = 0;
    for (const char of chars(clean(line))) {
      const n = textWidth(char); if (n > room) continue;
      if (size + n > room) { rows.push(current); current = ''; size = 0; }
      current += char; size += n;
    }
    rows.push(current);
  }
  if (rows.length > maxRows) rows[maxRows - 1] = clip(rows[maxRows - 1] + '…', width);
  return rows.slice(0, maxRows).map(text => row(tone === 'error' ? ERROR + text + RESET : text, tone === 'error' ? 'text' : tone));
}
/**
 * One choice: `❯` and bold accent when selected, an optional `1.` number, a grey
 * hint on the right. `focusColumn` is left unset: the row carries its own marker.
 */
export function optionRow(item, { selected = false, number, width, danger = false, indent = 0 }) {
  const prefix = ' '.repeat(indent) + (selected ? '❯ ' : '  ') + (number === undefined ? '' : `${number}. `);
  const hint = clip(item.hint ?? '', Math.max(0, Math.floor(width / 2) - 3));
  const label = clip(prefix + item.label, Math.max(0, width - (hint ? textWidth(hint) + 2 : 0)));
  // Danger is Spire's enemy-target red, a shade brighter than the host's.
  const colour = item.disabled ? MUTED : item.danger || danger ? DANGER : selected ? ACCENT : TEXT;
  return row(colour + (selected && !item.disabled ? BOLD : NORMAL) + label + reset
    + ' '.repeat(Math.max(0, width - textWidth(label) - textWidth(hint))) + hint);
}
/** The search line: typed text, or a grey placeholder while empty. */
export function searchRow(query, width, placeholder = '搜索…') {
  return { ...row(clip('⌕ ' + (query || placeholder), width), query ? 'text' : 'muted'),
    cursorColumn: Math.max(0, Math.min(width - 1, textWidth('⌕ ' + query))) };
}
/** `label  ‹ value ›`, the host form's toggle field. */
export function toggleRow(label, value, { active = false, width, labelWidth = 0 }) {
  const name = clip(clip(label, Math.max(labelWidth, textWidth(label)), true) + '  ', Math.max(0, width - 2));
  const shown = clip(`‹ ${value} ›`, Math.max(0, width - textWidth(name)));
  return row((active ? ACCENT + BOLD : MUTED) + name + NORMAL + TEXT + shown + RESET);
}
/** Dim italic lowercase hints matching Claude Code (`hintRow` in src/panel.ts); pairs that do not fit are dropped from the end. */
export function hintRow(pairs, width, indent = 0) {
  if (width <= 0) return row('');
  let remaining = Math.max(0, width - indent), text = ' '.repeat(indent);
  for (const [i, [rawKey, description]] of pairs.entries()) {
    const key = String(rawKey).toLowerCase();
    const separator = i ? ' · ' : '', content = `${key} ${description}`;
    if (textWidth(separator + content) > remaining && i) break;
    const shown = clip(content, Math.max(0, remaining - separator.length));
    text += MUTED + '\x1b[2;3m' + separator + shown + '\x1b[22;23m';
    remaining -= textWidth(separator + shown);
  }
  return row(text);
}
