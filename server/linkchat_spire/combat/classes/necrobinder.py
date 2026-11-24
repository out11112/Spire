from copy import deepcopy
from ... import engine as e
from .. import osty


DEBUFFS={'weak','vulnerable','frail','noBlock','noDraw','poison','doom','debilitate','hang','theGambit','shrink','demise','shacklingPotion',
         *e.TEMPORARY_STRENGTH_LOSS,'hyperbeamFocusDown','strangle','knockdown','tagTeam','sicEm','flanking','wraithForm','conqueror','borrowedTime','biasedCognition','oblivion','neurosurge'}
INSTANCE_KEYS={'strangle':'strangleInstances','knockdown':'knockdownInstances','tagTeam':'tagTeamInstances','sicEm':'sicEmInstances','flanking':'flankingInstances','oblivion':'oblivionInstances'}


def first_applier_records(target,field):
    records=target.setdefault(field,[])
    # These powers have one counter, not one instance per applying player.
    # Preserve the original applier when reading older multi-record states.
    if len(records)>1:
        records[0]['amount']=sum(record['amount'] for record in records)
        del records[1:]
    return records


def stack_first_applier(target,field,owner,amount):
    records=first_applier_records(target,field)
    if records:records[0]['amount']+=amount
    else:records.append({'owner':owner,'amount':amount})


def per_applier_records(target,field):
    merged={}
    for record in target.get(field,[]):
        owner=record['owner']
        if owner in merged:merged[owner]['amount']+=record['amount']
        else:merged[owner]=dict(record)
    target[field]=list(merged.values())
    return target[field]


def stack_per_applier(target,field,owner,amount):
    records=per_applier_records(target,field)
    record=next((r for r in records if r['owner']==owner),None)
    if record:record['amount']+=amount
    else:records.append({'owner':owner,'amount':amount})


def snapshot_debuffs(target):
    for field in ('strangleInstances','oblivionInstances'):
        if field in target:per_applier_records(target,field)
    powers={key:amount for key,amount in target['powers'].items() if key in DEBUFFS and amount>0 or key in ('strength','dexterity','focus','shrink') and amount<0}
    # Temporary strength loss also changes Strength; do not copy that component
    # twice when both the marker and the negative Strength power are present.
    if 'strength' in powers:
        powers['strength']+=sum(powers.get(key,0) for key in e.TEMPORARY_STRENGTH_LOSS)
        if powers['strength']==0:powers.pop('strength')
    if 'focus' in powers:
        powers['focus']+=powers.get('hyperbeamFocusDown',0)
        if powers['focus']==0:powers.pop('focus')
    return {'powers':powers,'instances':{key:deepcopy(target.get(key,[])) for key in INSTANCE_KEYS.values()}}


def spread(state,player,source_id,snapshot,card=None):
    for target in state['enemies']:
        if target['id']==source_id or target['hp']<=0:continue
        for key,amount in snapshot['powers'].items():
            if key in INSTANCE_KEYS:
                field=INSTANCE_KEYS[key]
                for record in snapshot['instances'][field]:
                    actor=state['players'].get(str(record['owner']),player)
                    value_key='multiplier' if key=='knockdown' else 'amount'
                    count=record.get(value_key,1)
                    if e.debuff(state,actor,target,key,count,card_source=card):
                        copied=deepcopy(record)
                        copied[value_key]=e.applied_debuff(card or {},target,key,count)
                        if key=='sicEm':stack_first_applier(target,field,copied['owner'],copied['amount'])
                        elif key in ('strangle','oblivion'):stack_per_applier(target,field,copied['owner'],copied['amount'])
                        else:target.setdefault(field,[]).append(copied)
            elif key in ('strength','dexterity','focus') and amount>0:e.power(target,key,amount)
            elif e.debuff(state,player,target,key,amount,card_source=card):
                if key in e.TEMPORARY_STRENGTH_LOSS:e.power(target,'strength',-amount)
                elif key=='hyperbeamFocusDown':e.power(target,'focus',-amount)


