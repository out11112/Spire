"""Serializable card continuations. Choices suspend effects without repeating payment."""
from copy import deepcopy
from .. import engine as e
from ..core.continuation import current
from ..content.data import load as load_data

SPLASH_POOLS=load_data('splash_pool.json')


def splash_candidates(state,upgraded=False,player=None):
    player=player or next(iter(state['players'].values()))
    character=player.get('character','ironclad')
    eligible=[]
    pools=dict(SPLASH_POOLS)
    if character!='ironclad':
        from ..run.events.transforms import POOLS
        pools['Ironclad']=[row for row in POOLS['ironclad'] if row['inCombat'] and e.CARDS[row['key']]['kind']=='attack']
    for name,rows in pools.items():
        if name.lower()==character:continue
        for row in rows:
            constraint=row['constraint']
            if len(state['players'])==1 and constraint=='MultiplayerOnly':continue
            if len(state['players'])>1 and constraint=='SingleplayerOnly':continue
            # Missing dependencies are a development error. Never silently offer
            # a reduced pool because some handlers have not been implemented.
            e.require(row['key'] in e.CARDS,'跨界候选牌实现缺失：'+row['key'])
            eligible.append(row['key'])
    return [e.new_card(state,key,upgraded) for key in e.combat_card_generation_shuffle(state,eligible)[:3]]


def generated_cards(state, pool, count, exclude=(), kind=None, cost=None,rarity=None,*,replacement=False):
    from ..run.events.transforms import POOLS
    members={row['key'] for row in POOLS[pool]} if pool in POOLS else None
    eligible=[k for k,d in e.CARDS.items() if d['pool']==pool and d['rarity'] not in ('basic','ancient','event')
              and (members is None or k in members)
              and k not in exclude and not d['values'].get('noCombatGenerate')
              and not (len(state['players'])==1 and d['values'].get('multiplayerOnly'))
              and not (len(state['players'])>1 and d['values'].get('singleplayerOnly'))
              and (kind is None or d['kind']==kind)
              and (rarity is None or d['rarity']==rarity)
              and (cost is None or d['cost']==cost and not d['values'].get('xCost'))]
    if replacement:
        return [e.new_card(state,e.combat_card_generation(state,eligible)) for _ in range(count)] if eligible else []
    return [e.new_card(state,k) for k in e.combat_card_generation_shuffle(state,eligible)[:count]]


def prepend(state, player, operations):
    state['effects']=[{**operation,'owner':player['id']} for operation in operations]+state.get('effects',[])


def reserve_draw(state,player,count,force_exhaust=False):
    # Cascade reserves the entire batch before playing any card. A headbutt or
    # shuffle produced by the first card must not replace the second reserved card.
    operations=[]
    for _ in range(count):
        if not player['draw']:
            e.shuffle_draw(state,player)
        if not player['draw']:
            from ..text.battle_log import emit
            emit(state,f"{player['name']} 自动出牌未发动：抽牌堆与弃牌堆为空",'autoplayFailed',actor=player['id'],reason='emptyPiles')
            break
        operations.append({'op':'autoplay','card':player['draw'].pop(),'forceExhaust':force_exhaust})
    return operations


def select_now(state,player,operation):
    runtime=current()
    e.require(runtime is not None,'嵌套选牌必须通过游戏动作执行。')
    runtime.fence+=1;fence=runtime.fence
    prepend(state,player,[operation,{'op':'fence','id':fence}]);run(state,fence=fence)


