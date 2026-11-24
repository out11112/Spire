import { stripVTControlCharacters } from 'node:util';
import stringWidth from 'string-width';
const segments = new Intl.Segmenter('zh-CN', { granularity: 'grapheme' });
const sgr = /\x1b\[[0-9;]*m/g;
const plain = (s: string) => stripVTControlCharacters(s).replace(/\r\n?/g, '\n').replace(/\t/g, '    ').replace(/[\x00-\x08\x0b-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/g, '');
function color(code: string): boolean {
  const values = code.slice(2, -1).split(';').map(v => Number(v || 0));
  for (let i = 0; i < values.length; i++) {
    const n = values[i]!;
    if (n === 0 || n === 39 || n === 49 || n >= 30 && n <= 37 || n >= 40 && n <= 47 || n >= 90 && n <= 97 || n >= 100 && n <= 107) continue;
    if (n !== 38 && n !== 48) return false;
    const mode = values[++i], count = mode === 5 ? 1 : mode === 2 ? 3 : 0;
    if (!count || i + count >= values.length) return false;
    for (let j = 0; j < count; j++) { const v = values[++i]!; if (!Number.isInteger(v) || v < 0 || v > 255) return false; }
  }
  return true;
}
export function cleanAnsi(text: string): string {
  // Strip string controls as a unit before retaining only validated color SGR.
  text = text.replace(/\x1b\][\s\S]*?(?:\x07|\x1b\\|$)/g, '').replace(/\x1b[P^_][\s\S]*?(?:\x1b\\|$)/g, '');
  let out = '', at = 0;
  for (const match of text.matchAll(sgr)) {
    out += plain(text.slice(at, match.index));
    if (color(match[0])) out += match[0];
    at = match.index + match[0].length;
  }
  return out + plain(text.slice(at));
}
export function ansiRows(text: string, width: number, base = '\x1b[39;49m'): string[] {
  text = cleanAnsi(text); const rows: string[] = []; let line = '', used = 0, fg = '', bg = '';
  const flush = () => { rows.push(line + base); line = fg + bg; used = 0; };
  for (const part of text.split(/(\x1b\[[0-9;]*m)/g)) {
    if (part.startsWith('\x1b[')) {
      const v = part.slice(2, -1).split(';').map(n => Number(n || 0));
      for (let i = 0; i < v.length; i++) {
        const n = v[i]!;
        if (n === 0) { fg = ''; bg = ''; line += base; }
        else if (n === 39) { fg = ''; line += base + bg; }
        else if (n === 49) { bg = ''; line += base + fg; }
        else {
          const code = [n]; if (n === 38 || n === 48) { const mode = v[++i]!; code.push(mode); for (let j = 0; j < (mode === 5 ? 1 : 3); j++) code.push(v[++i]!); }
          const escape = `\x1b[${code.join(';')}m`;
          if (n === 38 || n >= 30 && n <= 37 || n >= 90 && n <= 97) fg = escape; else bg = escape;
          line += escape;
        }
      }
    } else for (const { segment } of segments.segment(part)) {
      if (segment === '\n') { flush(); continue; }
      const size = stringWidth(segment); if (used + size > width && used) flush();
      if (size <= width) { line += segment; used += size; }
    }
  }
  flush(); return rows;
}
