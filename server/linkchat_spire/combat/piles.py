"""Card piles: hand, draw pile order, shuffles and exhaust."""
from ..text import battle_log
from copy import deepcopy
from ..content import CARDS, definition, card_view
from .costs import add as change_cost
from . import damage
from . import play
from ..core import state as run_state
from ..rng import draws

def add_to_hand(s,p,c,drawn=False):
    if len(p['hand'])>=10:p['discard'].append(c);return False
    p['hand'].append(c)
    if drawn and definition(c)['values'].get('drawEnergyLoss'):
        p['energy']=max(0,p['energy']-definition(c)['values']['drawEnergyLoss'])
        battle_log.emit(s,f"{p['name']} 抽到 {card_view(c)['name']}，失去 1 能量",owner=p['id'],public=f"{p['name']} 抽牌触发失去 1 能量")
    return True

def random_pile_position(s,pile,count):
    """``CardPilePosition.Random`` — the insert index, off the ``Shuffle`` stream.

    It reads like a combat draw and is not one: the reference takes it from
    ``Rng.Shuffle``, so putting it on a combat stream desyncs every later
    shuffle in the run.
    """
    from ..rng import streams
    with streams.open(s) as rngs:
        return rngs.run('Shuffle').next_int(count+1)

def insert_at_random(s,pile,card,*,draw_pile=False):
    """Put a card at a random position in a pile. Returns the index used."""
    index=random_pile_position(s,pile,len(pile))
    # Original draw piles are top-first; our draw() pops from the end.
    if draw_pile:index=len(pile)-index
    pile.insert(index,card)
    return index

def add_generated(s,p,c,pile='hand',creator=None,random_position=False):
    if definition(c)['values'].get('midnight') and not c.get('midnightClone'):
        change_cost(c,-s.get('exhaustCount',0),mode='add')
    if definition(c)['values'].get('pinpoint') and not c.get('pinpointClone'):
        change_cost(c,-p.get('skillsFinished',0),mode='add',expires=('turn',))
    if definition(c)['values'].get('stomp') and not c.get('stompClone'):
        change_cost(c,-p.get('attacksFinished',0),mode='add',expires=('turn',))
    from .classes.regent import prepare_blade
    prepare_blade(p,c)
    from ..relics.shop import entered_card
    entered_card(p,c)
    creator=creator or p
    if creator['hp']>0 and 'Regalite' in creator.get('relics',[]) and not creator.get('regaliteUsed'):
        creator['regaliteUsed']=True;damage.gain_block(s,creator,4,True)
    from .classes.boss import generated
    generated(s,c)
    creator['generatedThisCombat']=creator.get('generatedThisCombat',0)+1
    from .classes.silent import entered_combat
    entered_combat(s,p,c)
    if pile=='hand':add_to_hand(s,p,c)
    elif random_position:insert_at_random(s,p[pile],c,draw_pile=pile=='draw')
    else:p[pile].append(c)
    if creator['id']==p['id'] and CARDS[c['key']]['kind']=='status':
        from .classes.defect import combat_cards
        for candidate in combat_cards(s,p):
            if definition(candidate)['values'].get('rocketPunch'):change_cost(candidate,-1,mode='add',expires=('play',))
    from .classes.defect import on_generated
    for key in list(creator['powers']):
        if key in ('smokestack','trashToTreasure'):on_generated(s,creator,c,power_key=key)
        elif key=='arsenal' and creator['hp']>0 and creator['powers'][key]:damage.power(creator,'strength',creator['powers'][key])
        elif key=='pillarOfCreation' and creator['hp']>0 and creator['powers'][key]:damage.gain_block(s,creator,creator['powers'][key],True)
    from .classes.necrobinder import on_generated as necrobinder_on_generated
    necrobinder_on_generated(s,creator,c)

