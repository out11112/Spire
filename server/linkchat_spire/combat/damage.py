"""Block, damage, health and powers."""
from ..text import battle_log
from decimal import Decimal
from ..content import CARDS, definition
from ..core.errors import require
from . import battle
from . import piles
from ..core import state as run_state
from ..rng import draws

TEMPORARY_STRENGTH_LOSS=('darkShackles','mangle','temporaryStrengthDown','crushUnder','dyingStar','enfeeblingTouch','piercingWail','monarchsGazeDown','shacklingPotion')

def heal(p,n):
    p['hp']=min(p['maxHp'],p['hp']+int(n))
    from ..relics.hooks import hp_changed
    hp_changed(p)

def power(p,key,n):
    from .power_order import PLAYED_SINGLE_POWERS, played_instance_order
    if key in PLAYED_SINGLE_POWERS:
        played_instance_order(p)
        if not p['powers'].get(key):p['powers'].pop(key,None)
    if key in ('pagestorm','cacophony'):
        from .power_order import necrobinder_draw_order
        necrobinder_draw_order(p)
        if not p['powers'].get(key):p['powers'].pop(key,None)
    from .power_order import DRAW_COUNT_POWERS, CARD_COST_POWERS, ENERGY_MODIFIER_POWERS, CARD_LOCATION_POWERS
    if key in DRAW_COUNT_POWERS|CARD_COST_POWERS|ENERGY_MODIFIER_POWERS|CARD_LOCATION_POWERS and not p['powers'].get(key):p['powers'].pop(key,None)
    from .power_order import PLAYER_START_POWERS, player_start_order
    if key in PLAYER_START_POWERS:player_start_order(p)
    if key in PLAYER_START_POWERS and not p['powers'].get(key):
        p['powers'].pop(key,None)
        if key=='summonNextTurn':p['summonDueAtStart']=False
    from .power_order import CLEANUP_POWERS, cleanup_order
    if key in CLEANUP_POWERS:cleanup_order(p)
    from .power_order import HAND_DRAW_POWERS, hand_draw_order
    if key in HAND_DRAW_POWERS:hand_draw_order(p)
    if key=='swordSage':
        from .classes.regent import sword_sage_changed
        sword_sage_changed(p,n)
    if key in ('hailstorm','bomb','chainsOfBinding'):
        from .power_order import side_end_order
        side_end_order(p)
    if key=='vigor' and (not p['powers'].get(key) or p['powers'].get(key,0)+n<=0):p.pop('vigorAttack',None)
    if key=='darkEmbrace' and (not p['powers'].get(key) or p['powers'].get(key,0)+n<=0):p.pop('darkEmbraceEthereal',None)
    if key=='rupture' and (not p['powers'].get(key) or p['powers'].get(key,0)+n<=0):p.pop('ruptureCards',None)
    if key=='paleBlueDot' and (not p['powers'].get(key) or p['powers'].get(key,0)+n<=0):p.pop('paleBlueDotTriggered',None)
    if key=='helloWorld' and not p['powers'].get(key):p['helloWorldAtTurnStart']=0
    if key in ('darkEmbrace','noDraw','hibernate','lightningRod') and not p['powers'].get(key):p['powers'].pop(key,None)
    context=p.get('relicCombat')
    if context is not None and key=='strength' and n>0 and 'RuinedHelmet' in p.get('relics',[]) and not context.get('helmetUsed'):
        n*=2;context['helmetUsed']=True
    p['powers'][key]=p['powers'].get(key,0)+n
    if key in PLAYER_START_POWERS:player_start_order(p)
    if key in CLEANUP_POWERS:cleanup_order(p)
    if key in HAND_DRAW_POWERS:hand_draw_order(p)
    if key in ('hailstorm','bomb','chainsOfBinding'):side_end_order(p)

def block_amount(p,n,unpowered=False,source=None,multiplier=1):
    source=source or p
    if not unpowered and p['powers'].get('noBlock') and source.get('blockCard'):return 0
    amount=max(0,n+(0 if unpowered else source['powers'].get('dexterity',0)))
    if not unpowered and p['powers'].get('frail'):amount=Decimal(str(amount))*Decimal('.75')
    return amount*multiplier*(2**p['powers'].get('shadowmeld',0))

def block(p,n,unpowered=False,source=None,multiplier=1):
    amount=int(block_amount(p,n,unpowered,source,multiplier));before=p['block']
    p['block']=min(999999999,p['block']+amount)
    return p['block']-before

