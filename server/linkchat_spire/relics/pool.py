"""Complete reference relic bags, independent of effect implementation coverage.

Draws never filter by installed handlers. An unavailable effect is rejected by
acquisition, not replaced with another identity or silently removed from a bag.
"""
from ..run.rewards.odds import relic_rarity
from ..rng.mega_random import f32
from ..content.data import load as load_data

DATA=load_data('relic_data.json')
RARITIES=('common','uncommon','rare','shop')
NEXT={'shop':'common','common':'uncommon','uncommon':'rare','rare':None}
NO_SHOP={'AmethystAubergine','BowlerHat','LuckyFysh','OldCoin','TheCourier'}
EARLY={'AmethystAubergine','BowlerHat','BookOfFiveRings','DragonFruit','FrozenEgg',
       'Girya','JuzuBracelet','LastingCandy','LuckyFysh','MealTicket','MoltenEgg',
       'OldCoin','Planisphere','Shovel','ToxicEgg','WhiteBeastStatue','WhiteStar'}


def allowed(state,key):
    if key in EARLY and state.get('floor',0)>=(38 if len(state['players'])>1 else 41):return False
    if key=='MassiveScroll':return len(state['players'])>1
    if key in ('SilverCrucible','WingedBoots'):return len(state['players'])==1
    return True


BAG_RARITIES=('common','uncommon','rare','shop')


def bucket_order(pool):
    """The order the rarity buckets are shuffled in: first appearance in the pool.

    The reference stores them in a dictionary and shuffles its values, so the
    order is the order each rarity first shows up -- for every character that is
    uncommon, then common, then rare, then shop, not the enum order. It matters:
    each bucket draws from the same stream in turn.
    """
    seen=[]
    for key in pool:
        rarity=DATA[key]['rarity']
        if rarity not in seen:seen.append(rarity)
    return seen


def pool(player=None):
    pools=('shared',) if player is None else ('shared',player.get('character','ironclad'))
    return [key for key,d in DATA.items() if d['pool'] in pools and d['rarity'] in RARITIES]


def ordered_pool(character):
    """The bag's source list: every shared relic, then the character's own.

    The order is what the reference's ``Populate`` sees, and it decides both the
    per-rarity bucket contents and the order those buckets are created in — the
    buckets are shuffled one after another, so the creation order is the draw
    order. Filtered to the four rarities the bag actually holds.
    """
    return ([key for key,d in DATA.items()
             if d['pool']=='shared' and d['rarity'] in BAG_RARITIES]
            + [key for key,d in DATA.items()
               if d['pool']==character and d['rarity'] in BAG_RARITIES])


def has_available(state,player):
    bag=player.get('relicBag')
    keys=([key for values in bag['deques'].values() for key in values]+bag['fallback']) if bag else pool(player)
    return any(key not in player['relics'] and allowed(state,key) for key in keys)


def make_bag(state,keys):
    """Bucket the pool by rarity and shuffle each bucket off the up-front stream.

    The buckets are shuffled in first-appearance order and each draws from the
    same stream, so both the pool order and that order are part of the contract.
    """
    from ..rng import streams
    deques={}
    with streams.open(state) as rngs:
        rng=rngs.run('UpFront')
        for rarity in bucket_order(keys):
            bucket=[key for key in keys if DATA[key]['rarity']==rarity]
            rng.shuffle(bucket)
            deques[rarity]=bucket
    return {'deques':deques,'fallback':[]}


def remove(bag,key):
    for values in bag['deques'].values():
        values[:]=[item for item in values if item!=key]


def initialize(state):
    if 'sharedRelicBag' not in state:state['sharedRelicBag']=make_bag(state,pool())
    for player in state['players'].values():
        if 'relicBag' not in player:
            # The reference populates shared models first, then the character
            # pool.  ``pool(player)`` follows the globally alphabetised JSON
            # order and interleaves those groups, which consumes the same RNG
            # draws against different lists and changes the entire relic bag.
            player['relicBag']=make_bag(state,ordered_pool(player.get('character','ironclad')))
        for key in player['relics']+player.get('meltedRelics',[]):
            if key!='Circlet':remove(player['relicBag'],key);remove(state['sharedRelicBag'],key)


def pull_bag(state,bag,rarity,*,back=False,predicate=lambda key:True):
    for values in [*bag['deques'].values(),bag['fallback']]:
        values[:]=[key for key in values if allowed(state,key)]
    while rarity is not None:
        values=bag['deques'].get(rarity,[])
        positions=range(len(values)-1,-1,-1) if back else range(len(values))
        index=next((i for i in positions if predicate(values[i])),None)
        if index is not None:return values.pop(index)
        rarity=NEXT[rarity]
    values=bag['fallback']
    positions=range(len(values)-1,-1,-1) if back else range(len(values))
    index=next((i for i in positions if predicate(values[i])),None)
    return values.pop(index) if index is not None else 'Circlet'


def rarity_from(rng):
    """``RelicFactory.RollRarity`` on an explicit stream.

    Same thresholds as ``odds.relic_rarity``; it exists because a caller holding
    a stream of its own — a reward with an rng override — must roll there rather
    than on the player's own relic stream.
    """
    roll=rng.next_float()
    return 'common' if roll<f32(0.5) else 'uncommon' if roll<f32(0.83) else 'rare'


def pull(state,player,rarity=None,*,shop=False,exclude=(),shop_allowed=False):
    initialize(state)
    if rarity is None:rarity=relic_rarity(state,player)
    key=pull_bag(state,player['relicBag'],rarity,back=shop,
                 predicate=lambda key:key not in exclude and (not (shop or shop_allowed) or key not in NO_SHOP))
    remove(state['sharedRelicBag'],key)
    return key


def obtained(state,player,key):
    if key=='Circlet':return
    if 'relicBag' in player:remove(player['relicBag'],key)
    if 'sharedRelicBag' in state:remove(state['sharedRelicBag'],key)


def move_to_fallback(bag,key):
    if any(key in values for values in bag['deques'].values()):
        remove(bag,key);bag['fallback'].append(key)