def card_sort_key(c):
    """``CardModel.CompareTo``: ``ModelId`` first, then upgrade level.

    Every card shares the ``CARD`` category, so the id compares by its entry —
    the class name slugified to UPPER_SNAKE, ordinally. That is not the order of
    the CamelCase keys (``BODYGUARD`` < ``BODY_SLAM``, but ``BodySlam`` <
    ``Bodyguard``). ``StableShuffle`` sorts before it shuffles, so this key — not
    the pile order — decides which card each draw lands on.
    """
    from ..rng.mega_random import snake_case
    return (snake_case(c['key']).upper(),1 if c.get('upgraded') else 0)

# Pile orientation. The reference's piles are top-first: ``Draw`` takes
# ``Cards[0]`` and a shuffle's result list becomes the pile in list order. Ours
# are bottom-first — ``draw()`` pops the end — so a shuffle result is reversed
# on the way in, and the current pile reversed on the way out.

def top_first(pile):
    """A pile in the reference's order, for anything that indexes or filters it.

    ``NextItem``, ``TakeRandom`` and ``StableShuffle`` over ``Draw.Cards`` see the
    top card first; handing them our bottom-first list picks a different card.
    """
    return list(reversed(pile))

def stable_card_shuffle(s,stream,cards):
    """``cards.ToList().StableShuffle(Rng.<stream>)``: sort like ``List<CardModel>.Sort``, then shuffle."""
    cards=list(cards)
    return draws.run_rng(s,stream,lambda rng:rng.stable_shuffle(cards,key=card_sort_key))

def reference_sorted(cards):
    """``List<CardModel>.Sort()`` alone, for streams the caller shuffles itself."""
    from ..rng.mega_random import dotnet_sort
    return dotnet_sort(list(cards),card_sort_key)

def shuffle_cards(s,items):
    """``StableShuffle`` on the Shuffle stream. Takes and returns top-first order."""
    from ..rng import streams
    with streams.open(s) as rngs:
        return rngs.run('Shuffle').stable_shuffle(list(items),key=card_sort_key)

def initial_draw_pile(s,deck):
    """``Player.PopulateCombatState``: deck order, ``UnstableShuffle`` on the Shuffle stream.

    Unlike a later reshuffle the combat's first shuffle does not sort, so the
    deck's own order is part of the result. Returned in our bottom-first storage.
    """
    from ..rng import streams
    cards=deepcopy(list(deck))
    with streams.open(s) as rngs:
        rngs.run('Shuffle').shuffle(cards)
    return cards[::-1]

def shuffle_draw(s,p):
    if not p['draw'] and not p['discard']:return
    shuffle_listeners=list(reversed(p['draw']))+list(p['discard'])
    # ``CardPileCmd.Shuffle`` takes the discard pile first, then the draw pile
    # top-first; the sort only sees that order for cards with equal keys.
    battle_log.emit(s,f"{p['name']} 洗牌 · {len(p['discard'])+len(p['draw'])} 张",'shuffle',actor=p['id'])
    p['draw']=shuffle_cards(s,p['discard']+p['draw'][::-1])[::-1];p['discard']=[]
    from .enchantments import shuffled as enchantment_shuffle
    enchantment_shuffle(p,shuffle_listeners)
    if p['powers'].get('stratagem'):
        from .effects import select_now
        select_now(s,p,{'op':'select','source':'draw','destination':'hand','minimum':p['powers']['stratagem'],'maximum':p['powers']['stratagem'],'title':'计策：从洗好的抽牌堆取牌'})
    for relic_key in list(p['relics']):
        if relic_key=='TheAbacus':damage.gain_block(s,p,6,True)
        elif relic_key=='BiiigHug':add_generated(s,p,run_state.new_card(s,'Soot'),'draw',random_position=True)

