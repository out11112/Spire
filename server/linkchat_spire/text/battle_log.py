"""Encounter journal. Mutation observers never draw random numbers or allocate cards.

Observers are runtime-only dict/list subclasses. Deep copies deliberately become
plain containers, so snapshots and continuation origins contain no backreferences.
"""
from copy import deepcopy
import sys
import ast
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=128)
def trigger_scopes(filename):
    """Only identifiers from an executed conditional body, never guessed values."""
    from ..content import RELICS, POTIONS
    try:tree=ast.parse(Path(filename).read_text(encoding='utf-8'))
    except (OSError,SyntaxError):return []
    result=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.If) or not node.body:continue
        keys=[part.value for part in ast.walk(node.test) if isinstance(part,ast.Constant) and isinstance(part.value,str) and (part.value in RELICS or part.value in POTIONS)]
        if len(set(keys))==1:
            key=keys[0];kind="relic" if key in RELICS else "potion";name=(RELICS if key in RELICS else POTIONS)[key][0]
            result.append((node.body[0].lineno,node.body[-1].end_lineno,{"kind":kind,"key":key,"name":name}))
    return sorted(result,key=lambda row:row[1]-row[0])

@lru_cache(maxsize=128)
def loop_bindings(filename):
    try:tree=ast.parse(Path(filename).read_text(encoding='utf-8'))
    except (OSError,SyntaxError):return []
    return [(node.lineno,node.end_lineno,{part.id for part in ast.walk(node.target) if isinstance(part,ast.Name)})
            for node in ast.walk(tree) if isinstance(node,(ast.For,ast.AsyncFor))]

def active_relic_binding(frame,name):
    if name in frame.f_code.co_varnames[:frame.f_code.co_argcount]:return True
    return any(first<=frame.f_lineno<=last and name in names
               for first,last,names in loop_bindings(frame.f_code.co_filename))


def stale_loop_binding(frame,name):
    if name in frame.f_code.co_varnames[:frame.f_code.co_argcount]:return False
    last=max(line or 0 for _,_,line in frame.f_code.co_lines())
    bindings=[(first,end) for first,end,names in loop_bindings(frame.f_code.co_filename)
              if frame.f_code.co_firstlineno<=first<=last and name in names]
    return bool(bindings) and not any(first<=frame.f_lineno<=end for first,end in bindings)


STATS={'hp':'生命','maxHp':'最大生命','energy':'能量','stars':'辉星','block':'格挡'}
PILES={'hand':'手牌','draw':'抽牌堆','discard':'弃牌堆','exhaust':'消耗堆','inPlay':'结算区'}


def source():
    from ..content import CARDS, RELICS, POTIONS
    frame=sys._getframe(1)
    fallback=None;private_owner=None
    while frame:
        module=frame.f_globals.get('__name__','')
        if module.startswith('linkchat_spire.') and module!=__name__:
            local=frame.f_locals
            for first,last,trigger in trigger_scopes(frame.f_code.co_filename):
                if first<=frame.f_lineno<=last:return dict(trigger)
            if frame.f_code.co_name in ('draw','add_to_hand','reserve_draw'):
                player=local.get('p',local.get('player',{}))
                private_owner=player.get('id')
            for var in ('relic_key','relic','key'):
                key=local.get(var)
                if isinstance(key,str) and key in RELICS and active_relic_binding(frame,var):
                    return {'kind':'relic','key':key,'name':RELICS[key][0]}
            for var in ('potion','item','card','c','automatic_card'):
                obj=local.get(var)
                if isinstance(obj,dict) and not stale_loop_binding(frame,var):
                    key=obj.get('key')
                    if key in POTIONS and ('potion' in module or var=='potion'):
                        return {'kind':'potion','key':key,'name':POTIONS[key][0]}
                    if key in CARDS and fallback is None:
                        fallback={'kind':'card','key':key,'name':CARDS[key]['name']}
            if fallback is None and frame.f_code.co_name in ('power','debuff'):
                fallback={'kind':'power','key':local.get('key'),'name':local.get('key')}
        frame=frame.f_back
    result=fallback or {'kind':'rule','name':'战斗结算'}
    if private_owner is not None:result['_privateOwner']=private_owner
    return result


