"""Player actions: validation, the options a player has, and entering rooms."""
from ..content import cost_text
from ..text import battle_log
from copy import deepcopy
from ..content import POTIONS, RULES_VERSION, CONTENT_VERSION, SCHEMA_VERSION, card_view
from ..content.characters import CHARACTERS
from .errors import InvalidAction, require
from ..combat import battle
from ..combat import damage
from ..combat import play
from . import state as run_state
from ..rng import draws

def map_vote(s,ballots):
    """``MapSelectionSynchronizer``: one ballot drawn from ``Rng(seed, "map_point_selection")``.

    ``ballots`` must be in seat order, as the reference indexes votes by slot.
    """
    from ..rng import streams
    with streams.open(s) as rngs:
        return rngs.named('map_point_selection').next_item(list(ballots))

def map_routes(s):
    if 'journey' in s:
        from ..run.map.journey import routes
        return routes(s)
    return s['map'][s['floor']] if s['floor']<len(s['map']) else []

def enter_route(s,node):
    if 'journey' not in s:return enter_room(s,node)
    from ..run.map.journey import enter
    from ..run.events.events import allowed
    room=enter(s,node['id'],event_allowed=lambda key,state:allowed(state,key))
    # Journey already applies quest room-entry hooks before handing off identity.
    enter_room(s,room,quest_entered=True)

EVENTS={'Wellspring':'泉水','WhisperingHollow':'低语空谷','UnrestSite':'无休之处','TabletOfTruth':'真理石板','SapphireSeed':'蓝宝石种子'}

KINDS={'battle':'敌人','elite':'精英','boss':'Boss','event':'事件','rest':'休息','shop':'商人','treasure':'宝箱','ancient':'先古之民','unknown':'未知'}

def enter_room(s,node,*,quest_entered=False):
    from ..run.events.ancients import KEYS as ancient_keys
    require(node['kind'] in KINDS and (node['kind']!='ancient' or node.get('event') in ancient_keys|{'Neow'}),'房间效果尚未实现：'+str(node.get('event',node['kind'])))
    s['floor']+=1;s['node']=node;s['event']=None;s.pop('eventState',None)
    from ..run.map.quests import room_entered
    if not quest_entered:room_entered(s,node)
    for p in s['players'].values():p['vote']=None
    if node['kind'] in ('battle','elite','boss'):
        from ..relics.hooks import room_entered as relic_room_entered
        for p in s['players'].values():relic_room_entered(s,p,node['kind'])
        battle.start_battle(s,node['kind'],node.get('encounter'));return
    run_state.phase(s,'event' if node['kind']=='ancient' else node['kind'])
    from ..relics.hooks import room_entered as relic_room_entered
    for p in s['players'].values():relic_room_entered(s,p,node['kind'])
    if node['kind'] in ('event','ancient'):
        # The act's events are chosen when the act is generated and then walked
        # in order, so an event room always carries its identity. Drawing here
        # instead would be a second, differently-seeded decision and would
        # desync the up-front stream for every later act.
        require(node.get('event') is not None,'事件节点没有携带事件身份。')
        s['event']=node['event']
        if s['event'] not in EVENTS:
            from ..run.events.events import start
            start(s,s['event'])
    for p in s['players'].values():
        p['eventCount']=0;p['eventGold']=draws.player_rng(s,p,'Rewards',lambda rng:rng.next_int_range(26,45))
    if node['kind']=='shop':
        from ..run.shop import enter
        from .continuation import current
        runtime=current()
        if runtime and runtime.independent and len(s['players'])>1:
            from .turn_tasks import TurnTasks
            TurnTasks(s,runtime,[('shop:'+str(p['id']),lambda p=p:enter(s,p),())
                                 for p in s['players'].values()],action_mode=True).run()
        else:
            for p in s['players'].values():enter(s,p)
    if node['kind']=='treasure':
        from ..run.rewards.treasure import enter
        enter(s)

