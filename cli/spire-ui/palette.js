// Every colour the Spire screens use, in one place. Foregrounds match the host
// palette in src/theme.ts and stay within what the host's safeFrame lets through.
const rgb = (r, g, b) => `\x1b[38;2;${r};${g};${b}m`;
export const TEXT = rgb(212, 212, 212);
export const MUTED = rgb(128, 128, 128);
export const ACCENT = rgb(177, 185, 249);
export const ERROR = rgb(255, 107, 107);
export const DANGER = '\x1b[91m';
export const SELECTED = '\x1b[48;2;58;58;74m';
export const DANGER_SELECTED = '\x1b[48;2;55;35;35m';
export const RESET = '\x1b[0m';
// Route map: the focused node and its successors, reachable nodes, the rest.
export const MAP_FOCUS = '\x1b[1;93m';
export const MAP_NEXT = '\x1b[93m';
export const MAP_REACHABLE = '\x1b[92m';
export const MAP_IDLE = '\x1b[90m';
export const MAP_VOTES = '\x1b[33m';
export const GOLD = rgb(246, 226, 183);
export const BUFF = rgb(171, 223, 167);
export const DEBUFF = rgb(198, 160, 246);
/** A coloured span that hands the row back to `restore` (its tone colour) instead of resetting it. */
export const paint = (colour, text, restore = TEXT) => text ? `${colour}${text}${restore}` : '';
/** Removes colour from text whose look is replaced as a whole, such as a focused row. */
export const plain = text => String(text).replace(/\x1b\[[0-9;]*m/g, '');
// Card movement: the piles whose counts just changed.
export const PILE_DRAW = rgb(97, 175, 239);
export const PILE_DISCARD = rgb(212, 212, 212);
export const PILE_EXHAUST = rgb(198, 160, 246);
