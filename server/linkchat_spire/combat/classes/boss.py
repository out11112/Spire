"""Stateful boss effects, with persisted per-owner counters."""
from ...content.ascension import monster_value


def generated(state,card):
    if card['key']=='Wither':
        card['witherLevel']=card.get('witherLevel',0)+sum(m.get('witherUpgrades',0) for m in state.get('enemies',[]) if m['key']=='Aeonglass' and m['hp']>0)


def intensify(state,monster):
    from ... import engine as e
    from .defect import combat_cards
    for player in state['players'].values():
        if player['hp']>0:
            for card in combat_cards(state,player):
                if card['key']=='Wither':card['witherLevel']=card.get('witherLevel',0)+1
    monster['witherUpgrades']=monster.get('witherUpgrades',0)+1
    for player in state['players'].values():
        if player['hp']>0:
            for _ in range(monster_value(state,monster['key'],'WitherAmount',1)):
                e.add_generated(state,player,e.new_card(state,'Wither'),'discard',creator=monster)
    e.power(monster,'strength',monster_value(state,monster['key'],'IncreasingIntensityBaseStrength',3)+monster.get('additionalStrength',0))
    monster['additionalStrength']=monster.get('additionalStrength',0)+1


def after_card(state,player,card=None):
    from ... import engine as e
    if card:
        from ..afflictions import smog_played
        smog_played(state,player,card)
    for monster in state['enemies']:
        if card and monster['hp']>0 and monster.get('curlCard')==card['id']:
            monster.pop('curlCard');e.gain_block(state,monster,monster['powers'].pop('curlUp',0),True)
        if monster['hp']>0 and monster['powers'].get('galvanic') and card and card.get('affliction',{}).get('key')=='Galvanized':
            e.hit(state,player,player,monster['powers']['galvanic'],True)
        if monster['hp']>0 and monster['powers'].get('vitalSpark') and card and card.get('affliction',{}).get('key')=='Tainted':
            e.debuff(state,monster,player,'tainted',monster['powers']['vitalSpark'])
        if monster['hp']>0 and monster['powers'].get('enrage') and card and e.definition(card)['kind']=='skill':e.power(monster,'strength',monster['powers']['enrage'])
        if monster['hp']<=0 or monster['key']!='Aeonglass':continue
        counters=monster['witheringCounters'];uid=str(player['id'])
        counters[uid]-=1
        if counters[uid]<=0:
            e.add_generated(state,player,e.new_card(state,'Wither'),'hand',creator=monster)
            counters[uid]=6


def steal_card(state,monster,targets):
    from ... import engine as e
    def priority(card):
        if card.get('enchantment',{}).get('key')=='Imbued':return 3
        rarity=e.definition(card)['rarity']
        return 0 if rarity=='uncommon' else 1 if rarity in ('common','rare','event') else 2 if rarity in ('basic','quest') else 3 if rarity=='ancient' else 4
    for uid in targets:
        player=state['players'][str(uid)]
        if player['hp']<=0:continue
        deck={card['id']:card for card in player['deck']}
        candidates=[card for pile in ('draw','discard') for card in player[pile] if card['id'] in deck]
        if not candidates:continue
        rank=min(map(priority,candidates));candidates=[card for card in candidates if priority(card)==rank]
        stolen=e.combat_card_generation(state,candidates)
        for pile in ('draw','discard'):
            if stolen in player[pile]:player[pile].remove(stolen)
        original=deck[stolen['id']];player['deck'].remove(original)
        monster.setdefault('stolenCards',[]).append({'owner':str(uid),'card':original})
        e.log(state,f"{player['name']} 的 {e.definition(original)['name']} 被窃走。")