def advance_if_ready(s):
    from .continuation import current
    runtime=current()
    if s.get('pendingChoice') or s.get('pendingDecision') or s.get('effects'):return
    if runtime and runtime.scheduler and runtime.scheduler.pending():return
    if all((p['done'] and not p['pendingPotions'] and not p.get('pendingCardRewards') and not p.get('pendingRelicRewards') and not p.get('pendingGoldRewards') and not p.get('removalRewards')) or p['hp']<=0 for p in s['players'].values()):
        if not any(p['hp']>0 for p in s['players'].values()):run_state.phase(s,'defeat')
        else:
            run_state.phase(s,s.pop('afterRewards','map'))
            if s['phase']=='map':s.pop('eventCombat',None)
        for p in s['players'].values():p['vote']=None

def event_action(s,p,a):
    if s.get('eventState'):
        from ..run.events.events import act
        act(s,p,a);return
    event=s['event'];option=a.get('option');c=None
    from ..combat.enchantments import can_enchant
    if (event=='Wellspring' and option=='bathe') or (event=='WhisperingHollow' and option=='hug') or (event=='SapphireSeed' and (option=='plant' and any(can_enchant(x,'Sown',in_deck=True) for x in p['deck']) or option=='eat' and any(run_state.upgradable(x) for x in p['deck']))):
        c=run_state.find_card(p['deck'],a.get('choice'))
        if event in ('Wellspring','WhisperingHollow'):require(run_state.removable(c),'永恒牌不能移除或变换。')
    if event=='Wellspring':
        if option=='bottle':run_state.potion_reward(s,p)
        elif option=='bathe':p['deck'].remove(c);run_state.obtain_card(s,p,run_state.new_card(s,'Guilty'))
        else:raise InvalidAction('无效的事件选择。')
    elif event=='WhisperingHollow':
        if option=='gold':
            require(p['gold']>=p['eventGold'],'金币不足。');p['gold']-=p['eventGold'];run_state.potion_reward(s,p,2)
        elif option=='hug':
            from ..run.events.transforms import replacement, replace_in_pile
            replace_in_pile(s,p,p['deck'],c,replacement(s,p,c,in_combat=False))
            damage.lose_hp(s,p,9)
        else:raise InvalidAction('无效的事件选择。')
    elif event=='UnrestSite':
        if option=='rest':damage.heal(p,p['maxHp']);run_state.obtain_card(s,p,run_state.new_card(s,'PoorSleep'))
        elif option=='kill':damage.lose_max_hp(s,p,8);run_state.random_relic(s,p)
        else:raise InvalidAction('无效的事件选择。')
    elif event=='SapphireSeed':
        if option=='eat':
            damage.heal(p,9)
            if c is not None:require(run_state.upgradable(c),'这张牌不能升级。');run_state.upgrade(c)
        elif option=='plant':
            from ..combat.enchantments import enchant
            if c is not None:enchant(c,'Sown',in_deck=True)
        else:raise InvalidAction('无效的事件选择。')
    elif event=='TabletOfTruth':
        count=p['eventCount']
        if option=='smash':require(count==0,'已经开始解读，不能再破坏。');damage.heal(p,20)
        elif option=='giveup':require(count>0,'请先选择解读或破坏。')
        elif option=='decipher':
            cost=3*(2**count) if count<4 else p['maxHp']-1
            if cost>=p['maxHp']:
                # The reference lets the player take a fatal page: maximum health
                # drops to one and the character dies.
                p['maxHp']=1;damage.lose_hp(s,p,p['hp'])
            else:
                damage.lose_max_hp(s,p,cost)
                cards=[c for c in p['deck'] if run_state.upgradable(c)]
                if count==4:
                    for c in cards:run_state.upgrade(c)
                elif cards:run_state.upgrade(draws.player_rng(s,p,'Rewards',lambda rng:rng.next_item(list(cards))))
            p['eventCount']+=1
            # Reading further is what the count gate is for; a player who took the
            # fatal page cannot read again, so the terminal state advances now.
            if p['eventCount']<5 and p['hp']>0:return
        else:raise InvalidAction('无效的事件选择。')
    p['done']=True;advance_if_ready(s)

def apply(state,uid,action):
    require(state.get('schema')==SCHEMA_VERSION and state.get('rules')==RULES_VERSION and state.get('content')==CONTENT_VERSION,'存档版本不兼容，请使用原版本扩展。')
    from .continuation import apply as resume_action
    return deepcopy(resume_action(state,uid,action,_apply))

