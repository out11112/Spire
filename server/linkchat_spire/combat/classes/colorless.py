"""Colorless card hooks. Instanced counters are separate serializable records."""
from copy import deepcopy
from ... import engine as e


def data(player):return player.setdefault('colorless',{})


def before_card(state,player,card,definition,*,replay=False):
    values=definition['values']
    if definition['kind'] in ('attack','skill'):
        player['actionCards']=player.get('actionCards',0)+1
    card['calamityCount']=player['powers'].get('calamity',0) if definition['kind']=='attack' else 0
    if values.get('theBall') and not replay:
        allies=[p for p in state['players'].values() if p['id']!=player['id'] and p['hp']>0]
        if allies:card['passTo']=e.random_target(state,allies)['id']


def attack_extra(state,player,card,target):
    values=e.definition(card)['values'];amount=0
    if values.get('goldAxe'):amount+=state.get('totalPlays',0)
    if target and values.get('gangUp'):
        amount+=values['gangUp']*sum(count for uid,count in target.get('attackedBy',{}).items() if uid!=str(player['id']))
    if target and values.get('rend'):
        debuffs={'weak','vulnerable','frail','noBlock','noDraw','poison','constricted','doom','theGambit'}
        count=sum(n>0 for key,n in target['powers'].items() if key in debuffs)
        count+=sum(target['powers'].get(key,0)<0 for key in ('strength','dexterity'))
        count+=len(target.get('knockdownInstances',[]))
        amount+=count*values['rend']
    return amount


def apply_card(state,player,card,targets,ally):
    values=e.definition(card)['values'];records=data(player)
    if values.get('alchemize'):
        from ...run.potions import generate, procure
        procure(state,player,generate(state,player,in_combat=True,source='combat')[0])
    for key in ('fasten','prepTime','retainHand','nostalgia','dexterity','calamity','mayhem','stratagem','entropy'):
        if values.get(key):e.power(player,key,values[key])
    for key in ('beaconOfHope','theGambit'):
        if values.get(key):player['powers'][key]=1
    for key,record in [('automation',{'left':10,'energy':values.get('automation')}),
                       ('panache',{'left':5,'damage':values.get('panache'),'armed':False}),
                       ('bomb',{'left':3,'damage':values.get('bomb')}),
                       ('rollingBoulder',{'damage':values.get('rollingBoulder')})]:
        if values.get(key):
            if key=='panache':
                from ..power_order import played_instance_order
                played_instance_order(player)
            if key=='rollingBoulder':
                from ..power_order import player_start_order
                player_start_order(player)
            if key=='bomb':
                from ..power_order import side_end_order
                side_end_order(player)
            state['serial']+=1;record['id']=str(state['serial'])
            records.setdefault(key,[]).append(record)
            e.power(player,key,1)
    if ally:
        if values.get('allyEnergy'):ally['energy']+=values['allyEnergy']
        if values.get('allyBlock'):e.gain_block(state,ally,values['allyBlock'],source=player)
        if values.get('coordinate'):
            e.power(ally,'strength',values['coordinate']);e.power(ally,'coordinate',values['coordinate'])
        if values.get('mimic'):e.gain_block(state,player,ally['block'])
        if values.get('intercept'):
            sources=ally.setdefault('coverSources',[])
            if player['id'] not in sources:sources.append(player['id'])
            ally['powers']['covered']=len(sources)
            covered=player.setdefault('covering',[])
            if ally['id'] not in covered:covered.append(ally['id'])
            player['powers']['intercept']=len(covered)
    if values.get('knockdown'):
        for target in targets:
            if e.debuff(state,player,target,'knockdown',values['knockdown'],card_source=card):
                target.setdefault('knockdownInstances',[]).append({'owner':player['id'],'multiplier':e.applied_debuff(card,target,'knockdown',values['knockdown'])})
    if values.get('allBlock') or values.get('allDraw'):
        for teammate in state['players'].values():
            if teammate['hp']<=0:continue
            if values.get('allBlock'):e.gain_block(state,teammate,values['allBlock'],source=player)
            if values.get('allDraw'):e.draw(state,teammate,values['allDraw'])
    if values.get('anointed'):
        eligible=[c for c in e.top_first(player['draw']) if e.CARDS[c['key']]['rarity']=='rare']
        for chosen in e.combat_card_selection_shuffle(state,eligible)[:10-len(player['hand'])]:
            player['draw'].remove(chosen);e.add_to_hand(state,player,chosen)
    if values.get('prolong'):e.power(player,'blockNextTurn',player['block'])
    if values.get('restlessness') and not player['hand']:
        e.draw(state,player,values['restlessness']);player['energy']+=values['restlessness']
    if values.get('jackpot'):
        from ..effects import generated_cards
        for _ in range(values['jackpot']):
            for generated in generated_cards(state,player.get('character','ironclad'),1,cost=0):
                generated['upgraded']=card['upgraded'];e.add_generated(state,player,generated)
    if values.get('theBall'):card['bonusDamage']=card.get('bonusDamage',0)+values['theBall']
    if values.get('hiddenGem'):
        eligible=[c for c in e.top_first(player['draw']) if not e.definition(c)['values'].get('unplayable')
                  and e.replay_count(player,c)<1 and e.CARDS[c['key']]['kind'] not in ('curse','quest')]
        candidates=[c for c in eligible if e.CARDS[c['key']]['kind'] in ('attack','skill','power')] or eligible
        if candidates:
            selected=e.combat_card_selection(state,candidates)
            selected['extraReplays']=selected.get('extraReplays',0)+values['hiddenGem']
    if values.get('tagTeam'):
        for target in targets:
            if e.debuff(state,player,target,'tagTeam',values['tagTeam'],card_source=card):target.setdefault('tagTeamInstances',[]).append({'owner':player['id'],'amount':e.applied_debuff(card,target,'tagTeam',values['tagTeam'])})


