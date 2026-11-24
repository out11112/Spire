"""A0–A10 reward and unknown-room odds; all changing values live in the saved state.

Every roll here is a ``NextFloat`` on the lane the reference uses for it, and
the lane is not always the same one: a relic's rarity comes off ``Rewards`` on
a card or relic reward but off ``TreasureRoomRelics`` in a treasure room. The
changing probability values use binary32, as they do in the reference. Old
saves that used integer ten-thousandths are converted when first read.
"""
from . import reward_odds
from ...rng import streams
from ...rng.mega_random import f32


def _roll(state, lane, player=None):
    """``NextFloat()`` on the lane the reference takes this odds roll from.

    A lane belongs to the run or to one player, and the caller has to say which
    by passing a player or not: ``UnknownMapPoint`` and ``TreasureRoomRelics``
    are run lanes, ``Rewards`` and ``Shops`` are per-player. Guessing would
    draw from the wrong lane, which is the failure this whole migration exists
    to remove, so there is no default.
    """
    with streams.open(state) as rngs:
        if player is None:
            return rngs.run(lane).next_float()
        return rngs.player(streams.seat_of(player), lane).next_float()

UNKNOWN_BASE = {'battle': f32(.1), 'elite': f32(-1),
                'treasure': f32(.02), 'shop': f32(.03)}


def player_odds(player):
    saved = player.get('odds')
    if saved is None:
        saved = reward_odds.new_odds()
        player['odds'] = saved
    elif 'cardOffset' in saved:
        # Saves made before the reference-odds port stored both values as
        # integer ten-thousandths.  Convert once at the point the odds are next
        # used; JSON preserves the resulting binary32 values exactly enough to
        # resume the original sequence.
        saved = {
            'cardRarity': f32(saved['cardOffset'] / 10000),
            'potionReward': f32(saved['potion'] / 10000),
        }
        player['odds'] = saved
    return saved


def card_rarity(state, player, source='battle', *, dynamic=None, current_offset=False):
    """Roll card rarity with the reference's binary32 arithmetic.

    Encounter rewards change the future offset.  Non-encounter creation rolls
    base odds.  Merchant cards are the one third form: they use the current
    offset but leave it unchanged, represented by ``current_offset=True``.
    """
    odds = player_odds(player)
    if dynamic is None:
        dynamic = source in ('battle', 'elite', 'boss')
    type_ = reward_odds.type_for_source(source)
    with streams.open(state) as rngs:
        rng = rngs.player(streams.seat_of(player), 'Rewards')
        if dynamic:
            return reward_odds.card_rarity(rng, odds, type_, state.get('ascension',0))
        offset = odds['cardRarity'] if current_offset else f32(0.0)
        return reward_odds.roll_without_changing_future_odds(rng, type_, offset, state.get('ascension',0))


def potion_reward(state, player, source='battle', forced=False):
    odds = player_odds(player)
    with streams.open(state) as rngs:
        rng = rngs.player(streams.seat_of(player), 'Rewards')
        return reward_odds.potion_reward(rng, odds, is_elite=source == 'elite', forced=forced)


def relic_rarity(state, player=None, *, treasure=False):
    """A relic's rarity. Two callers, two lanes, and no third case.

    On a reward it is the player's own ``Rewards`` lane; in a treasure room it
    is the run's ``TreasureRoomRelics``. Neither is optional, so asking for
    neither is a caller mistake rather than a draw on some default.
    """
    if treasure:
        roll = _roll(state, 'TreasureRoomRelics')
    else:
        if player is None:
            raise ValueError('a reward relic roll is on the player Rewards lane')
        roll = _roll(state, 'Rewards', player)
    return 'common' if roll < f32(.5) else 'uncommon' if roll < f32(.83) else 'rare'


def potion_rarity(state, player):
    roll = _roll(state, 'Rewards', player)
    return 'common' if roll < f32(.65) else 'uncommon' if roll < f32(.9) else 'rare'


def reward_upgrade(state, player, rarity, act_index, *, base=0, modifier=None):
    threshold = base + (0 if rarity == 'rare' else act_index * (.125 if state.get('ascension',0)>=7 else .25))
    if modifier:
        threshold = modifier(threshold)
    return _roll(state, 'Rewards', player) <= threshold


def reset_unknown(state):
    base = state.setdefault('unknownBase', dict(UNKNOWN_BASE))
    if any(value > 2 for value in base.values()):
        base = {kind: f32(value / 10000) for kind,value in base.items()}
        state['unknownBase'] = base
    state['unknownOdds'] = dict(base)


def unknown_room(state, blacklist=(), *, allowed=None, increase=None):
    if 'unknownOdds' not in state:
        reset_unknown(state)
    elif any(value > 2 for value in state['unknownOdds'].values()):
        state['unknownOdds'] = {kind: f32(value / 10000)
                                for kind,value in state['unknownOdds'].items()}
        base = state.setdefault('unknownBase', dict(UNKNOWN_BASE))
        if any(value > 2 for value in base.values()):
            state['unknownBase'] = {kind: f32(value / 10000)
                                    for kind,value in base.items()}
    values = state['unknownOdds']
    base = state['unknownBase']
    eligible = set(values) | {'event'}
    eligible.difference_update(blacklist)
    if any('GoldenCompass' in p.get('relics',[]) and p.get('goldenCompassAct')==state.get('actIndex',0) for p in state.get('players',{}).values()):eligible.intersection_update({'event'})
    if any('JuzuBracelet' in player.get('relics',[]) for player in state.get('players',{}).values()):eligible.discard('battle')
    if allowed is not None:
        eligible.intersection_update(allowed)
    if not eligible:
        raise ValueError('未知房间没有合法类型。')
    # The original enum order is used for the no-event fallback.
    result = next(kind for kind in ('event','battle','elite','boss','treasure','shop','rest') if kind in eligible)
    roll = _roll(state, 'UnknownMapPoint')
    threshold = f32(0)
    for kind, value in values.items():
        if kind in eligible and value >= 0:
            threshold = f32(threshold + value)
            if roll <= threshold:
                result = kind
                break
    for kind, value in base.items():
        if kind == result:
            values[kind] = value
        elif kind in eligible:
            increment = increase(kind, value) if increase else value
            values[kind] = f32(values[kind] + increment)
    return result
