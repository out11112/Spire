"""Combat flow: starting a battle, turns, enemy turns and victory."""
from ..text import battle_log
from ..content.ascension import gold_range, monster_hp, monster_value, monster_intent
from copy import deepcopy
from ..content import definition, card_view
from ..run.rewards.rewards import card_choices
from ..run.rewards.odds import potion_reward as roll_potion_reward
from ..content.characters import CHARACTERS, reward_pool
from .costs import add as change_cost, expire as expire_cost
from .monsters import MONSTERS as ADDITIONAL_MONSTERS
from ..core.errors import require
from . import damage
from . import piles
from . import play
from ..core import state as run_state
from ..rng import draws

# No graphics/animation or Steam calls. Intent is part of the committed state.
ENEMIES={
 'Nibbit':('小啃兽',42,46,[{'damage':12},{'damage':6,'block':5},{'strength':2}]),
 'FuzzyWurmCrawler':('毛绒伏地虫',55,57,[{'damage':4},{'strength':7},{'damage':4}]),
 'LeafSlimeS':('树叶史莱姆（小）',11,15,[{'damage':3},{'status':'Slimed','count':1}]),
 'TwigSlimeS':('树枝史莱姆（小）',7,11,[{'damage':4}]),
 'Inklet':('墨宝',11,17,[{'damage':3},{'damage':2,'hits':3},{'damage':10}]),
 'Byrdonis':('多尼斯异鸟',81,84,[{'damage':17},{'damage':3,'hits':3}]),
 'BygoneEffigy':('旧日雕像',127,127,[{'sleep':True},{'strength':10},{'damage':13}]),
 'Vantom':('墨影幻灵',173,173,[{'damage':7},{'damage':6,'hits':2},{'damage':26,'status':'Wound','count':3},{'strength':2}]),
 'KnowledgeDemon':('知识恶魔',379,379,[{'knowledge':True},{'damage':17},{'damage':8,'hits':3},{'damage':11,'healPerPlayer':30,'strength':2}])}

ENEMIES.update(ADDITIONAL_MONSTERS)

def intent(s,e):
    moves=ENEMIES[e['key']][3];e['intent']=deepcopy(moves[e['move']]);e['intent']['targets']=[p['id'] for p in s['players'].values() if p['hp']>0]
    monster_intent(s,e,e['intent'])
    if e['key']=='TestSubject' and e['move']==2:e['intent']['hits']=3+e.get('extraClaws',0)
    if e['key']=='WaterfallGiant' and e['move'] in (4,7):e['intent']['damage']=e.get('pressureGun',monster_value(s,e['key'],'BasePressureGunDamage',20)) if e['move']==4 else e.get('eruptionDamage',0)
    if e['key']=='Axebot' and e['move']==0:e['intent']['strength']=monster_value(s,e['key'],'BootUpStrGain',3)*e.get('respawnCount',0)

def start_battle(s,kind,encounter=None):
    from .monsters import KINDS, formation
    # The act schedule picks the encounter when the map is built and the node
    # carries it, so a real battle never reaches the fallback below. It takes
    # the act's own first entry rather than drawing for one: the reference
    # walks its roster in order, and a draw here would desync every later one.
    if encounter is None and kind!='boss':
        from ..run.map.journey import current_act
        try:pool=current_act(s).get('normal' if kind=='battle' else 'elite') or []
        except (KeyError,IndexError):pool=[]
        encounter=pool[0] if pool else 'NibbitsNormal'
    if encounter is not None:
        require(encounter in KINDS,'遭遇效果尚未实现：'+str(encounter))
        require(KINDS[encounter]==kind,'遭遇类型与房间不一致。')
    battle_log.begin(s)
    run_state.phase(s,'combat');s['encounterKind']=kind;s['turn']=0;s['exhaustCount']=0;s['totalPlays']=0;s['side']='player'
    s['encounter']=encounter
    s.pop('mercGoldStolen',None);s.pop('mercEscaped',None)
    for p in s['players'].values():
        p.pop('recoveredGold',None);p.pop('endCommittedTurn',None)
    keys=formation(s,encounter) if encounter else ['Vantom']
    s['enemies']=battle_log.ObservedList([],s,'enemies') if isinstance(s['players'],battle_log.ObservedDict) else [];count=len(s['players'])
    for i,key in enumerate(keys):
        name,lo,hi,moves=ENEMIES[key]
        from .monsters import initial_hp, initialize as initialize_monster, random_branch
        lo,hi=monster_hp(s,key,lo,hi)
        hp=initial_hp(s,lo,hi)
        e={'id':f'e{i}','key':key,'name':name,'hp':hp,'maxHp':hp,'block':0,'powers':{},'move':0,'slowCards':0}
        if key=='BygoneEffigy':e['powers']['slow']=1
        if key in ('Vantom','Inklet'):e['powers']['slippery']=(monster_value(s,key,'SlipperyAmt',8) if key=='Vantom' else 1)*count
        if key=='Nibbit' and len(keys)>1:e['move']=1 if i==0 else 2
        if key=='LeafSlimeS':e['move']=random_branch(s,e,[(0,1.0,(('repeat',1),)),(1,1.0,(('repeat',1),))])
        if key=='Inklet' and i==1:e['move']=1
        s['enemies'].append(e);e=s['enemies'][-1]
        initialize_monster(s,e);intent(s,e)
    for p in s['players'].values():
        p.update(block=0,energy=0,powers={},hand=[],discard=[],exhaust=[],draw=piles.initial_draw_pile(s,p['deck']),hpLossCount=0,guardians=[],crimsonMantleLoss=0,infernoLoss=0,colorless={},coverSources=[],covering=[],drawnThisCombat=0,orbs=[],orbCapacity=0)
        p['relicCombat']={}
        p.pop('vigorAttack',None)
        p.pop('darkEmbraceEthereal',None)
        p.pop('ruptureCards',None)
        p.pop('sideEndPowerOrder',None)
        p['hellraiserInfinitePlays']=0
        p.pop('lastAttackPlayed',None)
        for field in ('hexSource','dampenCasters','dampenedCards','tenderPlayed','tenderSource','constrictSource'):p.pop(field,None)
        from .enchantments import reset_combat
        for card in p['draw']:
            reset_combat(card);card.pop('swordSageReplays',None)
        p.pop('skipDurationTicks',None);p.pop('shrinkSource',None)
        p['stars']=0;p['generatedThisCombat']=0;p['extraCardRewards']=0;p.pop('nightmareCopies',None)
        p.pop('nightmareInstances',None);p.pop('handDrawPowerOrder',None)
        p['lightningChanneled']=0;p['imitationTargets']={}
        p['orbitInstances']=[];p.pop('monologueApplied',None);p.pop('monologueInstances',None);p.pop('playedInstanceOrder',None);p.pop('cleanupPowerOrder',None);p.pop('playerStartPowerOrder',None);p.pop('paleBlueDotTriggered',None)
        p.pop('endRequested',None);p['voidCardsPlayed']=0
        p['cacophonyInstances']=[]
        p.pop('necrobinderDrawPowerOrder',None)
        p['soulboundInstances']=[];p.pop('deathHandled',None)
        p['inPlay']=[];p['turnNumber']=0;p['toricInstances']=[];p.pop('gigantificationCard',None)
        p['orbCapacity']=CHARACTERS[p.get('character','ironclad')]['orbSlots']
        p.pop('osty',None);p['etherealPlays']=0
        for key,stat in [('Vajra','strength'),('OddlySmoothStone','dexterity')]:
            if key in p['relics']:damage.power(p,stat,1)
    from ..content.characters import combat_start
    from ..relics.hooks import combat_start as relic_combat_start
    for enemy in s['enemies']:
        if enemy['key']=='Rocket':
            for p in s['players'].values():p['facing']='right';damage.debuff(s,enemy,p,'surrounded',1)
    for p in s['players'].values():combat_start(s,p);relic_combat_start(s,p)
    from ..relics.map import creature_added
    for enemy in s['enemies']:creature_added(s,enemy)
    for p in s['players'].values():
        if 'PetrifiedToad' in p['relics']:
            from ..run.potions import create, procure
            procure(s,p,create(s,'PotionShapedRock'))
    from .afflictions import vital_spark
    for enemy in s['enemies']:
        if enemy['powers'].get('vitalSpark'):vital_spark(s,enemy['powers']['vitalSpark'],initial=True)
        if enemy['powers'].get('galvanic'):
            from .afflictions import galvanic
            galvanic(s,enemy['powers']['galvanic'])
    next_turn(s)
    run_state.log(s,'进入战斗：'+'、'.join(e['name'] for e in s['enemies']))

