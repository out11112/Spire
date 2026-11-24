"""Silent effect timings, sharing the serialized synchronous continuation."""
from ... import engine as e


def shivs(state,player,count,*,upgraded=False,inky=False,batch=False):
    if inky or batch:
        if player['hp']<=0 or not any(t['hp']>0 for t in state['enemies']):return []
        # Batch creation precedes post-entry upgrades and enchantments.
        result=[e.new_card(state,'Shiv') for _ in range(count)]
        for card in result:e.add_generated(state,player,card)
        if upgraded:
            for card in result:e.upgrade(card)
        if inky:
            from ..enchantments import enchant
            for card in result:enchant(card,'Inky')
        return result
    result=[]
    for _ in range(count):
        if player['hp']<=0 or not any(t['hp']>0 for t in state['enemies']):break
        card=e.new_card(state,'Shiv',upgraded)
        e.add_generated(state,player,card);result.append(card)
    return result


def discard(state,player,cards,draw_count=0):
    """Snapshot identities; discard hooks, replacement draw, then Sly autoplay."""
    from ..effects import autoplay
    snapshot=list(cards);sly=[]
    if not snapshot:return
    for card in snapshot:
        if e.definition(card)['values'].get('sly'):sly.append(card)
        for pile in ('hand','draw','discard','exhaust'):
            if card in player[pile]:player[pile].remove(card)
        player['discard'].append(card)
        player['discardedThisTurn']=player.get('discardedThisTurn',0)+1
        if state.get('side')=='player' and player['hp']>0:
            if 'ToughBandages' in player['relics']:e.gain_block(state,player,3,True)
            if 'Tingsha' in player['relics']:
                targets=[t for t in state['enemies'] if t['hp']>0]
                if targets:e.hit(state,player,e.random_enemy(state,targets),3,True)
    if draw_count:e.draw(state,player,draw_count)
    for card in sly:
        if player['hp']<=0 or not any(t['hp']>0 for t in state['enemies']):break
        # The replacement draw or a previous Sly card may have moved this card.
        # Autoplay follows the same physical card, not its old pile position.
        for pile in ('hand','draw','discard','exhaust'):
            if card in player[pile]:player[pile].remove(card)
        autoplay(state,player,card)


def entered_combat(state,player,card):
    from ..afflictions import entered_combat as afflict
    afflict(state,player,card)
    if player['powers'].get('phantomBlades') and e.definition(card)['values'].get('shiv'):
        if 'retain' not in card.setdefault('addedKeywords',[]):card['addedKeywords'].append('retain')


def apply_card(state,player,card,targets,ally=None):
    values=e.definition(card)['values']
    for key in ('accuracy','accelerant','afterimage','permanentThorns','blur','burst','infiniteBlades','noxiousFumes','envenom'):
        if values.get(key):e.power(player,key,values[key])
    for key in ('corrosiveWave','serpentForm','shadowmeld','energyNextTurn','sneaky','speedster','toolsOfTheTrade','tracking','intangible'):
        if values.get(key) and not (card['key']=='Convergence' and key=='energyNextTurn'):e.power(player,key,values[key])
    if values.get('wraithForm'):e.debuff(state,player,player,'wraithForm',values['wraithForm'],card_source=card)
    for key in ('masterPlanner','wellLaidPlans'):
        if values.get(key):player['powers'][key]=1
    if values.get('cheaperAfterPlay'):e.change_cost(card,-values['cheaperAfterPlay'],mode='add')
    if ally:
        if values.get('concoct'):e.power(ally,'concoct',values['concoct'])
        if values.get('allyTemporaryDexterity'):
            e.power(ally,'dexterity',values['allyTemporaryDexterity']);e.power(ally,'fadeDexterity',values['allyTemporaryDexterity'])
    if values.get('fanOfKnives'):
        player['powers']['fanOfKnives']=1;shivs(state,player,values['fanOfKnives'])
    if values.get('phantomBlades'):
        e.power(player,'phantomBlades',values['phantomBlades'])
        from .defect import combat_cards
        for candidate in combat_cards(state,player,card):entered_combat(state,player,candidate)
    for target in targets:
        if target['hp']<=0:continue
        if values.get('expose'):
            had_block=target['block'];target['block']=0
            if had_block:e.block_broken(state,target,player)
            target['powers'].pop('artifact',None);e.debuff(state,player,target,'vulnerable',values['expose'],card_source=card)
        if values.get('piercingWail') and e.debuff(state,player,target,'piercingWail',values['piercingWail'],card_source=card):e.power(target,'strength',-values['piercingWail'])
        if values.get('malaise'):
            amount=card['capturedX']+values.get('malaiseBonus',0)
            if amount:
                e.debuff(state,player,target,'strength',-amount,card_source=card)
                e.debuff(state,player,target,'weak',amount,card_source=card)
        if values.get('flanking') and e.debuff(state,player,target,'flanking',values['flanking'],card_source=card):
            amount=e.applied_debuff(card,target,'flanking',values['flanking'])
            target.setdefault('flankingInstances',[]).append({'owner':player['id'],'amount':amount})
    if values.get('hazePoison'):
        for target in targets:
            if target['hp']>0:e.debuff(state,player,target,'poison',values['hazePoison'],card_source=card)
        for target in targets:
            if target['hp']>0:e.debuff(state,player,target,'weak',values['hazeWeak'],card_source=card)
    if values.get('mirage'):e.gain_block(state,player,sum(t['powers'].get('poison',0) for t in state['enemies'] if t['hp']>0))
    if values.get('outbreak'):
        for target in targets:
            if target['hp']>0:poison_tick(state,target,list(state['players'].values()))
    if values.get('knifeTrap'):
        from ..effects import autoplay
        snapshot=[c for c in player['exhaust'] if e.definition(c)['values'].get('shiv')]
        for candidate in snapshot:
            if player['hp']<=0 or not any(t['hp']>0 for t in state['enemies']):break
            if card['upgraded']:e.upgrade(candidate)
            for pile in ('hand','draw','discard','exhaust'):
                if candidate in player[pile]:player[pile].remove(candidate)
            autoplay(state,player,candidate,target=targets[0]['id'])
    if values.get('handTrick') or values.get('nightmare'):
        from ..effects import select_now
        operation=({'destination':'keyword','kind':'skill','keyword':'sly','temporary':True,'title':'选择本回合获得奇巧的技能'} if values.get('handTrick') else
                   {'destination':'nightmare','title':'选择下回合复制的手牌'})
        select_now(state,player,{'op':'select','source':'hand','minimum':1,'maximum':1,**operation})
    if values.get('shadowStep'):
        discard(state,player,list(player['hand']));e.power(player,'shadowStep',1)
    if values.get('temporaryDexterity'):
        e.power(player,'dexterity',values['temporaryDexterity']);e.power(player,'temporaryDexterity',values['temporaryDexterity'])
    if values.get('inkyShivs'):shivs(state,player,values['inkyShivs'],inky=True)
    if values.get('allShivs'):
        for ally in state['players'].values():
            if ally['hp']>0:shivs(state,ally,values['allShivs'])
    for _ in range(values.get('poisonBounces',0)):
        living=[target for target in state['enemies'] if target['hp']>0]
        if living:e.debuff(state,player,e.random_enemy(state,living),'poison',values['bouncePoison'],card_source=card)
    if values.get('poisonIfPoisoned'):
        for target in targets:
            if target['hp']>0 and target['powers'].get('poison',0)>0:e.debuff(state,player,target,'poison',values['poisonIfPoisoned'],card_source=card)
    if values.get('bulletTime'):
        for candidate in player['hand']:
            if not e.definition(candidate)['values'].get('xCost'):e.free_card(candidate)
        e.debuff(state,player,player,'noDraw',1,card_source=card)
    if values.get('calculatedGamble'):discard(state,player,list(player['hand']),len(player['hand']))
    if values.get('stormOfSteel'):
        snapshot=list(player['hand']);discard(state,player,snapshot)
        shivs(state,player,len(snapshot),upgraded=card['upgraded'],batch=True)
    if values.get('hiddenDaggers'):
        from ..effects import select_now
        select_now(state,player,{'op':'select','source':'hand','destination':'discard','activeDiscard':True,'minimum':2,'maximum':2,'title':'先弃掉 2 张手牌'})
        shivs(state,player,values['hiddenDaggers'],upgraded=card['upgraded'],batch=True)
    if card.get('inky'):
        for target in targets:
            if target['hp']>0:e.debuff(state,player,target,'weak',1,card_source=card)


