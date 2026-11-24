"""Persist ordering where one power identity has multiple hook instances."""

HAND_DRAW_POWERS={'creativeAi','spectrumShift','foregoneConclusion','infiniteBlades','sentryMode','callOfTheVoid','helloWorld','nightmare'}
PLAYER_START_POWERS={'toolsOfTheTrade','loop','hibernate','tyranny','summonNextTurn','entropy','crimsonMantle','inferno','rollingBoulder'}
DRAW_COUNT_POWERS={'drawNextTurn','toolsOfTheTrade','machineLearning','tyranny','demesne','clarity','mindRot'}
CARD_COST_POWERS={'danseMacabre','freeSkill','freeAttack','freePower','veilpiercer'}
ENERGY_MODIFIER_POWERS={'borrowedTime','tangled','curious'}
CARD_LOCATION_POWERS={'nostalgia','rebound','corruption'}
PLAYED_SINGLE_POWERS={'haunt','devourLife','blackHole','calamity','rage','afterimage','rupture','serpentForm','storm','subroutine','voidForm','paleBlueDot','masterPlanner','tender'}


def played_instance_order(player):
    from .classes.regent import monologues
    groups={'monologue':monologues(player),'panache':player.get('colorless',{}).get('panache',[])}
    candidates=[]
    for key in player['powers']:
        if key in PLAYED_SINGLE_POWERS and player['powers'][key]:candidates.append(key+':single')
        for index,record in enumerate(groups.get(key,[])):
            record.setdefault('id','legacy:'+str(index))
            candidates.append(key+':'+record['id'])
    order=[token for token in player.get('playedInstanceOrder',[]) if token in candidates]
    order.extend(token for token in candidates if token not in order)
    player['playedInstanceOrder']=order
    return list(order)


def after_played_instances(state,player,card):
    from .. import engine as e
    from .classes.defect import after_card as imitation_after_card
    from ..relics.hooks import after_card as relic_after_card
    for observer in list(state['players'].values()):
        if observer['id']==player['id']:after_owner_played_instances(state,player,card)
        elif e.definition(card)['kind']=='attack' and observer['powers'].get('sneaky'):
            e.gain_block(state,observer,observer['powers']['sneaky'],True)
        imitation_after_card(state,player,card,observer=observer)
        if observer['id']==player['id']:
            relic_after_card(state,player,card)
            from .enchantments import played as enchantment_played
            enchantment_played(card)
            enchantment=card.get('enchantment',{})
            if enchantment.get('key')=='Goopy':
                enchantment['amount']+=1
                permanent=next((entry for entry in player['deck'] if entry['id']==card['id']),None)
                if permanent and permanent.get('enchantment',{}).get('key')=='Goopy':permanent['enchantment']['amount']+=1


def after_owner_played_instances(state,player,card):
    from .. import engine as e
    from .classes.regent import monologues
    snapshots=card.pop('monologueSnapshots',{})
    for token in played_instance_order(player):
        key,ident=token.split(':',1)
        if key=='tender':
            player['tenderPlayed']=player.get('tenderPlayed',0)+1
            actor=next((enemy for enemy in state['enemies'] if enemy['id']==player.get('tenderSource')),player)
            e.debuff(state,actor,player,'strength',-1);e.debuff(state,actor,player,'dexterity',-1)
            continue
        if key=='masterPlanner':
            if e.definition(card)['kind']=='skill' and 'sly' not in card.setdefault('addedKeywords',[]):
                card['addedKeywords'].append('sly')
            continue
        if key=='paleBlueDot':
            if not player.get('paleBlueDotTriggered') and player.get('playsFinished',0)>=5:
                player['paleBlueDotTriggered']=True;e.power(player,'drawNextTurn',player['powers'][key])
            continue
        if key=='voidForm':
            if not card.get('replaysLeft') and card.get('manualSeries'):
                player['voidCardsPlayed']=player.get('voidCardsPlayed',0)+1
            continue
        if key=='storm':
            if card.get('stormOrbs'):
                from . import orbs
                orbs.channel(state,player,'lightning',card['stormOrbs'])
            continue
        if key=='subroutine':
            player['energy']+=card.get('subroutineEnergy',0)
            continue
        if key=='rupture':
            amount=player.get('ruptureCards',{}).pop(card['id'],0)
            if amount and player['hp']>0:e.power(player,'strength',amount)
            continue
        if key=='serpentForm':
            if card.get('serpentDamage'):
                living=[target for target in state['enemies'] if target['hp']>0]
                if living:e.hit(state,player,e.random_enemy(state,living),card['serpentDamage'],True)
            continue
        if key=='rage':
            if e.definition(card)['kind']=='attack' and player['hp']>0:
                e.gain_block(state,player,player['powers'].get(key,0),True)
            continue
        if key=='afterimage':
            if card.get('afterimageBlock'):e.gain_block(state,player,card['afterimageBlock'],True)
            continue
        if key=='blackHole':
            if not card.get('replaysLeft') and card.get('seriesStarsSpent'):
                from .classes.regent import black_hole
                black_hole(state,player)
            continue
        if key=='calamity':
            if card.get('calamityCount'):
                from .effects import generated_cards
                generated=[candidate for _ in range(player['powers'].get(key,0))
                           for candidate in generated_cards(state,player.get('character','ironclad'),1,kind='attack')]
                for candidate in generated:e.add_generated(state,player,candidate)
            continue
        if key in ('haunt','devourLife'):
            if card['key']!='Soul' or not player['powers'].get(key):continue
            if key=='devourLife':
                from . import osty
                osty.summon(state,player,player['powers'][key])
            else:
                targets=[target for target in state['enemies'] if target['hp']>0]
                if targets:e.hit(state,None,e.random_enemy(state,targets),player['powers'][key],True,unblockable=True)
            continue
        records=monologues(player) if key=='monologue' else player.get('colorless',{}).get('panache',[])
        record=next((r for r in records if r['id']==ident),None)
        if record is None:continue
        if key=='monologue':
            if ident in snapshots:
                e.power(player,'strength',snapshots[ident]);record['applied']+=record['strength']
        elif not record['armed']:record['armed']=True
        else:
            record['left']-=1
            if record['left']==0:
                for target in list(state['enemies']):
                    if target['hp']>0:e.hit(state,player,target,record['damage'],True)
                record['left']=5