def next_turn(s,extra_players=None):
    for enemy in s['enemies']:enemy['shellDamage']=0
    if extra_players is None:s['turn']+=1
    battle_log.emit(s,f"回合 {s['turn']} · 玩家行动",'turn')
    s['phaseId']+=1;s['side']='player'
    participants=list(s['players'].values()) if extra_players is None else extra_players
    for p in participants:p['helloWorldAtTurnStart']=p['powers'].get('helloWorld',0)
    s['turnParticipants']=[p['id'] for p in participants]
    if s['turn']==1:
        for enemy in s['enemies']:
            if enemy['hp']>0 and enemy['powers'].get('plating'):damage.gain_block(s,enemy,enemy['powers']['plating'],True)
    draw_due={str(p['id']):bool(p['powers'].get('drawNextTurn')) for p in participants}
    for p in participants:
        if p['hp']>0 and p['powers'].get('aggression'):
            cards=[c for c in p['discard'] if definition(c)['kind']=='attack']
            for c in draws.combat_card_selection_shuffle(s,cards)[:p['powers']['aggression']]:
                p['discard'].remove(c);piles.add_to_hand(s,p,c)
                if run_state.upgradable(c):run_state.upgrade(c)
    from ..relics.hooks import before_side_turn_start
    before_side_turn_start(s,participants)
    for e in s['enemies']:
        e['attackedBy']={}
        if e['hp']>0 and extra_players is None:intent(s,e)
    from .power_order import after_player_start
    def setup(p):
        prepare_player_turn(s,p,draw_due[str(p['id'])])
        if p['hp']>0:after_player_start(s,p)
        from ..relics.hooks import after_player_turn_start as relic_after_player_turn_start
        if p['hp']>0:relic_after_player_turn_start(s,p)
    from .orbs import turn_start as orb_turn_start
    from ..core.continuation import current
    runtime=current()
    if runtime is not None:
        from ..core.turn_tasks import TurnTasks
        jobs=[('setup:'+str(p['id']),lambda p=p:setup(p),()) for p in participants]
        jobs.append(('side',lambda:begin_side_turn(s,participants,normal_turn=extra_players is None,draw_due=draw_due),()))
        orb_names=tuple('orbs:'+str(p['id']) for p in participants)
        jobs.extend(('orbs:'+str(p['id']),lambda p=p:orb_turn_start(s,p) if p['hp']>0 else None,('side',)) for p in participants)
        jobs.extend(('auto:'+str(p['id']),lambda p=p:run_turn_autoplays(s,[p]) if p['hp']>0 else None,('setup:'+str(p['id']),'side',*orb_names)) for p in participants)
        TurnTasks(s,runtime,jobs).run()
    else:
        for p in participants:setup(p)
        begin_side_turn(s,participants,normal_turn=extra_players is None,draw_due=draw_due)
        for p in participants:
            if p['hp']>0:orb_turn_start(s,p)
        run_turn_autoplays(s,participants)
    play.after_card(s)

