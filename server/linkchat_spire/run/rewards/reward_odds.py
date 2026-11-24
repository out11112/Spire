"""Card-rarity and potion-reward odds, ported from the reference assembly.

Both ride the per-player ``Rewards`` stream and carry a value that shifts after
every roll, so the roll order matters as much as the arithmetic.

Both now have original-assembly replay coverage at A0–A10, including the
binary32 accumulator and RNG counter. The independent fixture is in
``tests/fixtures/reference-ascension.json.gz``; the headless logging adapter
and exact assembly hash are documented in ``tools/ascension-oracle/README.md``.

Two details that look like mistakes and are not:

* The roll is compared against the *rare* threshold plus the offset, and then
  against ``uncommonOdds + that same threshold``. A negative offset therefore
  eats into the uncommon band as well: the first regular roll is 65/35/0, not
  63/37/0. Do not renormalise.
* Every step is binary32, including ``CurrentValue``. Doing it in double drifts
  after a few dozen rolls.
"""
from ...rng.mega_random import f32

# CardRarityOddsType
REGULAR = 'RegularEncounter'
ELITE = 'EliteEncounter'
BOSS = 'BossEncounter'
SHOP = 'Shop'
UNIFORM = 'Uniform'

COMMON, UNCOMMON, RARE = 'common', 'uncommon', 'rare'

# Every constant is binary32 in the original, and the offsets accumulate, so a
# double literal here would drift away from the game after a few dozen rolls.
_BASE_ODDS = {
    # type: (common, uncommon, rare)
    REGULAR: (f32(0.6), f32(0.37), f32(0.03)),
    ELITE: (f32(0.5), f32(0.4), f32(0.1)),
    BOSS: (f32(0.0), f32(0.0), f32(1.0)),
    SHOP: (f32(0.54), f32(0.37), f32(0.09)),
    UNIFORM: (f32(0.33), f32(0.33), f32(0.33)),
}

BASE_RARITY_OFFSET = f32(-0.05)
MAX_RARITY_OFFSET = f32(0.4)
RARITY_GROWTH = f32(0.01)

BASE_POTION_ODDS = f32(0.4)
ELITE_POTION_BONUS = f32(0.25)
POTION_STEP = f32(0.1)


def new_odds():
    """The two odds a run starts with, as saved on the player."""
    return {'cardRarity': BASE_RARITY_OFFSET, 'potionReward': BASE_POTION_ODDS}


def _base(type_, rarity_index, ascension=0):
    if ascension>=7 and rarity_index==2 and type_ in (REGULAR,ELITE,SHOP):
        return f32({REGULAR:.0149,ELITE:.05,SHOP:.045}[type_])
    return _BASE_ODDS[type_][rarity_index]


def roll_without_changing_future_odds(rng, type_, offset, ascension=0):
    """``RollWithoutChangingFutureOdds(type, offset)`` — one draw, no state change."""
    roll = rng.next_float()
    rare_threshold = f32(_base(type_, 2, ascension) + f32(offset))
    if roll < rare_threshold:
        return RARE
    # Not an elif chain on independent bands: the uncommon band starts at the
    # rare threshold, so the offset shifts both.
    if roll < f32(_base(type_, 1, ascension) + rare_threshold):
        return UNCOMMON
    return COMMON


def card_rarity(rng, odds, type_=REGULAR, ascension=0):
    """``CardRarityOdds.Roll`` — draws once and moves the saved offset."""
    if type_ == BOSS:
        # A boss roll reads the base odds, not the accumulated offset, and the
        # offset still moves afterwards.
        rarity = roll_without_changing_future_odds(rng, type_, f32(0.0), ascension)
    else:
        rarity = roll_without_changing_future_odds(rng, type_, odds['cardRarity'], ascension)
    if rarity == RARE:
        odds['cardRarity'] = BASE_RARITY_OFFSET
    else:
        odds['cardRarity'] = min(f32(odds['cardRarity'] + (f32(.005) if ascension>=7 else RARITY_GROWTH)), MAX_RARITY_OFFSET)
    return rarity


def potion_reward(rng, odds, is_elite=False, forced=False):
    """``PotionRewardOdds.Roll``. A forced reward draws nothing at all."""
    if forced:
        return True
    bonus = ELITE_POTION_BONUS if is_elite else f32(0.0)
    threshold = f32(odds['potionReward'] + f32(bonus * 0.5))
    if rng.next_float() < threshold:
        odds['potionReward'] = f32(odds['potionReward'] - POTION_STEP)
        return True
    odds['potionReward'] = f32(odds['potionReward'] + POTION_STEP)
    return False


# The reward room's own room type maps onto the odds type.
ROOM_TO_TYPE = {
    'battle': REGULAR,
    'elite': ELITE,
    'boss': BOSS,
    'shop': SHOP,
}


def type_for_source(source):
    return ROOM_TO_TYPE.get(source, REGULAR)