def gain_block(s,p,n,unpowered=False,source=None,beacon_chain=(),card_source=False):
    if p['hp']<=0:return 0
    source=source or p;card_id=source.get('blockCard');multiplier=1
    vambrace=not unpowered and card_id and 'Vambrace' in source.get('relics',[]) and not source.get('vambraceUsed') and source.get('vambraceCard',card_id)==card_id
    if vambrace:multiplier*=2
    legion=not unpowered and card_id and 'PaelsLegion' in source.get('relics',[]) and source.get('paelsLegionCooldown',0)<=0
    if legion:multiplier*=2
    if card_id and (not unpowered or card_source):
        from .classes.defect import combat_cards
        card=next((card for card in combat_cards(s,source) if card['id']==card_id),None)
        if card and card.get('enchantment',{}).get('key')=='Nimble':n+=card['enchantment']['amount']
        if card and card.get('enchantment',{}).get('key')=='Goopy':n+=card['enchantment']['amount']-1
        if not unpowered and card and definition(card)['values'].get('minion') and 'VitruvianMinion' in source['relics']:multiplier*=2
    if not unpowered and (not card_id or source.get('blockDefend')):n+=p['powers'].get('fasten',0)
    if not unpowered and card_id and source['powers'].get('unmovable'):
        previous=sum(ident!=source.get('blockPlay') for ident in source.get('blockEvents',[]))
        if previous<source['powers']['unmovable']:multiplier*=2
    if not unpowered and any(m is p for m in s['enemies']):
        from .monsters import scaling
        count=len(s['players']);multiplier*=count*(1 if count<=2 else scaling(s))
    modified_amount=block_amount(p,n,unpowered,source,multiplier)
    gained=block(p,n,unpowered,source,multiplier)
    if gained:
        if legion and not source.get('paelsLegionCard'):source['paelsLegionCard']=card_id
        if vambrace:source['vambraceCard']=card_id
        if not unpowered and card_id:source.setdefault('blockEvents',[]).append(source.get('blockPlay'))
        targets=[x for x in s['enemies'] if x['hp']>0]
        if p['powers'].get('juggernaut') and targets:
            hit(s,p,draws.random_enemy(s,targets),p['powers']['juggernaut'],True)
    if p['powers'].get('beaconOfHope') and s.get('side','player')=='player' and p['id'] not in beacon_chain and modified_amount>=2:
        for ally in s['players'].values():
            if ally['id']!=p['id'] and ally['hp']>0:gain_block(s,ally,Decimal(modified_amount)/2,True,beacon_chain=beacon_chain+(p['id'],))
    return gained

def begin_vigor_attack(actor,card=None):
    # The reference keeps its command binding for this power instance's lifetime,
    # including when stacks gained mid-attack leave a nonzero remainder.
    if not actor or actor['hp']<=0 or not actor['powers'].get('vigor') or actor.get('vigorAttack'):return None
    binding={'card':card['id'] if card else None,'key':card['key'] if card else None,'amount':actor['powers']['vigor']}
    actor['vigorAttack']=binding
    return binding

def finish_vigor_attack(actor,binding):
    if binding is not None and actor.get('vigorAttack') is binding:
        power(actor,'vigor',-binding['amount'])
        if not actor['powers'].get('vigor'):actor['powers'].pop('vigor',None)