def after_death(state,monster):
    if monster.get('stolenCards'):
        from ...run.rewards.custom import offer_instances
        for record in monster.pop('stolenCards'):
            offer_instances(state,state['players'][record['owner']],[record['card']],special=True)
    if monster.get('possessedStats'):
        from ... import engine as e
        for uid,stats in monster.pop('possessedStats').items():
            for stat,amount in stats.items():
                if state['players'][uid]['hp']>0:e.power(state['players'][uid],stat,amount)
    if monster.get('powers',{}).get('surprise'):
        from ..monsters import spawn, initialize
        from ... import engine as e
        for key in ('SneakyGremlin','FatGremlin'):
            spawned=spawn(state,key);initialize(state,spawned);e.intent(state,spawned)
            if key=='FatGremlin':spawned['stolenGold']=dict(monster.get('stolenGold',{}))
        state['mercGoldStolen']=any(monster.get('stolenGold',{}).values())
    if monster.get('key')=='FatGremlin':
        for uid,amount in monster.get('stolenGold',{}).items():
            player=state['players'][uid]
            player['recoveredGold']=player.get('recoveredGold',0)+amount
    if monster.get('powers',{}).get('illusion'):
        from ... import engine as e
        for key,temporary in list(monster.get('debuffKeys',{}).items()):
            # These power types remain Buff even when their amounts are negative.
            if temporary or key in ('strength','dexterity','focus'):continue
            monster['powers'].pop(key,None);monster['debuffKeys'].pop(key,None)
        monster.update(pendingIllusion=True,move=1,block=0)
        e.intent(state,monster)
    if monster.get('powers',{}).get('reattach'):
        from ... import engine as e
        others=[m for m in state['enemies'] if m is not monster and m['powers'].get('reattach') and m['hp']>0]
        monster['fatalBlocked']=bool(others)
        if others:
            monster.update(pendingReattach=True,move=3,block=0)
            monster['powers']={'reattach':monster['powers']['reattach']}
            e.intent(state,monster)
    if any(m is monster for m in state['enemies']):
        from ... import engine as e
        remaining=[m for m in state['enemies'] if m['hp']>0]
        for other in remaining:
            if other['powers'].pop('crabRage',0):
                e.power(other,'strength',6);e.gain_block(state,other,99,True)
        if remaining and any(all(m['powers'].get(key) for m in remaining) for key in ('backAttackLeft','backAttackRight')):
            for player in state['players'].values():face(player,remaining[0])
    if monster.get('key')=='TorchHeadAmalgam':
        from ... import engine as e
        for queen in state['enemies']:
            if queen['key']=='Queen' and queen['hp']>0:
                queen['amalgamDied']=True
                if queen['move']==2:queen['move']=5;e.intent(state,queen)
    if monster.get('key')=='TestSubject' and monster['powers'].get('adaptable'):
        from ... import engine as e
        monster.update(awaitingRevive=True,move=6,block=0)
        monster['powers']={key:value for key,value in monster['powers'].items() if key in ('adaptable','painfulStabs')}
        state['testSubjectKills']=state.get('testSubjectKills',0)+1
        e.intent(state,monster)
    if monster.get('key')=='WaterfallGiant' and monster['powers'].get('steamEruption'):
        from ... import engine as e
        pressure=monster['powers']['steamEruption']
        monster.update(hp=999999999,maxHp=999999999,hpDisplay='infinite',move=6,deathHandled=False)
        monster['powers']={'steamEruption':pressure}
        e.intent(state,monster)


def move_effect(state,monster,move):
    from ... import engine as e
    if monster['key']=='TestSubject' and move==2:monster['extraClaws']=monster.get('extraClaws',0)+1
    if monster['key']!='WaterfallGiant':return
    if move==6:monster['eruptionDamage']=monster['powers'].pop('steamEruption',0)
    elif move==7:
        from .necrobinder import on_death
        monster['hp']=0;on_death(state,monster)
    else:
        if move==4:monster['pressureGun']=monster.get('pressureGun',monster_value(state,monster['key'],'BasePressureGunDamage',20))+5
        e.power(monster,'steamEruption',monster_value(state,monster['key'],'PressurizeAmount',15) if move==0 else 3)


def liquify(state,monster,targets):
    from ... import engine as e
    monster['sandpits']={str(uid):4 for uid in targets}
    for uid in targets:
        player=state['players'][str(uid)]
        if player['hp']<=0:continue
        for pile in ('draw','discard'):
            for _ in range(3):e.add_generated(state,player,e.new_card(state,'FranticEscape'),pile,creator=monster,random_position=True)


def enemy_start(state):
    from .necrobinder import on_death
    for monster in state['enemies']:
        if monster['hp']<=0:continue
        for uid,amount in list(monster.get('sandpits',{}).items()):
            player=state['players'][uid]
            monster['sandpits'][uid]=max(0,amount-1)
            if amount==1 and player['hp']>0:
                # This is a forced kill, not damage: Block and Buffer do not help.
                player['hp']=0;on_death(state,player)
                if player.get('osty') and player['osty']['hp']>0:
                    player['osty']['hp']=0;on_death(state,player['osty'])


def reattach_turn(state,monster):
    from ... import engine as e
    from ..monsters import advance
    if monster['move']==3:
        monster['move']=4;e.intent(state,monster)
        return
    if any(m is not monster and m['hp']>0 and m['powers'].get('reattach') for m in state['enemies']):
        monster.update(hp=min(monster['maxHp'],monster['powers']['reattach']),deathHandled=False,fatalBlocked=False)
        monster.pop('pendingReattach',None)
        advance(state,monster);e.intent(state,monster)


def face(player,target):
    if not player['powers'].get('surrounded') or target is None:return
    if target['powers'].get('backAttackLeft'):player['facing']='left'
    elif target['powers'].get('backAttackRight'):player['facing']='right'


def back_attack(actor,target):
    if not target['powers'].get('surrounded'):return False
    return bool(actor['powers'].get('backAttackLeft' if target.get('facing','right')=='right' else 'backAttackRight'))


def revive(state,monster):
    from ..monsters import hp
    monster.pop('awaitingRevive');monster['respawns']=monster.get('respawns',0)+1
    health=hp(state,monster_value(state,monster['key'],'SecondFormHp',200) if monster['respawns']==1 else monster_value(state,monster['key'],'ThirdFormHp',300))
    monster.update(hp=health,maxHp=health,deathHandled=False)
    if monster['respawns']==1:monster['powers']['painfulStabs']=1
    else:
        monster['powers'].pop('painfulStabs',None);monster['powers'].pop('adaptable',None)
        monster['powers']['nemesis']=1