def prepare_player_turn(s,p,draw_due):
    # Extra turns share s['turn']; only this participant's new turn resets the guard.
    p.pop('endCommittedTurn',None)
    p['demonTongueTriggered']=False
    p['boundDrawn']=0;p['skillsStarted']=0
    p['turnNumber']=p.get('turnNumber',0)+1
    p['done']=False;p['cardsPlayed']=0;p['attacksPlayed']=0;p['actionCards']=0;p['exhaustedThisTurn']=0;p['hpLostThisTurn']=False;p['blockEvents']=[];p.pop('blockCard',None);p.pop('blockDefend',None);p.pop('blockPlay',None)
    p['discardedThisTurn']=0;p['attacksFinished']=0;p['skillsFinished']=0;p['playsFinished']=0;p['energySpentThisTurn']=0
    p['starsGainedThisTurn']=0
    p['ostyAttacks']=0;p['extraDrawsThisTurn']=0;p['shivsFinished']=0
    p['seriesStarted']=0;p['zeroEnergyAttacks']=0;p['feralUsed']=0;p['statusDraws']=0
    p['voidCardsPlayed']=0
    p['doomAppliedThisTurn']=False
    p['slothPlays']=0
    p['summonDueAtStart']=bool(p['powers'].get('summonNextTurn'))
    if not p['powers'].get('barricade') and not p['powers'].get('blur'):p['block']=min(10,p['block']) if 'SturdyClamp' in p['relics'] else 0
    from .classes.special import after_block_cleared
    after_block_cleared(s,p)
    from ..relics.hooks import after_block_cleared as relic_after_block_cleared
    relic_after_block_cleared(s,p)
    if p['powers'].get('blur'):damage.power(p,'blur',-1)
    if p['powers'].get('blockNextTurn'):damage.gain_block(s,p,p['powers'].pop('blockNextTurn'),True)
    for pile in ('hand','draw','discard','exhaust'):
        for card in p[pile]:expire_cost(card,'turn');card.pop('freeThisTurn',None);card.pop('freeStarsThisTurn',None)
    if p['hp']<=0:return
    saved_energy=p['energy'] if 'IceCream' in p['relics'] and p['turnNumber']>1 else 0
    relic_energy=sum(key in p['relics'] for key in ('Ectoplasm','PhilosophersStone','VelvetChoker','SpikedGauntlets','PrismaticGem','BloodSoakedRose','BlessedAntler','WhisperingEarring'))
    relic_energy+=int('PaelsFlesh' in p['relics'] and p['turnNumber']>=3)
    relic_energy+=int('PumpkinCandle' in p['relics'] and p.get('pumpkinCombats',0)>0)
    max_energy=3+relic_energy+p['powers'].get('pyre',0)+p['powers'].get('friendship',0)+p['powers'].get('demesne',0)-p['powers'].get('wasteAway',0)+('Sozu' in p['relics'])+('Bread' in p['relics'] and p['turnNumber']>1)
    # The per-turn cap is what the screen prints beside the energy, so it belongs
    # to the state rather than to this one line of arithmetic.
    p['energyCapacity']=max_energy
    p['energy']=saved_energy+max_energy+p['powers'].pop('energyNextTurn',0)
    from ..relics.hooks import after_energy_reset
    after_energy_reset(p)
    from .classes.defect import after_energy_reset
    after_energy_reset(s,p)
    from .classes.regent import after_energy_reset as regent_after_energy_reset
    regent_after_energy_reset(s,p)
    from ..content.characters import after_energy_reset as character_after_energy_reset
    character_after_energy_reset(s,p)
    from ..run.potions import after_energy_reset as potion_after_energy_reset
    potion_after_energy_reset(s,p)
    if p['turnNumber']>1 and p['powers'].get('plating'):damage.power(p,'plating',-1)
    if 'HappyFlower' in p['relics']:p['flower']=(p['flower']+1)%3
    if 'HappyFlower' in p['relics'] and p['flower']==0:p['energy']+=1
    first=p['turnNumber']==1
    if first:
        if 'Anchor' in p['relics']:damage.gain_block(s,p,10,True)
        if 'FakeAnchor' in p['relics']:damage.gain_block(s,p,4,True)
        if 'Lantern' in p['relics']:p['energy']+=1
    from .classes.colorless import before_draw
    from .power_order import before_hand_draw
    before_hand_draw(s,p)
    from ..relics.shop import before_draw as shop_before_draw
    shop_before_draw(s,p)
    if first and 'NinjaScroll' in p['relics']:
        for _ in range(3):piles.add_generated(s,p,run_state.new_card(s,'Shiv'))
    before_draw(s,p)
    from .power_order import hand_draw_count
    piles.draw(s,p,hand_draw_count(s,p,draw_due),hand_draw=True)

def begin_side_turn(s,participants,*,normal_turn=True,draw_due=None):
    from ..relics.hooks import after_side_turn_start
    for p in participants:
        if p['hp']>0:damage.power(p,'strength',p['powers'].get('demonForm',0))
        from .classes.silent import turn_start as silent_turn_start
        if p['hp']>0:silent_turn_start(s,p)
        from .classes.necrobinder import turn_start as necrobinder_turn_start
        if p['hp']>0:necrobinder_turn_start(s,p)
        from .classes.defect import turn_start as defect_turn_start
        if p['hp']>0:defect_turn_start(s,p)
        from .classes.regent import turn_start as regent_turn_start
        if p['hp']>0:regent_turn_start(s,p)
        if p['hp']>0 and p['powers'].get('prepTime'):damage.power(p,'vigor',p['powers']['prepTime'])
        if p['hp']>0 and p['powers'].get('clarity'):damage.power(p,'clarity',-1)
        if p['hp']>0 and (draw_due or {}).get(str(p['id'])):p['powers'].pop('drawNextTurn',None)
        if p['hp']>0 and p['turnNumber']==1 and 'BloodVial' in p['relics']:damage.heal(p,2)
        if p['hp']>0 and p['turnNumber']==1 and 'FakeBloodVial' in p['relics']:damage.heal(p,1)
    if normal_turn:
        for source in s['enemies']:
            if source['hp']>0 and source['powers'].get('rampart'):
                for target in s['enemies']:
                    if target['hp']>0 and target['key']=='TurretOperator':damage.gain_block(s,target,source['powers']['rampart'],True)
    after_side_turn_start(s,participants)