def poison_tick(state,target,opponents):
    count=min(target['powers'].get('poison',0),1+sum(x['powers'].get('accelerant',0) for x in opponents if x['hp']>0))
    for _ in range(count):
        if target['hp']<=0:break
        e.hit(state,target,target,target['powers']['poison'],True,unblockable=True)
        if target['hp']>0:e.power(target,'poison',-1)


def before_draw(state,player,power_key=None,record_id=None):
    if power_key in (None,'infiniteBlades'):shivs(state,player,player['powers'].get('infiniteBlades',0))
    if power_key not in (None,'nightmare'):return
    from ..power_order import nightmares
    records=nightmares(player)
    for record in list(records):
        if record_id is not None and record['id']!=record_id:continue
        for _ in range(record['amount']):e.add_generated(state,player,e.copy_card(state,record['card']))
        records.remove(record);e.power(player,'nightmare',-record['amount'])
    if not records:player['powers'].pop('nightmare',None)


def on_draw(state,player,hand_draw):
    for target in state['enemies']:
        if target['hp']<=0:continue
        if player['powers'].get('corrosiveWave'):e.debuff(state,player,target,'poison',player['powers']['corrosiveWave'])
        if not hand_draw and state.get('side')=='player' and player['powers'].get('speedster'):
            e.hit(state,player,target,player['powers']['speedster'],True)


def turn_start(state,player):
    if player['powers'].get('shadowStep'):e.power(player,'doubleDamage',player['powers'].pop('shadowStep'))
    if player['powers'].get('wraithForm'):e.debuff(state,player,player,'dexterity',-player['powers']['wraithForm'])
    if player['powers'].get('noxiousFumes'):
        for target in state['enemies']:
            if target['hp']>0:e.debuff(state,player,target,'poison',player['powers']['noxiousFumes'])
    poison_tick(state,player,state['enemies'])


def after_player_turn_start(state,player):
    count=player['powers'].get('toolsOfTheTrade',0)
    if count:
        from ..effects import select_now
        select_now(state,player,{'op':'select','source':'hand','destination':'discard','activeDiscard':True,'minimum':count,'maximum':count,'title':f'必备工具：弃掉 {count} 张手牌'})


def after_card(state,player,card):
    if e.definition(card)['values'].get('shiv'):player['shivsFinished']=player.get('shivsFinished',0)+1


def turn_end(state,player):
    player['powers'].pop('burst',None)
    for key in ('corrosiveWave','shadowmeld'):player['powers'].pop(key,None)
    if player['powers'].get('doubleDamage'):e.power(player,'doubleDamage',-1)
