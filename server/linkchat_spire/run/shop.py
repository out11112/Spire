"""Saved normal merchant inventory, prices and atomic purchase operations."""
from ..content import cost_text
import math
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_EVEN

from .. import engine as e
from ..rng import mega_random
from .rewards import odds
from . import potions
from ..relics import pool as relic_pool

CARD_TYPES=('attack','attack','skill','skill','power')
RARITIES=('common','uncommon','rare')


def stream(player):return f'player:{player["id"]}:shops'





def pick(state,player,items):
    """``Shops.NextItem`` — one draw, committed before returning."""
    from ..rng import streams
    with streams.open(state) as rngs:
        return rngs.player(streams.seat_of(player),'Shops').next_item(list(items))


def roll(state,player,count):
    """``Shops.NextInt`` — one draw, committed before returning."""
    from ..rng import streams
    with streams.open(state) as rngs:
        return rngs.player(streams.seat_of(player),'Shops').next_int(count)


def rounded(value):
    """``Math.Round(double)`` — banker's rounding, used for relic prices."""
    return int(round(value))


def rounded_half_away(value):
    """``Mathf.RoundToInt`` / ``Mathf.Round`` — ties go away from zero."""
    return int(math.floor(value + 0.5)) if value >= 0 else -int(math.floor(-value + 0.5))


def rolled_cost(state,player,base,*,low,high,ties_away):
    """One shop price: a float32 roll, a float32 multiply, then a rounding.

    The reference rounds three different ways and does all of it in binary32,
    so this cannot be a Decimal multiplier: the arithmetic and the tie rule
    both change the last unit, and a shop price is an integer.
    """
    from ..rng import streams
    with streams.open(state) as rngs:
        rng=rngs.player(streams.seat_of(player),'Shops')
        roll=rng.next_float(low,high)
    scaled=mega_random.f32(mega_random.f32(float(base))*roll)
    return rounded_half_away(scaled) if ties_away else rounded(scaled)


def price(player,item):
    amount=Decimal(item.get('basePrice',item.get('price',0)))
    for key in player['relics']:
        if key=='MembershipCard':amount*=Decimal('.5')
        elif key=='TheCourier':amount*=Decimal('.8')
    return int(amount)


def identity(state):
    state['serial']+=1
    return 'shop:'+str(state['serial'])


def detail(player,item):
    """The shop row's own numbers: the price that applies now, the sale flag and
    the item text, so a client can lay out a detail pane without parsing labels."""
    if item['kind']=='card':
        card=e.card_view(item['card'])
        return {'kind':'card','cardId':card['id'],'type':card['kind'],'name':card['name'],'cost':card['cost'],**({'starCost':card['starCost']} if 'starCost' in card else {}),
                'description':card['description'],'price':price(player,item),'sale':bool(item.get('sale'))}
    name,description=(e.RELICS if item['kind']=='relic' else e.POTIONS).get(item['key'],(item['key'],'效果待实现'))
    return {'kind':item['kind'],'type':item['kind'],'name':name,'description':description,
            'price':price(player,item),'sale':bool(item.get('sale'))}


def card_entry(state,player,inventory,*,kind=None,rarity=None,sale=False):
    pool='colorless' if kind is None else player.get('character','ironclad')
    excluded={item['key'] for item in inventory if item['kind']=='card'}
    multiplayer=len(state['players'])>1
    candidates=[d for d in e.CARDS.values() if d['pool']==pool and d['rarity'] in RARITIES
                and d['key'] not in excluded and (kind is None or d['kind']==kind)
                and not d['values'].get('singleplayerOnly' if multiplayer else 'multiplayerOnly')]
    if rarity is None:
        rarity=odds.card_rarity(state,player,'shop',current_offset=True)
        start=RARITIES.index(rarity)
        rarity=next((RARITIES[(start+i)%3] for i in range(3)
                     if any(d['rarity']==RARITIES[(start+i)%3] for d in candidates)),None)
    candidates=[d for d in candidates if d['rarity']==rarity]
    e.require(bool(candidates),'商店卡牌候选池已耗尽。')
    selected=pick(state,player,[d['key'] for d in candidates])
    selected=next(d for d in candidates if d['key']==selected)
    card=e.new_card(state,selected['key'])
    from ..relics.hooks import modify_acquired_card
    modify_acquired_card(player,card)
    # Normal shops never roll an upgrade with act scaling. Hook upgrades are
    # handled separately, keeping card reward pity unchanged.
    base={'common':50,'uncommon':75,'rare':150}[rarity]
    if pool=='colorless':base=rounded(Decimal(base)*Decimal('1.15'))
    cost=rolled_cost(state,player,base,low=0.95,high=1.05,ties_away=True)
    if sale:cost//=2
    return {'id':identity(state),'kind':'card','key':card['key'],'card':card,
            'basePrice':cost,'sale':sale,'cardType':kind,'cardRarity':rarity if kind is None else None}


def relic_entry(state,player,inventory,rarity=None):
    key=relic_pool.pull(state,player,rarity,shop=True,
                        exclude=[item['key'] for item in inventory if item['kind']=='relic'])
    base={'common':175,'uncommon':225,'rare':275,'shop':200,'none':1}[relic_pool.DATA[key]['rarity']]
    return {'id':identity(state),'kind':'relic','key':key,
            'basePrice':rolled_cost(state,player,base,low=0.85,high=1.15,ties_away=False)}