def run_turn_autoplays(s,participants):
    from .effects import prepend, run
    from .classes.defect import combat_cards
    from ..run.events.ancient_relics import whisper
    for p in participants:
        operations=[{'op':'autoplayPile','source':'exhaust','cardId':card['id']} for card in list(p['exhaust']) if definition(card)['values'].get('bombardment')]
        if p['powers'].get('mayhem'):operations.append({'op':'autoplayDraw','count':p['powers']['mayhem']})
        previous=p.get('lastAttackPlayed')
        if 'HistoryCourse' in p['relics'] and previous and previous['turn']==p['turnNumber']-1:
            original=next((c for c in combat_cards(s,p) if c['id']==previous['card']['id']),previous['card'])
            duplicate=run_state.copy_card(s,original);duplicate['isDupe']=True
            duplicate.setdefault('removedKeywords',[]).append('exhaust')
            duplicate['addedKeywords']=[k for k in duplicate.get('addedKeywords',[]) if k!='exhaust']
            operations.append({'op':'autoplayCard','card':duplicate})
        if p['turnNumber']==1:
            operations.extend({'op':'autoplayIdentity','cardId':c['id']} for c in combat_cards(s,p) if c.get('enchantment',{}).get('key')=='Imbued')
        prepend(s,p,operations)
        if s.get('effects'):run(s)
        else:s.pop('effects',None)
        whisper(s,p)

def finish_combat(s):
    if s['phase']!='combat':return True
    if not any(p['hp']>0 for p in s['players'].values()):run_state.phase(s,'defeat');run_state.log(s,'队伍倒下，本次攀登结束。');return True
    if any(e['hp']>0 or e.get('awaitingRevive') for e in s['enemies']):return False
    royalties={str(p['id']):p['powers'].get('royalties',0) for p in s['players'].values()}
    # Team-wide phases match CombatManager: revive, end hooks, cleanup,
    # early victory, ordinary victory, then rewards.
    from ..relics.hooks import combat_end, combat_victory, combat_victory_early
    from .classes.special import after_combat
    for p in s['players'].values():
        if p['hp']<=0:p['hp']=1
    for p in s['players'].values():
        combat_end(s,p)
        after_combat(s,p)
        p['removalRewards']=p['powers'].get('forbiddenGrimoire',0)
        for c in list(p['deck']):
            if c['key']=='Guilty':
                c['combats']=c.get('combats',0)+1
                if c['combats']>=5:p['deck'].remove(c)
    for p in s['players'].values():
        p.pop('relicCombat',None)
        p.update(block=0,powers={},energy=0,hand=[],draw=[],discard=[],exhaust=[],inPlay=[])
    for p in s['players'].values():combat_victory_early(s,p)
    for p in s['players'].values():combat_victory(s,p)
    if s['encounterKind']=='boss':
        if 'journey' not in s:run_state.phase(s,'victory');run_state.log(s,'首幕通关！');return True
        from ..run.map.journey import complete_act
        s['afterRewards']=complete_act(s)
        if s['afterRewards']=='ending':
            from ..run.events.ending import start
            start(s);return True
    run_state.phase(s,'reward')
    if s.get('eventCombat',{}).get('noOrdinaryRewards'):
        if not s['eventCombat'].get('ranOutOfTime'):
            from ..run.rewards.gold import queue as queue_gold
            for p in s['players'].values():queue_gold(s,p,royalties[str(p['id'])],'Royalties')
        from ..run.events.events import finish_event_combat
        finish_event_combat(s);return True
    for p in s['players'].values():
        if s.get('encounter')=='FakeMerchantEventEncounter':gold=300
        elif s.get('encounter')=='ThievingHopperWeak' and any(m.get('escaped') for m in s['enemies']):gold=0
        elif s.get('mercEscaped'):gold=0 if s.get('mercGoldStolen') else draws.player_rng(s,p,'Rewards',lambda rng:rng.next_int_range(5,11))
        else:gold=draws.player_rng(s,p,'Rewards',lambda rng:rng.next_int_range(*gold_range(s,s['encounterKind'])))
        from ..run.rewards.gold import queue as queue_gold
        queue_gold(s,p,gold,'combat')
        queue_gold(s,p,p.pop('recoveredGold',0),'recovered')
        queue_gold(s,p,royalties[str(p['id'])],'Royalties')
        choices=card_choices(s,p,reward_pool(p),source=s['encounterKind'],act_index=s.get('actIndex',0))
        p['reward']=[run_state.new_card(s,c['key'],c['upgraded']) for c in choices]
        from ..run.rewards.custom import recipe
        p['rewardMeta']={'recipe':recipe(p,source=s['encounterKind'])}
        from ..relics.hooks import card_reward_options
        card_reward_options(p,p['reward'],s)
        p['extraRewardChoices']=[]
        for _ in range(p.pop('extraCardRewards',0)):
            extra=card_choices(s,p,reward_pool(p),source=s['encounterKind'],act_index=s.get('actIndex',0))
            p['extraRewardChoices'].append([run_state.new_card(s,c['key'],c['upgraded']) for c in extra])
            card_reward_options(p,p['extraRewardChoices'][-1],s)
        if s['encounterKind']=='elite':
            from ..run.rewards.custom import queue_relic
            queue_relic(s,p)
        if roll_potion_reward(s,p,s['encounterKind'],forced='WhiteBeastStatue' in p['relics']):run_state.potion_reward(s,p)
        from ..relics.hooks import combat_rewards
        combat_rewards(s,p)
        if 'LastingCandy' in p['relics'] and p['reward']:p['lastingCandyRewards']=p.get('lastingCandyRewards',0)+1
        if s.get('eventCombat',{}).get('key')=='FakeMerchant':
            for key in s['eventCombat']['relics']:
                s['serial']+=1;p.setdefault('pendingRelicRewards',[]).append({'id':'relicReward:'+str(s['serial']),'key':key})
        if s.get('eventCombat',{}).get('key')=='PunchOff':
            from ..run.rewards.custom import queue_relic
            from ..run.potions import generate
            queue_relic(s,p);p['pendingPotions'].extend(generate(s,p,source='rewards'))
        if s.get('eventCombat',{}).get('key')=='TheLanternKey':
            from ..run.rewards.custom import offer_instances
            offer_instances(s,p,[run_state.new_card(s,'LanternKey')],special=True)
            s['eventState']['players'][str(p['id'])]['done']=True
    run_state.log(s,'战斗胜利，选择奖励。');return True