def start(state, player, card, *, legacy=False):
    values=e.definition(card)['values'];operations=[]
    if legacy:
        if values.get('block'):operations.append({'op':'block','count':values['block']})
        if values.get('upgradeHand'):
            operations.append({'op':'select','source':'hand','destination':'upgrade','upgradeOnly':True,'minimum':1,'maximum':1,'title':'选择升级一张手牌'})
        else:operations.append({'op':'select','source':'hand','destination':'exhaust','minimum':1,'maximum':1,'title':'选择消耗一张手牌'})
        if values.get('draw'):operations.append({'op':'draw','count':values['draw']})
    if values.get('havoc'):operations.extend(reserve_draw(state,player,1,True))
    if values.get('cascade'):operations.extend(reserve_draw(state,player,card.get('capturedX',0)+values.get('cascadeBonus',0)))
    if values.get('beatDown'):
        eligible=[c for c in player['discard'] if e.definition(c)['kind']=='attack' and not e.definition(c)['values'].get('unplayable')]
        for chosen in e.stable_card_shuffle(state,'Shuffle',eligible)[:values['beatDown']]:
            operations.append({'op':'autoplayPile','source':'discard','cardId':chosen['id']})
    if values.get('catastrophe'):operations.extend({'op':'randomDrawPlay'} for _ in range(values['catastrophe']))
    if values.get('brand'):
        operations.extend([{'op':'hpLoss','count':values['hpLoss']},
                           {'op':'select','source':'hand','destination':'exhaust','minimum':1,'maximum':1,'title':'消耗一张手牌'},
                           {'op':'power','key':'strength','count':values['strength']}])
    if values.get('headbutt'):
        operations.append({'op':'select','source':'discard','destination':'draw','minimum':1,'maximum':1,'title':'选择一张弃牌放回抽牌堆顶'})
    if values.get('seekerStrike'):
        candidates=e.stable_card_shuffle(state,'CombatCardSelection',e.top_first(player['draw']))[:values['seekerStrike']]
        operations.append({'op':'select','source':'draw','destination':'hand','minimum':1,'maximum':1,'title':'选择一张候选牌加入手牌','cards':candidates})
    if values.get('drawDiscard'):
        discard_count=values.get('discardCount',values['drawDiscard'])
        operations.extend([{'op':'draw','count':values['drawDiscard']},
                           {'op':'select','source':'hand','destination':'discard','activeDiscard':True,'minimum':discard_count,'maximum':discard_count,'title':f'选择弃掉 {discard_count} 张手牌'}])
    if values.get('discardOnly'):
        operations.append({'op':'select','source':'hand','destination':'discard','activeDiscard':True,'minimum':values['discardOnly'],'maximum':values['discardOnly'],'title':f"选择弃掉 {values['discardOnly']} 张手牌"})
    if values.get('scrape'):operations.append({'op':'scrape','count':values['scrape']})
    if values.get('uproar'):operations.append({'op':'randomDrawPlay','kind':'attack'})
    if values.get('copyColorless'):
        operations.append({'op':'select','source':'hand','destination':'copy','colorlessOnly':True,'minimum':1,'maximum':1,'title':'选择一张无色手牌复制'})
    if values.get('photonCut'):
        operations.extend([{'op':'draw','count':values['photonCut']},
                           {'op':'select','source':'hand','destination':'draw','minimum':1,'maximum':1,'title':'将一张手牌放回抽牌堆顶'}])
    if values.get('graveblast'):operations.append({'op':'select','source':'discard','destination':'hand','minimum':1,'maximum':1,'title':'取回一张弃牌'})
    if values.get('grantKeyword'):
        operations.append({'op':'select','source':'hand','destination':'keyword','keyword':values['grantKeyword'],'minimum':1,'maximum':1,'title':'选择一张手牌赋予'+{'ethereal':'虚无','retain':'保留'}[values['grantKeyword']]})
    if values.get('thinkingAhead'):
        operations.append({'op':'draw','count':values['thinkingAhead']})
        operations.append({'op':'select','source':'hand','destination':'draw','minimum':1,'maximum':1,'title':'选择一张手牌放回抽牌堆顶'})
    if values.get('searchDraw'):
        operations.append({'op':'select','source':'draw','destination':'hand','kind':values['searchDraw'],'minimum':1,'maximum':1,'title':'从抽牌堆选择一张牌'})
    if values.get('purity'):
        operations.append({'op':'select','source':'hand','destination':'exhaust','minimum':0,'maximum':values['purity'],'title':f"选择至多 {values['purity']} 张手牌消耗"})
    if values.get('discovery'):
        operations.append({'op':'select','source':'generated','destination':'hand','minimum':0,'maximum':1,'title':'选择一张牌，本回合费用为 0',
                           'cards':generated_cards(state,player.get('character','ironclad'),3),'free':True})
    if values.get('splash'):
        operations.append({'op':'select','source':'generated','destination':'hand','minimum':0,'maximum':1,'title':'选择一张其他职业攻击牌，本回合免费',
                           'cards':splash_candidates(state,card['upgraded'],player),'free':True})
    operations.append({'op':'finish','card':deepcopy(card)})
    e.require(not state.get('pendingChoice'),'请先完成当前卡牌效果。')
    runtime=current();fence=None
    if runtime:
        runtime.fence+=1;fence=runtime.fence;operations.append({'op':'fence','id':fence})
    prepend(state,player,operations)
    run(state,fence=fence)


