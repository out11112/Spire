"""Architect's non-combat epilogue, with private resumable dialogue progress.

The encounter is a stage for attack animations. Neither attack animation calls
damage rules; proceeding wins the run without reducing either creature's HP.
"""
from ... import engine as e

LINES={'ironclad':(2,3,3),'silent':(1,1,1,1),'defect':(3,3,3),
       'necrobinder':(2,2,2,3),'regent':(3,3,3)}


def score(state):
    history=state.get('journey',{}).get('history',[])
    floors=sum(10*(row.get('actIndex',0)+1) for row in history)
    elites=sum(row['kind']=='elite' for row in history)
    bosses=sum(row['kind']=='boss' for row in history)
    gold=sum(p.get('scoreGoldGained',0) for p in state['players'].values())//(100*len(state['players']))
    base=floors+50*elites+100*bosses+gold
    return int(base*(1+0.1*state.get('ascension',0)))


def start(state):
    e.phase(state,'ending');state['event']='TheArchitect'
    state.pop('eventCombat',None);state.pop('afterRewards',None)
    state['encounter']='TheArchitectEventEncounter';state['encounterKind']='battle'
    from ...combat.monsters import hp
    amount=hp(state,9999)
    state['enemies']=[{'id':'architect','key':'Architect','name':'建筑师','hp':amount,'maxHp':amount,
                       'block':0,'powers':{},'move':0,'intent':{'hidden':True,'targets':[]}}]
    state['endingScore']=score(state)
    state['eventState']={'key':'TheArchitect','page':0,'votes':{},'players':{}}
    for uid,player in state['players'].items():
        visits=state.get('accountProgress',{}).get(uid,{}).get('characterWins',{}).get(player['character'],0)
        counts=LINES[player['character']]
        # Non-repeating dialogue exhaustion proceeds directly. Repeating
        # localization variants must be explicitly catalogued before enabling.
        lines=counts[visits] if visits<len(counts) else 0
        state['eventState']['players'][uid]={'page':0,'done':False,'visit':visits,'lines':lines,
            'startAttackers':'player' if lines and player['character']=='silent' else 'none',
            'endAttackers':('architect' if player['character']=='silent' and visits>=2 else 'both') if lines else 'none'}
    e.log(state,'第三幕通关，进入建筑师结局。攻击为演出，不扣生命。')


def choices(state,player):
    progress=state['eventState']['players'][str(player['id'])]
    if progress['done']:return []
    return [('proceed','结束攀登，结算胜利')] if progress['page']>=progress['lines']-1 else [('respond','回应并继续')]


def act(state,player,action):
    progress=state['eventState']['players'][str(player['id'])]
    e.require(action.get('event')=='TheArchitect' and action.get('page')==progress['page'],'结局页面已变化。')
    e.require(action.get('option') in [key for key,_ in choices(state,player)],'无效的结局选择。')
    if action['option']=='respond':progress['page']+=1;return
    progress['done']=True;player['done']=True
    if progress['endAttackers']!='none':
        progress['attackResolved']=True
        progress['displayDamage']=state['endingScore'] if progress['endAttackers']=='both' else 0
    e.log(state,player['name']+'完成结局，等待同伴。')
    if all(row['done'] for row in state['eventState']['players'].values()):
        e.phase(state,'victory');e.log(state,'三幕攀登完成！得分 '+str(state['endingScore']))


def description(state,player):
    progress=state['eventState']['players'][str(player['id'])]
    if state['phase']=='victory':return '三幕攀登完成！得分 '+str(state['endingScore'])
    if progress['done']:return '你已完成结局，等待同伴。得分 '+str(state['endingScore'])
    text=f"建筑师 · 得分 {state['endingScore']} · 结局 {min(progress['page']+1,max(1,progress['lines']))}/{max(1,progress['lines'])}。"
    if progress['startAttackers']=='player' and progress['page']==0:text+=' 你先向建筑师发起攻击演出。'
    if progress['page']>=progress['lines']-1:
        text+= {'both':' 双方攻击演出后结算胜利。','architect':' 建筑师攻击演出后结算胜利。','none':' 可以直接结算胜利。'}[progress['endAttackers']]
    else:text+=' 回应建筑师，继续结局。'
    return text
