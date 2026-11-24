"""Reward selection separated from committing ownership to a player's deck."""
from ... import engine as e
from . import odds

RARITIES = ('common','uncommon','rare')


def card_choices(state, player, definitions, *, source='battle', count=3, act_index=0, uniform=False,is_reward=None,pool_modifications=True,rarity_filter=None,kind_filter=None,odds_source=None,no_upgrade_roll=False,rng=None):
    """Three cards for a reward.

    ``rng`` overrides the stream every draw comes from, which the reference does
    with ``CardCreationOptions.WithRngOverride``. Under an override the upgrade
    roll is its own draw against a zero threshold rather than the usual odds, so
    a card is upgraded only when the roll lands exactly on zero — the draw
    happens either way and skipping it would shift every later draw.
    """
    if rng is not None:
        # Only the override paths the reference actually uses are modelled, and
        # both pin the rarity instead of rolling it: the crystal sphere asks for
        # one fixed rarity, so no rarity draw is suppressed by accident.
        assert uniform and rarity_filter is not None, 'an rng override needs a fixed rarity'
    if is_reward is None:is_reward=source in ('battle','elite','boss')
    definitions=list(definitions)
    if is_reward and pool_modifications and 'PrismaticGem' in player.get('relics',[]) and any(d['pool']!='colorless' for d in definitions):
        from ...content import CARDS
        definitions=list({d['key']:d for d in [*definitions,*[d for d in CARDS.values() if d['pool'] in ('ironclad','silent','regent','necrobinder','defect')]]}.values())
    if is_reward and pool_modifications and 'DingyRug' in player.get('relics',[]):
        from ...content import CARDS
        definitions=list({d['key']:d for d in [*definitions,*[d for d in CARDS.values() if d['pool']=='colorless']]}.values())
    multiplayer=len(state.get('players',{}))>1
    remaining = [d for d in definitions if d['rarity'] in RARITIES
                 and (rarity_filter is None or d['rarity']==rarity_filter) and (kind_filter is None or d['kind']==kind_filter)
                 and not (not multiplayer and d['values'].get('multiplayerOnly'))
                 and not (multiplayer and d['values'].get('singleplayerOnly'))]
    result=[]
    for _ in range(min(count,len(remaining))):
        eligible=remaining
        if not uniform:
            rolled=odds.card_rarity(state,player,odds_source,dynamic=False) if odds_source else odds.card_rarity(state,player,source)
            first=RARITIES.index(rolled)
            for i in range(3):
                rarity=RARITIES[(first+i)%3]
                eligible=[d for d in remaining if d['rarity']==rarity]
                if eligible:break
        selected=(eligible[rng.next_int(len(eligible))] if rng is not None
                  else e.player_rng(state,player,'Rewards',lambda rng:rng.next_item(list(eligible))))
        remaining.remove(selected)
        if rng is not None:
            upgraded=not no_upgrade_roll and rng.next_float()<=0
        else:
            upgraded=False if source=='event' or no_upgrade_roll else odds.reward_upgrade(state,player,selected['rarity'],act_index)
        card={'key':selected['key'],'upgraded':upgraded}
        from ...relics.hooks import modify_acquired_card
        modify_acquired_card(player,card,reward_preview=True)
        result.append(card)
    if (is_reward and source in ('battle','elite','boss') and state.get('phase')=='reward'
            and 'LastingCandy' in player.get('relics',[]) and player.get('lastingCandyRewards',0)%2==1):
        powers=[d for d in definitions if d['kind']=='power' and (rarity_filter is None or d['rarity']==rarity_filter) and kind_filter in (None,'power')]
        powers=[d for d in powers if d['key'] not in {c['key'] for c in result}] or powers
        result+=card_choices(state,player,powers,source='other',count=1,act_index=act_index,is_reward=False,pool_modifications=False,odds_source=source)
    return result