def necrobinder_draw_order(player):
    records=player.get('cacophonyInstances',[])
    for index,record in enumerate(records):record.setdefault('id','legacy:'+str(index))
    candidates=[]
    for key,amount in player['powers'].items():
        if key=='pagestorm' and amount:candidates.append(key)
        elif key=='cacophony':candidates.extend('cacophony:'+record['id'] for record in records)
    for record in records:
        token='cacophony:'+record['id']
        if token not in candidates:candidates.append(token)
    order=[token for token in player.get('necrobinderDrawPowerOrder',[]) if token in candidates]
    order.extend(token for token in candidates if token not in order)
    player['necrobinderDrawPowerOrder']=order
    return list(order)


def before_card_cost_powers(state,player,card):
    from .. import engine as e
    definition=e.combat_definition(player,card)
    # Cost readers observe earlier hook consumption, including during replays.
    for key in list(player['powers']):
        if key not in CARD_COST_POWERS or not player['powers'].get(key):continue
        if key=='danseMacabre':
            resolved=card.get('capturedX',0) if definition['values'].get('xCost') else e.energy_cost(state,player,card,in_play=True)
            if resolved>=2:e.gain_block(state,player,player['powers'][key],True)
        elif key=='veilpiercer':
            if definition['values'].get('ethereal'):e.power(player,key,-1)
        elif definition['kind']=={'freeSkill':'skill','freeAttack':'attack','freePower':'power'}[key]:
            e.power(player,key,-1)


def hand_draw_count(state,player,draw_due):
    from .. import engine as e
    from ..relics.hooks import hand_draw_bonus
    count=5
    for key,amount in player['powers'].items():
        if key not in DRAW_COUNT_POWERS or not amount:continue
        if key=='mindRot':count=max(0,count-amount)
        elif key=='clarity':count+=1
        elif key!='drawNextTurn' or draw_due:count+=amount
    first=player['turnNumber']==1
    if first:
        count+=2*sum(key in player['relics'] for key in ('BagOfPreparation','RingOfTheSnake'))
        if state['encounterKind']=='elite' and 'BoomingConch' in player['relics']:count+=2
        if 'BigMushroom' in player['relics']:count-=2
    count+=hand_draw_bonus(player)
    if first:
        # The reference walks the pile top-first, moving each Imbued card to the
        # bottom and then each innate card to the top, so the last innate card
        # visited ends up on top. Collected in that order, the innate cards are
        # appended (our top is the end); the bottom group comes out right in
        # storage order.
        bottom=[card for card in player['draw'] if card.get('enchantment',{}).get('key')=='Imbued']
        innate=[card for card in e.top_first(player['draw']) if card not in bottom and e.definition(card)['values'].get('innate')]
        player['draw']=bottom+[card for card in player['draw'] if card not in bottom and card not in innate]+innate
        count=min(10,max(count,len(innate)))
    return max(0,count)


def player_start_order(player):
    records=player.get('colorless',{}).get('rollingBoulder',[]);candidates=[]
    for key,amount in player['powers'].items():
        if key=='rollingBoulder':candidates.extend('rollingBoulder:'+r['id'] for r in records)
        elif key in PLAYER_START_POWERS and amount:candidates.append(key)
    for record in records:
        token='rollingBoulder:'+record['id']
        if token not in candidates:candidates.append(token)
    order=[token for token in player.get('playerStartPowerOrder',[]) if token in candidates]
    order.extend(token for token in candidates if token not in order)
    player['playerStartPowerOrder']=order
    return list(order)


