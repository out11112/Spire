"""Playing a card: costs, targets, resolution and settling."""
from ..text import battle_log
from copy import deepcopy
from decimal import Decimal
from ..content import CARDS, definition, card_view
from .costs import add as change_cost, free as free_card, expire as expire_cost
from ..core.errors import require
from . import battle
from . import damage
from . import piles
from ..core import state as run_state
from ..rng import draws

def attack_base(p,c,target=None,state=None):
    amount=raw_attack_base(p,c,target,state)
    enchantment=c.get('enchantment',{})
    # Enchantment multipliers precede additive power and relic hooks.
    if enchantment.get('key')=='Instinct':amount*=2
    if enchantment.get('key')=='Corrupted':amount=Decimal(amount)*Decimal('1.5')
    if 'MiniatureCannon' in p['relics'] and c.get('upgraded'):amount+=3
    if 'StrikeDummy' in p['relics'] and definition(c)['values'].get('strike'):amount+=3
    if 'FakeStrikeDummy' in p['relics'] and definition(c)['values'].get('strike'):amount+=1
    enchantment=c.get('enchantment',{})
    if enchantment.get('key')=='Sharp':amount+=enchantment['amount']
    if enchantment.get('key')=='TezcatarasEmber':amount+=3
    if enchantment.get('key')=='Momentum':amount+=enchantment.get('extraDamage',0)
    if enchantment and 'MysticLighter' in p['relics']:amount+=9
    if enchantment.get('key')=='Vigorous' and not enchantment.get('usedThisCombat'):amount+=enchantment['amount']
    return amount

def raw_attack_base(p,c,target=None,state=None):
    v=definition(c)['values']
    if v.get('bodySlam'):return p['block']
    if v.get('mindBlast'):return len(p['draw'])
    amount=v.get('damage',0)+v.get('ashenStrike',0)*len(p['exhaust'])
    if v.get('ostyMaxHpDamage') and p.get('osty',{}).get('hp',0)>0:amount+=p['osty']['maxHp']
    amount+=v.get('bully',0)*(target['powers'].get('vulnerable',0) if target else 0)
    amount+=v.get('discardDamage',0)*p.get('discardedThisTurn',0)+v.get('drawnDamage',0)*p.get('drawnThisCombat',0)
    amount-=v.get('handPenalty',0)*sum(x['id']!=c['id'] for x in p['hand'])
    amount+=v.get('generatedDamage',0)*p.get('generatedThisCombat',0)
    amount+=v.get('extraDrawDamage',0)*p.get('extraDrawsThisTurn',0)
    amount+=v.get('soulDamage',0)*sum(x['key']=='Soul' for x in p['exhaust'])
    if v.get('doomDamage'):amount+=target['powers'].get('doom',0) if target else 0
    if v.get('ostyCardDamage'):
        from .classes.defect import combat_cards
        cards={x['id']:x for x in combat_cards(state,p,c)}
        amount+=v['ostyCardDamage']*sum(x['id']!=c['id'] and definition(x)['values'].get('osty',False) for x in cards.values())
    if v.get('starCardDamage'):
        from .classes.defect import combat_cards
        cards={x['id']:x for x in combat_cards(state,p,c)}
        amount+=v['starCardDamage']*sum('starCost' in definition(x)['values'] or definition(x)['values'].get('starX',False) for x in cards.values())
    if v.get('perfectedStrike'):
        from .classes.defect import combat_cards
        all_cards={card['id']:card for card in combat_cards(state or {},p,c)}
        amount+=v['perfectedStrike']*sum(bool(definition(card)['values'].get('strike')) for card in all_cards.values())
    if state is not None:
        from .classes.colorless import attack_extra
        amount+=attack_extra(state,p,c,target)
    if v.get('ostyHpDamage'):amount+=max(0,p.get('osty',{}).get('hp',0))
    if v.get('shiv'):
        amount+=p['powers'].get('accuracy',0)
        if not p.get('shivsFinished'):amount+=p['powers'].get('phantomBlades',0)
    if not v.get('xCost') and c.get('paidEnergy',energy_cost(state,p,c) if state else definition(c)['cost'])==0:
        amount+=p['powers'].get('oneForAll',0)
    return amount

def replay_count(p,c):
    from .enchantments import extra_plays
    amount=c.get('extraReplays',0)+extra_plays(c)
    if c['key']=='SovereignBlade':
        from .classes.regent import prepare_blade
        prepare_blade(p,c);amount+=c['swordSageReplays']
    return amount

