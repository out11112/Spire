"""Combat-only card afflictions; registration is not interaction acceptance."""
from .. import engine as e

IMPLEMENTED={'Entangled','Hexed','Ringing','Bound','Tainted','Galvanized','Smog'}


def smog_blocks(player,card):
    return bool(player['powers'].get('smoggy') and card.get('affliction',{}).get('key')=='Smog')


def smog_played(state,player,card):
    if not player['powers'].get('smoggy') or e.definition(card)['kind']!='skill':return
    from .classes.defect import combat_cards
    for other in combat_cards(state,player):
        if e.definition(other)['kind']=='skill' and not other.get('affliction'):other['affliction']={'key':'Smog','amount':1}


def galvanic(state,amount):
    from .classes.defect import combat_cards
    for player in state['players'].values():
        for card in combat_cards(state,player):
            if e.definition(card)['kind']!='power':continue
            if card.get('affliction',{}).get('key')=='Galvanized':card['affliction']['amount']+=amount
            elif not card.get('affliction'):card['affliction']={'key':'Galvanized','amount':amount}


def vital_spark(state,amount,initial=False):
    from .classes.defect import combat_cards
    for player in state['players'].values():
        for card in combat_cards(state,player):
            if card.get('affliction',{}).get('key')=='Tainted':
                if not initial:card['affliction']['amount']=amount
                elif e.definition(card)['kind']=='skill':card['affliction']['amount']+=amount
            elif initial and not card.get('affliction') and e.definition(card)['kind']=='skill':card['affliction']={'key':'Tainted','amount':amount}


def bound_blocks(player,card):
    return bool(player['powers'].get('chainsOfBinding') and player.get('boundPlayed') and card.get('affliction',{}).get('key')=='Bound')


def drawn(state,player,card):
    amount=player['powers'].get('chainsOfBinding',0)
    if state.get('side')=='player' and amount and player.get('boundDrawn',0)<amount and not card.get('affliction'):
        card['affliction']={'key':'Bound','amount':amount};player['boundDrawn']=player.get('boundDrawn',0)+1


def ringing_blocks(player,card):
    return bool(player['powers'].get('ringing') and card.get('affliction',{}).get('key')=='Ringing' and player.get('cardsPlayed',0))


def entered_combat(state,player,card):
    kind=e.definition(card)['kind']
    # Owner powers precede enemy powers; the first eligible listener wins.
    for key,amount in player['powers'].items():
        if card.get('affliction'):continue
        if not amount:continue
        affliction=None
        if key=='smoggy' and player.get('skillsStarted',0) and kind=='skill':affliction='Smog'
        elif key=='tangled' and kind=='attack':affliction='Entangled'
        elif key=='hex':affliction='Hexed'
        elif key=='ringing':affliction='Ringing'
        if affliction:card['affliction']={'key':affliction,'amount':amount if key=='hex' else 1}
    # The card's own affliction listens after its owner's powers. Hexed clears
    # itself for an owner without Hex; Ringing has no such removal hook.
    if card.get('affliction',{}).get('key')=='Hexed' and not player['powers'].get('hex'):card.pop('affliction')
    for monster in state['enemies']:
        if monster['hp']<=0:continue
        for key,amount in monster['powers'].items():
            if card.get('affliction'):return
            if not amount:continue
            if key=='galvanic' and kind=='power':card['affliction']={'key':'Galvanized','amount':amount}
            elif key=='vitalSpark' and kind=='skill':card['affliction']={'key':'Tainted','amount':amount}


def power_applied(state,player,key):
    from .classes.defect import combat_cards
    for card in combat_cards(state,player):
        if card.get('affliction'):continue
        if key=='ringing':card['affliction']={'key':'Ringing','amount':1}
        elif key=='tangled' and e.definition(card)['kind']=='attack':
            card['affliction']={'key':'Entangled','amount':1}


