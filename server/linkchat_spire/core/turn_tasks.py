"""Cooperative turn jobs with ephemeral stacks and replayable input boundaries.

Only one worker holds the execution baton. No worker survives a game action;
resumption recreates jobs by replaying the action and its validated answers.
"""
from contextvars import ContextVar, copy_context
from copy import deepcopy
from threading import Event, Thread
from .continuation import NeedsChoice

ACTIVE_JOB=ContextVar('spire_turn_job',default=None)
CONTROL_KEYS=('effects','pendingChoice','pendingDecision','_effectsRunning')
CARD_CONTEXT_KEYS=('blockCard','blockDefend','blockPlay')


class Cancelled(BaseException):
    pass


class Job:
    def __init__(self,name,callback,dependencies):
        self.name=name;self.callback=callback;self.dependencies=dependencies
        self.status='new';self.controls={};self.card_contexts={};self.depth=0;self.answer=None;self.error=None
        self.cancelled=False;self.thread=None;self.go=Event();self.changed=Event()

    def execute(self):
        token=ACTIVE_JOB.set(self)
        try:
            self.go.wait()
            self.callback()
        except Cancelled:pass
        except BaseException as exc:self.error=exc
        finally:
            self.status='done';self.changed.set();ACTIVE_JOB.reset(token)


