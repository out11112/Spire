"""Persisted ancient map replacements and combat markers."""
from .. import engine as e


def fur_coat_shuffle(state,player,items):
    """``Fur Coat``'s own stream: ``runSeed + seat + hash(FurCoat)``.

    Not one of the fifteen and not the player's: the reference builds a fresh
    ``Rng`` per player per relic, so two relics doing this would not share.
    """
    from ..rng import streams
    items=list(items)
    return e.derived_rng(state,'FurCoat',[streams.seat_of(player)],lambda rng:rng.shuffle(items))


def mark_fur(state,player):
    from ..run.map.journey import current_act
    act=current_act(state);index=state['journey']['index']
    if player.get('furCoatAct')!=index:return
    nodes=act['map']['nodes'];saved=player.get('furCoatNodes')
    if saved is None or any(i not in nodes or nodes[i]['kind'] not in ('battle','elite') for i in saved):
        eligible=[n['id'] for n in nodes.values() if n['kind'] in ('battle','elite') and not n.get('furCoats')]
        saved=fur_coat_shuffle(state,player,eligible)[:8];player['furCoatNodes']=saved
    for ident in saved:
        owners=nodes[ident].setdefault('furCoats',[])
        if player['id'] not in owners:owners.append(player['id'])


def obtained(state,player,key):
    if key not in ('GoldenCompass','FurCoat'):return
    from ..run.map.journey import current_act
    e.require('journey' in state,'地图遗物需要三幕地图状态。')
    act=current_act(state);index=state['journey']['index']
    if key=='FurCoat':
        player['furCoatAct']=index;mark_fur(state,player);return
    player['goldenCompassAct']=index
    from ..run.map.maps import golden_path
    previous_row=act['map']['nodes'][act['current']]['row'] if act['current'] else None
    act['map']=golden_path(state,act['key'])
    from ..run.map.quests import bind_spoils
    bind_spoils(state,act['map'],index)
    if previous_row is not None:
        rows=act['map']['rooms']+1
        act['current']=f'{index}:{min(previous_row,rows)}:3'
    for owner in state['players'].values():
        owner['vote']=None
        if 'FurCoat' in owner['relics']:mark_fur(state,owner)


def creature_added(state,enemy):
    if 'journey' not in state:return
    from ..run.map.journey import current_act
    index=state['journey']['index'];ident=current_act(state)['current']
    if any('FurCoat' in p['relics'] and p.get('furCoatAct')==index and ident in p.get('furCoatNodes',[]) for p in state['players'].values()):enemy['hp']=1