def draw(s,p,n,*,hand_draw=False):
    result=[]
    if not hand_draw and s.get('side')=='player' and 'Fiddle' in p['relics']:return result
    if (p['powers'].get('noDraw') and not hand_draw) or p['hp']<=0:return result
    for _ in range(max(0,int(n))):
        if len(p['hand'])>=10 or p['hp']<=0 or not any(enemy['hp']>0 or enemy.get('awaitingRevive') for enemy in s['enemies']):break
        if not p['draw']:
            shuffle_draw(s,p)
        if not p['draw'] or len(p['hand'])>=10:break
        card=p['draw'].pop()
        if add_to_hand(s,p,card,True):
            from .classes.colorless import on_draw
            p['drawnThisCombat']=p.get('drawnThisCombat',0)+1
            if not hand_draw:p['extraDrawsThisTurn']=p.get('extraDrawsThisTurn',0)+1
            values=definition(card)['values']
            result.append(card)
            if p['powers'].get('hellraiser') and values.get('strike'):
                from .effects import autoplay
                # The reference's nine-play guard applies only to infinite-HP
                # training targets, not ordinary encounters.
                infinite=all(enemy.get('infiniteHp') for enemy in s['enemies'] if enemy['hp']>0)
                if not infinite:p['hellraiserInfinitePlays']=0
                if not infinite or p.get('hellraiserInfinitePlays',0)<9:
                    if infinite:p['hellraiserInfinitePlays']=p.get('hellraiserInfinitePlays',0)+1
                    p['hand'].remove(card);autoplay(s,p,card)
            if p['powers'].get('confused') and CARDS[card['key']]['cost']>=0 and not CARDS[card['key']]['values'].get('xCost'):change_cost(card,draws.roll_energy_cost(s))
            if values.get('drawCostReduction'):change_cost(card,-values['drawCostReduction'],mode='add')
            if values.get('drawDamageGrowth'):card['bonusDamage']=card.get('bonusDamage',0)+values['drawDamageGrowth']
            on_draw(s,p)
            from .classes.silent import on_draw as silent_on_draw
            silent_on_draw(s,p,hand_draw)
            from .classes.defect import on_draw as defect_on_draw
            defect_on_draw(s,p,card)
            from .classes.necrobinder import on_draw as necrobinder_on_draw
            necrobinder_on_draw(s,p,card)
            from .enchantments import drawn
            drawn(s,p,card)
            from .afflictions import drawn as affliction_drawn
            affliction_drawn(s,p,card)
    return result

def exhaust(s,p,c,*,caused_by_ethereal=False):
    for pile in ('hand','draw','discard'):
        if c in p[pile]:p[pile].remove(c)
    p['exhaust'].append(c)
    p['exhaustedThisTurn']=p.get('exhaustedThisTurn',0)+1
    s['exhaustCount']=s.get('exhaustCount',0)+1
    from .classes.defect import combat_cards
    for owner in s['players'].values():
        for candidate in combat_cards(s,owner):
            if definition(candidate)['values'].get('midnight'):
                change_cost(candidate,-1,mode='add')
    if p['hp']>0:
        if 'JossPaper' in p['relics']:
            if caused_by_ethereal:p['jossPaperEthereal']=p.get('jossPaperEthereal',0)+1
            else:
                p['jossPaperCards']=(p.get('jossPaperCards',0)+1)%5
                if p['jossPaperCards']==0:draw(s,p,1)
        if definition(c)['values'].get('exhaustEnergy'):
            # DrumOfBattle resolves its skill repeat modifiers on exhaustion,
            # without starting a card-play series or firing play listeners.
            repeats=1+play.replay_count(p,c)
            if 'ThrowingAxe' in p['relics'] and not p.get('throwingAxeUsed'):
                p['throwingAxeUsed']=True;repeats+=1
            for key in ('duplication','burst'):
                if p['powers'].get(key):repeats+=1;damage.power(p,key,-1)
            if p.get('seriesStarted',0)<p['powers'].get('echoForm',0):repeats+=1
            p['energy']+=max(0,repeats)*definition(c)['values']['exhaustEnergy']
        if p['powers'].get('feelNoPain'):damage.gain_block(s,p,p['powers']['feelNoPain'],True)
        if p['powers'].get('darkEmbrace'):
            if caused_by_ethereal:p['darkEmbraceEthereal']=p.get('darkEmbraceEthereal',0)+1
            else:draw(s,p,p['powers']['darkEmbrace'])
        from ..relics.hooks import after_exhaust
        after_exhaust(s,p)
        from ..relics.shop import after_exhaust as shop_after_exhaust
        shop_after_exhaust(s,p,c)
