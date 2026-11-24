// Decode extended keyboard reports only. Node readline handles legacy keys;
// Terminal owns stream boundaries, bracketed paste and cursor reports.
const names: Record<number, string> = {
  9: 'tab', 13: 'enter', 27: 'escape', 32: 'space', 127: 'backspace',
  57344: 'escape', 57345: 'enter', 57346: 'tab', 57347: 'backspace',
  57348: 'insert', 57349: 'delete', 57350: 'left', 57351: 'right',
  57352: 'up', 57353: 'down', 57354: 'pageup', 57355: 'pagedown',
  57356: 'home', 57357: 'end',
  // Disambiguation mode gives non-text keypad keys their own codes. Normalize
  // them to the same input as the main keyboard (including modified KP Enter).
  57399: '0', 57400: '1', 57401: '2', 57402: '3', 57403: '4',
  57404: '5', 57405: '6', 57406: '7', 57407: '8', 57408: '9',
  57409: '.', 57410: '/', 57411: '*', 57412: '-', 57413: '+',
  57414: 'enter', 57415: '=', 57416: ',',
  57417: 'left', 57418: 'right', 57419: 'up', 57420: 'down',
  57421: 'pageup', 57422: 'pagedown', 57423: 'home', 57424: 'end',
  57425: 'insert', 57426: 'delete',
};
function report(data: string) {
  const kitty = /^\x1b\[([0-9:;]+)u$/.exec(data);
  if (kitty) {
    const fields = kitty[1]!.split(';');
    if (fields.length > 3) return undefined;
    const key = /^(\d+)(?::(\d*))?(?::(\d*))?$/.exec(fields[0]!);
    const mods = /^(\d+)(?::([123]))?$/.exec(fields[1] || '1');
    if (!key || !mods || fields[2] !== undefined && !/^\d+(?::\d+)*$/.test(fields[2])) return undefined;
    return { code: Number(key[1]), shifted: Number(key[2]) || undefined, base: Number(key[3]) || undefined, modifier: Number(mods[1]), event: Number(mods[2] ?? 1) };
  }
  const other = /^\x1b\[27;(\d+);(\d+)~$/.exec(data);
  if (other) return { code: Number(other[2]), shifted: undefined, base: undefined, modifier: Number(other[1]), event: 1 };
  return undefined;
}
export function isKeyRelease(data: string): boolean { return report(data)?.event === 3; }
export function parseKey(data: string): string | undefined {
  const key = report(data);
  if (!key || !Number.isSafeInteger(key.modifier) || key.modifier < 1 || key.modifier > 256) return undefined;
  const modifiers = key.modifier - 1;
  // Unsupported super/hyper/meta chords must not become ordinary text.
  if (modifiers & 56) return undefined;
  const code = modifiers & 6 && key.base ? key.base : key.code;
  if (!Number.isInteger(code) || code < 0 || code > 0x10ffff || code >= 0xd800 && code <= 0xdfff) return undefined;
  let name = names[code] ?? (code >= 57364 && code <= 57398 ? `f${code - 57363}` : code >= 32 && !(code >= 0xe000 && code <= 0xf8ff) && !(code >= 0x7f && code <= 0x9f) ? String.fromCodePoint(code) : undefined);
  if (!name) return undefined;
  if (!(modifiers & 6) && !names[code]) {
    if (modifiers & 1 && key.shifted && key.shifted <= 0x10ffff && !(key.shifted >= 0xd800 && key.shifted <= 0xdfff)) name = String.fromCodePoint(key.shifted);
    else if (/^[a-z]$/.test(name) && Boolean(modifiers & 1) !== Boolean(modifiers & 64)) name = name.toUpperCase();
  }
  return `${modifiers & 4 ? 'ctrl+' : ''}${modifiers & 2 ? 'alt+' : ''}${modifiers & 1 ? 'shift+' : ''}${name}`;
}

// SGR mouse reports (xterm mode 1006). The legacy X10 encoding is deliberately
// not decoded: feed() reassembles UTF-8, so a coordinate byte above 0x7f would
// swallow the bytes after it and eat real keystrokes.
export type MouseButton = 'left' | 'middle' | 'right' | 'wheel-up' | 'wheel-down' | 'none';
export interface MouseReport { button: MouseButton; x: number; y: number; action: 'press' | 'release' | 'move' }
const SGR_MOUSE = /^\x1b\[<(\d{1,5});(\d{1,5});(\d{1,5})([Mm])/;
// A terminal that does not answer 1006 falls back to these two forms, where every
// field is the value plus 32 and the button code has no leading `<`.
const URXVT_MOUSE = /^\x1b\[(\d{1,5});(\d{1,5});(\d{1,5})([Mm])/;
const X10_MOUSE = /^\x1b\[M([\s\S]{3})/;
const BUTTONS: Record<number, MouseButton> = { 0: 'left', 1: 'middle', 2: 'right', 64: 'wheel-up', 65: 'wheel-down' };
const MOTION = 32, SHIFT = 4, BUTTON_MASK = 0b11000011;
/** Matches a whole report. Unknown codes consume but carry no report. */
export function parseMouse(data: string): { report?: MouseReport | undefined; length: number } | undefined {
  const sgr = SGR_MOUSE.exec(data);
  const urxvt = sgr ? undefined : URXVT_MOUSE.exec(data) ?? undefined;
  const x10 = sgr || urxvt ? undefined : X10_MOUSE.exec(data) ?? undefined;
  if (!sgr && !urxvt && !x10) return undefined;
  const length = (sgr ?? urxvt ?? x10)![0].length;
  const bytes = x10?.[1] ?? '';
  const code = sgr ? Number(sgr[1]) : urxvt ? Number(urxvt[1]) - 32 : (bytes.codePointAt(0) ?? 0) - 32;
  const x = sgr ? Number(sgr[2]) : urxvt ? Number(urxvt[2]) : (bytes.codePointAt(1) ?? 0) - 32;
  const y = sgr ? Number(sgr[3]) : urxvt ? Number(urxvt[3]) : (bytes.codePointAt(2) ?? 0) - 32;
  if (code < 0 || x < 0 || y < 0) return { length };
  const drop = (report?: MouseReport) => ({ length, report });
  // Shift is how a terminal hands text selection back to the user.
  if (code & SHIFT) return drop();
  const held = code & 3;
  if (code & MOTION) {
    // Keep left drags for the application's text-selection layer. Other drags stay inert.
    return held === 3 || held === 0 ? drop({ button: held === 0 ? 'left' : 'none', x, y, action: 'move' }) : drop();
  }
  if (held === 3 && !(code & 64)) return drop({ button: 'none', x, y, action: 'release' });
  const button = BUTTONS[code & BUTTON_MASK];
  if (button === undefined || held === 3) return drop();
  // The X10 form has no release event: every report is a press.
  return drop({ button, x, y, action: (sgr?.[4] ?? urxvt?.[4]) === 'm' ? 'release' : 'press' });
}
/** True while a mouse report is still arriving, in any of the three encodings. */
export function mousePrefix(data: string): boolean {
  return /^\x1b\[<?\d{0,5}(;\d{0,5}(;\d{0,5})?)?$/.test(data)
    || /^\x1b\[M[\s\S]{0,2}$/.test(data);
}
