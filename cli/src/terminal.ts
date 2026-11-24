import stringWidth from 'string-width';
import { cleanAnsi } from './ansi.js';
import { wrapAnsi } from './ansi-wrap.js';
import { isKeyRelease, mousePrefix, parseKey, parseMouse } from './keys.js';
import type { ExtensionHeader, ExtensionKey, ExtensionRow, ExtensionScreen } from './extension-api.js';

const RESET = '\x1b[0m';
const TONES: Record<NonNullable<ExtensionRow['tone']>, string> = {
  text: '\x1b[39m',
  title: '\x1b[1;36m',
  muted: '\x1b[90m',
  selected: '\x1b[36m',
  error: '\x1b[31m',
};

const PASTE_START = '\x1b[200~';
const PASTE_END = '\x1b[201~';

function padToWidth(text: string, width: number): string {
  const clean = cleanAnsi(text);
  const w = stringWidth(clean);
  if (w === width) return clean + RESET;
  if (w < width) return clean + RESET + ' '.repeat(width - w);
  // Truncate safely by wrapping to width and taking first row.
  const first = wrapAnsi(clean, width)[0] ?? '';
  const fw = stringWidth(first);
  return first + RESET + ' '.repeat(Math.max(0, width - fw));
}

function renderHeader(header: ExtensionHeader, columns: number): string[] {
  const logo = (header.logo ?? []).slice(0, 3);
  const logoWidth = logo.reduce((max, row) => Math.max(max, stringWidth(cleanAnsi(row))), 0);
  const gap = logoWidth > 0 ? 2 : 0;
  const rightWidth = Math.max(1, columns - logoWidth - gap);
  const meta = [
    `\x1b[1;36m${header.title}\x1b[0m${header.version ? ` \x1b[90m${header.version}\x1b[0m` : ''}`,
    header.subtitle ? `\x1b[90m${header.subtitle}\x1b[0m` : '',
    '',
  ];
  const rows: string[] = [];
  for (let i = 0; i < 3; i++) {
    const left = logoWidth > 0 ? padToWidth(logo[i] ?? '', logoWidth) + ' '.repeat(gap) : '';
    rows.push(left + padToWidth(meta[i] ?? '', rightWidth));
  }
  rows.push(`\x1b[90m${'─'.repeat(columns)}\x1b[0m`);
  rows.push(' '.repeat(columns));
  return rows;
}

function parseLegacySequence(seq: string): { key?: ExtensionKey; length: number } | undefined {
  const table: Record<string, ExtensionKey> = {
    '\x1b[A': { name: 'up', sequence: '\x1b[A' },
    '\x1b[B': { name: 'down', sequence: '\x1b[B' },
    '\x1b[C': { name: 'right', sequence: '\x1b[C' },
    '\x1b[D': { name: 'left', sequence: '\x1b[D' },
    '\x1bOA': { name: 'up', sequence: '\x1bOA' },
    '\x1bOB': { name: 'down', sequence: '\x1bOB' },
    '\x1bOC': { name: 'right', sequence: '\x1bOC' },
    '\x1bOD': { name: 'left', sequence: '\x1bOD' },
    '\x1b[H': { name: 'home', sequence: '\x1b[H' },
    '\x1b[F': { name: 'end', sequence: '\x1b[F' },
    '\x1bOH': { name: 'home', sequence: '\x1bOH' },
    '\x1bOF': { name: 'end', sequence: '\x1bOF' },
    '\x1b[Z': { name: 'tab', shift: true, sequence: '\x1b[Z' },
    '\x1b[3~': { name: 'delete', sequence: '\x1b[3~' },
    '\x1b[5~': { name: 'pageup', sequence: '\x1b[5~' },
    '\x1b[6~': { name: 'pagedown', sequence: '\x1b[6~' },
    '\x1b[1~': { name: 'home', sequence: '\x1b[1~' },
    '\x1b[4~': { name: 'end', sequence: '\x1b[4~' },
  };
  for (const [prefix, key] of Object.entries(table)) {
    if (seq.startsWith(prefix)) return { key, length: prefix.length };
  }
  const csi = /^\x1b\[[0-9;?]*[A-Za-z~]/.exec(seq);
  if (csi) {
    const raw = csi[0];
    if (isKeyRelease(raw)) return { length: raw.length };
    const decoded = parseKey(raw);
    if (decoded) {
      const parts = decoded.split('+');
      const name = parts.pop()!;
      const ctrl = parts.includes('ctrl');
      const meta = parts.includes('alt');
      const shift = parts.includes('shift');
      const value = !ctrl && !meta && name.length === 1 ? name : undefined;
      return { key: { name, ctrl, meta, shift, ...(value ? { value } : {}), sequence: raw }, length: raw.length };
    }
    return { length: raw.length };
  }
  return undefined;
}

export class StandaloneTerminal {
  private screen: ExtensionScreen | undefined;
  private resolveScreen: (() => void) | undefined;
  private rejectScreen: ((error: unknown) => void) | undefined;
  private active = false;
  private mouseEnabled = false;
  private buffer = '';
  private pasting = false;
  private pasteBuffer = '';
  private escTimer: NodeJS.Timeout | undefined;
  private readonly onDataBound = (chunk: Buffer) => this.handleChunk(chunk.toString('utf8'));
  private readonly onResizeBound = () => this.render();

  get columns() {
    return Math.max(40, process.stdout.columns || 80);
  }

  get rows() {
    return Math.max(12, process.stdout.rows || 24);
  }

  wrapText(text: string, width: number): string[] {
    return wrapAnsi(cleanAnsi(text), Math.max(1, width));
  }

  openScreen(screen: ExtensionScreen): Promise<void> {
    if (this.screen) return Promise.reject(new Error('已有活动界面'));
    return new Promise<void>((resolve, reject) => {
      this.screen = screen;
      this.resolveScreen = resolve;
      this.rejectScreen = reject;
      this.enter(Boolean(screen.mouse));
      this.render();
    });
  }

  refreshScreen(): void {
    if (this.screen) this.render();
  }

  closeScreen(error?: unknown): void {
    const resolve = this.resolveScreen;
    const reject = this.rejectScreen;
    this.screen = undefined;
    this.resolveScreen = undefined;
    this.rejectScreen = undefined;
    this.leave();
    if (error !== undefined) reject?.(error);
    else resolve?.();
  }

  private enter(mouse: boolean): void {
    if (this.active) return;
    this.active = true;
    this.mouseEnabled = mouse;
    if (process.stdin.isTTY) {
      process.stdin.setRawMode(true);
      process.stdin.resume();
    }
    process.stdin.on('data', this.onDataBound);
    process.stdout.on('resize', this.onResizeBound);
    let init = '\x1b[?1049h\x1b[?25l\x1b[?2004h';
    if (mouse) init += '\x1b[?1000h\x1b[?1002h\x1b[?1006h';
    process.stdout.write(init);
  }

  private leave(): void {
    if (!this.active) return;
    this.active = false;
    clearTimeout(this.escTimer);
    process.stdin.off('data', this.onDataBound);
    process.stdout.off('resize', this.onResizeBound);
    if (process.stdin.isTTY) {
      try { process.stdin.setRawMode(false); } catch {}
      process.stdin.pause();
    }
    let cleanup = '\x1b[?2004l\x1b[?25h\x1b[0m\x1b[?1049l';
    if (this.mouseEnabled) cleanup = '\x1b[?1006l\x1b[?1002l\x1b[?1000l' + cleanup;
    this.mouseEnabled = false;
    process.stdout.write(cleanup);
  }

  private render(): void {
    if (!this.screen || !this.active) return;
    try {
      const cols = this.columns;
      const totalRows = this.rows;
      const header = totalRows >= 8 ? this.screen.header?.() : undefined;
      const headerRows = header ? renderHeader(header, cols) : [];
      const bodyHeight = Math.max(1, totalRows - headerRows.length);
      const inset = cols >= 84 ? 2 : 0;
      const contentWidth = Math.max(1, cols - inset);
      const frame = this.screen.render(contentWidth, bodyHeight).slice(0, bodyHeight);

      let cursorPos: { row: number; col: number } | undefined;
      const outLines: string[] = [...headerRows];

      for (let i = 0; i < bodyHeight; i++) {
        const row = frame[i];
        if (!row) {
          outLines.push(' '.repeat(cols));
          continue;
        }
        if (row.inputRule !== undefined) {
          const label = row.inputRule ? ` ${row.inputRule} ` : '';
          const ruleLen = Math.max(0, cols - stringWidth(label));
          outLines.push(`\x1b[90m${label}${'─'.repeat(ruleLen)}\x1b[0m`);
          continue;
        }
        const tone = row.inputPrompt ? TONES.text : TONES[row.tone ?? 'text'];
        const prefix = row.inputPrompt && inset >= 2
          ? ' '.repeat(inset - 2) + '\x1b[90m❯ \x1b[0m'
          : ' '.repeat(inset);
        let body = padToWidth(tone + row.text, contentWidth);
        if (Number.isSafeInteger(row.focusColumn) && row.focusColumn! >= 0 && row.focusColumn! < contentWidth) {
          if (row.focusColumn === 0 && inset >= 2) {
            outLines.push(' '.repeat(inset - 2) + '\x1b[36m▸ \x1b[0m' + body);
          } else {
            outLines.push(prefix + body);
          }
        } else {
          outLines.push(prefix + body);
        }
        if (Number.isSafeInteger(row.cursorColumn) && row.cursorColumn! >= 0 && row.cursorColumn! < contentWidth) {
          cursorPos = { row: headerRows.length + i + 1, col: inset + row.cursorColumn! + 1 };
        }
      }

      let paint = '\x1b[?2026h\x1b[H\x1b[?25l' + outLines.slice(0, totalRows).join('\r\n');
      if (cursorPos) {
        paint += `\x1b[${cursorPos.row};${cursorPos.col}H\x1b[?25h`;
      }
      paint += '\x1b[?2026l';
      process.stdout.write(paint);
    } catch (error) {
      this.closeScreen(error);
    }
  }

  private handleChunk(data: string): void {
    if (!this.screen) return;
    clearTimeout(this.escTimer);
    this.buffer += data;

    while (this.buffer.length > 0 && this.screen) {
      if (this.pasting) {
        const end = this.buffer.indexOf(PASTE_END);
        if (end < 0) {
          this.pasteBuffer += this.buffer;
          this.buffer = '';
          return;
        }
        this.pasteBuffer += this.buffer.slice(0, end);
        this.buffer = this.buffer.slice(end + PASTE_END.length);
        this.pasting = false;
        const pasted = this.pasteBuffer;
        this.pasteBuffer = '';
        this.screen.paste?.(pasted);
        continue;
      }

      if (this.buffer.startsWith(PASTE_START)) {
        this.pasting = true;
        this.pasteBuffer = '';
        this.buffer = this.buffer.slice(PASTE_START.length);
        continue;
      }

      const mouse = parseMouse(this.buffer);
      if (mouse) {
        this.buffer = this.buffer.slice(mouse.length);
        if (mouse.report && this.screen.mouse) {
          const headerOffset = this.rows >= 8 && this.screen.header?.() ? 5 : 0;
          const inset = this.columns >= 84 ? 2 : 0;
          const x = mouse.report.x - 1 - inset;
          const y = mouse.report.y - 1 - headerOffset;
          if (x >= 0 && y >= 0) {
            this.screen.mouse({ ...mouse.report, x, y });
          }
        }
        continue;
      }
      if (mousePrefix(this.buffer)) {
        this.escTimer = setTimeout(() => {
          this.buffer = '';
        }, 30);
        return;
      }

      if (this.buffer.startsWith('\x1b')) {
        if (this.buffer.length === 1) {
          this.escTimer = setTimeout(() => {
            if (this.buffer === '\x1b' && this.screen) {
              this.buffer = '';
              this.screen.key({ name: 'escape', sequence: '\x1b' });
            }
          }, 25);
          return;
        }
        const seq = parseLegacySequence(this.buffer);
        if (seq) {
          this.buffer = this.buffer.slice(seq.length);
          if (seq.key) this.screen.key(seq.key);
          continue;
        }
        if (/^\x1b(\[[0-9;?]*|O)?$/.test(this.buffer) && this.buffer.length < 16) {
          this.escTimer = setTimeout(() => {
            this.buffer = '';
          }, 30);
          return;
        }
        // Alt+key or standalone escape
        const ch = this.buffer[1]!;
        this.buffer = this.buffer.slice(2);
        this.screen.key({ name: ch.toLowerCase(), meta: true, value: ch, sequence: '\x1b' + ch });
        continue;
      }

      const ch = this.buffer[0]!;
      this.buffer = this.buffer.slice(1);
      if (ch === '\r' || ch === '\n') {
        this.screen.key({ name: 'enter', sequence: ch });
      } else if (ch === '\t') {
        this.screen.key({ name: 'tab', sequence: ch });
      } else if (ch === '\x7f' || ch === '\b') {
        this.screen.key({ name: 'backspace', sequence: ch });
      } else if (ch === ' ') {
        this.screen.key({ name: 'space', value: ' ', sequence: ' ' });
      } else if (ch === '\x03') {
        this.screen.key({ name: 'c', ctrl: true, sequence: ch });
      } else if (ch.charCodeAt(0) >= 1 && ch.charCodeAt(0) <= 26) {
        const letter = String.fromCharCode(ch.charCodeAt(0) + 96);
        this.screen.key({ name: letter, ctrl: true, sequence: ch });
      } else {
        this.screen.key({ name: ch.toLowerCase(), value: ch, sequence: ch });
      }
    }
  }
}