def before_side_end(state,player):
    if not player['powers'].get('chainsOfBinding'):return
    player.pop('boundPlayed',None)
    from .classes.defect import combat_cards
    for card in combat_cards(state,player):
        if card.get('affliction',{}).get('key')=='Bound':card.pop('affliction')


def turn_end(state,player):
    if player['powers'].get('smoggy'):
        from .classes.defect import combat_cards
        for card in combat_cards(state,player):
            if card.get('affliction',{}).get('key')=='Smog':card.pop('affliction')
    if player['powers'].get('constrict'):e.hit(state,player,player,player['powers']['constrict'],True)
    if player['powers'].get('tender'):
        amount=player.pop('tenderPlayed',0)
        e.power(player,'strength',amount);e.power(player,'dexterity',amount)
    if player['powers'].pop('ringing',None):
        from .classes.defect import combat_cards
        for card in combat_cards(state,player):
            if card.get('affliction',{}).get('key')=='Ringing':card.pop('affliction')
    if not player['powers'].pop('tangled',None):return
    from .classes.defect import combat_cards
    for card in combat_cards(state,player):
        if card.get('affliction',{}).get('key')=='Entangled':card.pop('affliction')


def caster_power_applied(state,player,key,actor):
    from .classes.defect import combat_cards
    if key=='hex':
        player['hexSource']=actor['id']
        for card in combat_cards(state,player):
            if not card.get('affliction'):card['affliction']={'key':'Hexed','amount':player['powers']['hex']}
    elif key=='dampen':
        player['dampenCasters']=[actor['id']];player['dampenedCards']={}
        for card in combat_cards(state,player):
            if card.get('upgraded'):
                player['dampenedCards'][card['id']]=True;e.downgrade(card)


def caster_died(state,actor):
    from .classes.defect import combat_cards
    for player in state['players'].values():
        if player.get('constrictSource')==actor['id']:
            player.pop('constrictSource');player['powers'].pop('constrict',None)
        if actor['powers'].get('vitalSpark'):
            for card in combat_cards(state,player):
                if card.get('affliction',{}).get('key')=='Tainted':card.pop('affliction')
        if player.get('hexSource')==actor['id']:
            player.pop('hexSource');player['powers'].pop('hex',None)
            for card in combat_cards(state,player):
                if card.get('affliction',{}).get('key')=='Hexed':card.pop('affliction')
        if actor['id'] in player.get('dampenCasters',[]):
            player['dampenCasters'].remove(actor['id'])
            if not player['dampenCasters']:
                player.pop('dampenCasters');player['powers'].pop('dampen',None)
                originals=player.pop('dampenedCards',{})
                # Dampen tracks instances, including cards passed to a teammate.
                for owner in state['players'].values():
                    for card in combat_cards(state,owner):
                        if card['id'] in originals:e.upgrade(card)


# Official affliction titles and descriptions (afflictions.json). Entangled's
# energy icon is written out as 能量.
OFFICIAL = {'Entangled': '缠身：能量费用增加1。', 'Hexed': '邪咒：这张牌获得虚无。',
            'Ringing': '昏眩：你在本回合只能打出1张牌。',
            'Bound': '魂缚：每回合只能打出1张魂缚卡牌。卡牌会在回合结束时失去魂缚。',
            'Tainted': '污染：打出时获得{amount}层污染。', 'Galvanized': '流电：打出这张牌时受到{amount}点伤害。',
            'Smog': '烟雾：你在本回合无法再打出更多技能牌。回合结束时消除。'}
# The owner's status that keeps an affliction in force.
SOURCE_POWER = {'Entangled': 'tangled', 'Hexed': 'hex', 'Ringing': 'ringing', 'Bound': 'chainsOfBinding', 'Smog': 'smoggy'}


def description(affliction, active):
    text = OFFICIAL.get(affliction.get('key'))
    if text is None:
        return ''
    text = text.format(amount=affliction.get('amount', 1))
    power = SOURCE_POWER.get(affliction['key'])
    return text + ('' if power is None or active(power) else '（当前未生效）')
