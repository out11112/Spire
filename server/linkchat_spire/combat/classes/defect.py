from copy import deepcopy
from ... import engine as e
from .. import orbs

# ``OrbModel._validOrbs``. The order is the draw order, so it is part of the
# result and not a set to be tidied alphabetically.
ORBS = ['lightning', 'frost', 'dark', 'plasma', 'glass']


def roll_orb(state):
    """``OrbModel.GetRandomOrb`` — one draw from ``CombatOrbs``."""
    pool = list(ORBS)
    return e.run_rng(state, 'CombatOrbs', lambda rng: rng.next_item(pool))


def combat_cards(state,player,current=None):
    cards=[card for pile in ('hand','draw','discard','exhaust') for card in player[pile]]
    cards.extend(player.get('inPlay',[]))
    cards.extend(op['card'] for op in state.get('effects',[]) if op.get('owner')==player['id'] and 'card' in op)
    if current is not None:cards.append(current)
    seen=set();result=[]
    for card in cards:
        if id(card) not in seen:seen.add(id(card));result.append(card)
    return result


def apply_card(state,player,card,targets,ally=None):
    values=e.definition(card)['values']
    if values.get('focus'):e.power(player,'focus',values['focus'])
    if values.get('coolant'):e.power(player,'coolant',values['coolant'])
    for key in ('buffer','creativeAi','echoForm','hailstorm','iteration','lightningRod','loop','machineLearning','signalBoost','smokestack','storm','subroutine','thunder','trashToTreasure'):
        if values.get(key):e.power(player,key,values[key])
    if values.get('biasedCognition'):e.debuff(state,player,player,'biasedCognition',values['biasedCognition'],card_source=card)
    if values.get('feral'):
        if not player['powers'].get('feral'):player['feralUsed']=player.get('zeroEnergyAttacks',0)
        e.power(player,'feral',values['feral'])
    if ally:
        if values.get('allyChannel'):orbs.channel(state,ally,values['allyChannel'])
        if values.get('imitationLearning'):
            targets_by_id=player.setdefault('imitationTargets',{});key=str(ally['id'])
            targets_by_id[key]=targets_by_id.get(key,0)+values['imitationLearning']
            e.power(player,'imitationLearning',values['imitationLearning'])
    if values.get('oneForAll'):
        for teammate in state['players'].values():
            if teammate['hp']>0:e.power(teammate,'oneForAll',values['oneForAll'])
    if values.get('addOrbSlots'):orbs.change_capacity(player,values['addOrbSlots'])
    if values.get('doubleEnergy'):player['energy']*=2
    if values.get('allEnergy'):
        for ally in state['players'].values():
            if ally['hp']>0:ally['energy']+=values['allEnergy']
    if values.get('randomOrbs'):
        for _ in range(values['randomOrbs']):orbs.channel(state,player,roll_orb(state))
    if values.get('chill'):orbs.channel(state,player,'frost',sum(target['hp']>0 for target in state['enemies']))
    if values.get('rainbow'):
        for kind in ('lightning','frost','dark'):orbs.channel(state,player,kind)
    if values.get('tempest'):orbs.channel(state,player,'lightning',card['capturedX']+values.get('tempestBonus',0))
    if values.get('voltaic'):orbs.channel(state,player,'lightning',player.get('lightningChanneled',0))
    if values.get('multiCast') or values.get('evokeFirst'):
        count=values.get('evokeFirst',card['capturedX']+values.get('multiCastBonus',0))
        for index in range(count):orbs.evoke(state,player,dequeue=index==count-1)
    if values.get('hibernate'):
        e.power(player,'hibernate',1);orbs.channel(state,player,'frost',values['hibernate'])
    if values.get('spinner'):
        if values.get('spinnerChannel'):orbs.channel(state,player,'glass')
        e.power(player,'spinner',values['spinner'])
    if values.get('compact'):
        from ...run.events.transforms import replace_in_pile
        for original in list(player['hand']):
            if e.CARDS[original['key']]['kind']=='status' and e.removable(original):
                replace_in_pile(state,player,player['hand'],original,e.new_card(state,'Fuel',card['upgraded']))
    if values.get('geneticGrowth'):
        card['bonusBlock']=card.get('bonusBlock',0)+values['geneticGrowth']
        for original in player['deck']:
            if original['id']==card['id'] and original is not card:original['bonusBlock']=original.get('bonusBlock',0)+values['geneticGrowth']
    if values.get('moddedDraw'):
        e.draw(state,player,values['moddedDraw']);e.change_cost(card,1,mode='add')
    if values.get('reboot'):
        player['draw'].extend(player['hand']);player['hand']=[]
        e.shuffle_draw(state,player);e.draw(state,player,values['reboot'])
    if values.get('scavenge'):
        from ..effects import select_now
        select_now(state,player,{'op':'select','source':'hand','destination':'exhaust','minimum':1,'maximum':1,'title':'搜集：消耗一张手牌'})
        e.power(player,'energyNextTurn',values['scavenge'])
    if values.get('synchronize'):
        amount=values['synchronize']*len({orb['kind'] for orb in player.get('orbs',[])})
        if amount:e.power(player,'focus',amount);e.power(player,'synchronizeFocus',amount)
    if values.get('whiteNoise'):generate_power(state,player,free=True)
    if values.get('adaptiveStrike'):
        copy=e.copy_card(state,card);e.change_cost(copy,0);e.add_generated(state,player,copy,'discard')
    if values.get('zeroAfterPlay'):e.change_cost(card,0)
    if values.get('allForOne'):
        eligible=[]
        for candidate in player['discard']:
            definition=e.definition(candidate)
            if definition['kind'] in ('attack','skill','power') and not definition['values'].get('xCost') and e.energy_cost(state,player,candidate,clamp_zero=False)==0:
                eligible.append(candidate)
        for candidate in eligible:
            player['discard'].remove(candidate);e.add_to_hand(state,player,candidate)
    if values.get('claw'):
        for candidate in combat_cards(state,player,card):
            if candidate['key']=='Claw':candidate['bonusDamage']=candidate.get('bonusDamage',0)+values['claw']
    if values.get('compileDriver'):e.draw(state,player,len({orb['kind'] for orb in player.get('orbs',[])}))
    if values.get('ftl') and player.get('playsFinished',0)<values['ftl']:e.draw(state,player,1)
    for target in targets:
        if target['hp']>0 and values.get('attackIntentWeak') and 'damage' in target.get('intent',{}):e.debuff(state,player,target,'weak',values['attackIntentWeak'],card_source=card)
    if values.get('temporaryFocus'):
        amount=values['temporaryFocus']
        key={'Hotfix':'hotfixFocus','FocusedStrike':'focusedStrikeFocus','Hyperbeam':'hyperbeamFocusDown'}[card['key']]
        if amount<0:
            if e.debuff(state,player,player,key,-amount,card_source=card):e.power(player,'focus',amount)
        else:e.power(player,'focus',amount);e.power(player,key,amount)
    if values.get('freePower'):e.power(player,'freePower',values['freePower'])
    if values.get('generatedStatus'):
        for _ in range(values.get('statusCount',1)):e.add_generated(state,player,e.new_card(state,values['generatedStatus']),'discard')
    if values.get('channel'):orbs.channel(state,player,values['channel'],values.get('channelCount',1))
    if values.get('consumingShadow'):e.power(player,'consumingShadow',values['consumingShadow'])
    if values.get('drawAfterChannel'):e.draw(state,player,values['drawAfterChannel'])
    if values.get('darknessTriggers'):
        for orb in list(player.get('orbs',[])):
            if orb['kind']=='dark':
                for _ in range(values['darknessTriggers']):orbs.trigger(state,player,orb)
    if values.get('dualcast') and player.get('orbs'):
        orbs.evoke(state,player,dequeue=False);orbs.evoke(state,player)
    if values.get('shatter'):
        for _ in range(len(player.get('orbs',[]))):orbs.evoke(state,player,dequeue=False);orbs.evoke(state,player)
    if values.get('teslaCoil'):
        for orb in list(player.get('orbs',[])):
            if orb['kind']=='lightning':
                for _ in range(values['teslaCoil']):
                    for target in targets:orbs.trigger(state,player,orb,target=target)