def emit(s,text,kind='message',*,owner=None,public=None,source_info=None,**data):
    if not s.get('battleId') or not s.get('battleLogging'):return
    origin=source_info or source()
    private_owner=origin.pop('_privateOwner',None)
    if private_owner is not None and owner is None:owner=private_owner;public=public or text
    s['logSerial']=s.get('logSerial',0)+1
    entry={'id':s['logSerial'],'battleId':s['battleId'],'turn':s.get('turn',0),
           'side':s.get('side','player'),'kind':kind,'source':origin,
           'visibility':'public' if owner is None else 'owner','text':text,**data}
    if owner is not None:entry.update(owner=str(owner),publicText=public or '私有战斗记录')
    s.setdefault('log',[]).append(entry)


def begin(s):
    s['battleSerial']=s.get('battleSerial',0)+1
    s['battleId']=s['battleSerial'];s['logSerial']=0;s['log']=[]
    s['battleLogging']=True;s['battleLogIncomplete']=False


def legacy(s):
    if s.get('battleId') or s.get('phase')!='combat':return
    # Old logs have no encounter identity. Keep only the suffix after a proven
    # battle-start marker; never guess that a map/reward message is combat.
    old=s.get('log',[]);start=next((i for i in range(len(old)-1,-1,-1)
        if '进入战斗：' in (old[i].get('text','') if isinstance(old[i],dict) else old[i])),None)
    begin(s);s['battleLogIncomplete']=True
    if start is not None:
        for row in old[start:]:
            text=row.get('text','') if isinstance(row,dict) else row
            if not any(x in text for x in ('暂停','准备','继续攀登')):emit(s,text,'legacy')


def project(entry,uid):
    if entry.get('source',{}).get('key')=='OddlySmoothStone' and not (entry.get('kind')=='power' and entry.get('field')=='dexterity'):
        entry={**entry,'source':{'kind':'rule','name':'战斗结算'}}
    if entry.get('visibility')!='owner' or entry.get('owner')==str(uid):return deepcopy(entry)
    # Explicit allowlist: card identities, sources and pile payloads are private.
    return {**{k:entry[k] for k in ('id','battleId','turn','side','kind') if k in entry},
            'visibility':'public','source':{'kind':'rule','name':'战斗结算'},
            'text':entry.get('publicText','私有战斗记录')}


def metadata(s):
    rows=s.get('log',[]) if s.get('battleId') else []
    return {'battleId':s.get('battleId'),'total':len(rows),'first':rows[0]['id'] if rows else None,
            'last':rows[-1]['id'] if rows else None,'incomplete':s.get('battleLogIncomplete',False)}


