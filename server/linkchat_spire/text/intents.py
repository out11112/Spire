"""Public intent categories, in the reference move declaration's order.

intent_types.json contains identifiers only, derived from v0.111.0 declarations.
Execution parameters (buff strengths, healing, thresholds, summons) are private.
"""
from ..content.data import load as load_data
TYPES=load_data('intent_types.json')


def display(enemy,intent,uid):
    moves=TYPES.get(enemy.get('key'),[])
    types=moves[enemy.get('move',-1)] if 0<=enemy.get('move',-1)<len(moves) else ['unknown']
    if enemy.get('stunned') or intent.get('stunned'):types=['stun']
    if enemy.get('awaitingRevive') and not intent.get('revive'):types=['hidden']
    result=[]
    for kind in types:
        row={'type':kind}
        if kind in ('attack','deathBlow'):
            row.update(damage=intent.get('damageByTarget',{}).get(str(uid),intent.get('damage',0)),hits=intent.get('hits',1))
        if kind=='status' and 'count' in intent:row['count']=intent['count']+sum(extra.get('count',0) for extra in intent.get('statusExtra',[]))
        result.append(row)
    return result
