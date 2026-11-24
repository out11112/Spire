"""Run-start scheduling, ported from ``RunManager.GenerateRooms`` and ``ActModel.GenerateRooms``.

Everything the game decides before the first room is drawn from one stream --
``RunRngSet.UpFront`` -- and the acts are walked in order, so the *sequence* is
the contract, not just the stream. In particular the act-2 and act-3 shared
ancients are split off before any act's rooms are generated, and each act draws
its events, then weak encounters, then regular encounters, then fifteen elites,
then a boss, then an ancient.

Pools are taken in the reference's declaration order. Reordering a pool changes
which entry an index-based draw lands on, so the order in ``world_data.json`` is
load-bearing.
"""

from ...rng.grab_bag import GrabBag
from ...content.data import load as load_data

WORLD = load_data('world_data.json')
ELITE_SCHEDULE_LENGTH = 15


def act_pools(act_name):
    """The ordered pools one act draws from, in the reference's order."""
    act = WORLD['acts'][act_name]
    encounters = act['encounters']
    definitions = WORLD['encounters']

    def kind_matches(key, kind, weak=None):
        entry = definitions[key]
        if entry['kind'] != kind:
            return False
        return weak is None or entry['weak'] == weak

    return {
        'weak': [k for k in encounters if kind_matches(k, 'battle', True)],
        'regular': [k for k in encounters if kind_matches(k, 'battle', False)],
        'elite': [k for k in encounters if kind_matches(k, 'elite')],
        'boss': [k for k in encounters if kind_matches(k, 'boss')],
        'events': list(act['events']) + list(WORLD['sharedEvents']),
        'ancients': list(act['ancients']),
        'weak_count': act['weak'],
        'rooms': act['rooms'],
    }


def shares_tags(first, second):
    """``EncounterModel.SharesTagsWith`` — any shared tag, not all of them."""
    if first is None or second is None:
        return False
    return bool(set(WORLD['encounters'][first]['tags']) & set(WORLD['encounters'][second]['tags']))


def _add_without_repeating_tags(chosen, bag, rng):
    last = chosen[-1] if chosen else None

    def acceptable(encounter):
        return not shares_tags(encounter, last) and encounter != last

    encounter = bag.grab_and_remove(rng, acceptable)
    if encounter is None:
        encounter = bag.grab_and_remove(rng)
    if encounter is not None:
        chosen.append(encounter)


def _fill(pool, count, rng, chosen):
    bag = GrabBag()
    for _ in range(count):
        if not bag.any():
            for encounter in pool:
                bag.add(encounter, 1.0)
        _add_without_repeating_tags(chosen, bag, rng)


def split_shared_ancients(rng, shared_ancients, act_count):
    """``RunManager.GenerateRooms``'s shared-ancient split, before any act is built.

    Returns one list per act after the first; the remainder stays unused.
    """
    remaining = list(shared_ancients)
    rng.shuffle(remaining)
    split = []
    for _ in range(act_count - 1):
        count = rng.next_int(len(remaining) + 1)
        subset = remaining[:count]
        remaining = [item for item in remaining if item not in subset]
        split.append(subset)
    return split


def generate_act_rooms(rng, act_name, is_multiplayer, shared_ancients=(), disabled_events=frozenset()):
    """``ActModel.GenerateRooms`` for one act, on the shared up-front stream."""
    pools = act_pools(act_name)
    rooms = int(pools['rooms']) - int(bool(is_multiplayer))

    # The reference shuffles events, then filters; a disabled event therefore
    # still consumes its position in the draw.
    events = list(pools['events'])
    rng.shuffle(events)
    events = [key for key in events if key not in disabled_events]

    normal = []
    _fill(pools['weak'], pools['weak_count'], rng, normal)
    _fill(pools['regular'], rooms - pools['weak_count'], rng, normal)

    elite = []
    _fill(pools['elite'], ELITE_SCHEDULE_LENGTH, rng, elite)

    boss = rng.next_item(pools['boss'])
    ancient = rng.next_item(list(pools['ancients']) + list(shared_ancients))

    return {
        'normal': normal,
        'elite': elite,
        'boss': boss,
        'ancient': ancient,
        'events': events,
        'visited': {'battle': 0, 'elite': 0, 'boss': 0, 'event': 0},
    }