def run(state,*,fence=None):
    if state.get('_effectsRunning') and fence is None or state.get('pendingChoice'):return
    was_running=state.get('_effectsRunning',False)
    state['_effectsRunning']=True
    try:
        while state.get('effects') and not state.get('pendingChoice'):
            operation=state['effects'].pop(0);player=state['players'][str(operation['owner'])]
            if operation['op']=='fence':
                e.require(operation['id']==fence,'自动出牌恢复边界不一致。')
                if not state['effects']:state.pop('effects')
                return
            if operation['op']=='finish':
                e.settle_card(state,player,operation['card']);continue
            if player['hp']<=0:continue
            if operation['op']=='draw':
                e.draw(state,player,operation['count']);continue
            if operation['op']=='autoplayCard':
                autoplay(state,player,operation['card']);continue
            if operation['op']=='autoplayIdentity':
                for pile in ('hand','draw','discard','exhaust'):
                    card=next((c for c in player[pile] if c['id']==operation['cardId']),None)
                    if card:
                        player[pile].remove(card);autoplay(state,player,card);break
                continue
            if operation['op']=='autoplayDraw':
                prepend(state,player,reserve_draw(state,player,operation['count']));continue
            if operation['op']=='hpLoss':
                e.lose_hp(state,player,operation['count'],True);continue
            if operation['op']=='power':
                e.power(player,operation['key'],operation['count']);continue
            if operation['op']=='block':
                e.gain_block(state,player,operation['count']);continue
            if operation['op']=='scrape':
                drawn=e.draw(state,player,operation['count'])
                discarded=[card for card in drawn if card in player['hand'] and (e.energy_cost(state,player,card,clamp_zero=False)!=0 or e.definition(card)['values'].get('xCost'))]
                from .classes.silent import discard
                discard(state,player,discarded)
                continue
            if operation['op'] in ('autoplay','replay'):
                autoplay(state,player,operation['card'],force_exhaust=operation.get('forceExhaust',False),replay=operation['op']=='replay');continue
            if operation['op'] in ('autoplayPile','randomDrawPlay','randomHandAttack'):
                source=operation.get('source','hand' if operation['op']=='randomHandAttack' else 'draw')
                candidates=player[source]
                if operation.get('kind'):candidates=[card for card in candidates if e.definition(card)['kind']==operation['kind']]
                if operation['op']=='autoplayPile':
                    if operation.get('topOnly'):candidates=candidates[-1:]
                    candidates=[c for c in candidates if c['id']==operation['cardId']]
                elif operation['op']=='randomHandAttack':candidates=[c for c in candidates if e.definition(c)['kind']=='attack' and not e.definition(c)['values'].get('unplayable')]
                else:candidates=[c for c in candidates if not e.definition(c)['values'].get('unplayable')] or candidates
                if candidates:
                    if operation['op']=='randomDrawPlay':
                        # Catastrophe and Uproar: ``StableShuffle(Rng.Shuffle).FirstOrDefault()``
                        # over the draw pile, top card first.
                        card=e.stable_card_shuffle(state,'Shuffle',e.top_first(candidates))[0]
                    else:
                        # A random hand attack or pile card: ``CombatCardSelection.NextItem``.
                        card=e.combat_card_selection(state,candidates)
                    player[source].remove(card);autoplay(state,player,card)
                continue
            e.require(operation['op']=='select','未知的卡牌效果。')
            cards=operation.get('cards',player.get(operation['source'],[]))
            cards=[c for c in cards if (not operation.get('kind') or e.definition(c)['kind']==operation['kind']) and (not operation.get('upgradeOnly') or e.upgradable(c))]
            if operation.get('colorlessOnly'):cards=[c for c in cards if e.CARDS[c['key']]['pool'] in ('colorless','token') or e.definition(c)['values'].get('visualColorless')]
            if operation.get('keyword'):cards=[c for c in cards if not e.definition(c)['values'].get(operation['keyword'])]
            if operation.get('playableOnly'):cards=[c for c in cards if not e.definition(c)['values'].get('unplayable')]
            if operation['source']=='deck' and (operation.get('transformKey') or operation.get('transformableOnly')):cards=[c for c in cards if e.removable(c)]
            if not cards:continue
            state['serial']+=1
            state['pendingChoice']={**operation,'id':str(state['serial']),'cards':deepcopy(cards),
                                    'minimum':min(operation['minimum'],len(cards)),
                                    'maximum':min(operation['maximum'],len(cards))}
            runtime=current()
            if runtime:
                if runtime.vakuu:
                    resolve(state,player,{'cards':[c['id'] for c in cards[:state['pendingChoice']['maximum']]],'choiceId':state['pendingChoice']['id']});continue
                answer=runtime.answer(state)
                resolve(state,player,answer);continue
            return
        if state.get('pendingChoice'):return
        state.pop('effects',None)
    finally:
        if was_running:state['_effectsRunning']=True
        else:state.pop('_effectsRunning',None)
    e.after_card(state)