def enemy_turn(s):
    battle_log.emit(s,'敌方行动','turn',source_info={'kind':'rule','name':'敌方回合'})
    from .classes.colorless import before_side_end as colorless_before_side_end, turn_end as colorless_turn_end
    participants=[p for p in s['players'].values() if p['id'] in s.get('turnParticipants',[x['id'] for x in s['players'].values()])]
    end_relic_flags={p['id']:(p['block']==0 and 'Orichalcum' in p['relics'],p['block']==0 and 'FakeOrichalcum' in p['relics']) for p in participants}
    for p in participants:
        from ..run.potions import before_side_end
        before_side_end(s,p)
        if p['hp']>0 and p['powers'].get('plating'):damage.gain_block(s,p,p['powers']['plating'],True)
        if (p['hp']>0 and 'PaelsEye' in p['relics'] and not p.get('paelsEyeUsed') and not p.get('manualFinished')
                and not ('WhisperingEarring' in p['relics'] and p['turnNumber']==1)):
            p['paelsEyeExtra']=True
            for card in list(p['hand']):piles.exhaust(s,p,card)
    # Finish each shared hook phase for all participants before orb/hand cleanup.
    for p in participants:
        orichalcum,fake_orichalcum=end_relic_flags[p['id']]
        if p['hp']>0:
            from .classes.defect import before_turn_end
            from .power_order import side_end_order
            for listener in side_end_order(p):
                if listener=='hailstorm':before_turn_end(s,p)
                elif listener=='chainsOfBinding':
                    from .afflictions import before_side_end as clear_bound
                    clear_bound(s,p)
                else:colorless_before_side_end(s,p,record_id=listener.split(':',1)[1])
            from ..relics.hooks import before_flush as relic_before_flush
            if fake_orichalcum:damage.gain_block(s,p,3,True)
            if orichalcum:damage.gain_block(s,p,6,True)
            relic_before_flush(s,p)
        if finish_combat(s):return
    for p in participants:
        regret_count=len(p['hand'])
        if p['hp']>0:
            from .orbs import turn_end
            turn_end(s,p)
        if finish_combat(s):return
        hand_at_end=list(p['hand'])
        end_effects=('endDamage','endHpLoss','regret','endGoldLoss','endWeak','endFrail')
        for c in hand_at_end:
            v=play.combat_definition(p,c)['values']
            if v.get('ethereal') and not any(v.get(key) for key in end_effects):piles.exhaust(s,p,c,caused_by_ethereal=True)
        for c in hand_at_end:
            if p['hp']<=0:break
            v=play.combat_definition(p,c)['values'];before=p['hp']
            if not any(v.get(key) for key in end_effects):continue
            if c not in p['hand']:continue
            p['hand'].remove(c)
            if v.get('endDamage'):damage.hit(s,p,p,v['endDamage'],True,True)
            loss=v.get('endHpLoss',0)+(regret_count if v.get('regret') else 0)
            if loss:damage.lose_hp(s,p,loss,True)
            if p['hp']<before:
                run_state.log(s,f"{p['name']}：{card_view(c)['name']} 导致失去 {before-p['hp']} HP")
            if v.get('endGoldLoss'):p['gold']=max(0,p['gold']-v['endGoldLoss'])
            for flag,key in [('endWeak','weak'),('endFrail','frail')]:
                if v.get(flag):
                    if not p['powers'].get(key):p.setdefault('skipDurationTicks',[]).append(key)
                    damage.power(p,key,1)
            if v.get('ethereal'):piles.exhaust(s,p,c,caused_by_ethereal=True)
            else:p['discard'].append(c)
        for c in list(p['hand']):
            v=definition(c)['values']
            if not v.get('retain') and not c.get('retainThisTurn') and not p['powers'].get('retainHand') and not p['powers'].get('wellLaidPlans') and 'RunicPyramid' not in p['relics'] and not ('RingingTriangle' in p['relics'] and p['turnNumber']==1):p['hand'].remove(c);p['discard'].append(c)
        for pile in ('hand','draw','discard','exhaust'):
            for c in p[pile]:c.pop('retainThisTurn',None);c.pop('slyThisTurn',None)
        if 'Bookmark' in p['relics']:
            candidates=[c for c in p['hand'] if not definition(c)['values'].get('xCost') and definition(c)['cost']>0]
            if candidates:change_cost(draws.combat_card_selection(s,candidates),-1,mode='add',expires=('play','combat'))
        # Rage and flame barrier expire at the end of the player's side only for
        # rage; barrier persists through enemy attacks until their side ends.
        p['powers'].pop('rage',None)
        colorless_turn_end(s,p)
        # These hooks run after hand cleanup, in power acquisition order.
        from .power_order import cleanup_order
        for token in cleanup_order(p):
            key=token.split(':',1)[0]
            if key=='monologue':
                from .classes.regent import expire_monologue
                expire_monologue(s,p,token.split(':',1)[1])
            if key=='noDraw':p['powers'].pop(key,None)
            elif key=='darkEmbrace':piles.draw(s,p,p['powers'][key]*p.pop('darkEmbraceEthereal',0))
            elif key=='hellraiser':p['hellraiserInfinitePlays']=0
            elif key=='hyperbeamFocusDown':damage.power(p,'focus',p['powers'].pop(key))
            elif key in ('temporaryFocus','hotfixFocus','focusedStrikeFocus','synchronizeFocus'):
                amount=p['powers'].pop(key)
                if amount>0:damage.debuff(s,p,p,'focus',-amount)
                elif amount<0:damage.power(p,'focus',-amount)
            elif key=='consumingShadow':
                from .classes.defect import turn_end as defect_turn_end
                defect_turn_end(s,p)
            elif key in ('temporaryDexterity','fadeDexterity','helicalDart','potionTemporaryDexterity'):
                amount=p['powers'].pop(key)
                if amount:damage.debuff(s,p,p,'dexterity',-amount)
            elif key in ('setupStrike','feedingFrenzy','coordinate','reptileTrinket','potionTemporaryStrength'):
                amount=p['powers'].pop(key)
                if amount:damage.debuff(s,p,p,'strength',-amount)
        if p['powers'].get('retainHand'):damage.power(p,'retainHand',-1)
        if p['powers'].get('debilitate'):damage.power(p,'debilitate',-1)
        from .classes.regent import turn_end as regent_turn_end
        regent_turn_end(s,p)
        from .classes.silent import turn_end as silent_turn_end
        silent_turn_end(s,p)
        p['powers'].pop('borrowedTime',None)
        from .afflictions import turn_end as affliction_turn_end
        affliction_turn_end(s,p)
        from ..run.potions import side_end
        side_end(s,p)
        from .classes.special import turn_end as special_turn_end
        special_turn_end(s,p)
        from ..relics.hooks import turn_end as relic_turn_end
        relic_turn_end(s,p)
    from .classes.necrobinder import doom_side_end
    for enemy in s['enemies']:
        enemy.pop('skittishUsed',None)
        enemy.pop('oblivionInstances',None);enemy['powers'].pop('oblivion',None)
    if any(enemy['hp']>0 for enemy in s['enemies']):
        allies=list(s['players'].values())+[p['osty'] for p in s['players'].values() if p.get('osty')]
        doom_side_end(s,allies,participants+[p['osty'] for p in participants if p.get('osty')])
    if finish_combat(s):return
    from .classes.special import after_side_end_late
    for p in participants:
        after_side_end_late(s,p)
        if finish_combat(s):return
    extra=[p for p in s['players'].values() if p['hp']>0 and (p['powers'].get('ambergris') or p.get('paelsEyeExtra'))]
    if extra:
        for p in extra:
            if p['powers'].get('ambergris'):damage.power(p,'ambergris',-1)
            if p.pop('paelsEyeExtra',False):p['paelsEyeUsed']=True
        next_turn(s,extra);return
    s['side']='enemy'
    for enemy in s['enemies']:enemy['shellDamage']=0
    from .classes.silent import poison_tick
    for target in s['enemies']:
        if target['hp']>0:poison_tick(s,target,list(s['players'].values()))
    if finish_combat(s):return
    from .classes.boss import enemy_start
    enemy_start(s)
    if finish_combat(s):return
    for enemy in s['enemies']:
        if enemy['hp']>0:enemy['slowCards']=0
    for e in list(s['enemies']):
        if e.get('pendingIllusion'):
            e.pop('pendingIllusion');e.update(hp=e['maxHp'],deathHandled=False)
        if e.get('pendingReattach'):
            from .classes.boss import reattach_turn
            reattach_turn(s,e)
            continue
        if e.get('awaitingRevive'):
            from .classes.boss import revive
            revive(s,e)
        if e['hp']<=0:continue
        if not e['powers'].get('burrowed'):e['block']=0
        executing_move=e['move']
        if s['turn']>1 and e['powers'].get('plating'):damage.power(e,'plating',-len(s['players']))
        stunned=e.pop('stunned',False);v={'targets':[]} if stunned else e['intent']
        if v.get('stealCard'):
            from .classes.boss import steal_card
            steal_card(s,e,v['targets'])
        if v.get('bloat') and sum(m['hp']>0 and m['key']=='GasBomb' for m in s['enemies'])<5:
            from .monsters import spawn, initialize
            bomb=spawn(s,'GasBomb');initialize(s,bomb);intent(s,bomb)
        if v.get('thornsBefore'):damage.power(e,'thorns',max(-e['powers'].get('thorns',0),v['thornsBefore']))
        damaging_hits=0;wounded_targets={}
        vigor_binding=damage.begin_vigor_attack(e) if 'damage' in v else None
        for _ in range(v.get('hits',1)):
            hit_unblocked=False
            for uid in v['targets']:
                p=s['players'][str(uid)]
                if e['hp']<=0:break
                if p['hp']>0 and 'damage' in v:
                    result={};damage.hit(s,e,p,v['damage'],result=result)
                    hit_unblocked=hit_unblocked or result.get('unblocked',0)>0
                    if result.get('receiverHpLost',0)>0:wounded_targets[uid]=wounded_targets.get(uid,0)+1
            damaging_hits+=int(hit_unblocked)
        if 'damage' in v:damage.finish_vigor_attack(e,vigor_binding)
        if e['powers'].get('painfulStabs'):
            for uid,count in wounded_targets.items():
                p=s['players'][str(uid)]
                if p['hp']>0:
                    for _ in range(count*e['powers']['painfulStabs']):piles.add_generated(s,p,run_state.new_card(s,'Wound'),'discard',creator=e)
        if e['hp']<=0:continue
        if v.get('selfKill'):
            from .classes.necrobinder import on_death
            e['hp']=0;on_death(s,e);continue
        if damaging_hits and e['powers'].get('suck'):damage.power(e,'strength',e['powers']['suck']*damaging_hits)
        if v.get('knowledge'):
            from .classes.special import knowledge_choice
            knowledge_choice(s,e)
        if v.get('thornsAfter'):damage.power(e,'thorns',v['thornsAfter'])
        if v.get('liquify'):
            from .classes.boss import liquify
            liquify(s,e,v['targets'])
        if v.get('layEggs'):
            from .monsters import spawn, initialize
            for _ in range(min(v['layEggs'],6-sum(m['hp']>0 for m in s['enemies']))):
                summoned=spawn(s,'ToughEgg');initialize(s,summoned)
                summoned['powers']['minion']=1;intent(s,summoned)
        if v.get('hatchEgg'):
            from .monsters import hp as scale_hp
            health=scale_hp(s,monster_value(s,'ToughEgg','HatchlingMinHp',19)+draws.niche_int(s,4))
            e.update(hp=health,maxHp=health,name='Hatchling',hatched=True)
            e['powers']={key:amount for key,amount in e['powers'].items() if key=='minion'}
            e.pop('debuffKeys',None)
        if v.get('fabricate'):
            from .monsters import spawn, initialize, monster_ai_choose
            pools=[['Guardbot','Noisebot'],['Zapbot','Stabbot']] if v['fabricate']==2 else [['Zapbot','Stabbot']]
            for pool in pools:
                key=monster_ai_choose(s,[key for key in pool if key!=e.get('lastBot')])
                e['lastBot']=key;summoned=spawn(s,key);initialize(s,summoned)
                summoned['powers']['minion']=1;intent(s,summoned)
        if v.get('guardFabricator'):
            for teammate in s['enemies']:
                if teammate['hp']>0 and teammate['key']=='Fabricator':damage.gain_block(s,teammate,v['guardFabricator'],True)
        if v.get('escapeEnemy'):
            e.update(hp=0,escaped=True,deathHandled=True)
            if e['key']=='FatGremlin':s['mercEscaped']=True
            continue
        if v.get('stealGold') and e['powers'].get('thievery',0)>0:
            for uid,p in s['players'].items():
                if p['hp']>0:
                    stolen=min(p['gold'],e['powers']['thievery']);p['gold']-=stolen
                    e.setdefault('stolenGold',{})[uid]=e.get('stolenGold',{}).get(uid,0)+stolen
        if v.get('ratBackup'):
            from .monsters import spawn, initialize
            if sum(m['hp']>0 for m in s['enemies'])<5:
                summoned=spawn(s,'TwoTailedRat');initialize(s,summoned);intent(s,summoned)
            rats=[m for m in s['enemies'] if m['hp']>0 and m['key']=='TwoTailedRat']
            calls=max(m.get('ratCalls',0) for m in rats)+1
            for rat in rats:rat['ratCalls']=calls
            e['ratCalled']=True
        if v.get('summonEnemy'):
            from .monsters import spawn, initialize
            summoned=spawn(s,v['summonEnemy']);initialize(s,summoned);intent(s,summoned)
        if v.get('teamStrength'):
            for teammate in s['enemies']:
                if teammate['hp']>0:damage.power(teammate,'strength',v['teamStrength'])
        if v.get('hiveSpit'):
            hive=e['powers'].get('personalHive',0)
            if 0<hive<3:damage.power(e,'personalHive',1);damage.power(e,'strength',1)
            else:damage.power(e,'strength',2)
        if v.get('intensify'):
            from .classes.boss import intensify
            intensify(s,e)
        if v.get('burrowed'):damage.power(e,'burrowed',v['burrowed'])
        if v.get('flutter'):
            from .monsters import hp as scale_power
            e['powers']['flutter']=scale_power(s,v['flutter'])
        if v.get('soar'):e['powers']['soar']=1
        if v.get('land'):e['powers'].pop('soar',None)
        if v.get('intangible'):damage.power(e,'intangible',v['intangible'])
        if v.get('beckon'):
            for uid in v['targets']:
                p=s['players'][str(uid)]
                if p['hp']>0:
                    piles.add_generated(s,p,run_state.new_card(s,'Beckon'),'draw',creator=e,random_position=True)
                    piles.add_generated(s,p,run_state.new_card(s,'Beckon'),'discard',creator=e)
        if v.get('plow'):
            from .monsters import hp as scale_threshold
            damage.power(e,'plow',scale_threshold(s,v['plow']))
        if v.get('healPerPlayer'):damage.heal(e,v['healPerPlayer']*len(s['players']))
        if v.get('ritual'):
            if not e['powers'].get('ritual'):e['ritualFresh']=True
            damage.power(e,'ritual',v['ritual'])
        if v.get('status'):
            for uid in v['targets']:
                p=s['players'][str(uid)]
                if p['hp']>0:
                    for _ in range(v['count']):piles.add_generated(s,p,run_state.new_card(s,v['status']),v.get('statusPile','discard'),creator=e)
                    # Some moves split the same status across piles, one of them
                    # at a random position.
                    for extra in v.get('statusExtra',[]):
                        for _ in range(extra['count']):
                            piles.add_generated(s,p,run_state.new_card(s,extra['status']),extra.get('pile','discard'),creator=e,
                                          random_position=extra.get('randomPosition',False))
        for key,amount in v.get('debuffs',{}).items():
            for uid in v['targets']:
                damage.debuff(s,e,s['players'][str(uid)],key,amount)
        if v.get('allyStrength'):
            for teammate in s['enemies']:
                if teammate is not e and teammate['hp']>0:damage.power(teammate,'strength',v['allyStrength'])
        if v.get('block'):
            from .monsters import block as scaled_block
            damage.gain_block(s,e,scaled_block(s,v['block']),True)
        if v.get('moveBlock'):damage.gain_block(s,e,v['moveBlock'])
        if v.get('dexterity'):damage.power(e,'dexterity',v['dexterity'])
        damage.power(e,'strength',v.get('strength',0))
        if v.get('vigor'):damage.power(e,'vigor',v['vigor'])
        if not stunned and e['key']=='SlumberingBeetle' and executing_move==2:e['powers'].pop('plating',None)
        if v.get('vitalSpark'):
            damage.power(e,'vitalSpark',v['vitalSpark'])
            from .afflictions import vital_spark
            vital_spark(s,e['powers']['vitalSpark'])
        if not stunned:
            from .classes.boss import move_effect
            move_effect(s,e,executing_move)
        if e['hp']<=0:continue
        if stunned or e['key'] in ('Tunneler','CeremonialBeast','LagavulinMatriarch','WaterfallGiant','TerrorEel') and e['move']!=executing_move:pass
        elif e['key'] in ADDITIONAL_MONSTERS:
            from .monsters import advance
            advance(s,e)
        elif e['key']=='BygoneEffigy':e['move']=min(2,e['move']+1)
        elif e['key']=='Inklet':
            from .monsters import random_branch
            e['move']=random_branch(s,e,[(2,1.0,(('repeat',1),)),(1,1.0,(('repeat',1),))]) if e['move']==0 else 0
        elif e['key']=='KnowledgeDemon':e['move']=1 if e['move']==3 and e.get('knowledgeCount',0)>=3 else (e['move']+1)%4
        else:e['move']=(e['move']+1)%len(ENEMIES[e['key']][3])
        for key in ('weak','vulnerable'):
            if e['powers'].get(key):damage.power(e,key,-1)
        for key in list(e['powers']):
            if key in damage.TEMPORARY_STRENGTH_LOSS:damage.power(e,'strength',e['powers'].pop(key))
            elif key=='hyperbeamFocusDown':damage.power(e,'focus',e['powers'].pop(key))
        e.pop('flankingInstances',None);e['powers'].pop('flanking',None)
        if e['powers'].get('conqueror'):damage.power(e,'conqueror',-1)
        e.pop('knockdownInstances',None);e['powers'].pop('knockdown',None)
        e.pop('strangleInstances',None);e['powers'].pop('strangle',None)
        e.pop('sicEmInstances',None);e['powers'].pop('sicEm',None)
        if e['powers'].get('debilitate'):damage.power(e,'debilitate',-1)
    doom_side_end(s,s['enemies'],s['enemies'])
    for e in s['enemies']:
        from ..run.potions import side_end
        # These powers listen to side end, after every enemy has acted.
        # Newly granted Intangible does not consume its first stack here.
        if e['hp']>0 and e['powers'].get('intangible'):damage.power(e,'intangible',-1)
        if e['hp']>0 and e['powers'].get('nemesis'):
            e['nemesisActive']=not e.get('nemesisActive',False)
            if e['nemesisActive']:damage.power(e,'intangible',1)
            else:e['powers'].pop('intangible',None)
        if e['hp']>0 and e['powers'].get('battlewornDummyTimeLimit'):
            damage.power(e,'battlewornDummyTimeLimit',-1)
            if not e['powers']['battlewornDummyTimeLimit']:
                s.setdefault('eventCombat',{})['ranOutOfTime']=True
                e.update(hp=0,escaped=True,deathHandled=True)
        if e['hp']>0 and e['powers'].get('territorial'):damage.power(e,'strength',e['powers']['territorial'])
        if e['hp']>0 and e['powers'].get('highVoltage'):damage.power(e,'strength',e['powers']['highVoltage'])
        if e['hp']>0 and e['powers'].get('hatch'):damage.power(e,'hatch',-1)
        if e['hp']>0 and e['powers'].get('escapeArtist',0)>1:damage.power(e,'escapeArtist',-1)
        if e['powers'].get('asleep')==1:e['powers'].pop('plating',None)
        if e['hp']>0 and e['powers'].get('plating'):damage.gain_block(s,e,e['powers']['plating'],True)
        if e['powers'].get('asleep'):
            damage.power(e,'asleep',-1)
            if not e['powers']['asleep']:e['powers'].pop('asleep')
        side_end(s,e)
        if e['hp']>0 and e['powers'].get('slumber'):
            damage.power(e,'slumber',-1)
            if not e['powers']['slumber']:
                e['powers'].pop('slumber');e['powers'].pop('plating',None);e['move']=1
    for p in s['players'].values():
        p['powers'].pop('covered',None);p['powers'].pop('intercept',None);p['covering']=[];p['coverSources']=[]
        p['powers'].pop('thorns',None)
        p['powers'].pop('tainted',None)
        p['powers'].pop('concoct',None)
        if p['powers'].get('intangible'):damage.power(p,'intangible',-1)
        p['powers'].pop('underworld',None)
        skip=p.pop('skipDurationTicks',[])
        for key in ('weak','vulnerable','frail','noBlock','colossus'):
            if p['powers'].get(key) and key not in skip:damage.power(p,key,-1)
    if not finish_combat(s):next_turn(s)