def energy_cost(s,p,c,*,in_play=False,clamp_zero=True):
    d=combat_definition(p,c);v=d['values']
    if v.get('unplayable'):return d['cost']
    if v.get('xCost'):return p['energy']
    cost=d['cost']
    for key,amount in p['powers'].items():
        if key=='borrowedTime':cost+=amount
        elif key=='tangled' and c.get('affliction',{}).get('key')=='Entangled':cost+=amount
        elif key=='curious' and d['kind']=='power' and cost>0:cost=max(0,cost-amount)
    if d['kind']=='power' and 'SpikedGauntlets' in p['relics']:cost+=1
    if v.get('etherealCostReduction'):cost-=v['etherealCostReduction']*p.get('etherealPlays',0)
    if v.get('flatten') and p.get('ostyAttacks'):cost=0
    if d['kind']=='skill' and p['powers'].get('corruption'):cost=0
    playable_pile=in_play or any(card['id']==c['id'] for pile in ('hand','inPlay') for card in p.get(pile,[]))
    if playable_pile:
        if v.get('ethereal') and p['powers'].get('veilpiercer'):cost=0
        if d['kind']=='skill' and p['powers'].get('freeSkill'):cost=0
        if d['kind']=='power' and p['powers'].get('freePower'):cost=0
        if d['kind']=='attack' and p['powers'].get('freeAttack'):cost=0
    if playable_pile and p['powers'].get('voidForm',0)>p.get('voidCardsPlayed',0) and not v.get('xCost'):cost=0
    from ..relics.hooks import scarf_free
    if scarf_free(p,c):cost=0
    return max(0,cost) if clamp_zero else cost

def combat_definition(p,c):
    result=definition(c,owner=p)
    if result['values'].get('shiv') and p['powers'].get('fanOfKnives'):result['target']='all'
    if c['key']=='SovereignBlade' and p['powers'].get('seekingEdge'):result['target']='all'
    return result

def combat_card_view(s,p,c):
    result=card_view(c,owner=p)
    result['target']=combat_definition(p,c)['target']
    from ..text.attack_preview import damage_by_target
    damage_preview=damage_by_target(s,p,c)
    if damage_preview is not None:result['damagePreview']={'basis':'currentStateBeforeBlock','byTarget':damage_preview}
    if not definition(c)['values'].get('unplayable') and result['cost']!='X':result['cost']=energy_cost(s,p,c)
    if 'starCost' in definition(c)['values'] or definition(c)['values'].get('starX'):result['starCost']='X' if definition(c)['values'].get('starX') else star_cost(p,c)
    return result

def star_cost(p,c,*,in_play=False):
    values=definition(c)['values']
    from ..relics.hooks import scarf_free
    if scarf_free(p,c):return 0
    if values.get('starX'):return p.get('stars',0)
    playable_pile=in_play or any(card['id']==c['id'] for pile in ('hand','inPlay') for card in p.get(pile,[]))
    if playable_pile and p['powers'].get('voidForm',0)>p.get('voidCardsPlayed',0):return 0
    if c.get('freeThisTurn') or c.get('freeStarsThisTurn') or c.get('freeThisCombat'):return 0
    return max(0,values.get('starCost',0))