def autoplay(state,player,card,force_exhaust=False,replay=False,target=None,spend_resources=False):
    if player['hp']<=0 or not any(enemy['hp']>0 or enemy.get('awaitingRevive') for enemy in state['enemies']):
        from ..text.battle_log import emit
        destination=next((pile for pile in ('hand','draw','discard','exhaust','inPlay') if any(c['id']==card['id'] for c in player.get(pile,[]))),'removed')
        emit(state,f"自动出牌 {e.card_view(card)['name']} 未发动：行动者倒下或战斗结束；最终去向 {destination}",'autoplayFailed',actor=player['id'],card=card['key'],reason='combatEndedOrActorDown',destination=destination)
        return
    from .afflictions import ringing_blocks, bound_blocks, smog_blocks
    from ..text.battle_log import emit
    def failed(reason):
        emit(state,f"{player['name']} 自动出牌 {e.card_view(card)['name']} 未发动：{reason}",'autoplayFailed',actor=player['id'],card=card['key'],reason=reason)
        e.settle_card(state,player,card,played=False)
        destination=next((pile for pile in ('hand','draw','discard','exhaust','inPlay') if any(c['id']==card['id'] for c in player.get(pile,[]))),'removed')
        emit(state,f"{e.card_view(card)['name']} 最终去向：{destination}",'autoplayDestination',actor=player['id'],card=card['key'],destination=destination)
    definition=e.combat_definition(player,card)
    if force_exhaust:card['forceExhaust']=True
    if not replay and 'VelvetChoker' in player['relics'] and player.get('velvetChokerPlayed',0)>=6:failed('天鹅绒项圈：本回合已打出六张牌');return
    if not replay and (ringing_blocks(player,card) or bound_blocks(player,card) or smog_blocks(player,card)):failed('鸣响' if ringing_blocks(player,card) else '束缚' if bound_blocks(player,card) else '烟雾');return
    target=card.get('replayTarget') if replay else target
    if definition['target'] in ('enemy','ally') and target is None:
        candidates=([enemy for enemy in state['enemies'] if enemy['hp']>0] if definition['target']=='enemy' else
                    [ally for ally in state['players'].values() if ally['hp']>0 and ally['id']!=player['id']])
        if not candidates:failed('没有有效目标');return
        # Enemy targets ride the run's CombatTargets stream. A random *ally* has no
        # confirmed counterpart in the reference, so it keeps the local domain
        # rather than being moved onto a stream that may not own it.
        target=(e.random_enemy(state,candidates) if definition['target']=='enemy'
                else e.random_target(state,candidates))['id']
    if definition['values'].get('unplayable') or not replay and player['powers'].get('sloth') and player.get('slothPlays',0)>=player['powers']['sloth']:
        failed('不可打出' if definition['values'].get('unplayable') else '懒惰：本回合已达到出牌上限');return
    runtime=current()
    if runtime:
        runtime.fence+=1;fence=runtime.fence
        prepend(state,player,[{'op':'fence','id':fence}]);runtime.depth+=1
        block_context={key:player[key] for key in ('blockCard','blockDefend','blockPlay') if key in player}
        try:
            e.play(state,player,{'target':target},automatic_card=card,replay=replay,spend_resources=spend_resources)
            run(state,fence=fence)
        finally:
            runtime.depth-=1
            for key in ('blockCard','blockDefend','blockPlay'):
                if key in block_context:player[key]=block_context[key]
                else:player.pop(key,None)
    else:e.play(state,player,{'target':target},automatic_card=card,replay=replay,spend_resources=spend_resources)