def finish_requested_turn(s,p):
    if p.pop('endRequested',False) and not p['done'] and p['hp']>0:
        from .effects import end_turn
        p['done']=True;p['endCommittedTurn']=s['turn'];end_turn(s,p);return True
    return False

def all_ready_to_end_turn(s):
    """``CombatManager.AllPlayersReadyToEndTurn`` — the point of no return.

    Once every player is ready the enemy turn is claimed and an undo can no
    longer be honoured, which is exactly what a player who has just pressed end
    needs to be told before they press it.
    """
    return all(p['done'] or p['hp']<=0 for p in s['players'].values())

def commit_ready_turn(s):
    """Run end requests once, after every living player has committed."""
    if s.get('phase')!='combat' or s.get('side')!='player' or not all_ready_to_end_turn(s):return False
    from ..core.continuation import current
    runtime=current()
    if runtime and runtime.depth:return False
    participants=s.get('turnParticipants',[p['id'] for p in s['players'].values()])
    for member in s['players'].values():
        if member['id'] not in participants or member['hp']<=0 or member.get('endCommittedTurn')==s['turn']:continue
        member['endCommittedTurn']=s['turn']
        from .effects import end_turn
        end_turn(s,member)
        if s.get('phase')!='combat' or s.get('pendingChoice') or s.get('pendingDecision') or s.get('effects'):return True
    if s.get('phase')=='combat' and s.get('side')=='player':enemy_turn(s)
    return True