def turn_start(state,player):
    if player['powers'].get('biasedCognition'):e.debuff(state,player,player,'focus',-player['powers']['biasedCognition'])
    if player['powers'].get('coolant'):
        count=len({orb['kind'] for orb in player.get('orbs',[])})
        e.gain_block(state,player,count*player['powers']['coolant'],True)


def generate_power(state,player,free=False):
    from ..effects import generated_cards
    for card in generated_cards(state,player.get('character','ironclad'),1,kind='power'):
        if free:e.free_card(card)
        e.add_generated(state,player,card)


def after_energy_reset(state,player):
    for key in list(player['powers']):
        if key=='lightningRod' and player['powers'].get(key):
            orbs.channel(state,player,'lightning');e.power(player,key,-1)
        elif key=='spinner':orbs.channel(state,player,'glass',player['powers'][key])


def before_draw(state,player):
    for _ in range(player['powers'].get('creativeAi',0)):generate_power(state,player)


def after_player_turn_start(state,player,power_key=None):
    # Shared hook listeners run in power acquisition order: Hibernate can
    # expire before Loop activates Frost, or remain active for that activation.
    for key in list(player['powers']):
        if power_key is not None and key!=power_key:continue
        if key=='loop':
            for _ in range(player['powers'].get(key,0)):
                if player.get('orbs'):orbs.trigger(state,player,player['orbs'][0])
        elif key=='hibernate' and player['powers'].get(key):e.power(player,key,-1)


