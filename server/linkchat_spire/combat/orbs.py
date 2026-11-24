"""Serializable orb slots and passive/evoke effects, including non-Defect owners."""
from .. import engine as e

IDENTITIES={'DarkOrb':'dark','FrostOrb':'frost','GlassOrb':'glass','LightningOrb':'lightning','PlasmaOrb':'plasma'}


def value(player,base):return max(0,base+player['powers'].get('focus',0))


def change_capacity(player,amount):
    player['orbCapacity']=min(10,max(0,player.get('orbCapacity',0)+amount))
    # Removing slots drops the newest orbs without evoking them.
    del player.setdefault('orbs',[])[player['orbCapacity']:]


def channel(state,player,kind,count=1):
    e.require(kind in IDENTITIES.values(),'未知充能球。')
    for _ in range(count):
        if player['hp']<=0 or not any(target['hp']>0 for target in state['enemies']):return
        # Ironclad has no initial slots; original cross-character channeling
        # grants one slot, not Defect's starting three slots.
        if not player.get('orbCapacity'):
            if player.get('character','ironclad')=='defect':return
            player['orbCapacity']=1
        queue=player.setdefault('orbs',[])
        if len(queue)>=player['orbCapacity']:evoke(state,player)
        state['serial']+=1
        queue.append({'id':str(state['serial']),'kind':kind,'charge':6 if kind=='dark' else 4 if kind=='glass' else 0})
        if kind=='lightning':player['lightningChanneled']=player.get('lightningChanneled',0)+1
        if 'Metronome' in player['relics']:
            player['metronomeOrbs']=player.get('metronomeOrbs',0)+1
            if player['metronomeOrbs']==7:
                for enemy in list(state['enemies']):
                    if enemy['hp']>0:e.hit(state,player,enemy,30,True)


def trigger(state,player,orb,*,evoked=False,target=None,count_affected_by_hooks=False):
    count=1+int(count_affected_by_hooks and not evoked and 'GoldPlatedCables' in player['relics'] and bool(player.get('orbs')) and player['orbs'][0] is orb)
    for _ in range(count):_trigger_once(state,player,orb,evoked=evoked,target=target)


def _trigger_once(state,player,orb,*,evoked=False,target=None):
    if player['hp']<=0:return
    kind=orb['kind'];enemies=[target for target in state['enemies'] if target['hp']>0]
    if kind=='plasma':player['energy']+=2 if evoked else 1;return
    if kind=='frost':
        amount=value(player,5 if evoked else 2);e.gain_block(state,player,amount,True)
        if player['powers'].get('hibernate'):
            for ally in state['players'].values():
                if ally['id']!=player['id']:e.gain_block(state,ally,amount,True)
        return
    if kind=='dark' and not evoked:orb['charge']+=value(player,6);return
    if not enemies:return
    if kind=='dark':targets=[min(enemies,key=lambda enemy:enemy['hp'])];amount=orb['charge']
    elif kind=='lightning':
        targets=[target] if target is not None else [e.random_enemy(state,enemies)]
        amount=value(player,8 if evoked else 3)
        if 'InfusedCore' in player['relics']:amount+=1
    else:
        e.require(kind=='glass','未知充能球。')
        targets=enemies;amount=value(player,orb['charge'])*(2 if evoked else 1)
        if amount and not evoked:orb['charge']=max(0,orb['charge']-1)
    for enemy in targets:
        if enemy['hp']>0:e.hit(state,player,enemy,amount,True)
    if evoked and kind=='lightning' and player['powers'].get('thunder'):
        for enemy in targets:
            if enemy['hp']>0:e.hit(state,player,enemy,player['powers']['thunder'],True)


def evoke(state,player,*,dequeue=True,last=False):
    queue=player.get('orbs',[])
    if queue:
        index=-1 if last else 0
        orb=queue.pop(index) if dequeue else queue[index]
        trigger(state,player,orb,evoked=True)


def turn_start(state,player):
    for orb in list(player.get('orbs',[])):
        if orb['kind']=='plasma':trigger(state,player,orb,count_affected_by_hooks=True)


def turn_end(state,player):
    for orb in list(player.get('orbs',[])):
        if orb['kind']!='plasma':trigger(state,player,orb,count_affected_by_hooks=True)


def view(player):
    names={'lightning':'闪电','frost':'冰霜','dark':'黑暗','plasma':'等离子','glass':'玻璃'}
    return [{**orb,'name':names[orb['kind']]} for orb in player.get('orbs',[])]