def _apply(state,uid,action,*,_inplace=False):
    require(state.get('schema')==SCHEMA_VERSION and state.get('rules')==RULES_VERSION and state.get('content')==CONTENT_VERSION,'存档版本不兼容，请使用原版本扩展。')
    s=state if _inplace else deepcopy(state);battle_log.observe(s);run_state.ensure_player_seats(s);p=s['players'].get(str(uid));require(p is not None,'你不在此房间。')
    kind=action.get('type');terminal=s['phase'] in ('victory','defeat','abandoned')
    if kind=='pause':
        if not terminal:
            s['paused']=True
            for x in s['players'].values():x['ready']=False

    elif kind=='ready':
        require(not terminal and (s['paused'] or s['phase']=='lobby'),'当前不需要准备。')
        require(s.get('mode')=='solo' or len(s['players'])>=2,'多人模式至少需要 2 名玩家，单人请使用单人模式。')
        p['ready']=True
        if len(s['players'])>=(1 if s.get('mode')=='solo' else 2) and all(x['ready'] for x in s['players'].values()):
            s['paused']=False
            # Resuming ends the voting cycle: an old abandon vote must not count
            # towards a later pause's unanimity.
            for x in s['players'].values():x.pop('abandon',None)
            if s['phase']=='lobby':
                from ..run.map.journey import initialize
                initialize(s,len(s['players'])>1);run_state.phase(s,'map')

    elif kind=='abandon':
        require(not terminal,'本局已结束。')
        require(p['seat']==0,'只有房主可以放弃本局。')
        for x in s['players'].values():x.pop('abandon',None)
        run_state.phase(s,'abandoned');s['paused']=False
        for key in ('continuation','turnChoices','turnReady','pendingChoice','pendingDecision','effects'):s.pop(key,None)
    else:
        require((not s['paused'] or kind=='character' and s['phase']=='lobby') and not terminal,'游戏已暂停或结束。')
        require(action.get('phaseId')==s['phaseId'],'阶段已变化，请根据最新界面重新操作。')
        stage=s['phase']
        if s.get('pendingDecision'):
            require(kind=='decide','请先完成当前选择。')
        elif s.get('pendingChoice'):
            require(kind=='choose','请先完成当前选牌。')
        elif p.get('pendingCardRewards') or p.get('pendingRelicRewards') or p.get('pendingGoldRewards'):
            require(kind in ('goldReward','customReward','customRelicReward','reward','rewardRemove','skipRemoval','claimPotion','skipPotion','potion','dropPotion'),'请先处理待领取奖励。')
        if kind=='character':
            require(s['phase'] in ('lobby','map') and s['floor']==0 and s['turn']==0 and (not s.get('characterConfigured') or s['phase']=='lobby'),'仅能在开始攀登前选择职业。')
            character=action.get('character');require(isinstance(character,str) and character in CHARACTERS,'未知职业。')
            s['players'][str(uid)]=run_state.player(s,uid,p['name'],character,p.get('seat'))
            run_state.log(s,f"{p['name']} 选择 {CHARACTERS[character]['name']}")
        elif kind=='choose':
            from ..combat.effects import resolve
            resolve(s,p,action)
        elif kind=='play':require(stage=='combat','当前不在战斗中。');play.play(s,p,action)
        elif kind=='end':
            require(stage=='combat' and p['hp']>0 and not p['done'],'当前不能结束回合。');p['done']=True
            battle.commit_ready_turn(s)
        elif kind=='undoEnd':
            # Ignoring a stale or already-resolving undo is the whole contract,
            # so there is nothing to reject: the action is accepted and simply
            # decides nothing. It still counts as one action, because the
            # revision is the wrapper's to move and every accepted action moves
            # it once; that is what makes a retry idempotent at the transport.
            require(stage=='combat','当前不在战斗中。')
            battle.undo_end(s,p,action)
        elif kind in ('potion','dropPotion'):
            from ..run.events.events import potions_locked
            require(not potions_locked(s,p),'请先完成事件交易，当前不能使用或丢弃药水。')
            require(p['hp']>0,'倒下后不能使用药水。')
            item=next((x for x in p['potions'] if x['id']==action.get('potion')),None);require(item is not None,'药水已不存在。')
            if kind=='dropPotion':
                p['potions'].remove(item)
                from ..relics.hooks import inventory_changed
                inventory_changed(s,p)
            else:
                from ..run.potions import use
                use(s,p,item,action.get('target'))
        elif kind in ('claimPotion','skipPotion'):
            require(stage in ('reward','event','rest','shop','treasure') and p['pendingPotions'],'没有待领取药水。')
            item=next((item for item in p['pendingPotions'] if item['id']==action.get('potion')),None);require(item is not None,'奖励已变化。')
            if kind=='claimPotion':
                from ..run.potions import procure
                require(procure(s,p,item) or 'Sozu' in p['relics'],'药水栏已满，请在药水面板丢弃一瓶后领取。')
            p['pendingPotions'].remove(item);advance_if_ready(s)
        elif kind=='vote':
            require(stage=='map','当前不在地图。');nodes=map_routes(s);require(action.get('node') in [n['id'] for n in nodes],'路线无效。');p['vote']=action['node']
            if all(x['vote'] is not None for x in s['players'].values()):
                selected=map_vote(s,[x['vote'] for x in sorted(s['players'].values(),key=lambda x:x.get('seat',0))]);enter_route(s,next(n for n in nodes if n['id']==selected))
        elif kind=='treasurePick':
            from ..run.rewards.treasure import pick
            pick(s,p,action.get('index'))
        elif kind=='nextAct':
            require(stage=='actComplete' and 'journey' in s and not p['done'],'当前不能进入下一幕。')
            p['done']=True
            if all(x['done'] for x in s['players'].values()):
                from ..run.map.journey import advance_act
                advance_act(s);run_state.phase(s,'map');s['event']=None;s.pop('eventState',None)
                for member in s['players'].values():member['vote']=None
        elif kind=='goldReward':
            from ..run.rewards.gold import claim
            claim(s,p,action)
            if stage!='combat':advance_if_ready(s)
        elif kind=='customRelicReward':
            from ..run.rewards.custom import claim_relic
            claim_relic(s,p,action)
            if stage!='combat':advance_if_ready(s)
        elif kind=='customReward':
            from ..run.rewards.custom import claim
            claim(s,p,action)
            if stage!='combat':advance_if_ready(s)
        elif kind=='reward':
            require(stage=='reward' and not p['done'],'当前没有待领取的奖励。');ident=action.get('card')
            if ident in ('reroll','sacrifice'):
                from ..run.rewards.custom import alternate, recipe
                reward=p.setdefault('rewardMeta',{'recipe':recipe(p,source=s['encounterKind'])});reward['cards']=p['reward']
                alternate(s,p,reward,ident);p['reward']=reward['cards']
                if ident=='reroll':s['revision']+=1;return s
            elif ident!='skip':run_state.obtain_card(s,p,deepcopy(run_state.find_card(p.get('reward',[]),ident)))
            if p.get('extraRewardChoices'):
                p['reward']=p['extraRewardChoices'].pop(0);p.setdefault('rewardMeta',{}).pop('rerolled',None)
            else:p['done']=True;advance_if_ready(s)
        elif kind in ('rewardRemove','skipRemoval'):
            require(stage=='reward' and p.get('removalRewards',0)>0,'当前没有删牌奖励。')
            if kind=='rewardRemove':
                card=run_state.find_card(p['deck'],action.get('choice'));require(run_state.removable(card),'永恒牌不能移除。');p['deck'].remove(card)
            p['removalRewards']-=1;advance_if_ready(s)
        elif kind=='buy':
            require(stage=='shop' and not p['done'],'当前不能购物。')
            from ..run.shop import buy
            buy(s,p,action.get('item'))
        elif kind=='removeCard':
            require(stage=='shop' and not p['done'],'当前不能删牌。')
            from ..run.shop import remove_card
            remove_card(s,p,action.get('choice'))
        elif kind=='rest':
            require(stage=='rest' and not p['done'],'当前不能休息。')
            require(action.get('option') not in p.get('restUsed',[]),'本次营地已使用这个选项。')
            if action.get('option')=='heal':
                damage.heal(p,p['maxHp']*3//10+(15 if 'RegalPillow' in p['relics'] else 0))
                from ..relics.hooks import rest_heal
                rest_heal(s,p)
            elif action.get('option')=='mend':
                from .decisions import select
                require(len(s['players'])>1 and p['hp']>0,'愈合仅限多人营地的存活玩家。')
                allies=[member for member in s['players'].values() if member['id']!=p['id'] and member['hp']>0]
                require(allies,'没有可治疗的队友。')
                rows=[{'id':str(member['id']),'label':f"{member['name']}：{member['hp']}/{member['maxHp']} HP，恢复 {member['maxHp']*3//10} HP"} for member in allies]
                selected=select(s,p,'mend','愈合：选择一名队友，恢复其 30% 最大生命',rows,0,1)
                if not selected:return s
                target=s['players'].get(selected[0]['id'])
                require(target is not None and target['id']!=p['id'] and target['hp']>0,'队友已无法接受治疗。')
                damage.heal(target,target['maxHp']*3//10)
                from ..relics.hooks import rest_heal
                rest_heal(s,p)
            elif action.get('option')=='upgrade':c=run_state.find_card(p['deck'],action.get('choice'));require(run_state.upgradable(c),'这张牌不能升级。');run_state.upgrade(c)
            elif action.get('option')=='hatch':
                from ..run.map.quests import hatch
                hatch(s,p)
            elif action.get('option')=='dig':
                require('Shovel' in p['relics'],'没有铲子。')
                from ..relics.pool import pull
                run_state.relic(s,p,pull(s,p))
            elif action.get('option')=='lift':
                require('Girya' in p['relics'] and p.get('giryaLifts',0)<3,'当前不能举重。')
                p['giryaLifts']=p.get('giryaLifts',0)+1
            elif action.get('option')=='kindle':
                require('PumpkinCandle' in p['relics'],'没有南瓜蜡烛。');p['pumpkinCombats']=p.get('pumpkinCombats',0)+5
            elif action.get('option')=='clone':
                require('PaelsGrowth' in p['relics'],'没有佩尔的增生组织。')
                for c in list(p['deck']):
                    if c.get('enchantment',{}).get('key')=='Clone':run_state.obtain_card(s,p,run_state.copy_card(s,c))
            elif action.get('option')=='cook':
                from .decisions import select
                cards=[c for c in p['deck'] if run_state.removable(c)]
                require('MeatCleaver' in p['relics'] and len(cards)>=2,'烹饪需要两张可移除的牌。')
                rows=[{'id':c['id'],'label':card_view(c)['name']+'：'+card_view(c)['description']} for c in cards]
                chosen=select(s,p,'cook','烹饪：移除两张牌，或不选以取消',rows,0,2)
                require(len(chosen) in (0,2),'请选择两张牌，或不选以取消。')
                if not chosen:return s
                for row in chosen:p['deck'].remove(run_state.find_card(cards,row['id']))
                p['maxHp']+=5;damage.heal(p,5)
            else:raise InvalidAction('无效休息操作。')
            p.setdefault('restUsed',[]).append(action.get('option'))
            p['done']='MiniatureTent' not in p['relics'];advance_if_ready(s)
        elif kind=='sphere':
            require(stage=='event' and s.get('event')=='CrystalSphere' and not p['done'],'当前不能占卜。')
            require(not s.get('pendingChoice') and not s.get('pendingDecision'),'请先完成当前选择。')
            from ..run.events.events import sphere_act
            sphere_act(s,p,action)
        elif kind=='event':
            require(stage in ('event','ending') and not p['done'],'事件已结束。')
            if stage=='ending':
                from ..run.events.ending import act
                act(s,p,action)
            else:event_action(s,p,action)
        elif kind=='continue':
            require(stage!='treasure' or s.get('treasure',{}).get('resolved',True),'请等待全员选择宝箱遗物。')
            require((stage in ('shop','treasure') or stage=='rest' and 'MiniatureTent' in p['relics']) and not p['done'],'当前不能继续。');p['done']=True;advance_if_ready(s)
        else:raise InvalidAction('未知操作。')
    s['revision']+=1
    return s

def options(s,p):
    from .turn_tasks import choice_state
    blocked=bool((s.get('pendingChoice') or s.get('pendingDecision')) and not s.get('turnChoices')
                 and not any(str(s.get(key,{}).get('owner'))==str(p['id']) for key in ('pendingChoice','pendingDecision')))
    task_blocked=bool(s.get('turnChoices') and str(p['id']) not in {str(uid) for uid in s.get('turnReady',[])}
                      and not any(str(row['value']['owner'])==str(p['id']) for row in s['turnChoices']))
    s=choice_state(s,p['id'])
    def opt(id,label,action,choice=None):return {'id':id,'label':label,'action':action,'choice':choice}
    characters=[opt('character:'+key,f"职业：{value['name']} · {value['hp']} HP",{'type':'character','character':key}) for key,value in CHARACTERS.items() if key!=p.get('character','ironclad')]
    if s['phase'] in ('victory','defeat','abandoned'):return []
    if s['paused'] or s['phase']=='lobby':
        return ([opt('ready','准备 / 继续',{'type':'ready'})] if not p['ready'] and (s.get('mode')=='solo' or len(s['players'])>=2) else []) + (characters if s['phase']=='lobby' else [])
    if s.get('pendingChoice'):
        from ..combat.effects import choice_options
        return choice_options(s,p)
    if s.get('pendingDecision'):
        from .decisions import options as decision_options
        return decision_options(s,p)
    if blocked or task_blocked:return []
    reward_rows=[]
    if p.get('pendingGoldRewards'):
        from ..run.rewards.gold import options as gold_options
        reward_rows.extend(gold_options(p))
    if p.get('pendingCardRewards'):
        from ..run.rewards.custom import options as custom_options
        reward_rows.extend(custom_options(p))
    if p.get('pendingRelicRewards'):
        from ..run.rewards.custom import relic_options
        reward_rows.extend(relic_options(p))
    for item in p['pendingPotions']:
        name,description=POTIONS[item['key']]
        reward_rows.extend([opt('claim:'+item['id'],f'领取 {name}：{description}（满栏时先在药水面板丢弃）',{'type':'claimPotion','potion':item['id']}),opt('skip:'+item['id'],f'放弃本次 {name} 奖励',{'type':'skipPotion','potion':item['id']})])
    if s['phase']=='reward' and p.get('removalRewards'):
        reward_rows.extend([opt('rewardRemove',f"禁忌魔典：移除一张牌（剩余 {p['removalRewards']} 次）",{'type':'rewardRemove'},'deck'),opt('skipRemoval','跳过一次删牌奖励',{'type':'skipRemoval'})])
    if s['phase']=='reward' and not p['done']:
        cards=[card_view(c) for c in p.get('reward',[])]
        reward_rows.extend([opt(c['id'],f"{c['name']} [{cost_text(c)}] {c['description']}",{'type':'reward','card':c['id']}) for c in cards]+[opt('skip','跳过卡牌奖励',{'type':'reward','card':'skip'})])
        from ..run.rewards.custom import alternatives
        reward_rows.extend(opt(key,label,{'type':'reward','card':key}) for key,label in alternatives(p,p.get('rewardMeta',{})))
    if reward_rows:return reward_rows
    if p['done']:return []
    stage=s['phase']
    if stage=='map':return [opt(n['id'],KINDS[n['kind']]+(' · 毛皮大衣：敌人 1 HP' if n.get('furCoats') else '')+(' · 飞行（消耗 1 次）' if n.get('requiresFlight') else ''),{'type':'vote','node':n['id']}) for n in map_routes(s)]+(characters if s['floor']==0 and s['turn']==0 and not s.get('characterConfigured') else [])
    if stage=='actComplete':return [opt('nextAct','进入下一幕',{'type':'nextAct'})]
    if stage=='reward':
        cards=[card_view(c) for c in p.get('reward',[])]
        return [opt(c['id'],f"{c['name']} [{cost_text(c)}] {c['description']}",{'type':'reward','card':c['id']}) for c in cards]+[opt('skip','跳过卡牌奖励',{'type':'reward','card':'skip'})]
    if stage=='rest':
        rows=[opt('heal','休息：恢复 30% 最大生命'+('，额外恢复 15' if 'RegalPillow' in p['relics'] else ''),{'type':'rest','option':'heal'}),opt('upgrade','锻造：升级一张牌',{'type':'rest','option':'upgrade'},'deckUpgrade')]
        if len(s['players'])>1 and p['hp']>0 and any(member['id']!=p['id'] and member['hp']>0 for member in s['players'].values()):
            rows.append(opt('mend','愈合：为一名队友恢复其 30% 最大生命',{'type':'rest','option':'mend'}))
        if any(c['key']=='ByrdonisEgg' for c in p['deck']):rows.append(opt('hatch','孵化：让蛋变为飞鸟俯冲',{'type':'rest','option':'hatch'}))
        if 'Shovel' in p['relics']:rows.append(opt('dig','挖掘：获得一件随机遗物',{'type':'rest','option':'dig'}))
        if 'PumpkinCandle' in p['relics']:rows.append(opt('kindle','添火：南瓜蜡烛增加五场战斗',{'type':'rest','option':'kindle'}))
        if 'PaelsGrowth' in p['relics']:rows.append(opt('clone','复制：复制所有带克隆附魔的牌',{'type':'rest','option':'clone'}))
        if 'MeatCleaver' in p['relics'] and sum(run_state.removable(c) for c in p['deck'])>=2:rows.append(opt('cook','烹饪：移除两张牌，增加 5 最大生命',{'type':'rest','option':'cook'}))
        if 'Girya' in p['relics'] and p.get('giryaLifts',0)<3:rows.append(opt('lift',f"举重：每场战斗额外获得 1 力量（已举重 {p.get('giryaLifts',0)}/3）",{'type':'rest','option':'lift'}))
        rows=[row for row in rows if row['id'] not in p.get('restUsed',[])]
        if 'MiniatureTent' in p['relics']:rows.append(opt('leaveRest','离开营地',{'type':'continue'}))
        return rows
    if stage=='shop':
        from ..run.shop import detail, label, removal_price
        rows=[{**opt(x['id'],label(p,x),{'type':'buy','item':x['id']}),'shop':detail(p,x)} for x in p['shop']]
        if not p['removed']:rows.append({**opt('remove',f"删牌 · {removal_price(p)} 金币",{'type':'removeCard'},'deck'),'shop':{'kind':'removal','type':'removal','name':'删牌服务','description':'从牌组中移除一张牌。','price':removal_price(p),'sale':False}})
        return rows+[opt('continue','离开商店',{'type':'continue'})]
    if stage=='treasure':
        from ..run.rewards.treasure import options as treasure_options
        return treasure_options(s,p)
    if stage in ('event','ending'):
        if s.get('eventState'):
            from ..run.events.events import options as event_options
            return event_options(s,p)
        from ..combat.enchantments import can_enchant
        from ..text.events import label as L
        tablet=p['eventCount']
        decipher=('INITIAL.DECIPHER_1','DECIPHER_1.DECIPHER','DECIPHER_2.DECIPHER','DECIPHER_3.DECIPHER','DECIPHER_4.DECIPHER')[min(tablet,4)]
        choices={'Wellspring':[('bottle',L('WELLSPRING','INITIAL.BOTTLE'),None),('bathe',L('WELLSPRING','INITIAL.BATHE',BatheCurses=1),'deck')],
        'WhisperingHollow':[('gold',L('WHISPERING_HOLLOW','INITIAL.GOLD',Gold=p['eventGold']),None),('hug',L('WHISPERING_HOLLOW','INITIAL.HUG',HpLoss=9),'deck')],
        'UnrestSite':[('rest',L('UNREST_SITE','INITIAL.REST'),None),('kill',L('UNREST_SITE','INITIAL.KILL',MaxHpLoss=8),None)],
        'SapphireSeed':[('eat',L('SAPPHIRE_SEED','INITIAL.EAT',Heal=9),'deckUpgrade' if any(run_state.upgradable(c) for c in p['deck']) else None),('plant',L('SAPPHIRE_SEED','INITIAL.PLANT',Enchantment='播种'),'deckEnchant' if any(can_enchant(c,'Sown',in_deck=True) for c in p['deck']) else None)],
        'TabletOfTruth': [('decipher',L('TABLET_OF_TRUTH',decipher,DecipherMaxHpLoss=3*2**tablet if tablet<4 else p['maxHp']-1),None)]+([('smash',L('TABLET_OF_TRUTH','INITIAL.SMASH',SmashHPGain=20),None)] if tablet==0 else [('giveup',L('TABLET_OF_TRUTH','DECIPHER.GIVE_UP'),None)])}
        return [opt(k,label,{'type':'event','option':k},choice) for k,label,choice in choices[s['event']]]
    return []