def generate_souls(state,player,count,upgraded=False,creator=None):
    cards=[e.new_card(state,'Soul',upgraded) for _ in range(count)]
    for card in cards:
        e.add_generated(state,player,card,'draw',creator=creator);player['draw'].remove(card)
        e.insert_at_random(state,player['draw'],card,draw_pile=True)


def before_card(state,player,card):
    card['oblivionDoom']=[{'target':target['id'],'amount':sum(r['amount'] for r in target.get('oblivionInstances',[]) if r['owner']==player['id'])} for target in state['enemies'] if target['hp']>0]
    from ..power_order import before_card_cost_powers
    before_card_cost_powers(state,player,card)
    if e.combat_definition(player,card)['values'].get('ethereal') and player['powers'].get('spiritOfAsh'):
        e.gain_block(state,player,player['powers']['spiritOfAsh'],True)


def before_draw(state,player,power_key=None):
    if power_key in (None,'sentryMode'):
        for _ in range(player['powers'].get('sentryMode',0)):e.add_generated(state,player,e.new_card(state,'SweepingGaze'))
    if power_key in (None,'callOfTheVoid') and player['powers'].get('callOfTheVoid'):
        from ..effects import generated_cards
        cards=[]
        for _ in range(player['powers']['callOfTheVoid']):cards+=generated_cards(state,player.get('character','ironclad'),1)
        for card in cards:
            card.setdefault('addedKeywords',[]).append('ethereal');e.add_generated(state,player,card)


def on_draw(state,player,card):
    from ..power_order import necrobinder_draw_order
    for owner in state['players'].values():
        if owner['hp']<=0:continue
        for token in necrobinder_draw_order(owner):
            if token=='pagestorm':
                if owner is player and e.combat_definition(player,card)['values'].get('ethereal') and player['powers'].get('pagestorm'):
                    e.draw(state,player,player['powers']['pagestorm'])
                continue
            record=next((r for r in owner.get('cacophonyInstances',[]) if 'cacophony:'+r['id']==token),None)
            if record is None:continue
            record['left']-=1
            if record['left']==0:
                record['left']=33;targets=[x for x in state['enemies'] if x['hp']>0]
                if targets:e.hit(state,owner,e.random_enemy(state,targets),record['damage'],True)


def on_generated(state,creator,card):
    if card['key']!='Soul':return
    for recipient in state['players'].values():
        if recipient['hp']<=0:continue
        for record in first_applier_records(recipient,'soulboundInstances'):
            if record['owner']==creator['id'] and not record.get('adding'):
                record['adding']=True
                try:generate_souls(state,recipient,record['amount'])
                finally:record.pop('adding',None)


def on_debuff(state,actor,target,key,temporary=False):
    if key=='doom' and actor['powers'].get('shroud'):e.gain_block(state,actor,actor['powers']['shroud'],True)
    if target in state['enemies'] and not temporary and actor['powers'].get('sleightOfFlesh'):
        e.hit(state,actor,target,actor['powers']['sleightOfFlesh'],True)


def lose_strength(state,actor,target,amount,*,card_source=None):
    e.debuff(state,actor,target,'strength',-amount,card_source=card_source)


def after_attack_damage(state,actor,target,amount):
    if amount<=0 or target['hp']<=0:return
    controller=state['players'].get(str(actor.get('owner',actor['id'])))
    if not controller:return
    for owner in state['players'].values():
        if owner['hp']<=0:continue
        if owner is controller and owner['powers'].get('reaperForm'):
            e.debuff(state,owner,target,'doom',amount*owner['powers']['reaperForm'])
        elif owner is not controller and owner['hp']>0 and owner['powers'].get('underworld'):
            e.debuff(state,owner,target,'doom',amount*owner['powers']['underworld'])


def doom_side_end(state,creatures,participants):
    doomed=[c for c in creatures if c['hp']>0 and c['powers'].get('doom',0)>=c['hp']]
    if doomed and any(c is doomed[0] for c in participants):doom_kill(state,doomed)


