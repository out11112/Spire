"""Saved three-act navigation and room schedules, independent of combat effects.

Only room identity is chosen here. Handlers must implement that identity; callers
must not substitute an unrelated encounter/event when content is unavailable.
"""
from . import run_setup
from ...rng import streams
from .maps import act_sequence, generate_map, reachable
from ..rewards.odds import reset_unknown, unknown_room
from ...content.data import load as load_data

WORLD = load_data('world_data.json')
ACT_NAMES = {'Overgrowth':'密林', 'Underdocks':'暗港', 'Hive':'巢穴', 'Glory':'荣耀'}
SHARED_ANCIENTS = ['Darv']


def initialize(state, multiplayer):
    """Generate once after the lobby is locked; never called by projections.

    Everything here comes off the single ``UpFront`` stream in the reference's
    order: the shared-ancient split first, then each act's events, weak and
    regular encounters, elites, boss and ancient, act by act. The maps are
    drawn from their own per-act streams while this block is held open.
    """
    if 'journey' in state:return
    from ..events.events import DISABLED
    acts=act_sequence(state);records=[]
    with streams.open(state) as rngs:
        up_front=rngs.run('UpFront')
        shared=run_setup.split_shared_ancients(up_front,SHARED_ANCIENTS,len(acts))
        for index,key in enumerate(acts):
            scheduled=run_setup.generate_act_rooms(
                up_front,key,multiplayer,shared[index-1] if index else [],DISABLED)
            if index==2 and state.get('ascension',0)>=10:
                scheduled['secondBoss']=up_front.next_item([boss for boss in run_setup.act_pools(key)['boss'] if boss!=scheduled['boss']])
            spoils=any(c['key']=='SpoilsMap' and c.get('spoilsActIndex',1)==index for p in state.get('players',{}).values() for c in p.get('deck',[]))
            records.append({'key':key,'map':generate_map(state,key,multiplayer,spoils=spoils),
                            'normal':scheduled['normal'],'elite':scheduled['elite'],
                            'boss':scheduled['boss'],'secondBoss':scheduled.get('secondBoss'),'ancient':scheduled['ancient'],
                            'events':scheduled['events'],'visited':scheduled['visited'],
                            'current':None,'path':[],'complete':False})
    state['journey']={'index':0,'acts':records,'visitedEvents':[],'history':[], 'ending':False}
    state['actIndex']=0
    from .quests import bind_spoils
    for index,act in enumerate(records):bind_spoils(state,act['map'],index)
    reset_unknown(state)


def current_act(state):return state['journey']['acts'][state['journey']['index']]


def routes(state):
    act=current_act(state)
    if act['complete']:return []
    if act['current'] is None:return [act['map']['nodes'][act['map']['start']]]
    if any('WingedBoots' in p.get('relics',[]) and p.get('wingedBootsUsed',0)<3 for p in state.get('players',{}).values()):
        current=act['map']['nodes'][act['current']]
        return [{**node,'requiresFlight':node['id'] not in current['children']}
                for node in act['map']['nodes'].values() if node['row']==current['row']+1]
    return reachable(act['map'],act['current'])


def next_event(state, allowed):
    act=current_act(state);pool=act['events'];visited=state['journey']['visitedEvents']
    start=act['visited']['event']
    # Prefer unseen, eligible events. On exhaustion repeat an eligible event;
    # never bypass its prerequisites or hand an unsupported event to the UI.
    from ..events.events import DISABLED
    for unseen in (True,False):
        for offset in range(len(pool)):
            index=(start+offset)%len(pool);key=pool[index]
            # Old saves keep the pool they were dealt, so a disabled event is skipped
            # here as well rather than only when the pool is built.
            if key in DISABLED:continue
            if allowed(key,state) and (not unseen or key not in visited):
                act['visited']['event']=start+offset+1
                if key not in visited:visited.append(key)
                return key
    raise ValueError('当前没有满足条件的事件。')