def turn_is_resolving(s):
    """Past the point of no return: the end has been claimed, not just offered."""
    return s.get('phase')=='combat' and (s.get('side')!='player' or all_ready_to_end_turn(s))

def end_turn_state(s,p):
    """What the end-turn control should show, and why.

    Three states, not two: a player may be able to end, able to undo, or
    neither because the turn is already resolving. Collapsing the third into
    "disabled" is what makes a client offer an undo that cannot be honoured.
    """
    if s.get('phase')!='combat':return {'canEndTurn':False,'canUndoEndTurn':False,'reason':'不在战斗中。'}
    if p['hp']<=0:return {'canEndTurn':False,'canUndoEndTurn':False,'reason':'你已经倒下。'}
    if s.get('pendingChoice') or s.get('pendingDecision'):
        return {'canEndTurn':False,'canUndoEndTurn':False,'reason':'请先完成当前选择。'}
    if turn_is_resolving(s):
        return {'canEndTurn':False,'canUndoEndTurn':False,'reason':'回合正在结算。'}
    if p['done']:
        # Undo stays open only while some other player has yet to commit.
        return {'canEndTurn':False,'canUndoEndTurn':True,'reason':'已结束回合，等待同伴。'}
    return {'canEndTurn':True,'canUndoEndTurn':False,'reason':''}

def undo_end(s,p,action):
    """``UndoEndPlayerTurnAction``: take back an end that has not been claimed.

    Returns whether anything changed, so a caller that wants to can tell the
    two apart; the action path does not, because ignoring is the contract.

    The turn number is the dedup and a stale one is *ignored*, not rejected:
    the client cannot know the turn moved on, so a late undo is a race it
    cannot avoid rather than a mistake it can correct. Rejecting it would turn
    a lost race into an error the player has to clear.
    """
    # Silently: a late undo is not something the player did, and writing it to
    # the game log would make an ignored action a visible change -- which is
    # exactly what "ignored" has to not be.
    if action.get('turn')!=s['turn']:return False
    if s.get('phase')!='combat' or s.get('side')!='player':return False
    if not p['done'] or p.get('endCommittedTurn')==s['turn']:return False
    p['done']=False
    run_state.log(s,f"{p['name']} 撤销了结束回合。")
    return True
