import { stripVTControlCharacters } from 'node:util';

import { MUTED, RESET } from './palette.js';

const segmenter = new Intl.Segmenter('zh-CN', { granularity: 'grapheme' });
const sgr = /^\x1b\[[0-9;]*m$/;
export const clean = value => stripVTControlCharacters(String(value ?? ''))
  .replace(/[\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/g, ' ');
const graphemes = text => [...segmenter.segment(text)].map(part => part.segment);
const cellWidth = text => /[\p{Emoji_Presentation}\p{Regional_Indicator}\u20e3\p{Script=Han}\p{Script=Hangul}\p{Script=Hiragana}\p{Script=Katakana}\u1100-\u115f\u2329\u232a\u2e80-\u303e\u3040-\ua4cf\uac00-\ud7a3\uf900-\ufaff\ufe10-\ufe19\ufe30-\ufe6f\uff00-\uff60\uffe0-\uffe6]/u.test(text) || /\p{Extended_Pictographic}.*\ufe0f/u.test(text) ? 2 : /^[\p{Mark}\p{Default_Ignorable_Code_Point}]+$/u.test(text) ? 0 : 1;
const tokens = text => String(text ?? '').split(/(\x1b\[[0-9;]*m)/)
  .flatMap(part => sgr.test(part) ? [part] : graphemes(clean(part)));
export const textWidth = text => graphemes(clean(text)).reduce((total, part) => total + cellWidth(part), 0);
export function cut(text, width) {
  width = Math.max(0, Math.floor(width));
  let result = '', used = 0;
  for (const token of tokens(text)) {
    if (sgr.test(token)) { result += token; continue; }
    const size = cellWidth(token);
    if (used + size > width) return result.includes('\x1b') ? result + RESET : result;
    result += token; used += size;
  }
  return result;
}
export const pad = (text, width) => {
  const value = cut(text, width);
  return value + ' '.repeat(Math.max(0, width - textWidth(value)));
};
export function wrap(text, width) {
  width = Math.max(1, Math.floor(width));
  const rows = [];
  for (const paragraph of String(text ?? '').split('\n')) {
    let line = '', used = 0, styles = '';
    for (const token of tokens(paragraph)) {
      if (sgr.test(token)) { line += token; styles = token === RESET ? '' : styles + token; continue; }
      const size = cellWidth(token);
      if (used + size > width && used) {
        rows.push(line + (styles ? RESET : '')); line = styles; used = 0;
      }
      if (size <= width) { line += token; used += size; }
    }
    rows.push(line + (styles ? RESET : ''));
  }
  return rows;
}
export function listWindow(count, index, top, height) {
  height = Math.max(1, height);
  if (index < top) top = index;
  if (index >= top + height) top = index - height + 1;
  return Math.max(0, Math.min(top, Math.max(0, count - height)));
}
/** One tab row with clickable overflow arrows, without changing category keys. */
export function tabStrip(tabs, group, width, colours) {
  if (!tabs.length) return { text: '', hits: [] };
  const active = Math.max(0, tabs.findIndex(tab => tab.id === group));
  const labels = tabs.map(tab => cut(' ' + tab.name + ' ', Math.max(4, width - 4)));
  let first = 0;
  while (first < active && labels.slice(first, active + 1).reduce((n, label) => n + textWidth(label) + 1, 0) > width - 4) first++;
  let text = '', column = 0;
  const hits = [];
  if (first) { text = MUTED + '‹ ' + RESET; hits.push({ group: tabs[first - 1].id, x: 0, w: 1 }); column = 2; }
  for (let i = first; i < tabs.length; i++) {
    const label = labels[i], gap = column > (first ? 2 : 0) ? 1 : 0;
    const reserve = i < tabs.length - 1 ? 2 : 0;
    if (column + gap + textWidth(label) + reserve > width) {
      hits.push({ group: tabs[i].id, x: Math.max(0, width - 1), w: 1 });
      text = pad(text, width - 1) + MUTED + '›' + RESET;
      break;
    }
    if (gap) { text += ' '; column++; }
    hits.push({ group: tabs[i].id, x: column, w: textWidth(label) });
    text += (i === active ? colours.selected + colours.text + '\x1b[1m' : MUTED) + label + RESET;
    column += textWidth(label);
  }
  return { text: cut(text, width), hits };
}