def damage_amount(actor,target,n,*,card_key=None,controller=None,lethality=0,card_instance=None):
    if actor.get('key')=='TheForgotten':n+=actor['powers'].get('dexterity',0)
    if actor.get('owner') and controller:n+=controller['powers'].get('calcify',0)
    vigor=actor['powers'].get('vigor',0);binding=actor.get('vigorAttack')
    if binding and ((card_instance and card_instance['id']!=binding['card']) or (card_key and card_key!=binding['key'])):vigor=0
    amount=Decimal(max(0,n+actor['powers'].get('strength',0)+vigor+target['powers'].get('tainted',0)))
    owner=controller or actor
    if card_instance and 'PenNib' in owner.get('relics',[]) and owner.get('penNibCard')==card_instance['id']:amount*=2
    if actor['powers'].get('weak'):
        weak=Decimal('.75')
        if 'PaperKrane' in target.get('relics',[]):weak-=Decimal('.15')
        if actor['powers'].get('debilitate'):weak-=1-weak
        amount*=weak
    if actor['powers'].get('shrink'):amount*=Decimal('.7')
    from .classes.boss import back_attack
    if back_attack(actor,target):amount*=Decimal('1.5')
    if target['powers'].get('vulnerable'):
        cruelty=actor['powers'].get('cruelty',0) if target is not actor else 0
        if not cruelty and actor.get('owner') and controller and target is not controller:cruelty=controller['powers'].get('cruelty',0)
        multiplier=Decimal('1.5')+Decimal(cruelty)/100
        if 'PaperPhrog' in actor.get('relics',[]) and actor is not target:multiplier+=Decimal('.25')
        amount*=multiplier+(multiplier-1 if target['powers'].get('debilitate') else 0)
    if target['powers'].get('colossus') and actor['powers'].get('vulnerable'):amount*=Decimal('.5')
    if target['powers'].get('tank'):amount*=Decimal('1.5')
    if target['powers'].get('soar'):amount*=Decimal('.5')
    if actor is not target and 'UndyingSigil' in target.get('relics',[]) and actor['hp']<=actor['powers'].get('doom',0):amount*=Decimal('.5')
    if target['powers'].get('flutter'):amount*=Decimal('.5')
    if target['powers'].get('guarded'):amount*=Decimal('.5')**target['powers']['guarded']
    if target['powers'].get('covered'):amount=Decimal(0)
    if target['powers'].get('intercept'):amount*=1+target['powers']['intercept']
    for effect in target.get('knockdownInstances',[]):
        if effect['owner']!=actor.get('id'):amount*=effect['multiplier']
    if target['powers'].get('slow'):amount*=1+Decimal(target.get('slowCards',0))/10
    if card_key=='Hang' and target['powers'].get('hang'):amount*=target['powers']['hang']
    if card_key=='SovereignBlade' and target['powers'].get('conqueror'):amount*=2
    controller=controller or actor
    if card_key and CARDS[card_key]['values'].get('minion') and 'VitruvianMinion' in controller.get('relics',[]):amount*=2
    if card_key and controller.get('gigantificationCard')==card_key:amount*=3
    if card_key and target['powers'].get('weak'):amount*=1+Decimal(controller['powers'].get('tracking',0))/100
    if card_key and controller['powers'].get('doubleDamage'):amount*=2
    if lethality:amount*=1+Decimal(lethality)/100
    for record in target.get('flankingInstances',[]):
        if record['owner']!=actor.get('id'):amount*=record['amount']
    amount=min(1,int(amount)) if target['powers'].get('intangible') else int(amount)
    return min(amount,target['powers']['hardToKill']) if 'hardToKill' in target['powers'] else amount

def block_broken(s,target,breaker):
    if target['powers'].get('burrowed') and target.get('key')=='Tunneler':
        target['powers'].pop('burrowed');target['move']=3;target['block']=0;battle.intent(s,target)
    if str(target['id']) not in s['players'] and breaker and 'HandDrill' in breaker.get('relics',[]):
        debuff(s,breaker,target,'vulnerable',2)