def potion_entry(state,player,item=None):
    if item is None:item=potions.generate(state,player,source='shops')[0]
    base={'common':50,'uncommon':75,'rare':100}[potions.DATA[item['key']]['rarity']]
    return {'id':identity(state),'kind':'potion','key':item['key'],'potion':item,
            'basePrice':rolled_cost(state,player,base,low=0.95,high=1.05,ties_away=True)}


def enter(state,player):
    inventory=[];sale=roll(state,player,len(CARD_TYPES))
    for index,kind in enumerate(CARD_TYPES):inventory.append(card_entry(state,player,inventory,kind=kind,sale=index==sale))
    for rarity in ('uncommon','rare'):inventory.append(card_entry(state,player,inventory,rarity=rarity))
    for rarity in (None,None,'shop'):inventory.append(relic_entry(state,player,inventory,rarity))
    for item in potions.generate(state,player,3,source='shops'):inventory.append(potion_entry(state,player,item))
    player['shop']=inventory;player['removed']=False;player.pop('foulPotionThrown',None)
    refresh(player)
    if 'LordsParasol' in player['relics']:purchase_everything(state,player)


def purchase_everything(state,player):
    from .rewards.custom import finish_nested
    from ..combat.effects import select_now
    # Snapshot the slots: Courier replaces a purchased entry, but the free
    # purchase visits each original slot once, never its replacement again.
    original=list(player['shop'])
    for item in original:
        if item['kind']=='potion' and ('Sozu' in player['relics'] or len(player['potions'])>=potions.capacity(player)):continue
        buy(state,player,item['id'],ignore_cost=True)
        if item['kind']=='relic':finish_nested(state,player)
    eligible=[c for c in player['deck'] if e.removable(c)]
    if eligible and not player['removed']:
        select_now(state,player,{'op':'select','source':'deck','cards':eligible,'destination':'removeDeck',
                                'minimum':1,'maximum':1,'title':'领主阳伞：免费移除一张牌（不可跳过）'})
        player['removeCost']+=50 if state.get('ascension',0)>=6 else 25;player['removed']=True;purchased(state,player,0)


def refresh(player):
    from ..relics.hooks import modify_acquired_card
    for item in player.get('shop',[]):
        if item['kind']=='card':modify_acquired_card(player,item['card'])
        item['price']=price(player,item)


def purchased(state,player,cost):
    if cost>0 and 'MawBank' in player['relics']:player['mawBankSpent']=True
    refresh(player)


def buy(state,player,ident,*,ignore_cost=False):
    item=next((item for item in player['shop'] if item['id']==ident),None)
    e.require(item is not None,'商品已售出。')
    cost=0 if ignore_cost else price(player,item);e.require(player['gold']>=cost,'金币不足。')
    # Acquisition can suspend for a private choice; the outer action transaction
    # replays from its origin, preserving item identity and charging once.
    if item['kind']=='potion':
        e.require('Sozu' not in player['relics'],'添水阻止获得药水。')
        e.require(len(player['potions'])<potions.capacity(player),'药水栏已满。')
        e.require(potions.procure(state,player,deepcopy(item['potion'])),'无法获得药水。')
        player['gold']-=cost
    elif item['kind']=='card':
        e.obtain_card(state,player,deepcopy(item['card']));player['gold']-=cost
    else:
        e.require(item['key'] in e.RELICS,'遗物效果尚未实现：'+item['key'])
        player['gold']-=cost;e.relic(state,player,item['key'])
    position=player['shop'].index(item)
    if 'TheCourier' in player['relics']:
        if item['kind']=='card':replacement=card_entry(state,player,player['shop'],kind=item['cardType'],rarity=item['cardRarity'])
        elif item['kind']=='relic':replacement=relic_entry(state,player,player['shop'])
        else:replacement=potion_entry(state,player)
        player['shop'][position]=replacement
    else:player['shop'].remove(item)
    purchased(state,player,cost)
    e.log(state,f"{player['name']} 花费 {cost} 金币购买商品")


def removal_price(player):return price(player,{'basePrice':player['removeCost']})


def remove_card(state,player,ident):
    e.require(not player['removed'],'本次商店已使用删牌服务。')
    cost=removal_price(player);e.require(player['gold']>=cost,'金币不足。')
    card=e.find_card(player['deck'],ident);e.require(e.removable(card),'永恒牌不能移除。')
    player['deck'].remove(card);player['gold']-=cost;player['removeCost']+=50 if state.get('ascension',0)>=6 else 25;player['removed']=True
    purchased(state,player,cost)


def label(player,item):
    if item['kind']=='card':
        card=e.card_view(item['card']);description=f"{card['name']} [{cost_text(card)}] {card['description']}"
    else:
        name,description=(e.RELICS if item['kind']=='relic' else e.POTIONS).get(item['key'],(item['key'],'效果待实现'))
        description=f'{name}：{description}'
    return f"{description} · {price(player,item)} 金币"+(' · 半价' if item.get('sale') else '')
