import stringWidth from 'string-width';
const segmenter = new Intl.Segmenter('zh-CN', { granularity: 'grapheme' });
const RESET = '\x1b[0m', END_LINK = '\x1b]8;;\x1b\\';
interface Glyph { text: string; width: number; style: string; link: string }
// Line-breaking punctuation rules for CJK text: these never start or end a row.
const CLOSING = /^[，。、；：！？）」』》〉】〕｝…—,.;:!?)\]}%’”·・～]$/u, OPENING = /^[（「『《〈【〔｛“‘([{]$/u;
const blank = (glyph: Glyph) => /^ +$/.test(glyph.text);
/** Wrap sanitized SGR/OSC-8 text. Each row closes styles and links independently. */
export function wrapAnsi(text: string, columns: number): string[] {
  const width = Number.isFinite(columns) ? Math.max(1, Math.floor(columns)) : 1;
  const styles = new Map<string, string>(); let link = '';
  const rows: string[] = [], glyphs: Glyph[] = [];
  const paint = (line: Glyph[]) => {
    let out = '', active = '', href = '';
    for (const glyph of line) {
      if (href !== glyph.link) { if (href) out += END_LINK; if (glyph.link) out += glyph.link; href = glyph.link; }
      if (active !== glyph.style) { if (active) out += RESET; out += glyph.style; active = glyph.style; }
      out += glyph.text;
    }
    return out + (href ? END_LINK : '') + (active ? RESET : '');
  };
  const flush = () => {
    if (!glyphs.length) { rows.push(''); return; }
    let start = 0;
    while (start < glyphs.length) {
      let end = start, used = 0, space = -1, content = false;
      while (end < glyphs.length && used + glyphs[end]!.width <= width) {
        const glyph = glyphs[end]!;
        if (/^ +$/.test(glyph.text)) { if (content) space = end; } else content = true;
        used += glyph.width; end++;
      }
      let next = end;
      // Wide characters may break on either side, so a CJK run need not move whole to the next row.
      let soft = -1;
      if (end < glyphs.length && !blank(glyphs[end]!)) for (let j = end; j > start; j--) {
        const before = glyphs[j - 1]!, after = glyphs[j]!;
        if (!blank(before) && (before.width > 1 || after.width > 1) && !CLOSING.test(after.text) && !OPENING.test(before.text)) { soft = j; break; }
      }
      if (soft > space) { end = soft; next = soft; }
      else if (end < glyphs.length && space > start && !blank(glyphs[end]!)) {
        end = space; next = space + 1;
        while (next < glyphs.length && glyphs[next]!.text === ' ') next++;
      } else if (end < glyphs.length) {
        while (next < glyphs.length && glyphs[next]!.text === ' ') next++;
      }
      rows.push(paint(glyphs.slice(start, end))); start = next;
    }
    glyphs.length = 0;
  };
  for (const part of text.split(/(\x1b\[[0-9;]*m|\x1b\]8;[^;\x07\x1b]*;[^\x07\x1b]*(?:\x07|\x1b\\))/g)) {
    if (part.startsWith('\x1b]8;')) { link = /^\x1b\]8;;(?:\x07|\x1b\\)$/.test(part) ? '' : part; continue; }
    if (part.startsWith('\x1b[')) {
      const values = part.slice(2, -1).split(';').map(n => Number(n || 0));
      for (let i = 0; i < values.length; i++) {
        const n = values[i]!;
        if (n === 0) { styles.clear(); continue; }
        const off: Record<number, string[]> = { 22: ['1', '2'], 23: ['3'], 24: ['4'], 29: ['9'], 39: ['fg'], 49: ['bg'] };
        if (off[n]) { for (const key of off[n]) styles.delete(key); continue; }
        const codes = [n];
        if (n === 38 || n === 48) { const mode = values[++i]!; codes.push(mode); for (let j = 0; j < (mode === 2 ? 3 : 1); j++) codes.push(values[++i]!); }
        const key = n === 38 || n >= 30 && n <= 37 || n >= 90 && n <= 97 ? 'fg' : n === 48 || n >= 40 && n <= 47 || n >= 100 && n <= 107 ? 'bg' : String(n);
        styles.set(key, `\x1b[${codes.join(';')}m`);
      }
      continue;
    }
    for (const { segment } of segmenter.segment(part)) {
      if (segment === '\n') { flush(); continue; }
      const size = stringWidth(segment);
      glyphs.push({ text: size > width ? '�' : segment, width: Math.min(size, width), style: [...styles.values()].join(''), link });
    }
  }
  flush(); return rows;
}