def hit(s,actor,target,n,unpowered=False,card_source=False,unblockable=False,card_key=None,lethality=0,result=None,card_instance=None):
    require(actor is not None or unpowered,'无来源伤害必须是不受攻击加成的伤害。')
    if target['hp']<=0:return
    hp_before=target['hp'];protected=0
    amount=max(0,int(n)) if unpowered else damage_amount(actor,target,n,card_key=card_key,controller=s['players'].get(str(actor.get('owner')),actor),lethality=lethality,card_instance=card_instance)
    if unpowered:
        from .classes.boss import back_attack
        if actor is not None and back_attack(actor,target):amount=int(Decimal(amount)*Decimal('1.5'))
    if target['powers'].get('intangible'):amount=min(1,amount)
    if 'hardToKill' in target['powers']:amount=min(amount,target['powers']['hardToKill'])
    # Player `thorns` is FlameBarrier; permanent/player and enemy Thorns
    # react before damage, while FlameBarrier reacts after damage.
    player_target=str(target['id']) in s['players']
    thorns=target['powers'].get('permanentThorns',0)+(0 if player_target else target['powers'].get('thorns',0))
    if actor is not None and thorns and (not unpowered or card_instance is not None and card_instance['key']=='Omnislice'):
        hit(s,target,actor,thorns,True)
    block_owner=s['players'].get(str(target.get('owner')),target)
    absorbed=0 if unblockable else min(block_owner['block'],amount);block_owner['block']-=absorbed;lost=amount-absorbed
    if target['powers'].get('hardenedShell'):lost=min(lost,max(0,target['powers']['hardenedShell']-target.get('shellDamage',0)))
    pet=target.get('osty')
    if lost and not unpowered and pet and pet['hp']>0:
        from .classes.necrobinder import osty_hp_lost
        protected=min(pet['hp'],lost);osty_hp_lost(s,target,protected);lost-=protected
        run_state.log(s,f"{pet['name']} 承受 {protected} 伤害")
    if lost and target['powers'].get('slippery'):
        lost=1
    if lost and target['powers'].get('buffer'):lost=0;power(target,'buffer',-1)
    dealer=s['players'].get(str(actor.get('owner')),actor) if actor is not None else None
    from ..relics.hooks import modify_hp_loss
    # The reference runs the after-Osty pass (Tungsten Rod, Beating Remnant)
    # before the late pass, so the Boot floors whatever is left after them.
    lost=modify_hp_loss(target,lost,in_combat=s.get('phase')=='combat')
    if not unpowered and target is not dealer and 'TheBoot' in dealer.get('relics',[]) and 0<lost<5:lost=5
    if target.get('owner') and s['players'].get(str(target['owner']),{}).get('osty') is target:
        from .classes.necrobinder import osty_hp_lost
        osty_hp_lost(s,s['players'][str(target['owner'])],lost)
    else:target['hp']=max(0,target['hp']-lost)
    battle_log.emit(s,f"{target['name']} 受到 {amount} 伤害 · 格挡吸收 {absorbed} · 实际失去 {max(0,hp_before-target['hp'])} 生命",'damage',actor=actor.get('id') if actor else None,target=target['id'],amount=amount,absorbed=absorbed,hpLoss=max(0,hp_before-target['hp']))
    if target['powers'].get('hardenedShell'):target['shellDamage']=target.get('shellDamage',0)+max(0,hp_before-target['hp'])
    if target['hp']<hp_before and target['powers'].get('slippery'):power(target,'slippery',-1)
    if lost and not unpowered and target['hp']>0 and target['powers'].get('flutter'):
        power(target,'flutter',-1)
        if not target['powers']['flutter']:
            target['powers'].pop('flutter');target['stunned']=True
            if target.get('key')=='ThievingHopper':target['move']=min(4,target['move']+1)
            battle.intent(s,target)
    if target['hp']<hp_before and target['powers'].get('slumber'):
        power(target,'slumber',-1)
        if not target['powers']['slumber']:
            target['powers'].pop('slumber')
            # Waking early costs the beetle its plating as well.
            target['powers'].pop('plating',None)
            if target['hp']>0 and target.get('key')=='SlumberingBeetle':target['move']=2;battle.intent(s,target)
    if target['hp']<hp_before and 'shriek' in target['powers'] and target['hp']<=target['powers']['shriek']:
        target['powers'].pop('shriek')
        if target['hp']>0 and target.get('key')=='TerrorEel':target['move']=2;battle.intent(s,target)
    if target['hp']<hp_before and target['powers'].get('asleep'):
        target['powers'].pop('asleep');target['powers'].pop('plating',None)
        if target['hp']>0 and target.get('key')=='LagavulinMatriarch':target['move']=5;battle.intent(s,target)
    if target['hp']<hp_before and target['powers'].get('plow') and target['hp']<=target['powers']['plow']:
        for key in ('strength',)+TEMPORARY_STRENGTH_LOSS:target['powers'].pop(key,None)
        target['powers'].pop('plow')
        if target['hp']>0 and target.get('key')=='CeremonialBeast':
            target['secondPhase']=True;target['move']=2;battle.intent(s,target)
    if result is not None:result.update(unblocked=max(0,hp_before-target['hp'])+protected,receiverHpLost=max(0,hp_before-target['hp']))
    fully_blocked=not unblockable and (absorbed>0 or block_owner['block']>0) and lost+protected==0
    if actor is not None and actor['powers'].get('imbalanced') and fully_blocked:
        if actor.get('key')=='BowlbugRock':actor['offBalance']=True
        else:actor['stunned']=True
    if not fully_blocked and 'EmotionChip' in target.get('relics',[]):target['emotionChipDamaged']=True
    if lost>0 and not unblockable and str(target['id']) in s['players'] and 'LavaLamp' in target.get('relics',[]):target['lavaLampDamaged']=True
    if absorbed and block_owner['block']==0:block_broken(s,target,dealer)
    if not unpowered and str(actor['id']) in s['players'] and str(target['id']) not in s['players']:
        record=target.setdefault('attackedBy',{});record[str(actor['id'])]=record.get(str(actor['id']),0)+1
    if lost and not unpowered and target['powers'].pop('theGambit',0):target['hp']=0
    if lost and str(target['id']) in s['players']:hp_lost(s,target,max(0,hp_before-target['hp']),card_source)
    if lost and not unpowered and actor['hp']>0 and str(target['id']) in s['players'] and actor['powers'].get('paperCuts'):
        lose_max_hp(s,target,actor['powers']['paperCuts'])

    if lost and not unpowered and target['hp']>0:
        for key in ('envenom','concoct'):
            if actor['powers'].get(key):debuff(s,actor,target,'poison',actor['powers'][key])
    if not unpowered and card_instance is not None and target['powers'].get('curlUp'):
        target.setdefault('curlCard',card_instance['id'])
    flame_barrier=target['powers'].get('thorns',0) if player_target else 0
    if not unpowered and flame_barrier and actor['hp']>0:
        hit(s,target,actor,flame_barrier,True)
    if not unpowered and absorbed and target['powers'].get('reflect') and actor['hp']>0:
        hit(s,target,actor,absorbed,True)
    if not unpowered and actor['powers'].get('monarchsGaze') and target['hp']>0:
        amount=actor['powers']['monarchsGaze']
        if debuff(s,actor,target,'monarchsGazeDown',amount):power(target,'strength',-amount)
    from .classes.necrobinder import after_attack_damage, on_death
    if not unpowered:after_attack_damage(s,actor,target,absorbed+lost)
    if not unpowered and target['powers'].get('personalHive'):
        owner=s['players'].get(str(actor.get('owner',actor['id'])))
        if owner:
            for _ in range(target['powers']['personalHive']):piles.add_generated(s,owner,run_state.new_card(s,'Dazed'),'draw',creator=target,random_position=True)
    if target['hp']<=0:on_death(s,target)
    if actor is not None and actor.get('owner') and target.get('sicEmInstances'):
        from .osty import summon
        from .classes.necrobinder import first_applier_records
        for record in first_applier_records(target,'sicEmInstances'):
            if record['owner']==actor['owner']:summon(s,s['players'][str(actor['owner'])],record['amount'])
    return absorbed+lost

