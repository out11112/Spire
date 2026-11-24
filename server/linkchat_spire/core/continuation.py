"""Resume synchronous nested rules by deterministic replay of one pure action.

The engine has no external effects: all mutations, logs and RNG live in its state.
Only an unfinished action's starting snapshot and validated choices are retained.
Replaying replaces that action's partial result; it never adds its payment twice.
This also resumes choices raised from inside draw/shuffle hooks without saving a
Python stack or pretending the enclosing card has already finished.
"""
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass, field


@dataclass
class Runtime:
    answers:list=field(default_factory=list)
    cursor:int=0
    fence:int=0
    depth:int=0
    finalizing:bool=False
    vakuu:bool=False
    choice_handler:object=None
    scheduler:object=None
    independent:bool=False

    def answer(self,state):
        if self.choice_handler is not None:return self.choice_handler(state)
        if self.cursor==len(self.answers):raise NeedsChoice(state)
        action=self.answers[self.cursor];self.cursor+=1
        return action


CURRENT=ContextVar('spire_action_runtime',default=None)


class NeedsChoice(Exception):
    def __init__(self,state):self.state=state


def current():return CURRENT.get()


def apply(state,uid,action,execute):
    from .. import engine as e
    from ..combat.effects import validate_choice
    journal=state.get('continuation')
    from .choice_policy import actions, enabled
    independent=bool(journal.get('independent',False)) if journal else enabled()
    allowed_actions=actions(state)
    turn_action=bool(journal and state.get('turnChoices') and action.get('type') in allowed_actions)
    if journal and (action.get('type') in ('choose','decide') or turn_action):
        e.require(not state['paused'] and state['phase'] not in ('victory','defeat','abandoned'),'游戏已暂停或结束。')
        e.require(action.get('phaseId')==state['phaseId'],'阶段已变化，请根据最新界面重新操作。')
        player=state['players'].get(str(uid));e.require(player is not None,'你不在此房间。')
        from .turn_tasks import choice_state
        selected_state=choice_state(state,uid,action)
        if turn_action:
            e.require(str(uid) in {str(owner) for owner in state.get('turnReady',[])},'请先完成自己的回合准备或选择。')
        elif action['type']=='choose':validate_choice(selected_state,player,action)
        else:
            from .decisions import validate
            validate(selected_state,player,action)
        origin=journal['origin'];root_uid=journal['owner'];root_action=journal['action']
        recorded=deepcopy(action)
        recorded.pop('_turnActor',None)
        if turn_action:recorded['_turnActor']=player['id']
        answers=journal['answers']+[recorded]
    elif journal or action.get('type') in ('pause','ready','abandon'):
        return execute(state,uid,action)
    else:
        origin=state;root_uid=uid;root_action=action;answers=[]
    runtime=Runtime(answers=answers,independent=independent);token=CURRENT.set(runtime);suspended=False
    try:
        try:
            if (((origin.get('phase')=='combat' and origin.get('side')=='player'
                      and root_action.get('type') in ('play','potion','dropPotion'))
                     or (independent and origin.get('phase')=='combat' and origin.get('side')=='player'
                         and root_action.get('type') in ('goldReward','customReward','customRelicReward'))
                     or (origin.get('phase')!='combat' and independent
                         and root_action.get('type') in actions(origin))
                     or (journal and state.get('turnChoices') and origin.get('event')=='FieldOfManSizedHoles'
                         and root_action.get('type')=='event'))
                    and len(origin['players'])>1
                    and not origin.get('pendingChoice') and not origin.get('pendingDecision')):
                from .turn_tasks import TurnTasks, Job
                result=deepcopy(origin)
                tasks=TurnTasks(result,runtime,[],action_mode=True)
                job=Job('action-root:'+str(root_uid),lambda:tasks.execute_action(root_uid,root_action),())
                tasks.jobs.append(job);tasks.by_name[job.name]=job
                tasks.run()
                if result.get('phase') in ('event','rest','shop','treasure','reward'):e.advance_if_ready(result)
            else:
                result=execute(origin,root_uid,root_action)
            runtime.finalizing=True;e.after_card(result)
        except NeedsChoice as pause:
            result=pause.state;suspended=True
        e.require(runtime.cursor==len(answers),'选牌恢复记录与规则不一致。')
    finally:CURRENT.reset(token)
    simulation_log_serial=result.get('logSerial',0)
    if journal:
        # Replay reconstructs the same encounter journal from its original state.
        # Keep structured visibility/source data and deterministic event IDs.
        result['paused']=state['paused']
        for key,player in result['players'].items():
            player['ready']=state['players'][key]['ready']
            if 'abandon' in state['players'][key]:player['abandon']=state['players'][key]['abandon']
    result['revision']=state['revision']+1
    result.pop('continuation',None)
    if suspended:
        result['continuation']={'origin':deepcopy(origin),'owner':root_uid,'action':deepcopy(root_action),
                                'answers':deepcopy(answers),'simulatedLogSerial':simulation_log_serial,'independent':independent}
    return result


def rebase_phase(state,delta):
    """Invalidate pre-SL actions while preserving replay of an entry-time choice."""
    state['phaseId']+=delta
    journal=state.get('continuation')
    if journal:
        rebase_phase(journal['origin'],delta)
        for action in [journal['action'],*journal['answers']]:
            if 'phaseId' in action:action['phaseId']+=delta