def after_player_start(state,player):
    from .. import engine as e
    from .classes import silent as silent_rules, defect as defect_rules, regent as regent_rules, necrobinder as necrobinder_rules, colorless as colorless_rules
    for token in player_start_order(player):
        key=token.split(':',1)[0]
        if not player['powers'].get(key):continue
        if key=='toolsOfTheTrade':silent_rules.after_player_turn_start(state,player)
        elif key in ('loop','hibernate'):defect_rules.after_player_turn_start(state,player,power_key=key)
        elif key=='tyranny':regent_rules.after_player_turn_start(state,player)
        elif key=='summonNextTurn':necrobinder_rules.after_player_turn_start(state,player)
        elif key=='entropy':colorless_rules.after_player_turn_start(state,player)
        elif key=='rollingBoulder':colorless_rules.after_draw(state,player,record_id=token.split(':',1)[1])
        elif key=='crimsonMantle':
            e.lose_hp(state,player,player.get('crimsonMantleLoss',1))
            if player['hp']>0:e.gain_block(state,player,player['powers'][key],True)
        elif key=='inferno':e.lose_hp(state,player,player.get('infernoLoss',1))
CLEANUP_POWERS={'noDraw','darkEmbrace','hellraiser','hyperbeamFocusDown','temporaryFocus','hotfixFocus','focusedStrikeFocus','synchronizeFocus','consumingShadow','temporaryDexterity','fadeDexterity','helicalDart','potionTemporaryDexterity','setupStrike','feedingFrenzy','coordinate','reptileTrinket','potionTemporaryStrength','monologue'}


def cleanup_order(player):
    from .classes.regent import monologues
    records=monologues(player);candidates=[]
    for key,amount in player['powers'].items():
        if key=='monologue':candidates.extend('monologue:'+r['id'] for r in records)
        elif key in CLEANUP_POWERS and amount:candidates.append(key)
    for record in records:
        token='monologue:'+record['id']
        if token not in candidates:candidates.append(token)
    order=[token for token in player.get('cleanupPowerOrder',[]) if token in candidates]
    order.extend(token for token in candidates if token not in order)
    player['cleanupPowerOrder']=order
    return list(order)


def nightmares(player):
    records=player.setdefault('nightmareInstances',[])
    for index,card in enumerate(player.pop('nightmareCopies',[])):
        records.append({'id':'legacy:'+str(index),'card':card,'amount':3})
    return records


def hand_draw_order(player):
    records=nightmares(player);candidates=[]
    for key,amount in player['powers'].items():
        if key=='nightmare':candidates.extend('nightmare:'+row['id'] for row in records)
        elif key in HAND_DRAW_POWERS and amount>0:candidates.append(key)
    for row in records:
        token='nightmare:'+row['id']
        if token not in candidates:candidates.append(token)
    order=[token for token in player.get('handDrawPowerOrder',[]) if token in candidates]
    order.extend(token for token in candidates if token not in order)
    player['handDrawPowerOrder']=order
    return list(order)


def queue_nightmare(state,player,card,amount=3):
    from .. import engine as e
    hand_draw_order(player)
    snapshot=e.copy_card(state,card);snapshot.pop('affliction',None)
    state['serial']+=1
    nightmares(player).append({'id':str(state['serial']),'card':snapshot,'amount':amount})
    e.power(player,'nightmare',amount)


def before_hand_draw(state,player):
    from .classes import silent as silent_rules, defect as defect_rules, regent as regent_rules, necrobinder as necrobinder_rules, special as special_rules
    for token in hand_draw_order(player):
        key=token.split(':',1)[0]
        if key in ('infiniteBlades','nightmare'):
            silent_rules.before_draw(state,player,power_key=key,record_id=token.split(':',1)[1] if key=='nightmare' else None)
        elif key=='creativeAi':defect_rules.before_draw(state,player)
        elif key in ('spectrumShift','foregoneConclusion'):regent_rules.before_draw(state,player,power_key=key)
        elif key in ('sentryMode','callOfTheVoid'):necrobinder_rules.before_draw(state,player,power_key=key)
        elif key=='helloWorld':special_rules.before_draw(state,player)


def side_end_order(player):
    candidates=[]
    bombs=player.get('colorless',{}).get('bomb',[])
    for key,amount in player['powers'].items():
        if key in ('hailstorm','chainsOfBinding') and amount>0:candidates.append(key)
        elif key=='bomb':candidates.extend('bomb:'+record['id'] for record in bombs)
    # A new Bomb record is installed just before its aggregate display amount.
    for record in bombs:
        token='bomb:'+record['id']
        if token not in candidates:candidates.append(token)
    order=[token for token in player.get('sideEndPowerOrder',[]) if token in candidates]
    order.extend(token for token in candidates if token not in order)
    player['sideEndPowerOrder']=order
    return list(order)
