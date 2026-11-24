"""Private, read-only display projections for card selection options."""
from copy import deepcopy
from .. import engine as e
from ..content import cost_text


def card_display(state, player, card, choice=None):
    choice=choice or {}
    preview=deepcopy(card)
    owner=deepcopy(player)
    free=bool(choice.get('free') or choice.get('destination')=='freeCombat')
    if free:e.free_card(preview,combat=choice.get('destination')=='freeCombat')
    view=e.card_view(preview,owner=owner)
    base_energy=view['cost'];base_stars=view.get('starCost')
    combat=bool(state and state.get('phase')=='combat' and choice.get('source')!='deck'
                and choice.get('destination')!='deck')
    if combat:
        as_hand=choice.get('source')=='hand' or choice.get('destination')=='hand'
        if view['cost'] not in ('X','—') and not e.definition(preview)['values'].get('unplayable'):
            view['cost']=e.energy_cost(state,owner,preview,in_play=as_hand)
        if 'starCost' in view and view['starCost']!='X':view['starCost']=e.star_cost(owner,preview,in_play=as_hand)
    result={key:view[key] for key in ('id','name','cost','description')}
    if 'starCost' in view:result['starCost']=view['starCost']
    marked_free=free or preview.get('freeThisTurn') or preview.get('freeThisCombat')
    if view['cost']==0 and (marked_free or isinstance(base_energy,int) and base_energy>0):result['freeEnergy']=True
    if view.get('starCost')==0 and (marked_free or preview.get('freeStarsThisTurn') or isinstance(base_stars,int) and base_stars>0):result['freeStars']=True
    return result


def display_row(state, player, cards, *, prefix='', choice=None):
    displays=[card_display(state,player,card,choice) for card in cards]
    label=prefix+'；'.join(f"{card['name']} [{cost_text(card)}] {card['description']}" for card in displays)
    return {'label':label,'displayCards':displays,'displayPrefix':prefix}


def decision_item(state, player, item):
    """Resolve saved candidate identities without changing the replay journal."""
    kind=state['pendingDecision']['kind']
    cards=[];prefix=''
    if kind=='bundle':cards=item.get('cards',[])
    elif kind in ('ancientCards','enchantDeck','copyDeck','cook'):
        cards=[card for card in player['deck'] if card['id']==item['id']]
    elif kind=='rewardSet' and item.get('operation')=='card':
        cards=[card for reward in player.get('pendingCardRewards',[]) if reward['id']==item.get('reward')
               for card in reward['cards'] if card['id']==item.get('card')]
        prefix='领取 '
    return {'id':item['id'],**(display_row(state,player,cards,prefix=prefix,choice={'source':'deck'})
                             if cards else {'label':item['label']})}