def play(s,p,a,*,automatic_card=None,replay=False,spend_resources=False):
    automatic=automatic_card is not None
    require(replay or 'VelvetChoker' not in p['relics'] or p.get('velvetChokerPlayed',0)<6,'天鹅绒项圈：每回合最多打出六张牌。')
    require((automatic or not p['done']) and p['hp']>0,'你已结束回合或倒下。')
    c=automatic_card if automatic else run_state.find_card(p['hand'],a.get('card'))
    c['relicAutoPlay']=automatic
    from .afflictions import smog_blocks
    require(replay or not smog_blocks(p,c),'烟雾：这张技能牌本回合无法打出。')
    from .afflictions import ringing_blocks
    require(replay or not ringing_blocks(p,c),'昏眩：本回合已经打出过卡牌。')
    from .afflictions import bound_blocks
    require(replay or not bound_blocks(p,c),'魂缚：本回合已经打出过魂缚卡牌。')
    d=combat_definition(p,c);v=d['values'];cost=0 if automatic and not spend_resources else energy_cost(s,p,c,in_play=automatic)
    x_value=c.get('capturedX',p['energy']) if replay else p['energy']
    stars=c.get('capturedStars',star_cost(p,c,in_play=automatic)) if replay else star_cost(p,c,in_play=automatic)
    if not replay:c['paidEnergy']=cost
    c['lethalityPercent']=p['powers'].get('lethality',0) if d['kind']=='attack' and not p.get('attacksPlayed') and not replay else 0
    if not replay:c['resourceEnergyValue']=energy_cost(s,p,c,in_play=automatic)
    require(automatic or not any(x['key']=='Enthralled' for x in p['hand']) or c['key']=='Enthralled','必须先打出手牌中的执迷。')
    require(automatic or not any(x['key']=='Normality' for x in p['hand']) or p.get('cardsPlayed',0)<3,'凡庸：每回合最多打出 3 张牌。')
    require(not v.get('unplayable') and p['energy']>=cost,'能量不足或这张牌不可打出。')
    require(automatic or not v.get('attackOnlyHand') or all(definition(x)['kind']=='attack' for x in p['hand']),'交锋：手牌中只能有攻击牌。')
    require(replay or not p['powers'].get('sloth') or p.get('slothPlays',0)<p['powers']['sloth'],'懒惰：本回合不能再打出卡牌。')
    require(automatic or p.get('stars',0)>=stars,'辉星不足。')
    require(automatic or not v.get('emptyDrawOnly') or not p['draw'],'抽牌堆必须为空才能打出这张牌。')
    from .osty import alive as osty_alive
    require(automatic or not v.get('requiresOsty') or osty_alive(p),'必须有存活的奥斯提。')
    targets=[e for e in s['enemies'] if e['hp']>0]
    if d['target']=='enemy':
        target=next((e for e in (s['enemies'] if replay or automatic else targets) if e['id']==a.get('target')),None);require(target is not None,'目标已失效，请重新选择。');targets=[target]
    ally=None
    if d['target']=='ally':
        ally=next((x for x in s['players'].values() if x['id']==a.get('target') and x['id']!=p['id'] and x['hp']>0),None)
        require(ally is not None,'请选择存活的其他队友。');targets=[]
    candidates=[x for x in p['hand'] if x['id']!=c['id'] and (not v.get('upgradeHand') or run_state.upgradable(x))]
    needs=(v.get('upgradeHand') and not c['upgraded']) or v.get('exhaustChoice') or (v.get('trueGrit') and c['upgraded'])
    if needs and candidates and not automatic:
        # This choice is a second target, not the played card: reusing find_card
        # here reported a missing choice as "that card is no longer there", which
        # sends the player looking at the wrong thing.
        chosen=next((x for x in candidates if x['id']==a.get('choice')),None)
        require(chosen is not None,'请先选择这张牌要处理的牌。')
    else:
        chosen=None
    from .classes.boss import face
    if d['target']=='enemy' and targets:face(p,targets[0])
    battle_log.emit(s,f"{p['name']} {'自动' if automatic else '手动'}打出 {card_view(c)['name']} · 能量 {cost} · 辉星 {0 if automatic and not spend_resources else stars}",'play',actor=p['id'],card=c['key'],target=a.get('target'),automatic=automatic,replay=replay,energy=cost,stars=0 if automatic and not spend_resources else stars)
    p['energy']-=cost
    if not automatic or spend_resources:p['stars']=p.get('stars',0)-stars
    from .classes.regent import after_payment
    after_payment(s,p,cost,0 if automatic and not spend_resources else stars)
    p['energySpentThisTurn']=p.get('energySpentThisTurn',0)+cost
    if c in p['hand']:p['hand'].remove(c)
    if not any(x is c for x in p.setdefault('inPlay',[])):p['inPlay'].append(c)
    if not replay:
        c['seriesStarsSpent']=0 if automatic and not spend_resources else stars
        c['manualSeries']=not automatic
        if v.get('xCost') and 'ChemicalX' in p['relics']:x_value+=2
        c['capturedX']=x_value;c['replayTarget']=a.get('target');c['replaysLeft']=replay_count(p,c)
        if 'ThrowingAxe' in p['relics'] and not p.get('throwingAxeUsed'):p['throwingAxeUsed']=True;c['replaysLeft']+=1
        if p['powers'].get('duplication'):c['replaysLeft']+=1;damage.power(p,'duplication',-1)
        c['capturedStars']=stars
        if p.get('seriesStarted',0)<p['powers'].get('echoForm',0):c['replaysLeft']+=1
        if d['kind']=='power' and p['powers'].get('signalBoost'):c['replaysLeft']+=1;damage.power(p,'signalBoost',-1)
        if d['kind']=='attack' and not c.get('isDupe') and c['resourceEnergyValue']==0 and p.get('feralUsed',0)<p['powers'].get('feral',0):
            c['feralReturn']=True;p['feralUsed']=p.get('feralUsed',0)+1
        if d['kind']=='skill' and p['powers'].get('burst'):
            c['replaysLeft']+=1;damage.power(p,'burst',-1)
        if d['kind']=='attack':
            if p['powers'].get('oneTwoPunch'):
                c['replaysLeft']+=1;damage.power(p,'oneTwoPunch',-1)
            if d['target'] in ('enemy','all'):
                for target in targets:
                    instances=target.get('tagTeamInstances',[])
                    c['replaysLeft']+=sum(record['amount'] for record in instances if record['owner']!=p['id'])
                    target['tagTeamInstances']=[record for record in instances if record['owner']==p['id']]
                    target['powers']['tagTeam']=sum(record['amount'] for record in target['tagTeamInstances'])
        if c['replaysLeft']<0:
            clear_play_costs(c)
            settle_card(s,p,c,played=False);after_card(s);return
        p['seriesStarted']=p.get('seriesStarted',0)+1
    p['cardsPlayed']=p.get('cardsPlayed',0)+1
    play_id=p['cardsPlayed']
    if p['powers'].get('rupture') and s.get('side','player')=='player':p.setdefault('ruptureCards',{})[c['id']]=0
    if d['kind']=='skill':p['skillsStarted']=p.get('skillsStarted',0)+1
    if p['powers'].get('chainsOfBinding') and c.get('affliction',{}).get('key')=='Bound' and not c.get('isDupe'):p['boundPlayed']=True
    from .classes.colorless import before_card, apply_card
    from .classes.special import before_card as special_before_card
    special_before_card(s,p,c,replay)
    if d['kind']=='attack' and 'PenNib' in p['relics']:
        p['penNibAttacks']=(p.get('penNibAttacks',0)+1)%10
        if p['penNibAttacks']==0:p['penNibCard']=c['id']
    if d['kind']=='attack' and 'MusicBox' in p['relics'] and not p.get('musicBoxUsed') and not p.get('musicBoxCard'):p['musicBoxCard']=c['id']
    if 'IntimidatingHelmet' in p['relics'] and c.get('resourceEnergyValue',0)>=2:damage.gain_block(s,p,4,True)
    before_card(s,p,c,d,replay=replay)
    c['afterimageBlock']=p['powers'].get('afterimage',0)
    c['serpentDamage']=p['powers'].get('serpentForm',0)
    if d['kind']=='attack' and c['resourceEnergyValue']==0:p['zeroEnergyAttacks']=p.get('zeroEnergyAttacks',0)+1
    from .classes.defect import before_card as defect_before_card
    defect_before_card(s,p,c,replay)
    from .classes.regent import before_card as regent_before_card
    regent_before_card(s,p,c)
    from .classes.necrobinder import before_card as necrobinder_before_card
    necrobinder_before_card(s,p,c)
    c['strangleDamage']=[{'target':target['id'],'amount':sum(record['amount'] for record in target.get('strangleInstances',[]) if record['owner']==p['id'])} for target in s['enemies'] if target['hp']>0]
    if v.get('forgePerHit'):c['forgeAttackResults']=0
    if v.get('misery'):
        from .classes.necrobinder import snapshot_debuffs
        c['copiedDebuffs']=snapshot_debuffs(targets[0])
    p['blockCard']=c['id'];p['blockDefend']=bool(v.get('defend'));p['blockPlay']=play_id
    if d['kind']=='skill' and p['powers'].get('corruption'):c['forceExhaust']=True
    if d['kind']=='attack':
        from .classes.defect import combat_cards
        for candidate in combat_cards(s,p,c):
            if definition(candidate)['values'].get('stomp'):
                change_cost(candidate,-1,mode='add',expires=('turn',))
        p['attacksPlayed']=p.get('attacksPlayed',0)+1
        if p['attacksPlayed']==3:
            for _ in range(p['powers'].get('juggling',0)):
                copy=run_state.copy_card(s,c);piles.add_generated(s,p,copy)

    if v.get('osty') and not osty_alive(p) and not (v.get('sicEm') or v.get('grantKeyword')):
        settle_card(s,p,c);after_card(s);return
    if automatic and needs or any(v.get(key) for key in ('thinkingAhead','searchDraw','purity','discovery','splash','brand','havoc','cascade','beatDown','catastrophe')):
        from .effects import start
        start(s,p,c,legacy=bool(automatic and needs));return
    if v.get('hpLoss'):damage.lose_hp(s,p,v['hpLoss'],True)
    if p['hp']>0:
        if v.get('delayedBlock'):
            preview=deepcopy(p);preview['block']=0
            multiplier=2 if p['powers'].get('unmovable',0)>sum(ident!=p.get('blockPlay') for ident in p.get('blockEvents',[])) else 1
            delayed_block_amount=damage.block(preview,v['delayedBlock'],source=p,multiplier=multiplier)
        if v.get('block'):
            amount=v['block']+v.get('strengthBlock',0)*max(0,p['powers'].get('strength',0))
            for _ in range(2 if v.get('evilEye') and p.get('exhaustedThisTurn') else 1):
                gained=damage.gain_block(s,p,amount)
                if v.get('toricToughness'):
                    p.setdefault('toricInstances',[]).append({'left':v['toricToughness'],'block':gained})
                    damage.power(p,'toricToughness',v['toricToughness'])
                if v.get('repeatBlockNextTurn'):damage.power(p,'blockNextTurn',gained)
        if v.get('delayedBlock'):damage.power(p,'blockNextTurn',delayed_block_amount)
        if ally:
            if v.get('allyStrength'):damage.power(ally,'strength',v['allyStrength'])
            if v.get('demonicShield'):damage.gain_block(s,ally,p['block'],source=p)
        if d['kind']=='attack':
            attack_total=0;first_results={}
            attack_actor=p.get('osty') if v.get('osty') else p
            from ..text.attack_preview import hit_count
            hits=hit_count(s,p,c,targets[0] if targets else {'powers':{}},x_value,stars)
            if v.get('flakCannon'):
                from .classes.defect import combat_cards
                exhausted={card['id'] for card in p['exhaust']}
                snapshot={card['id']:card for card in combat_cards(s,p) if CARDS[card['key']]['kind']=='status' and card['id'] not in exhausted}
                hits=len(snapshot)
                for consumed in snapshot.values():
                    s['effects']=[op for op in s.get('effects',[]) if not (op.get('op')=='autoplay' and op.get('card',{}).get('id')==consumed['id'])]
                    piles.exhaust(s,p,consumed)
            if v.get('fiendFire'):
                snapshot=list(p['hand']);hits=len(snapshot)
                for consumed in snapshot:piles.exhaust(s,p,consumed)
            if v.get('osty'):
                if osty_alive(p):p['ostyAttacks']=p.get('ostyAttacks',0)+1
                else:hits=0
            vigor_binding=damage.begin_vigor_attack(attack_actor,c)
            # These cards still execute their attack command when its hit count
            # is zero, so AfterAttack consumes Gigantification normally.
            attack_command=hits>0 or any(v.get(key) for key in ('xCost','starX','fiendFire','finisher','lunarBlast','radiate','etherealHits','flechettes','barrage','helixDrill','flakCannon'))
            gigantic=attack_command and bool(p['powers'].get('gigantification')) and not p.get('gigantificationCard') and bool(attack_actor and attack_actor['hp']>0)
            if gigantic:p['gigantificationCard']=c['key']
            flute=hits>0 and v.get('osty') and 'BoneFlute' in p['relics']
            while hits>0:
                hits-=1
                hit_targets=[draws.random_enemy(s)] if d['target']=='random' and any(e['hp']>0 for e in s['enemies']) else targets
                if d['target']=='all':hit_targets=[enemy for enemy in s['enemies'] if enemy['hp']>0]
                for e in hit_targets:
                    alive=e['hp']>0
                    if attack_actor and attack_actor['hp']>0:
                        received={}
                        attack_total+=damage.hit(s,attack_actor,e,attack_base(p,c,e,s),card_key=c['key'],lethality=c.get('lethalityPercent',0),result=received,card_instance=c) or 0
                        if received:first_results.setdefault(e['id'],received['receiverHpLost'])
                        if received and v.get('forgePerHit'):c['forgeAttackResults']+=1
                    if v.get('echoingSlash') and alive and e['hp']<=0:hits+=1
                    if v.get('killEnergy') and alive and e['hp']<=0:p['energy']+=v['killEnergy']
                    if v.get('killStars') and alive and e['hp']<=0:
                        from .classes.regent import gain_stars
                        gain_stars(s,p,v['killStars'])
                    if v.get('feed') and alive and e['hp']<=0 and not e.get('fatalBlocked') and not e['powers'].get('minion'):
                        p['maxHp']+=v['feed'];damage.heal(p,v['feed'])
                    if v.get('fatalGold') and alive and e['hp']<=0 and not e.get('fatalBlocked') and not e['powers'].get('minion'):run_state.gain_gold(s,p,v['fatalGold'])
                    if v.get('theHunt') and alive and e['hp']<=0 and not e.get('fatalBlocked') and not e['powers'].get('minion'):
                        p['extraCardRewards']=p.get('extraCardRewards',0)+1;damage.power(p,'theHunt',1)
            if flute:damage.gain_block(s,p,2,True)
            for enemy in s['enemies']:
                if enemy['hp']>0 and enemy['powers'].get('skittish') and not enemy.get('skittishUsed') and first_results.get(enemy['id'],0)>0:
                    enemy['skittishUsed']=True;damage.gain_block(s,enemy,enemy['powers']['skittish'],True)
            if gigantic:p.pop('gigantificationCard',None);damage.power(p,'gigantification',-1)
            c['attackDamage']=attack_total
            if attack_actor:damage.finish_vigor_attack(attack_actor,vigor_binding)
            if v.get('fisticuffs'):damage.gain_block(s,p,attack_total)
            if v.get('omnislice'):
                for other in s['enemies']:
                    if other not in targets and other['hp']>0:damage.hit(s,p,other,attack_total,True,card_source=True,card_instance=c)
        # Meteor Shower completes each debuff across the current opponents in order.
        if c['key']=='MeteorShower':
            for key in ('weak','vulnerable'):
                for enemy in [enemy for enemy in s['enemies'] if enemy['hp']>0]:
                    damage.debuff(s,p,enemy,key,v[key],card_source=c)
        # Thunderclap and HighFive query opponents again after their attack
        # resolves; the reference applies the debuff to whatever is hittable at
        # that point, not to the play-time target snapshot.
        debuff_targets=[enemy for enemy in s['enemies'] if enemy['hp']>0] if c['key'] in ('Thunderclap','HighFive') else targets
        for e in debuff_targets:
            if e['hp']>0:
                for key in ('weak','vulnerable','poison'):
                    if v.get(key) and not (c['key']=='MeteorShower' and key in ('weak','vulnerable')):damage.debuff(s,p,e,key,v[key],card_source=c)
                if v.get('strangle') and damage.debuff(s,p,e,'strangle',v['strangle'],card_source=c):
                    from .classes.necrobinder import stack_per_applier
                    stack_per_applier(e,'strangleInstances',p['id'],damage.applied_debuff(c,e,'strangle',v['strangle']))
                if v.get('darkShackles'):
                    key='mangle' if c['key']=='Mangle' else 'darkShackles'
                    if damage.debuff(s,p,e,key,v['darkShackles'],card_source=c):damage.power(e,'strength',-v['darkShackles'])
                if v.get('doubleVulnerable') and e['powers'].get('vulnerable'):damage.debuff(s,p,e,'vulnerable',e['powers']['vulnerable'],card_source=c)
                if v.get('enemyStrength'):damage.power(e,'strength',v['enemyStrength'])
                if v.get('dominate'):damage.power(p,'strength',e['powers'].get('vulnerable',0))
        if v.get('removeOrbSlots'):
            from .orbs import change_capacity
            change_capacity(p,-v['removeOrbSlots'])
        for key in ('strength','rage','thorns','demonForm','feelNoPain','darkEmbrace','rupture','noBlock','juggling','aggression','colossus','crimsonMantle','cruelty','inferno','juggernaut','pyre','plating','unmovable','freeAttack','vicious','oneTwoPunch','stampede'):
            if v.get(key):damage.power(p,key,v[key])
        first_tank=bool(v.get('tank') and not p['powers'].get('tank'))
        for key in ('barricade','corruption','tank','hellraiser'):
            if v.get(key):p['powers'][key]=1
        for key in ('freeSkill','drawNextTurn'):
            if v.get(key):damage.power(p,key,v[key])
        if v.get('shivs'):
            from .classes.silent import shivs
            shivs(s,p,v['shivs'])
        for key in ('crimsonMantle','inferno'):
            if v.get(key):p[key+'Loss']=p.get(key+'Loss',0)+1
        if first_tank:
            for teammate in s['players'].values():
                if teammate['id']!=p['id'] and teammate['hp']>0:
                    guardians=teammate.setdefault('guardians',[])
                    if p['id'] not in guardians:guardians.append(p['id'])
                    teammate['powers']['guarded']=len(guardians)
        if v.get('heal'):damage.heal(p,v['heal'])
        if v.get('outrage'):
            for teammate in s['players'].values():
                if teammate['hp']>0:
                    piles.add_generated(s,teammate,run_state.copy_card(s,c),'discard',creator=p)
        if v.get('setupStrike'):damage.power(p,'strength',v['setupStrike']);damage.power(p,'setupStrike',v['setupStrike'])
        if v.get('rampage'):c['bonusDamage']=c.get('bonusDamage',0)+v['rampage']
        if v.get('thrash'):
            attacks=[x for x in p['hand'] if definition(x)['kind']=='attack']
            if attacks:
                consumed=draws.combat_card_selection(s,attacks)
                c['bonusDamage']=c.get('bonusDamage',0)+damage.damage_amount(p,{'powers':{}},attack_base(p,consumed,state=s))
                piles.exhaust(s,p,consumed)
        if v.get('randomExhaust') and p['hand']:piles.exhaust(s,p,draws.combat_card_selection(s,p['hand']))
        if v.get('upgradeHand'):
            for x in candidates if c['upgraded'] else ([chosen] if chosen else []):run_state.upgrade(x)
        if chosen and (v.get('exhaustChoice') or v.get('trueGrit')):piles.exhaust(s,p,chosen)
        if v.get('trueGrit') and not c['upgraded'] and p['hand']:piles.exhaust(s,p,draws.combat_card_selection(s,p['hand']))
        if v.get('blockPerExhaust'):
            for x in [x for x in p['hand'] if definition(x)['kind']!='attack']:
                piles.exhaust(s,p,x);damage.gain_block(s,p,v['blockPerExhaust'])
        p['energy']+=v.get('energy',0)
        if v.get('draw') and (not v.get('impatience') or not any(definition(x)['kind']=='attack' for x in p['hand'])):piles.draw(s,p,v['draw'])
        if v.get('escapePlan'):
            drawn=piles.draw(s,p,1)
            if drawn and definition(drawn[0])['kind']=='skill':damage.gain_block(s,p,v['escapePlan'])
        if v.get('drawRetain'):
            for drawn in piles.draw(s,p,v['drawRetain']):drawn['retainThisTurn']=True
        if v.get('drawToFull'):piles.draw(s,p,10-len(p['hand']))
        if v.get('pillage'):
            while len(p['hand'])<10:
                drawn=piles.draw(s,p,1)
                if not drawn or definition(drawn[0])['kind']!='attack':break
        if v.get('primalForce'):
            from ..run.events.transforms import replace_in_pile
            for original in list(p['hand']):
                if definition(original)['kind']=='attack':
                    replace_in_pile(s,p,p['hand'],original,run_state.new_card(s,'GiantRock',c['upgraded']))
        if v.get('stoke'):
            from .effects import generated_cards
            snapshot=list(p['hand'])
            for consumed in snapshot:piles.exhaust(s,p,consumed)
            generated_batch=generated_cards(s,p.get('character','ironclad'),len(snapshot),replacement=True)
            for generated in generated_batch:generated['upgraded']=c['upgraded']
            for generated in generated_batch:piles.add_generated(s,p,generated)
        if v.get('jackOfAllTrades'):
            from .effects import generated_cards
            for generated in generated_cards(s,'colorless',v['jackOfAllTrades'],exclude=('JackOfAllTrades',)):piles.add_generated(s,p,generated)
        if v.get('infernalBlade'):
            from .effects import generated_cards
            for generated in generated_cards(s,p.get('character','ironclad'),1,kind='attack'):
                free_card(generated);piles.add_generated(s,p,generated)
        if v.get('noDraw'):damage.debuff(s,p,p,'noDraw',1,card_source=c)
        if v.get('copy'):piles.add_generated(s,p,run_state.copy_card(s,c),'discard')
        if v.get('franticEscape'):
            for e in s['enemies']:
                if e['hp']>0 and e.get('sandpits'):
                    if str(p['id']) in e['sandpits']:e['sandpits'][str(p['id'])]+=1
                    break
                if e['hp']>0 and e['powers'].get('sandpit') and e.get('sandpitTarget')==p['id']:
                    damage.power(e,'sandpit',1);break
            change_cost(c,1,mode='add')
        apply_card(s,p,c,targets,ally)
        from .classes.defect import apply_card as defect_apply_card
        defect_apply_card(s,p,c,targets,ally)
        from .classes.regent import apply_card as regent_apply_card
        regent_apply_card(s,p,c,targets,ally)
        from .classes.necrobinder import apply_card as necrobinder_apply_card
        necrobinder_apply_card(s,p,c,targets,ally)
        from .classes.silent import apply_card as silent_apply_card
        silent_apply_card(s,p,c,targets,ally)
        from .classes.special import apply_card as special_apply_card
        special_apply_card(s,p,c,targets)
    if any(v.get(key) for key in ('headbutt','seekerStrike','drawDiscard','discardOnly','scrape','uproar','copyColorless','photonCut','graveblast','grantKeyword')) and p['hp']>0 and any(e['hp']>0 for e in s['enemies']):
        from .effects import start
        start(s,p,c);return
    settle_card(s,p,c)
    after_card(s)