def doom_kill(state,creatures):
    doomed=[c for c in creatures if c['hp']>0 and c['powers'].get('doom',0)>=c['hp']]
    for creature in doomed:
        if creature['hp']>0:
            if creature.get('owner') and state['players'].get(str(creature['owner']),{}).get('osty') is creature:
                osty_hp_lost(state,state['players'][str(creature['owner'])],creature['hp'])
            else:
                creature['hp']=0
                from ...run.potions import prevent_death
                if not prevent_death(state,creature):on_death(state,creature)
            if creature['hp']<=0:
                e.log(state,f"{creature['name']} 被灾厄击倒")
    for player in state['players'].values():
        if 'BookRepairKnife' in player['relics'] and player['hp']>0:
            count=sum(creature is not player and not creature.get('fatalBlocked') and not creature['powers'].get('minion') for creature in doomed)
            if count:e.heal(player,3*count)


def osty_hp_lost(state,player,amount):
    pet=player.get('osty')
    if not pet or pet['hp']<=0:return
    lost=min(pet['hp'],amount);pet['hp']-=lost
    if lost and player['powers'].get('necroMastery'):
        for target in state['enemies']:
            if target['hp']>0:e.hit(state,player,target,lost*player['powers']['necroMastery'],True,unblockable=True)
    if pet['hp']<=0:on_death(state,pet)


def turn_start(state,player):
    targets=[x for x in state['enemies'] if x['hp']>0]
    if targets and player['powers'].get('countdown'):
        e.debuff(state,player,e.random_enemy(state,targets),'doom',player['powers']['countdown'])
    if player['powers'].get('neurosurge'):e.debuff(state,player,player,'doom',player['powers']['neurosurge'])


def after_player_turn_start(state,player):
    if player.get('summonDueAtStart'):
        amount=player['powers'].pop('summonNextTurn',0)
        if amount:osty.summon(state,player,amount)


def on_death(state,creature):
    if creature['hp']<=0:
        for target in [*state['players'].values(),*state['enemies']]:
            if target.get('shrinkSource')==creature['id']:
                target['powers'].pop('shrink',None);target.pop('shrinkSource',None)
    if creature['hp']>0 or creature.get('deathHandled'):return
    creature['deathHandled']=True
    for ally in state['players'].values():
        for sources,power in (('guardians','guarded'),('coverSources','covered')):
            if creature['id'] in ally.get(sources,[]):
                ally[sources].remove(creature['id']);ally['powers'][power]=len(ally[sources])
    if creature.get('powers',{}).get('stock',0)>0:
        from ..monsters import spawn
        remaining=creature['powers']['stock']-1
        replacement=spawn(state,'Axebot',hp_bonus=(2-remaining)*10,powers={'stock':remaining} if remaining else {})
        replacement['respawnCount']=2-remaining
        e.intent(state,replacement)
    if creature.get('powers',{}).get('infested'):
        from ..monsters import spawn_wrigglers
        spawn_wrigglers(state)
    from ..afflictions import caster_died
    caster_died(state,creature)
    if any(enemy is creature for enemy in state['enemies']):
        for enemy in state['enemies']:
            if enemy is not creature and enemy['hp']>0 and enemy['powers'].get('ravenous'):
                enemy['stunned']=True;e.power(enemy,'strength',enemy['powers']['ravenous'])
    from .defect import combat_cards
    for player in state['players'].values():
        for card in combat_cards(state,player):
            amount=e.combat_definition(player,card)['values'].get('deathCostReduction',0)
            if amount:e.change_cost(card,-amount,mode='add')
    from .boss import after_death
    after_death(state,creature)
    if any(enemy is creature for enemy in state['enemies']):
        for player in state['players'].values():
            if player['hp']>0 and 'GremlinHorn' in player['relics']:
                player['energy']+=1;e.draw(state,player,1)
    if any(enemy is creature for enemy in state['enemies']) and not creature['powers'].get('minion'):
        teammates=[enemy for enemy in state['enemies'] if enemy is not creature and enemy['hp']>0]
        if teammates and all(enemy['powers'].get('minion') for enemy in teammates):
            for enemy in teammates:enemy['hp']=0;on_death(state,enemy)


