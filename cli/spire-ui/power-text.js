// Official status wording from the exported catalog. The templates use the
// game's SmartFormat syntax; this fills the stack count, owner and side, plus
// the per-instance values the server projects as `powerDetails`, and falls
// back to the plain description when a template still needs a missing value.
const MARKUP = /\[\/?(?:gold|blue|green|red|purple|yellow|white|orange|gray|grey)\]/g;

// Split on `sep` outside nested braces.
function splitTop(text, sep) {
  const parts = []; let depth = 0, start = 0;
  for (let i = 0; i < text.length; i++) {
    if (text[i] === '{') depth++;
    else if (text[i] === '}') depth--;
    else if (text[i] === sep && depth === 0) { parts.push(text.slice(start, i)); start = i + 1; }
  }
  parts.push(text.slice(start));
  return parts;
}

const test = (clause, value) => {
  const m = /^(<=|>=|==|<|>)(-?\d+(?:\.\d+)?)$/.exec(clause);
  if (!m) return undefined;
  const n = Number(m[2]);
  return { '<': value < n, '>': value > n, '<=': value <= n, '>=': value >= n, '==': value === n }[m[1]];
}

function token(body, values, fill) {
  const at = body.indexOf(':');
  const name = at < 0 ? body : body.slice(0, at), format = at < 0 ? undefined : body.slice(at + 1);
  if (name === '') return '';
  if (name === 'singleStarIcon') return '辉星';
  if (name === 'energyPrefix') return '能量';
  const value = values[name];
  const branch = text => fill(text.replaceAll('{}', String(value)));
  if (format === undefined) return value === undefined || typeof value === 'boolean' ? undefined : String(value);
  if (format.startsWith('cond:')) {
    const parts = splitTop(format.slice(5), '|');
    if (parts.every(part => !/^(<=|>=|==|<|>)-?\d/.test(part))) return branch(value ? parts[0] : parts[1] ?? '');
    for (const part of parts) {
      const q = part.indexOf('?');
      if (q < 0) return branch(part);
      if (typeof value !== 'number') return undefined;
      const hit = test(part.slice(0, q), value);
      if (hit === undefined) return undefined;
      if (hit) return branch(part.slice(q + 1));
    }
    return '';
  }
  if (typeof value === 'boolean' && !format.includes('(')) {
    const [yes, no = ''] = splitTop(format, '|');
    return fill(value ? yes : no);
  }
  if (typeof value !== 'number') return undefined;
  if (format === 'energyIcons()') return `${value}能量`;
  if (format === 'starIcons()') return `${value}辉星`;
  if (format === 'abs()') return String(Math.abs(value));
  if (['diff()', 'percentLess()', 'percentMore()'].includes(format)) return String(value);
  if (format.startsWith('plural:')) { const [one, many = one] = splitTop(format.slice(7), '|'); return fill(value === 1 ? one : many); }
  const choose = /^choose\((-?\d+)\):/.exec(format);
  if (choose) { const [yes, no = ''] = splitTop(format.slice(choose[0].length), '|'); return branch(value === Number(choose[1]) ? yes : no); }
  return undefined;
}

// Returns the rendered text, or undefined when a token cannot be filled.
export function fillTemplate(template, values) {
  const fill = text => {
    let out = '', depth = 0, start = -1;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (c === '{') { if (depth++ === 0) start = i; }
      else if (c === '}') {
        if (--depth < 0) return undefined;
        if (depth === 0) {
          const part = token(text.slice(start + 1, i), values, fill);
          if (part === undefined) return undefined;
          out += part;
        }
      } else if (depth === 0) out += c;
    }
    return depth === 0 ? out : undefined;
  };
  return fill(template.replace(MARKUP, ''));
}

/**
 * `templates` maps a status key to {smartDescription, description}; `context`
 * gives the stack count, the owner's name, whether the owner is a player and
 * whether the run has several players, plus any extra named values.
 */
export function powerDescription(templates, key, { amount, owner, isPlayer, multiplayer, values = {} } = {}) {
  const entry = templates?.[key];
  if (!entry) return undefined;
  const all = { Amount: amount, OwnerName: owner, OnPlayer: !!isPlayer, IsMultiplayer: !!multiplayer, ...values };
  for (const template of [entry.smartDescription, entry.description]) {
    if (!template) continue;
    const text = fillTemplate(template, all);
    if (text !== undefined) return text.replace(/\s*\n\s*/g, '').trim();
  }
  return undefined;
}