def hp_lost(s,p,n,card_source=False):
    if n<=0:return
    if s.get('phase')=='combat' and 'BeatingRemnant' in p.get('relics',[]):p['beatingRemnantLoss']=p.get('beatingRemnantLoss',0)+n
    from ..relics.hooks import after_damage_received, hp_changed
    hp_changed(p)
    after_damage_received(s,p,n)
    p['hpLossCount']=p.get('hpLossCount',0)+1;p['hpLostThisTurn']=True
    if p['hp']<=0:
        from ..run.potions import prevent_death
        prevent_death(s,p)
    if p['hp']<=0:
        from .classes.necrobinder import on_death
        on_death(s,p)
        return
    if s.get('phase')=='combat' and s.get('side','player')=='player' and p['powers'].get('rupture'):
        source=p.get('inPlay',[])[-1] if card_source and p.get('inPlay') else None
        pending=p.get('ruptureCards',{})
        if source and source['id'] in pending:pending[source['id']]+=p['powers']['rupture']
        else:power(p,'strength',p['powers']['rupture'])
    if p['powers'].get('inferno') and s.get('side','player')=='player':
        for target in list(s['enemies']):
            if target['hp']>0:hit(s,p,target,p['powers']['inferno'],True)

def lose_hp(s,p,n,card_source=False):
    attempted=n>0
    if s.get('phase')=='combat' and p['powers'].get('intangible') and n>0:n=1
    if s.get('phase')=='combat' and p['powers'].get('buffer') and n>0:power(p,'buffer',-1);n=0
    from ..relics.hooks import modify_hp_loss
    n=modify_hp_loss(p,n,in_combat=s.get('phase')=='combat')
    before=p['hp'];p['hp']=max(0,p['hp']-n)
    if attempted and 'EmotionChip' in p.get('relics',[]):p['emotionChipDamaged']=True
    hp_lost(s,p,before-p['hp'],card_source)

