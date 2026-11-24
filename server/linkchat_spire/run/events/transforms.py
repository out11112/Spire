"""Reference transformation pools and uniform identity selection.

Transformation is not a reward roll: rarity odds and pity counters are untouched.
The fully unlocked reference catalog is retained even while card implementation
is in progress; missing effects must never silently shrink the candidate pool.
"""
from ... import engine as e
from ...content.data import load as load_data

POOLS=load_data('transformation_pool.json')


def candidates(state,original,*,in_combat=True):
    """``CardFactory.GetFilteredTransformationOptions``.

    A card that is not a status or a curse transforms only into commons, commons
    and rares — the rarity filter is part of the rule, not a nicety. A status or
    a curse has no such restriction.
    """
    d=e.definition(original)
    rarity=d['rarity']
    pool='colorless' if d['kind']=='quest' or rarity in ('event','ancient','token') else d['pool']
    e.require(pool in POOLS,'变牌候选池未定义：'+pool)
    multiplayer=len(state['players'])>1
    unrestricted=rarity in ('status','curse')
    # A key with no implemented card yet is left in the pool so the dependency
    # check below can name it, rather than failing on the rarity lookup.
    def rarity_of(key):
        return e.CARDS.get(key,{}).get('rarity')
    result=[row['key'] for row in POOLS[pool] if row['key']!=original['key']
            and (unrestricted or rarity_of(row['key']) in (None,'common','uncommon','rare'))
            and (not in_combat or row['inCombat'])
            and row['constraint']!=('SingleplayerOnly' if multiplayer else 'MultiplayerOnly')]
    e.require(bool(result),'没有符合原作规则的变牌候选。')
    return result


def replacement(state,player,original,*,in_combat=True,source='transformations'):
    """One replacement draw.

    ``source`` names the stream the reference uses: a plain transform rides the
    player's ``Transformations`` stream, while the relic that reshuffles the whole
    deck rides the run's ``Niche`` stream.
    """
    from ...rng import streams
    e.require(in_combat or e.removable(original),'这张牌不能变形。')
    e.require(source in ('transformations','niche'),'未知的变牌随机来源。')
    pool=candidates(state,original,in_combat=in_combat)
    missing=[key for key in pool if key not in e.CARDS]
    e.require(not missing,'变牌依赖尚未补齐：'+', '.join(missing))
    with streams.open(state) as rngs:
        if source=='niche':rng=rngs.run('Niche')
        else:rng=rngs.player(streams.seat_of(player),'Transformations')
        key=rng.next_item(pool)
    return e.new_card(state,key)


def replace_in_pile(state,player,source,original,replacement):
    e.require(source is not player['deck'] or e.removable(original),'这张牌不能变形。')
    source[source.index(original)]=replacement
    if source is player['deck']:
        from ...relics.hooks import modify_acquired_card
        modify_acquired_card(player,replacement)
        from ...relics.hooks import card_added
        card_added(state,player,replacement)
    else:
        player['generatedThisCombat']=player.get('generatedThisCombat',0)+1
        from ...combat.classes.silent import entered_combat
        entered_combat(state,player,replacement)
    return replacement