def end_turn(state,player):
    operations=[{'op':'randomHandAttack'} for _ in range(player['powers'].get('stampede',0))]
    operations.extend({'op':'autoplayPile','source':'exhaust','cardId':card['id']} for card in list(player['exhaust']) if e.definition(card)['values'].get('howlFromBeyond'))
    # Snapshot listeners in pile order; each checks the current top when reached.
    listeners=player['hand']+list(reversed(player['draw']))+player['discard']+player['exhaust']+player.get('inPlay',[])
    operations.extend({'op':'autoplayPile','source':'draw','cardId':card['id'],'topOnly':True}
                      for card in listeners if e.definition(card)['values'].get('invincibleTop'))
    prepend(state,player,operations);run(state)


def refresh_choice(state,choice):
    """Keep original candidate identities and revalidate their current cards."""
    if choice['source']=='generated':return
    player=state['players'][str(choice['owner'])]
    identities={card['id'] for card in choice['cards']}
    cards=[card for card in player[choice['source']] if card['id'] in identities]
    cards=[card for card in cards if (not choice.get('kind') or e.definition(card)['kind']==choice['kind'])
           and (not choice.get('upgradeOnly') or e.upgradable(card))
           and (not choice.get('keyword') or not e.definition(card)['values'].get(choice['keyword']))
           and (not choice.get('playableOnly') or not e.definition(card)['values'].get('unplayable'))]
    if choice.get('colorlessOnly'):
        cards=[card for card in cards if e.CARDS[card['key']]['pool'] in ('colorless','token') or e.definition(card)['values'].get('visualColorless')]
    if choice['source']=='deck' and (choice.get('transformKey') or choice.get('transformableOnly')):
        cards=[card for card in cards if e.removable(card)]
    if choice.get('destination')=='upgrade':cards=[card for card in cards if e.upgradable(card)]
    if choice['source']=='deck' and choice.get('destination') in ('removeDeck','randomTransform','transform'):
        cards=[card for card in cards if e.removable(card)]
    if choice.get('destination')=='enchant':
        from .enchantments import can_enchant
        cards=[card for card in cards if can_enchant(card,choice['enchantment'],in_deck=choice['source']=='deck')]
    choice['cards']=deepcopy(cards)
    choice['minimum']=min(choice['minimum'],len(cards));choice['maximum']=min(choice['maximum'],len(cards))


def validate_choice(state,player,action):
    choice=state.get('pendingChoice')
    e.require(choice and choice['owner']==player['id'] and action.get('choiceId')==choice['id'],'选牌请求已失效或不属于你。')
    selected=action.get('cards')
    e.require(isinstance(selected,list) and all(isinstance(ident,str) for ident in selected),'请选择有效卡牌。')
    e.require(len(set(selected))==len(selected) and choice['minimum']<=len(selected)<=choice['maximum'],'选择数量不符合要求。')
    # Validate every selected identity before moving any card.
    for ident in selected:e.find_card(choice['cards'],ident)
    source=choice['cards'] if choice['source']=='generated' else player[choice['source']]
    cards=[e.find_card(source,ident) for ident in selected]
    return choice,source,cards