def clear_play_costs(card):
    expire_cost(card,'play')
    for key in ('untilPlayedCost','potionTurnCost','enlightenmentTurn'):card.pop(key,None)
    if card.pop('freeThisTurn',False):card['freeStarsThisTurn']=True

def settle_card(s,p,c,played=True):
    from .classes.colorless import after_card as colorless_after_card, result_pile
    d=definition(c);v=d['values']
    if played:
        if p['hp']<=0:return
        enchantment=c.get('enchantment',{})
        if enchantment.get('key')=='Momentum':enchantment['extraDamage']=enchantment.get('extraDamage',0)+enchantment['amount']
        if enchantment.get('key')=='Adroit':damage.gain_block(s,p,enchantment['amount'])
        if enchantment.get('key')=='Swift' and not enchantment.get('usedThisCombat'):
            enchantment['usedThisCombat']=True
            piles.draw(s,p,enchantment['amount'])
        if c.get('enchantment',{}).get('key')=='Corrupted':damage.hit(s,p,p,2,True,True,unblockable=True)
        if p['hp']<=0:return
        if p['hp']>0 and c.get('sown') and not c.get('sownUsed'):
            p['energy']+=c.get('enchantment',{}).get('amount',1);c['sownUsed']=True
        if d['kind']=='skill':
            from .classes.defect import combat_cards
            for candidate in combat_cards(s,p,c):
                if definition(candidate)['values'].get('pinpoint'):
                    change_cost(candidate,-1,mode='add',expires=('turn',))
        p['playsFinished']=p.get('playsFinished',0)+1
        if d['kind'] in ('attack','skill'):
            key='attacksFinished' if d['kind']=='attack' else 'skillsFinished';p[key]=p.get(key,0)+1
        colorless_after_card(s,p,c)
        clear_play_costs(c)
        from .classes.necrobinder import after_card as necrobinder_after_card
        necrobinder_after_card(s,p,c)
        for record in c.get('strangleDamage',[]):
            target=next((target for target in s['enemies'] if target['id']==record['target']),None)
            if target and target['hp']>0 and record['amount']:damage.hit(s,None,target,record['amount'],True,unblockable=True)
        from .classes.silent import after_card as silent_after_card
        silent_after_card(s,p,c)
        from .classes.boss import after_card as boss_after_card
        boss_after_card(s,p,c)
        from .classes.regent import after_card_late as regent_after_card_late
        regent_after_card_late(s,p,c)
        if d['kind']=='attack' and not c.get('isDupe'):
            p['lastAttackPlayed']={'turn':p.get('turnNumber',s['turn']),'card':deepcopy(c)}
        for e in s['enemies']:
            if e['powers'].get('slow'):e['slowCards']+=1
        if c.get('replaysLeft',0)>0 and p['hp']>0 and any(e['hp']>0 or e.get('awaitingRevive') for e in s['enemies']):
            from .effects import prepend
            c['replaysLeft']-=1;prepend(s,p,[{'op':'replay','card':c}]);return
    already_placed=played and any(c in p[pile] for pile in ('hand','draw','discard','exhaust'))
    p['inPlay']=[x for x in p.get('inPlay',[]) if x['id']!=c['id']]
    forced=c.pop('forceExhaust',False)
    if d['kind']!='power' and not c.get('isDupe') and not already_placed:
        if c.pop('feralReturn',False) and not forced:piles.add_to_hand(s,p,c)
        elif v.get('exhaust') or forced:piles.exhaust(s,p,c)
        else:result_pile(s,p,c)
    for key in ('capturedX','capturedStars','priorTargetHits','forgeAttackResults','replayTarget','replaysLeft','calamityCount','strangleDamage'):c.pop(key,None)
    for key in ('copiedDebuffs','attackDamage','resourceEnergyValue','afterimageBlock','serpentDamage'):c.pop(key,None)
    for key in ('stormOrbs','subroutineEnergy','imitationCopies','paidEnergy','feralReturn'):c.pop(key,None)
    c.pop('seriesStarsSpent',None)
    c.pop('monologueStrength',None)
    c.pop('monologueSnapshots',None)
    c.pop('manualSeries',None)
    c.pop('oblivionDoom',None);c.pop('lethalityPercent',None)
    p.pop('blockCard',None);p.pop('blockDefend',None);p.pop('blockPlay',None)

def check_empty_hand(s,player):
    if s.get('side')!='player' or 'UnceasingTop' not in player['relics'] or player.get('done'):return
    while player['hp']>0 and not player['hand'] and any(enemy['hp']>0 for enemy in s['enemies']):
        if not piles.draw(s,player,1):break

def after_card(s):
    if s['phase']!='combat':return
    from ..core.continuation import current
    runtime=current()
    if runtime and (not runtime.finalizing or runtime.depth):return
    if s.get('pendingChoice') or s.get('pendingDecision') or s.get('_effectsRunning'):return
    if any(p.get('pendingCardRewards') or p.get('pendingRelicRewards') for p in s['players'].values()):
        # Loot from a dead enemy remains private, but must not hold a cleared
        # battlefield in combat while another player is still claiming it.
        if not s.get('effects'):battle.finish_combat(s)
        return
    if s.get('effects'):
        from .effects import run
        run(s);return
    if battle.finish_combat(s):return
    if s.get('side')=='player':
        for player in s['players'].values():
            check_empty_hand(s,player)
        if battle.finish_combat(s):return
    for p in s['players'].values():
        if battle.finish_requested_turn(s,p):return
    battle.commit_ready_turn(s)