class TurnTasks:
    def __init__(self,state,runtime,specifications,*,action_mode=False):
        self.state=state;self.runtime=runtime;self.action_mode=action_mode
        self.jobs=[Job(*spec) for spec in specifications]
        self.by_name={job.name:job for job in self.jobs}
        if len(self.by_name)!=len(self.jobs):raise ValueError('Duplicate turn task')
        if any(dep not in self.by_name for job in self.jobs for dep in job.dependencies):raise ValueError('Unknown turn dependency')

    def add(self,name,callback,dependencies=()):
        if name in self.by_name:raise ValueError('Duplicate turn task')
        job=Job(name,callback,dependencies)
        self.jobs.append(job);self.by_name[name]=job

    def pending(self):
        return any(job.status!='done' for job in self.jobs)

    def take_controls(self):
        return {key:self.state.pop(key) for key in CONTROL_KEYS if key in self.state}

    def take_card_contexts(self):
        return {uid:{key:p.pop(key) for key in CARD_CONTEXT_KEYS if key in p} for uid,p in self.state['players'].items()}

    def restore_card_contexts(self,contexts):
        for uid,values in contexts.items():self.state['players'][uid].update(values)

    def switch(self,job,answer=None,cancel=False):
        outer=self.take_controls();outer_cards=self.take_card_contexts();outer_depth=self.runtime.depth
        self.restore_card_contexts(job.card_contexts)
        self.state.update(job.controls);self.runtime.depth=job.depth if job.thread else outer_depth+1
        job.answer=answer;job.cancelled=cancel;job.changed.clear()
        if job.thread is None:
            context=copy_context();job.status='running'
            job.thread=Thread(target=lambda:context.run(job.execute),name='spire-turn:'+job.name,daemon=True)
            job.thread.start()
        job.go.set();job.changed.wait()
        job.controls=self.take_controls();job.depth=self.runtime.depth
        job.card_contexts=self.take_card_contexts();self.restore_card_contexts(outer_cards)
        self.state.update(outer);self.runtime.depth=outer_depth
        if job.error is not None:raise job.error

    def answer(self,state):
        job=ACTIVE_JOB.get()
        if job not in self.jobs or state is not self.state:raise RuntimeError('Choice outside active turn task')
        job.go.clear();job.status='waiting';job.changed.set();job.go.wait()
        if job.cancelled:raise Cancelled()
        job.status='running'
        return job.answer

    def start_ready(self):
        while True:
            combat_over=(self.state.get('phase')=='combat' and not any(enemy['hp']>0 or enemy.get('awaitingRevive') for enemy in self.state['enemies']))
            for job in self.jobs:
                if job.status=='waiting':
                    player=self.state['players'].get(job.name.split(':',1)[1]) if ':' in job.name else None
                    if self.state.get('phase') in ('abandoned','defeat','victory') or combat_over or player is not None and player['hp']<=0:
                        self.switch(job,cancel=True)
                    elif 'pendingChoice' in job.controls:
                        from ..combat.effects import refresh_choice
                        choice=job.controls['pendingChoice']
                        refresh_choice(self.state,choice)
                        if not choice['cards']:
                            self.switch(job,{'type':'choose','choiceId':choice['id'],'cards':[]})
                    elif 'pendingDecision' in job.controls:
                        from .decisions import refresh
                        decision=job.controls['pendingDecision'];refresh(self.state,decision)
                        if not decision['options']:
                            self.switch(job,{'type':'decide','decisionId':decision['id'],'selections':[]})
            ready=[job for job in self.jobs if job.status=='new' and all(self.by_name[dep].status=='done' for dep in job.dependencies)]
            if not ready:return
            for job in ready:self.switch(job)

    def run(self):
        previous=self.runtime.choice_handler;previous_scheduler=self.runtime.scheduler
        self.runtime.choice_handler=self.answer;self.runtime.scheduler=self
        try:
            self.start_ready()
            while any(job.status!='done' for job in self.jobs):
                waiting=[job for job in self.jobs if job.status=='waiting']
                if not waiting:raise RuntimeError('Cyclic turn task dependency')
                if self.runtime.cursor==len(self.runtime.answers):
                    snapshot=deepcopy(self.state);choices=[]
                    for job in waiting:
                        for key in ('pendingChoice','pendingDecision'):
                            if key in job.controls:choices.append({'kind':key,'value':deepcopy(job.controls[key])})
                    if not choices:raise RuntimeError('Turn task paused without a choice')
                    snapshot['turnChoices']=choices
                    snapshot['turnReady']=self.ready_players()
                    snapshot[choices[0]['kind']]=deepcopy(choices[0]['value'])
                    raise NeedsChoice(snapshot)
                action=self.runtime.answers[self.runtime.cursor]
                if '_turnActor' in action:
                    from .. import engine as e
                    owner=action['_turnActor']
                    e.require(owner in self.ready_players(),'回合动作的持有者尚未完成准备。')
                    from .choice_policy import actions
                    allowed=actions(self.state)
                    e.require(action.get('type') in allowed,'无效的回合动作记录。')
                    self.runtime.cursor+=1
                    job=Job('action-'+str(self.runtime.cursor)+':'+str(owner),lambda owner=owner,action=action:self.execute_action(owner,action),())
                    self.jobs.append(job);self.by_name[job.name]=job
                    self.switch(job);self.start_ready();continue
                ident=action.get('choiceId') if action.get('type')=='choose' else action.get('decisionId')
                job=next((job for job in waiting if any(job.controls.get(key,{}).get('id')==ident for key in ('pendingChoice','pendingDecision'))),None)
                if job is None:raise RuntimeError('Turn answer no longer matches a pending task')
                self.runtime.cursor+=1;self.switch(job,action);self.start_ready()
        finally:
            # A suspended public snapshot was copied before unwinding stacks.
            # Their finally blocks clean up only the discarded simulation state.
            for job in self.jobs:
                if job.status=='waiting':self.switch(job,cancel=True)
                if job.thread is not None:job.thread.join()
            self.runtime.choice_handler=previous;self.runtime.scheduler=previous_scheduler

    def execute_action(self,owner,action):
        from .. import engine as e
        from ..combat.effects import run
        e._apply(self.state,owner,action,_inplace=True)
        if self.state.get('effects'):run(self.state)
        if self.state.get('phase')!='combat':return
        player=self.state['players'][str(owner)]
        e.check_empty_hand(self.state,player)
        e.finish_requested_turn(self.state,player)

    def ready_players(self):
        ready=[]
        for player in self.state['players'].values():
            uid=player['id'];auto=self.by_name.get('auto:'+str(uid))
            blocked=any(job.status in ('new','waiting') and (job.name.endswith(':'+str(uid)) or any(job.controls.get(key,{}).get('owner')==uid for key in ('pendingChoice','pendingDecision'))) for job in self.jobs)
            if player['hp']>0 and (self.action_mode or auto is not None and auto.status=='done') and not blocked:ready.append(uid)
        return ready


def choice_state(state,uid,action=None):
    choices=state.get('turnChoices')
    if not choices:
        if action is not None:return state
        projected=dict(state)
        for key in ('pendingChoice','pendingDecision'):
            if key in projected and str(projected[key]['owner'])!=str(uid):projected.pop(key)
        return projected
    ident=(action.get('choiceId') or action.get('decisionId')) if action else None
    own=[row for row in choices if str(row['value']['owner'])==str(uid) and (ident is None or row['value']['id']==ident)]
    selected=own[0] if own else None
    projected=dict(state);projected.pop('pendingChoice',None);projected.pop('pendingDecision',None)
    if selected is not None:projected[selected['kind']]=selected['value']
    return projected