def resolve(state, player, action):
    choice,source,cards=validate_choice(state,player,action)
    state.pop('pendingChoice')
    if choice.get('activeDiscard'):
        from .classes.silent import discard
        discard(state,player,cards,draw_count=len(cards) if choice.get('drawSelected') else 0);run(state);return
    for card in cards:
        if choice['destination']=='enchant':
            from .enchantments import enchant
            enchant(card,choice['enchantment'],in_deck=choice['source']=='deck',amount=choice.get('enchantmentAmount',1));continue
        if choice['destination']=='knowledge':
            values=e.definition(card)['values'];e.debuff(state,player,player,values['knowledgePower'],values['knowledgeAmount'])
            continue
        if choice['destination']=='freeCombat':
            e.free_card(card,combat=True);card.pop('potionTurnCost',None);continue
        if choice['destination']=='randomTransform':
            from ..run.events.transforms import replacement, replace_in_pile
            # A transform draws from the player's Transformations stream; only the
            # relic that reshuffles the whole deck uses the run's Niche stream.
            # Event-driven transforms pass their own event domain, which is not a
            # stream in the reference and falls back to Transformations.
            rng_source='niche' if choice.get('stream')=='niche' else 'transformations'
            new=replacement(state,player,card,in_combat=choice['source']!='deck',source=rng_source)
            if choice.get('upgradeTransform') and e.upgradable(new):e.upgrade(new)
            replace_in_pile(state,player,source,card,new)
            continue
        if choice['destination']=='removeDeck':
            e.require(choice['source']=='deck' and e.removable(card),'这张牌不能移除。')
            source.remove(card);continue
        if choice['destination']=='transfigure':
            values=e.definition(card)['values']
            if not values.get('xCost') and not values.get('unplayable'):e.change_cost(card,1,mode='add')
            card['extraReplays']=card.get('extraReplays',0)+1
            continue
        if choice['destination']=='transform':
            from ..run.events.transforms import replace_in_pile
            upgrade_after=choice.get('upgradeAfterTransform',False)
            replacement=e.new_card(state,choice['transformKey'],choice.get('upgraded',False) and not upgrade_after)
            replace_in_pile(state,player,source,card,replacement)
            if upgrade_after and choice.get('upgraded'):e.upgrade(replacement)
            continue
        if choice['destination']=='autoplayRepeated':
            for _ in range(choice['repeat']):
                if player['hp']<=0 or not any(x['hp']>0 for x in state['enemies']):break
                for pile in ('hand','draw','discard','exhaust'):
                    player[pile][:]=[c for c in player[pile] if c['id']!=card['id']]
                autoplay(state,player,card)
            continue
        if choice['destination']=='upgrade':e.upgrade(card);continue
        if choice['destination']=='copy':
            for _ in range(choice.get('copies',1)):e.add_generated(state,player,e.copy_card(state,card))
            continue
        if choice['destination']=='keyword':
            if choice.get('temporary'):card[choice['keyword']+'ThisTurn']=True
            else:card.setdefault('addedKeywords',[]).append(choice['keyword'])
            continue
        if choice['destination']=='nightmare':
            from .power_order import queue_nightmare
            queue_nightmare(state,player,card);continue
        source.remove(card)
        if choice.get('free'):e.free_card(card)
        if choice['destination']=='hand':
            if choice['source']=='generated':e.add_generated(state,player,card,creator=state['players'].get(str(choice.get('creator')),player))
            else:e.add_to_hand(state,player,card)
        elif choice['destination']=='exhaust':e.exhaust(state,player,card)
        elif choice['destination']=='deck':e.obtain_card(state,player,card)
        else:player[choice['destination']].append(card)
    run(state)


def choice_options(state, player):
    from ..text.choices import display_row
    choice=state['pendingChoice']
    if choice['owner']!=player['id']:return []
    rarity_order={key:i for i,key in enumerate(('none','basic','common','uncommon','rare','ancient','event','token','status','curse','quest'))}
    cards=sorted(choice['cards'],key=lambda c:(rarity_order.get(e.CARDS[c['key']]['rarity'],0),c['key'],c['id']))
    live={card['id']:card for card in player.get(choice.get('source'),[])}
    rows=[{'id':card['id'],**display_row(state,player,[live.get(card['id'],card)],choice=choice)} for card in cards]
    if choice['maximum']==1:
        for row in rows:row['action']={'type':'choose','choiceId':choice['id'],'cards':[row['id']]}
        if choice['minimum']==0:rows.append({'id':'skip','label':'跳过','action':{'type':'choose','choiceId':choice['id'],'cards':[]}})
        return rows
    for row in rows:row['pick']=row['id']
    return rows+[{'id':'confirmChoice','label':'确认选择','action':{'type':'choose','choiceId':choice['id'],'cards':[]}}]