def on_draw(state,player):
    for record in data(player).get('automation',[]):
        record['left']-=1
        if record['left']==0:player['energy']+=record['energy'];record['left']=10


def after_card(state,player,card):
    state['totalPlays']=state.get('totalPlays',0)+1
    card['lastPlayedTurn']=player.get('turnNumber',state['turn'])
    from ..power_order import after_played_instances
    after_played_instances(state,player,card)


def before_draw(state,player):
    for pile in ('draw','discard','exhaust'):
        for card in list(player[pile]):
            if e.definition(card)['values'].get('returnNextTurn') and card.get('lastPlayedTurn')==player.get('turnNumber',state['turn'])-1:
                player[pile].remove(card);e.add_to_hand(state,player,card)


def after_player_turn_start(state,player):
    if player['powers'].get('entropy'):
        from ..effects import select_now
        amount=player['powers']['entropy']
        select_now(state,player,{'op':'select','source':'hand','destination':'randomTransform','minimum':amount,'maximum':amount,
                                'transformableOnly':True,'title':'熵：选择按原牌所属池随机变形的手牌'})


def after_draw(state,player,record_id=None):
    for record in data(player).get('rollingBoulder',[]):
        if record_id is not None and record['id']!=record_id:continue
        for target in list(state['enemies']):
            if target['hp']>0:e.hit(state,player,target,record['damage'],True)
        record['damage']+=5


def before_side_end(state,player,record_id=None):
    records=data(player)
    for record in list(records.get('bomb',[])):
        if record_id is not None and record['id']!=record_id:continue
        record['left']-=1
        if record['left']==0:
            for target in list(state['enemies']):
                if target['hp']>0:e.hit(state,player,target,record['damage'],True)
            records['bomb'].remove(record);e.power(player,'bomb',-1)


def turn_end(state,player):
    player['powers'].pop('oneTwoPunch',None)
    for record in data(player).get('panache',[]):record['left']=5


def result_pile(state,player,card):
    recipient=state['players'].get(str(card.pop('passTo',None)),player)
    return_top=card.pop('nostalgiaReturn',False)
    rebound=card.pop('reboundReturn',False)
    if recipient is not player:
        e.insert_at_random(state,recipient['draw'],card,draw_pile=True)
    elif return_top or rebound or e.definition(card)['values'].get('returnToTop'):player['draw'].append(card)
    elif e.definition(card)['values'].get('returnToHand'):e.add_to_hand(state,player,card)
    else:player['discard'].append(card)
