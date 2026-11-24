"""Typed non-card choices suspended inside the existing action replay journal."""
from copy import deepcopy
from .. import engine as e
from .continuation import current


def validate(state,player,action):
    decision=state.get('pendingDecision')
    e.require(decision and decision['owner']==player['id'] and action.get('decisionId')==decision['id'],'选择已失效或不属于你。')
    selected=action.get('selections')
    e.require(isinstance(selected,list) and all(isinstance(key,str) for key in selected),'请选择有效选项。')
    e.require(len(set(selected))==len(selected) and decision['minimum']<=len(selected)<=decision['maximum'],'选择数量不符合要求。')
    candidates={item['id']:item for item in decision['options']}
    e.require(all(key in candidates for key in selected),'选项不存在。')
    return [candidates[key] for key in selected]


def select(state,player,kind,title,options,minimum=1,maximum=1):
    runtime=current();e.require(runtime is not None,'选择必须通过游戏动作执行。')
    if runtime.vakuu:return deepcopy(options[:maximum])
    e.require(len({item['id'] for item in options})==len(options),'候选身份重复。')
    e.require(0<=minimum<=maximum<=len(options),'选择数量无效。')
    state['serial']+=1
    state['pendingDecision']={'id':'decision:'+str(state['serial']),'owner':player['id'],'kind':kind,
                              'title':title,'minimum':minimum,'maximum':maximum,'options':deepcopy(options)}
    action=runtime.answer(state)
    e.require(action.get('type')=='decide','恢复记录的选择类型不一致。')
    selected=validate(state,player,action);state.pop('pendingDecision')
    return selected


def options(state,player):
    decision=state['pendingDecision']
    if player['id']!=decision['owner']:return []
    rows=[{**item,'action':{'type':'decide','decisionId':decision['id'],'selections':[item['id']]}}
          for item in candidate_options(state,player)]
    # A decision that can be resolved with nothing selected has to say so: one row
    # per candidate cannot express an empty selection, which left the camp cooking
    # choice impossible to cancel from the client.
    if decision['minimum']==0:
        rows.append({'id':'decideCancel','label':'不选，取消',
                     'action':{'type':'decide','decisionId':decision['id'],'selections':[]}})
    return rows


def candidate_options(state,player):
    from ..text.choices import decision_item
    decision=state['pendingDecision']
    if player['id']!=decision['owner']:return []
    return [decision_item(state,player,item) for item in decision['options']]


def refresh(state,decision):
    """Deck-backed decisions retain identities but lose ineligible candidates."""
    if decision['kind']=='mend':
        decision['options']=[row for row in decision['options'] if state['players'].get(row['id'],{}).get('hp',0)>0]
        decision['maximum']=min(decision['maximum'],len(decision['options']))
        return
    if decision['kind'] not in ('cook','copyDeck'):return
    player=state['players'][str(decision['owner'])]
    cards={card['id']:card for card in player['deck']}
    eligible=lambda card:e.removable(card) if decision['kind']=='cook' else e.definition(card)['kind']!='quest'
    rows=[row for row in decision['options'] if row['id'] in cards and eligible(cards[row['id']])]
    if decision['kind']=='cook' and len(rows)<2:rows=[]
    decision['options']=rows
    decision['minimum']=min(decision['minimum'],len(rows));decision['maximum']=min(decision['maximum'],len(rows))
