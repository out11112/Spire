"""Draws from the named streams: which lane each kind of roll uses."""
from ..core import state as run_state

def run_rng(s,key,draw):
    """Draw from one of the reference's named run-level streams.

    Each of the fifteen is its own lane: drawing from the wrong one, or from a
    shared one, changes every later result in both. ``draw`` is called *inside*
    the block, because a handle returned past it holds a detached copy whose
    counter never reaches the save — every draw would then repeat the first.

    Use this rather than ``rand`` for anything the original routes to a named
    stream.
    """
    from . import streams
    with streams.open(s) as rngs:
        return draw(rngs.run(key))

def player_rng(s,p,key,draw):
    """Draw from one of the reference's per-player streams (``Rewards``, ...)."""
    from . import streams
    run_state.ensure_player_seats(s)
    with streams.open(s) as rngs:
        return draw(rngs.player(streams.seat_of(p),key))

def derived_rng(s,name,parts,draw,*,key=None):
    """Draw from a stream the reference derives from run state rather than names."""
    from . import streams
    with streams.open(s) as rngs:
        return draw(rngs.derived(name,*parts,key=key))

def combat_card_selection(s,items):
    """``CombatCardSelection.NextItem`` — one card out of a set."""
    items=list(items)
    return run_rng(s,'CombatCardSelection',lambda rng:rng.next_item(items))

def combat_card_selection_shuffle(s,items):
    """``CombatCardSelection`` shuffle, then take. ``N-1`` draws, like the reference's."""
    items=list(items)
    return run_rng(s,'CombatCardSelection',lambda rng:rng.shuffle(items))

def combat_card_generation(s,items):
    """``CombatCardGeneration.NextItem`` — one card made up on the spot."""
    items=list(items)
    return run_rng(s,'CombatCardGeneration',lambda rng:rng.next_item(items))

def combat_card_generation_shuffle(s,items):
    """``CombatCardGeneration`` shuffle whole-then-take.

    ``TakeRandom`` shuffles the *entire* pool before taking, so it costs ``N-1``
    draws rather than ``count-1``; drawing ``count`` times instead is the other
    reference path, ``GetForCombat``, and the two are not interchangeable.
    """
    items=list(items)
    return run_rng(s,'CombatCardGeneration',lambda rng:rng.shuffle(items))

def rewards_rng(s,p,draw):
    """Draw from the player's ``Rewards`` lane."""
    return player_rng(s,p,'Rewards',draw)

def niche_int(s,count):
    """``Niche.NextInt`` — the odd out-of-combat count or HP offset."""
    return run_rng(s,'Niche',lambda rng:rng.next_int(count))

def niche_choose(s,items):
    """``Niche.NextItem`` — one uniformly chosen card, relic or pool."""
    items=list(items)
    return run_rng(s,'Niche',lambda rng:rng.next_item(items))

def niche_shuffled(s,items):
    """``Niche`` shuffle, then take. ``N-1`` draws, like the reference's."""
    items=list(items)
    return run_rng(s,'Niche',lambda rng:rng.shuffle(items))

def roll_energy_cost(s):
    """``CombatEnergyCosts.NextInt(4)`` — a card's new random cost."""
    return run_rng(s,'CombatEnergyCosts',lambda rng:rng.next_int(4))

def random_target(s,candidates):
    """``CombatTargets.NextItem(...)`` — one uniformly chosen target."""
    items=list(candidates)
    return run_rng(s,'CombatTargets',lambda rng:rng.next_item(items))

def random_enemy(s,pool=None):
    """``RunRngSet.CombatTargets.NextItem(HittableEnemies)`` — one draw, committed.

    The reference draws random enemy targets from the run-level stream, so the
    order of these draws is shared across the whole party and the whole fight.
    """
    from . import streams
    options=[e for e in s['enemies'] if e['hp']>0] if pool is None else list(pool)
    with streams.open(s) as rngs:
        return rngs.run('CombatTargets').next_item(options)