def apply_card(state,player,card,targets,ally=None):
    values=e.combat_definition(player,card)['values']
    if values.get('summon'):osty.summon(state,player,values['summon'])
    if values.get('blockAfterSummon'):e.gain_block(state,player,values['blockAfterSummon'])
    if values.get('healOsty') and osty.alive(player):e.heal(player['osty'],values['healOsty'])
    if values.get('sacrificeOsty') and osty.alive(player):
        amount=player['osty']['maxHp']*values['sacrificeOsty'];osty_hp_lost(state,player,player['osty']['hp']);e.gain_block(state,player,amount)
    if values.get('friendshipStrengthLoss'):
        lose_strength(state,player,player,values['friendshipStrengthLoss'])
    for key in ('calcify','countdown','danseMacabre','devourLife','haunt','summonNextTurn','lethality','friendship','sentryMode','shroud','sleightOfFlesh','callOfTheVoid','demesne','forbiddenGrimoire','necroMastery','pagestorm','reaperForm','spiritOfAsh','underworld'):
        if values.get(key):e.power(player,key,values[key])
    if values.get('selfStrengthLoss'):lose_strength(state,player,player,values['selfStrengthLoss'])
    if values.get('soulbound') and ally:
        stack_first_applier(ally,'soulboundInstances',player['id'],values['soulbound'])
        e.power(ally,'soulbound',values['soulbound'])
    if values.get('seance') or values.get('transfigure'):
        from ..effects import select_now
        operation={'source':'draw','destination':'transform','transformKey':'Soul','upgraded':False} if values.get('seance') else {'source':'hand','destination':'transfigure'}
        select_now(state,player,{'op':'select','minimum':1,'maximum':1,'title':'选择变为灵魂的牌' if values.get('seance') else '选择增加费用和重放次数的牌',**operation})
    if values.get('neurosurge'):e.debuff(state,player,player,'neurosurge',values['neurosurge'],card_source=card)
    if values.get('allSummon'):
        for teammate in state['players'].values():
            if teammate['hp']>0:osty.summon(state,teammate,values['allSummon'])
    if values.get('allySouls'):
        for teammate in state['players'].values():
            if teammate['hp']>0:generate_souls(state,teammate,values['allySouls'],creator=player)
    if values.get('borrowedTime'):e.debuff(state,player,player,'borrowedTime',values['borrowedTime'],card_source=card)
    if values.get('cacophony'):
        from ..power_order import necrobinder_draw_order
        necrobinder_draw_order(player)
        state['serial']+=1
        player.setdefault('cacophonyInstances',[]).append({'id':str(state['serial']),'left':33,'damage':values['cacophony']});e.power(player,'cacophony',values['cacophony'])
    if values.get('deathDoorBlock'):
        for _ in range(3 if player.get('doomAppliedThisTurn') else 1):e.gain_block(state,player,values['deathDoorBlock'])
    if values.get('dirgeSummon'):
        count=card.get('capturedX',0)
        for _ in range(count):osty.summon(state,player,values['dirgeSummon'])
        generate_souls(state,player,count,card.get('upgraded',False))
    if values.get('cleanse') or values.get('dredge'):
        from ..effects import select_now
        amount=1 if values.get('cleanse') else min(values['dredge'],10-len(player['hand']))
        if amount:select_now(state,player,{'op':'select','source':'draw' if values.get('cleanse') else 'discard',
                                          'destination':'exhaust' if values.get('cleanse') else 'hand','minimum':amount,'maximum':amount,
                                          'title':'选择消耗抽牌堆的牌' if values.get('cleanse') else '选择取回的弃牌'})
    if values.get('eidolon'):
        from ..effects import autoplay
        cards=[c for c in player['exhaust'] if e.combat_definition(player,c)['values'].get('ethereal') and not e.definition(c)['values'].get('unplayable')]
        for candidate in cards:
            if player['hp']<=0 or not any(x['hp']>0 for x in state['enemies']):break
            for pile in ('hand','draw','discard','exhaust'):player[pile][:]=[c for c in player[pile] if c['id']!=candidate['id']]
            autoplay(state,player,candidate)
    for target in targets:
        if target['hp']<=0:continue
        if values.get('enemyStrengthLoss'):lose_strength(state,player,target,values['enemyStrengthLoss'],card_source=card)
        if values.get('oblivion') and e.debuff(state,player,target,'oblivion',values['oblivion'],card_source=card):
            records=target.setdefault('oblivionInstances',[]);record=next((r for r in records if r['owner']==player['id']),None)
            amount=e.applied_debuff(card,target,'oblivion',values['oblivion'])
            if record:record['amount']+=amount
            else:records.append({'owner':player['id'],'amount':amount})
        if values.get('doom'):e.debuff(state,player,target,'doom',values['doom'],card_source=card)
        if values.get('noEscape'):e.debuff(state,player,target,'doom',values['noEscape']+5*(target['powers'].get('doom',0)//10),card_source=card)
        if values.get('captureSpirit'):e.hit(state,player,target,values['captureSpirit'],True,unblockable=True)
        if values.get('damageToDoom'):e.debuff(state,player,target,'doom',card.get('attackDamage',0),card_source=card)
        if values.get('debilitate'):e.debuff(state,player,target,'debilitate',values['debilitate'],card_source=card)
        if values.get('hang'):e.debuff(state,player,target,'hang',min(max(2,target['powers'].get('hang',0)),999999999-target['powers'].get('hang',0)),card_source=card)
        if values.get('sicEm') and e.debuff(state,player,target,'sicEm',values['sicEm'],card_source=card):
            stack_first_applier(target,'sicEmInstances',player['id'],e.applied_debuff(card,target,'sicEm',values['sicEm']))
    if values.get('weakAfterDoom'):
        for target in list(state['enemies']):
            if target['hp']>0:e.debuff(state,player,target,'weak',values['weakAfterDoom'],card_source=card)
    if values.get('drawAfterDoom'):e.draw(state,player,values['drawAfterDoom'])
    if values.get('endOfDays'):doom_kill(state,state['enemies'])
    if values.get('misery'):spread(state,player,card['replayTarget'],card['copiedDebuffs'],card)
    if values.get('soulDrawGeneration'):generate_souls(state,player,values['soulDrawGeneration'])
    if values.get('upgradeDiscard'):
        candidates=[candidate for candidate in player['discard'] if e.upgradable(candidate)]
        for candidate in e.combat_card_selection_shuffle(state,candidates)[:values['upgradeDiscard']]:e.upgrade(candidate)
    # Osty can die to retaliation while the attack above resolves. The play-time
    # guard already ran, so the block and the draw are unconditional here; only
    # the sacrifice re-checks aliveness, as in the reference.
    if values.get('fetch') and card.get('lastPlayedTurn')!=player.get('turnNumber',state['turn']):e.draw(state,player,values['fetch'])
    if values.get('ostySacrificeBlock'):
        e.gain_block(state,player,values['ostySacrificeBlock'])
        if osty.alive(player):osty_hp_lost(state,player,player['osty']['hp'])
    if values.get('veilpiercer'):e.power(player,'veilpiercer',values['veilpiercer'])
    if values.get('reave') or values.get('severance'):
        piles=('draw','discard','hand') if values.get('severance') else ('draw',)
        souls=[e.new_card(state,'Soul',bool(values.get('reave') and card['upgraded'])) for _ in piles]
        for pile,soul in zip(piles,souls):
            e.add_generated(state,player,soul,pile)
            if pile=='draw':player['draw'].remove(soul);e.insert_at_random(state,player['draw'],soul,draw_pile=True)
    if values.get('scythe'):
        card['bonusDamage']=card.get('bonusDamage',0)+values['scythe']
        for original in player['deck']:
            if original['id']==card['id']:original['bonusDamage']=original.get('bonusDamage',0)+values['scythe']


def after_card(state,player,card):
    values=e.combat_definition(player,card)['values']
    for record in card.get('oblivionDoom',[]):
        target=next((x for x in state['enemies'] if x['id']==record['target']),None)
        if target and target['hp']>0 and record['amount']:e.debuff(state,player,target,'doom',record['amount'])
    if values.get('ethereal'):player['etherealPlays']=player.get('etherealPlays',0)+1