def enter(state, ident, *, event_allowed):
    """Mutate only inside the engine's copy-on-action transaction."""
    act=current_act(state)
    node=next((n for n in routes(state) if n['id']==ident),None)
    if node is None:raise ValueError('该节点不与当前位置相连。')
    if node.get('requiresFlight'):
        for player in state.get('players',{}).values():
            if 'WingedBoots' in player.get('relics',[]) and player.get('wingedBootsUsed',0)<3:
                player['wingedBootsUsed']=player.get('wingedBootsUsed',0)+1
    previous=state['journey']['history'][-1] if state['journey']['history'] else None
    kind=node['kind'];resolved=kind
    from .quests import has, room_entered
    lantern=state['journey']['index']==2 and has(state,'LanternKey')
    if kind=='unknown':
        children=[act['map']['nodes'][n] for n in node['children']]
        no_shop=(previous and previous['kind']=='shop') or (children and all(n['kind']=='shop' for n in children))
        resolved='event' if lantern else unknown_room(state,blacklist=('shop',) if no_shop else ())
    room={'id':ident,'kind':resolved,'mapKind':kind,'act':act['key'],'actIndex':state['journey']['index'],'row':node['row']}
    if resolved in ('battle','elite'):
        pool=act['normal' if resolved=='battle' else 'elite'];cursor=act['visited'][resolved]
        room['encounter']=pool[cursor%len(pool)];act['visited'][resolved]+=1
    elif resolved=='boss':
        room['encounter']=act.get('secondBoss') if act.get('secondBoss') and act['map'].get('firstBoss')!=act['map']['boss'] and ident==act['map']['boss'] else act['boss']
        act['visited']['boss']+=1
    elif resolved=='ancient':room['event']=act['ancient']
    elif resolved=='event':room['event']='WarHistorianRepy' if lantern else next_event(state,event_allowed)
    act['current']=ident;act['path'].append(ident)
    state['journey']['history'].append(dict(room))
    if kind=='unknown':
        from ...engine import heal
        for player in state.get('players',{}).values():
            if player['hp']>0 and 'Planisphere' in player['relics']:heal(player,5)
    state['actIndex']=room['actIndex'];state['actFloor']=node['row']
    room_entered(state,room)
    return room


def complete_act(state):
    act=current_act(state)
    if act.get('secondBoss') and act['map'].get('firstBoss')!=act['map']['boss'] and act['current']==act['map'].get('firstBoss'):return 'map'
    if act['current']!=act['map']['boss'] or act['complete']:
        raise ValueError('当前不能结束这一幕。')
    act['complete']=True
    if state['journey']['index']==2:
        state['journey']['ending']=True
        return 'ending'
    return 'actComplete'


def advance_act(state):
    journey=state['journey']
    if not current_act(state)['complete'] or journey['index']>=2:
        raise ValueError('当前不能进入下一幕。')
    journey['index']+=1;state['actIndex']=journey['index'];state['actFloor']=0
    act=current_act(state)
    if any(c['key']=='SpoilsMap' and c.get('spoilsActIndex',1)==journey['index'] for p in state.get('players',{}).values() for c in p.get('deck',[])) and not act['map'].get('spoils'):
        act['map']=generate_map(state,act['key'],len(state.get('players',{}))>1,spoils=True)
    from .quests import bind_spoils
    bind_spoils(state,act['map'],journey['index'])
    reset_unknown(state)


def display(state):
    """The act's map as the client may draw it.

    Ids, grid position, the public room kind, real links and the current/visited/
    reachable state only: the route labels already publish all of it. The event
    pool, the pre-drawn encounters, rewards and the seed stay on the server, and
    an unknown room is reported as unknown."""
    from ...engine import KINDS
    act=current_act(state);graph=act['map']
    reachable_ids={node['id'] for node in routes(state)}
    nodes=[]
    for node in graph['nodes'].values():
        kind=KINDS.get(node['kind'],node['kind'])
        entry={'id':node['id'],'row':node['row'],'col':node['col'],'kind':node['kind'],
               'type':kind,'children':list(node['children'])}
        if node['id'] in reachable_ids:
            entry['detail']=kind+(' · 毛皮大衣：敌人 1 HP' if node.get('furCoats') else '')+(' · 飞行（消耗 1 次）' if node.get('requiresFlight') else '')
        nodes.append(entry)
    return {'act':{'index':state['journey']['index'],'name':act['key']},'start':graph['start'],
            'boss':graph['boss'],'rooms':graph['rooms'],'nodes':nodes,'current':act['current'],
            'path':list(act['path']),'reachable':sorted(reachable_ids),'complete':act['complete']}


def summary(state):
    act=current_act(state)
    return {'index':state['journey']['index'],'key':act['key'],'name':ACT_NAMES[act['key']],
            'row':state.get('actFloor',0),'rooms':act['map']['rooms'],
            'boss':act['boss'],'current':act['current'],'path':list(act['path'])}
