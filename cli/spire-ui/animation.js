// Pile changes between two combat snapshots. The server sends whole states, so
// a turn arrives at once; the screen lights the count of each pile whose size
// changed for a moment.
export const FRAME_MS = 80;       // redraw interval while something is lit
export const HOLD_MS = 900;       // how long a changed count stays lit

const PILES = ['draw', 'discard', 'exhaust'];
function pileCount(self, pile) {
  if (pile === 'draw') return self.draw?.length ?? self.drawCount ?? 0;
  if (pile === 'exhaust') return self.exhaust?.length ?? self.exhaustCount ?? 0;
  return self.discard?.length ?? 0;
}
/** How this player's piles changed between two snapshots, or undefined. */
export function pileChange(before, after) {
  // A fight that just began: the opening hand came out of the draw pile.
  if (before && before.phase !== 'combat' && after?.phase === 'combat' && after.turn === 1 && Array.isArray(after.self?.hand) && after.self.hand.length) {
    return { changed: ['draw', ...PILES.slice(1).filter(pile => pileCount(after.self, pile))] };
  }
  // phaseId moves on every turn, so the same fight is recognised by its floor.
  if (before?.phase !== 'combat' || after?.phase !== 'combat' || before.floor !== after.floor) return undefined;
  if (!before.self || !after.self) return undefined;
  const changed = PILES.filter(pile => pileCount(before.self, pile) !== pileCount(after.self, pile));
  return changed.length ? { changed } : undefined;
}
export function animation(change, start) {
  return { ...change, start, end: start + HOLD_MS };
}
/** Which piles are lit at `now`; undefined once they are not. */
export function frameAt(anim, now) {
  if (!anim || now >= anim.end) return undefined;
  return { changed: new Set(anim.changed) };
}