def before_turn_end(state,player):
    if player['powers'].get('hailstorm') and any(orb['kind']=='frost' for orb in player.get('orbs',[])):
        for target in state['enemies']:
            if target['hp']>0:e.hit(state,player,target,player['powers']['hailstorm'],True)


def turn_end(state,player):
    for _ in range(player['powers'].get('consumingShadow',0)):orbs.evoke(state,player,last=True)


def on_draw(state,player,card):
    if e.CARDS[card['key']]['kind']=='status':
        player['statusDraws']=player.get('statusDraws',0)+1
        if player['statusDraws']==1 and player['powers'].get('iteration'):e.draw(state,player,player['powers']['iteration'])


def on_generated(state,creator,card,power_key=None):
    if e.CARDS[card['key']]['kind']!='status':return
    for key in ([power_key] if power_key else list(creator['powers'])):
        if key=='smokestack' and creator['powers'].get(key):
            for target in state['enemies']:
                if target['hp']>0:e.hit(state,creator,target,creator['powers'][key],True)
        elif key=='trashToTreasure':
            for _ in range(creator['powers'][key]):
                orbs.channel(state,creator,roll_orb(state))


def before_card(state,player,card,replay):
    kind=e.definition(card)['kind']
    card['stormOrbs']=player['powers'].get('storm',0) if kind=='power' else 0
    card['subroutineEnergy']=player['powers'].get('subroutine',0) if kind=='power' else 0
    card['imitationCopies']=[]
    if kind=='power' and not replay:
        for observer in state['players'].values():
            if observer['hp']>0 and observer.get('imitationTargets',{}).get(str(player['id']),0)>0:
                card['imitationCopies'].append({'owner':observer['id'],'card':e.copy_card(state,card)})


def after_card(state,player,card,observer=None):
    from ..effects import autoplay
    copies=card.get('imitationCopies',[])
    selected=[copy for copy in copies if observer is None or str(copy['owner'])==str(observer['id'])]
    card['imitationCopies']=[copy for copy in copies if copy not in selected]
    for copy in selected:
        observer=state['players'][str(copy['owner'])];key=str(player['id'])
        if observer.get('imitationTargets',{}).get(key,0)>0:
            observer['imitationTargets'][key]-=1;e.power(observer,'imitationLearning',-1)
            autoplay(state,observer,copy['card'])