def lose_max_hp(s,p,n,card_source=False):
    require(n>=0,'最大生命损失不能为负数。')
    maximum=p['maxHp']-n
    if p['hp']>maximum:lose_hp(s,p,p['hp']-maximum,card_source)
    p['maxHp']=max(1,maximum);p['hp']=min(p['hp'],p['maxHp'])
    from ..relics.hooks import hp_changed
    hp_changed(p)

def applied_debuff(card,target,key,default):
    return card.get('appliedDebuffs',{}).get(str(target['id']),{}).get(key,default)

def debuff(s,actor,target,key,n,*,card_source=None):
    if key=='poison' and n>0 and 'SneckoSkull' in actor.get('relics',[]):n+=1
    if target['hp']<=0 or n<=0 and not (key=='shrink' and n==-1 or key in ('strength','dexterity','focus') and n<0):return False
    if key=='dampen' and target['powers'].get('dampen'):
        if actor['id'] not in target['dampenCasters']:target['dampenCasters'].append(actor['id'])
        return True
    if key in ('hex','ringing','smoggy') and target['powers'].get(key):return False
    if target['powers'].get('artifact'):
        battle_log.emit(s,f"{target['name']} 的人工制品抵消 {key} {n}",'debuffBlocked',actor=actor['id'],target=target['id'],power=key,amount=n,reason='artifact')
        power(target,'artifact',-1);return False
    battle_log.emit(s,f"{actor['name']} 向 {target['name']} 施加 {key} {n}",'debuff',actor=actor['id'],target=target['id'],power=key,amount=n)
    original=n
    first_application=not target['powers'].get(key)
    if (card_source is not None and 'UnsettlingLamp' in actor.get('relics',[])
            and target in s['enemies'] and not actor.get('unsettlingLampUsed')):
        actor.setdefault('unsettlingLampCard',card_source['id'])
    if card_source is not None and not (key=='shrink' and n==-1):
        for owner in s['players'].values():
            if ('UnsettlingLamp' in owner.get('relics',[]) and not owner.get('unsettlingLampUsed')
                    and owner.get('unsettlingLampCard')==card_source['id']):n*=2
    if card_source is not None:
        card_source.setdefault('appliedDebuffs',{}).setdefault(str(target['id']),{})[key]=n
    # Temporary stat-loss wrappers own the restoration amount. Their callers
    # subtract the original amount; account for only the additional loss here.
    if key in TEMPORARY_STRENGTH_LOSS and n!=original:
        power(target,'strength',original-n)
    if key=='hyperbeamFocusDown' and n!=original:power(target,'focus',original-n)
    if str(target['id']) in s['players'] and key in ('weak','vulnerable','frail') and not target['powers'].get(key):
        target.setdefault('skipDurationTicks',[]).append(key)
    if key=='shrink':
        if first_application:target['powers']['shrink']=n
        elif target['powers'].get('shrink',0)>=0:power(target,key,n)
        if first_application:target['shrinkSource']=actor['id']
    else:power(target,key,n)
    possess={'strength':'possessStrength','dexterity':'possessSpeed'}.get(key)
    if possess and n<0 and actor['powers'].get(possess) and str(target['id']) in s['players']:
        records=actor.setdefault('possessedStats',{}).setdefault(str(target['id']),{})
        records[key]=records.get(key,0)-n
    target.setdefault('debuffKeys',{})[key]=key in TEMPORARY_STRENGTH_LOSS or key=='hyperbeamFocusDown'
    if first_application and key in ('tangled','ringing') and str(target['id']) in s['players']:
        from .afflictions import power_applied
        power_applied(s,target,key)
    if key in ('hex','dampen') and str(target['id']) in s['players']:
        from .afflictions import caster_power_applied
        caster_power_applied(s,target,key,actor)
    if first_application and key=='tender':target['tenderSource']=actor['id']
    if first_application and key=='constrict':target['constrictSource']=actor['id']
    if key=='doom':actor['doomAppliedThisTurn']=True
    from .classes.necrobinder import on_debuff
    on_debuff(s,actor,target,key,temporary=key in TEMPORARY_STRENGTH_LOSS or key=='hyperbeamFocusDown')
    if key=='vulnerable' and actor['powers'].get('vicious'):piles.draw(s,actor,actor['powers']['vicious'])
    return True