class ObservedDict(dict):
    def __init__(self,value,state,role,actor=None):
        self.state=state;self.role=role;self.actor=actor
        dict.__init__(self)
        for key,item in value.items():dict.__setitem__(self,key,self.wrap(key,item))
    def __deepcopy__(self,memo):
        result={};memo[id(self)]=result
        for key,value in self.items():result[deepcopy(key,memo)]=deepcopy(value,memo)
        return result
    def wrap(self,key,value):
        if self.role=='actors' and isinstance(value,dict):return ObservedDict(value,self.state,'actor')
        if self.role=='actor':
            if key=='powers':return ObservedDict(value,self.state,'powers',self)
            if key in PILES:return ObservedList(value,self.state,key,self)
            if key=='osty' and isinstance(value,dict):return ObservedDict(value,self.state,'actor')
        return value
    def __setitem__(self,key,value):
        old=self.get(key,0 if self.role=='powers' or key in STATS else None)
        value=self.wrap(key,value);dict.__setitem__(self,key,value)
        if self.role=='powers' or self.role=='actor' and key in STATS:
            if old!=value:
                actor=self.actor if self.role=='powers' else self
                name=actor.get('name',str(actor.get('id','单位')))
                from .official import power_name
                label=power_name(key,'intent' not in actor) if self.role=='powers' else STATS[key]
                kind='power' if self.role=='powers' else key
                emit(self.state,f'{name} · {label} {old} → {value}',kind,actor=actor.get('id'),field=key,before=old,after=value)
                if key=='hp' and old and old>0 and value<=0:emit(self.state,f'{name} 倒下','death',actor=actor.get('id'))
                if key=='hp' and old is not None and old<=0 and value>0:emit(self.state,f'{name} 复活','revive',actor=actor.get('id'))
        elif self.role=='actor' and key=='powers' and old is not None:
            for power in sorted(set(old)|set(value)):
                if old.get(power,0)!=value.get(power,0):
                    from .official import power_name
                    emit(self.state,f"{self.get('name','单位')} · {power_name(power,'intent' not in self)} {old.get(power,0)} → {value.get(power,0)}",'power',actor=self.get('id'),field=power,before=old.get(power,0),after=value.get(power,0))
    def __delitem__(self,key):
        if self.role=='powers':self[key]=0
        dict.__delitem__(self,key)
    def pop(self,key,*default):
        if key not in self:
            if default:return default[0]
            raise KeyError(key)
        value=self[key];del self[key];return value
    def update(self,*args,**kwargs):
        for key,value in dict(*args,**kwargs).items():self[key]=value
    def setdefault(self,key,default=None):
        if key not in self:self[key]=default
        return self[key]
    def clear(self):
        for key in list(self):del self[key]
    def popitem(self):
        key=next(reversed(self));return key,self.pop(key)
    def __ior__(self,other):self.update(other);return self


class ObservedList(list):
    def __init__(self,value,state,role,actor=None):
        self.state=state;self.role=role;self.actor=actor
        list.__init__(self,(self.wrap(x) for x in value))
    def __deepcopy__(self,memo):
        result=[];memo[id(self)]=result;result.extend(deepcopy(x,memo) for x in self);return result
    def wrap(self,value):
        if self.role=='enemies' and isinstance(value,dict):return ObservedDict(value,self.state,'actor')
        return value
    def record(self,value,verb):
        if self.role=='enemies':
            if verb=='加入':emit(self.state,f"召唤 {value.get('name','敌人')}",'summon',actor=value.get('id'))
            return
        # Routine pile transfers are deliberately omitted from the journal.
    def append(self,value):
        value=self.wrap(value);list.append(self,value);self.record(value,'加入')
    def insert(self,index,value):
        value=self.wrap(value);list.insert(self,index,value);self.record(value,'加入')
    def extend(self,values):
        for value in list(values):self.append(value)
    def pop(self,index=-1):
        value=list.pop(self,index);self.record(value,'离开');return value
    def remove(self,value):
        index=self.index(value);self.pop(index)
    def clear(self):
        while self:self.pop()
    def __delitem__(self,index):
        values=self[index] if isinstance(index,slice) else [self[index]]
        list.__delitem__(self,index)
        for value in values:self.record(value,'离开')
    def __setitem__(self,index,value):
        old=self[index] if isinstance(index,slice) else [self[index]]
        values=[self.wrap(x) for x in value] if isinstance(index,slice) else [self.wrap(value)]
        list.__setitem__(self,index,values if isinstance(index,slice) else values[0])
        # Reordering must never reveal future draw order.
        if self.role=='draw':return
        for item in old:self.record(item,'离开')
        for item in values:self.record(item,'加入')
    def __iadd__(self,values):self.extend(values);return self


def observe(s):
    legacy(s)
    if not isinstance(s.get('players'),ObservedDict):s['players']=ObservedDict(s['players'],s,'actors')
    if not isinstance(s.get('enemies'),ObservedList):s['enemies']=ObservedList(s.get('enemies',[]),s,'enemies')
    return s
