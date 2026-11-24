"""The run's random streams, held in the save as plain JSON.

Run state is persisted with ``json.dumps`` and copied with ``deepcopy`` for every
action, so streams cannot live in it as objects. They are stored as the original's
own serialisable form — counter plus the four xoshiro lanes — and materialised for
the duration of a ``with`` block:

    with streams.open(state) as rngs:
        encounter = rngs.run('UpFront').next_item(pool)

Writes go back only when the block completes without raising, which matches the
copy-on-action model: a failed action throws its copy away, and so does its
randomness. Views, previews and retries must never open a block at all — a
projection that draws is a bug, and the fixtures catch it as a counter drift.
"""

from . import mega_random

# The run-level streams, in the original's enum order.
RUN_STREAM_KEYS = tuple(key for key, _ in mega_random.RUN_RNG_STREAMS)
PLAYER_STREAM_KEYS = tuple(key for key, _ in mega_random.PLAYER_RNG_STREAMS)


def canonical_state_streams(seat_count=1):
    """A fresh stream block for a new run."""
    return {'named': {}, 'players': {}, 'run': None, 'seats': seat_count}


class Streams:
    """Live view over ``state['streams']``; one per ``with`` block.

    Blocks nest -- ``journey.initialize`` holds the up-front stream open while
    ``generate_map`` opens its own for the act's map stream. Each section is
    therefore written back only when *this* handle touched it, and the named and
    per-player maps merge rather than replace, so an outer block cannot roll back
    what an inner one already committed.
    """

    __slots__ = ('_state', '_block', '_run', '_players', '_named',
                 '_dirty_run', '_dirty_players', '_dirty_named', '_dirty_seats')

    def __init__(self, state):
        self._state = state
        self._block = state.setdefault('streams', canonical_state_streams())
        saved = self._block.get('run')
        self._run = (mega_random.RunRngSet.from_serializable(seed_string(state), saved)
                     if saved else mega_random.RunRngSet(seed_string(state)))
        self._players = {}
        self._named = {}
        self._dirty_run = self._dirty_players = self._dirty_named = self._dirty_seats = False

    # -- accessors --------------------------------------------------------

    def run(self, key):
        """A run-level stream, e.g. ``'UpFront'`` or ``'Shuffle'``."""
        self._dirty_run = True
        return self._run.get(key)

    def player(self, seat, key):
        """A per-player stream. ``seat`` is the fixed seat number, not an account."""
        self._dirty_players = True
        seat = int(seat)
        if seat not in self._players:
            saved = self._block['players'].get(str(seat))
            seed = (self._run.seed + seat) & mega_random.MASK64
            self._players[seat] = (mega_random.PlayerRngSet.from_serializable(seed, saved)
                                   if saved else mega_random.PlayerRngSet(seed))
        return self._players[seat].get(key)

    def named(self, name):
        """A standalone stream such as ``act_selection``, seeded from the run seed."""
        self._dirty_named = True
        if name not in self._named:
            saved = self._block['named'].get(name)
            if saved:
                self._named[name] = mega_random.Rng.from_serializable(saved)
            else:
                seed = (mega_random.run_seed(seed_string(self._state))
                        + mega_random.deterministic_hash(name)) & mega_random.MASK64
                self._named[name] = mega_random.Rng(seed)
        return self._named[name]

    def event(self, name, seat, *, shared=False):
        """An event's own stream.

        ``EventModel`` seeds it as ``runSeed + (shared ? 0 : slot) + hash(entry)``,
        so a shared event's stream is the same for everyone and a per-player one
        is not. The slot is part of the key, not just the seed: two seats reading
        the same event must not share a stream.
        """
        self._dirty_named = True
        slot = 0 if shared else int(seat)
        key = f'event:{name}:{slot}'
        if key not in self._named:
            saved = self._block['named'].get(key)
            if saved:
                self._named[key] = mega_random.Rng.from_serializable(saved)
            else:
                seed = (mega_random.run_seed(seed_string(self._state)) + slot
                        + mega_random.deterministic_hash(name)) & mega_random.MASK64
                self._named[key] = mega_random.Rng(seed)
        return self._named[key]

    def derived(self, name, *parts, key=None):
        """A stream the reference derives from run state instead of naming.

        Four of these sit alongside the fifteen named streams and are just as
        independent: ``EncounterModel`` seeds ``runSeed + TotalFloor + hash(id)``,
        ``MonsterModel`` ``runSeed + mapCol + mapRow + actIndex + combatId``, a
        per-relic helper ``runSeed + playerSlot + hash(relicId) + mixin``, and
        ``EventModel`` the same shape as ``event`` above. Sharing one lane
        between any two of them changes results.
        """
        self._dirty_named = True
        if key is None:
            key = 'derived:' + str(name) + ':' + ':'.join(str(part) for part in parts)
        if key not in self._named:
            saved = self._block['named'].get(key)
            if saved:
                self._named[key] = mega_random.Rng.from_serializable(saved)
            else:
                seed = (mega_random.run_seed(seed_string(self._state)) + sum(parts)
                        + mega_random.deterministic_hash(str(name))) & mega_random.MASK64
                self._named[key] = mega_random.Rng(seed)
        return self._named[key]

    def seat_count(self):
        return self._block.get('seats', 1)

    def set_seat_count(self, count):
        self._dirty_seats = True
        self._block['seats'] = int(count)

    # -- persistence ------------------------------------------------------

    def commit(self):
        if self._dirty_run:
            self._block['run'] = self._run.to_serializable()
        if self._dirty_players:
            players = dict(self._block.get('players') or {})
            players.update({str(seat): rngs.to_serializable()
                            for seat, rngs in self._players.items()})
            self._block['players'] = players
        if self._dirty_named:
            named = dict(self._block.get('named') or {})
            named.update({name: rng.to_serializable()
                          for name, rng in self._named.items()})
            self._block['named'] = named
        self._dirty_run = self._dirty_players = self._dirty_named = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is None:
            self.commit()
        return False


def open(state):
    """Open the run's streams for one action. Use as a context manager."""
    return Streams(state)


def seat_of(player):
    """The player's fixed seat number. The reference seeds player streams by slot."""
    seat=player.get('seat')
    # Small rules-unit fixtures may contain a single anonymous player. Seat zero
    # is the only account-independent default; real run actions normalize every
    # player before any draw.
    return seat if isinstance(seat,int) and seat>=0 else 0


def seed_string(state):
    """The canonical seed the run was created with."""
    return state.get('seed') or ''


def display_seed(state):
    """What the room shows so a player can reproduce the run."""
    return seed_string(state)
