from ... import engine as e
from .defect import combat_cards


def owned_blades(player):
    seen=set()
    for pile in ('hand','draw','discard','exhaust','inPlay'):
        for card in player.get(pile,[]):
            if card['key']=='SovereignBlade' and card['id'] not in seen:
                seen.add(card['id']);yield card


def prepare_blade(player,card):
    if card['key']=='SovereignBlade':
        card.setdefault('swordSageReplays',player['powers'].get('swordSage',0))


def sword_sage_changed(player,amount):
    for card in owned_blades(player):
        prepare_blade(player,card)
        card['swordSageReplays']+=amount


def gain_stars(state,player,amount):
    if amount<=0:return
    player['stars']=player.get('stars',0)+amount
    player['starsGainedThisTurn']=player.get('starsGainedThisTurn',0)+amount
    black_hole(state,player)


def black_hole(state,player):
    amount=player['powers'].get('blackHole',0)
    if amount and player['hp']>0:
        for enemy in state['enemies']:
            if enemy['hp']>0:e.hit(state,player,enemy,amount,True)


def after_payment(state,player,energy,stars):
    if stars>0 and 'MiniRegent' in player['relics'] and not player.get('miniRegentUsed'):
        player['miniRegentUsed']=True;e.power(player,'strength',1)
    if stars>0 and 'GalacticDust' in player['relics']:
        total=player.get('galacticDustStars',0)+stars
        player['galacticDustStars']=total%10
        if total>=10:e.gain_block(state,player,total//10*10,True)
    if stars and player['powers'].get('childOfTheStars'):
        e.gain_block(state,player,stars*player['powers']['childOfTheStars'],True)
    for record in player.get('orbitInstances',[]):
        old=record['spent'];record['spent']+=energy
        player['energy']+=(record['spent']//4-old//4)*record['amount']


def monologues(player):
    records=player.get('monologueInstances')
    if records is None:
        # Older saves stored only combined strength. Preserve that total until
        # expiry; its original distribution among instances is unavailable.
        records=[];amount=player['powers'].get('monologue',0)
        if amount:records.append({'id':'legacy','strength':amount,'applied':player.pop('monologueApplied',0)})
        player['monologueInstances']=records
    return records


def add_monologue(state,player,amount):
    from ..power_order import played_instance_order
    played_instance_order(player)
    from ..power_order import cleanup_order
    cleanup_order(player)
    state['serial']+=1
    monologues(player).append({'id':str(state['serial']),'strength':amount,'applied':0})
    e.power(player,'monologue',amount)


def expire_monologue(state,player,record_id):
    records=monologues(player)
    record=next((r for r in records if r['id']==record_id),None)
    if record is None:return
    records.remove(record)
    e.power(player,'monologue',-record['strength'])
    if record['applied']:e.debuff(state,player,player,'strength',-record['applied'])
    if not records:player['powers'].pop('monologue',None)


def before_card(state,player,card):
    if player['powers'].get('theSealedThrone'):gain_stars(state,player,player['powers']['theSealedThrone'])
    card['monologueSnapshots']={r['id']:r['strength'] for r in monologues(player)}


def before_draw(state,player,power_key=None):
    if power_key in (None,'spectrumShift') and player['powers'].get('spectrumShift'):
        from ..effects import generated_cards
        for card in generated_cards(state,'colorless',player['powers']['spectrumShift']):e.add_generated(state,player,card)
    amount=player['powers'].get('foregoneConclusion',0) if power_key in (None,'foregoneConclusion') else 0
    if amount:
        from ..effects import select_now
        if not player['draw']:e.shuffle_draw(state,player)
        select_now(state,player,{'op':'select','source':'draw','destination':'hand','minimum':amount,'maximum':amount,'title':'既定结局：选择加入手牌的牌'})
        player['powers'].pop('foregoneConclusion',None)


def turn_end(state,player):
    player.pop('paleBlueDotTriggered',None)


def forge(state,player,amount,shared=False):
    if not any(enemy['hp']>0 for enemy in state['enemies']):return
    blades=[c for c in combat_cards(state,player) if c['key']=='SovereignBlade' and not c.get('isDupe')]
    exhausted={c['id'] for c in player['exhaust']}
    if not any(c['id'] not in exhausted for c in blades):
        blade=e.new_card(state,'SovereignBlade');e.add_generated(state,player,blade);blades.append(blade)
    # Serialized continuations may hold another representation of the same card.
    damage_by_id={blade['id']:blade.get('bonusDamage',0)+amount for blade in blades}
    for blade in blades:blade['bonusDamage']=damage_by_id[blade['id']]
    if player['powers'].get('hammerTime') and not shared:
        for ally in state['players'].values():
            if ally is not player and ally['hp']>0:forge(state,ally,amount,shared=True)


def after_energy_reset(state,player):
    amount=player['powers'].pop('starNextTurn',0)
    if amount:gain_stars(state,player,amount)
    if player['powers'].get('genesis'):gain_stars(state,player,player['powers']['genesis'])


def turn_start(state,player):
    if player['powers'].get('furnace'):forge(state,player,player['powers']['furnace'])
    if player['powers'].get('reflect'):e.power(player,'reflect',-1)


def after_player_turn_start(state,player):
    if player['powers'].get('tyranny'):
        from ..effects import select_now
        n=player['powers']['tyranny']
        select_now(state,player,{'op':'select','source':'hand','destination':'exhaust','minimum':n,'maximum':n,'title':'暴政：选择消耗手牌'})


def apply_card(state,player,card,targets,ally=None):
    values=e.definition(card)['values']
    if values.get('stars'):gain_stars(state,player,values['stars'])
    if values.get('glowDraw'):
        e.draw(state,player,values['glowDraw']);e.power(player,'drawNextTurn',values['glowDraw'])
    if values.get('seekingEdge'):player['powers']['seekingEdge']=1
    if values.get('summonForth'):
        hand_ids={card['id'] for card in player['hand']}
        blades={card['id']:card for card in combat_cards(state,player) if card['key']=='SovereignBlade' and card['id'] not in hand_ids}
        for ident,blade in blades.items():
            for pile in ('draw','discard','exhaust','inPlay'):
                player[pile]=[card for card in player.get(pile,[]) if card['id']!=ident]
            e.add_to_hand(state,player,blade)
    if values.get('bigBang'):
        gain_stars(state,player,1);player['energy']+=1;forge(state,player,5)
    if values.get('forge'):forge(state,player,values['forge'])
    if values.get('drawAfterForge'):e.draw(state,player,values['drawAfterForge'])
    if values.get('forgePerHit'):
        hits=targets[0].get('attackedBy',{}).get(str(player['id']),0)-card.get('forgeAttackResults',0)
        forge(state,player,values['forgePerHit']*(1+hits))
    if values.get('monologue'):add_monologue(state,player,values['monologue'])
    if card['key']=='Convergence':e.power(player,'energyNextTurn',values['energyNextTurn'])
    for key in ('starNextTurn','parry','vigor','arsenal','furnace','genesis','swordSage','childOfTheStars','blackHole','pillarOfCreation','theSealedThrone','paleBlueDot','foregoneConclusion','monarchsGaze','reflect','royalties','spectrumShift','tyranny'):
        if values.get(key):e.power(player,key,values[key])
    if values.get('voidForm'):
        e.power(player,'voidForm',values['voidForm']);player['voidCardsPlayed']=999999999;player['endRequested']=True
    if values.get('plot'):
        for teammate in state['players'].values():
            if teammate['hp']>0:e.power(teammate,'drawNextTurn',values['plot'])
    if values.get('tutor') and ally:
        from ..effects import select_now
        select_now(state,ally,{'op':'select','source':'draw','destination':'hand','minimum':1,'maximum':1,'title':'教导：选择加入自己手牌的牌'})
    if values.get('minionTransform'):
        from ..effects import select_now
        select_now(state,player,{'op':'select','source':values.get('transformSource','hand'),'destination':'transform',
                                'minimum':0 if values.get('transformOptional') else values['transformCount'],'maximum':values['transformCount'],
                                'transformKey':values['minionTransform'],'upgraded':card.get('upgraded',False),
                                'upgradeAfterTransform':card['key']=='Charge','title':'选择变为仆从的牌'})
    if values.get('decisionsDecisions'):
        from ..effects import select_now
        select_now(state,player,{'op':'select','source':'hand','destination':'autoplayRepeated','minimum':1,'maximum':1,
                                'kind':'skill','playableOnly':True,'repeat':values['decisionsDecisions'],'title':'选择自动打出三次的技能'})
    if values.get('quasar'):
        from ..effects import generated_cards, select_now
        cards=generated_cards(state,'colorless',3)
        for candidate in cards:candidate['upgraded']=card.get('upgraded',False)
        select_now(state,player,{'op':'select','source':'generated','destination':'hand','minimum':0,'maximum':1,'cards':cards,'title':'类星体：选择无色牌，可跳过'})
    if values.get('orbit'):
        player.setdefault('orbitInstances',[]).append({'spent':0,'amount':values['orbit']});e.power(player,'orbit',values['orbit'])
    if values.get('constellationBlock') and ally:
        e.draw(state,ally,1);ally['energy']+=1;e.gain_block(state,ally,values['constellationBlock'],source=player)
    if values.get('colorlessGeneration') or values.get('largesse'):
        from ..effects import generated_cards
        for generated in generated_cards(state,'colorless',values.get('colorlessGeneration',1)):
            if values.get('largesse'):generated['upgraded']=card.get('upgraded',False)
            e.add_generated(state,ally if values.get('largesse') else player,generated,creator=player)
    if values.get('hammerTime'):player['powers']['hammerTime']=1
    if values.get('sovereignBlade') and player['powers'].get('parry'):
        e.gain_block(state,player,player['powers']['parry'])
    if values.get('manifestAuthority'):
        from ..effects import generated_cards
        for generated in generated_cards(state,'colorless',1):
            generated['upgraded']=card.get('upgraded',False);e.add_generated(state,player,generated)
    if values.get('debris') or values.get('fillDebris'):
        count=10-len(player['hand']) if values.get('fillDebris') else values['debris']
        debris=[e.new_card(state,'Debris') for _ in range(count)]
        for generated in debris:e.add_generated(state,player,generated)
    for target in targets:
        if values.get('resonance') and target['hp']>0:
            e.debuff(state,player,target,'strength',-1,card_source=card)
        if values.get('conqueror') and target['hp']>0:e.debuff(state,player,target,'conqueror',values['conqueror'],card_source=card)
        if values.get('temporaryEnemyStrength') and target['hp']>0:
            key={'CrushUnder':'crushUnder','DyingStar':'dyingStar','EnfeeblingTouch':'enfeeblingTouch'}[card['key']]
            if e.debuff(state,player,target,key,values['temporaryEnemyStrength'],card_source=card):e.power(target,'strength',-values['temporaryEnemyStrength'])


def after_card_late(state,player,card):
    # The late listener pass snapshots cards in pile order, not by class.
    candidates=[candidate for pile in ('hand','draw','discard','exhaust','inPlay') for candidate in player.get(pile,[])]
    for candidate in candidates:
        pile=next((pile for pile in ('hand','draw','discard','exhaust','inPlay') if candidate in player.get(pile,[])),None)
        values=e.definition(candidate)['values'];count=values.get('returnAfterSkills')
        skill_return=(count and pile not in (None,'hand') and e.definition(card)['kind']=='skill' and player.get('skillsFinished',0)%count==0)
        threshold=values.get('returnAfterEnergy')
        energy_return=(threshold and pile=='discard' and card.get('resourceEnergyValue',0)>=threshold)
        if skill_return or energy_return:
            player[pile].remove(candidate);e.add_to_hand(state,player,candidate)
