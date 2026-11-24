"""Private, saved card rewards offered outside the ordinary combat reward page."""
from copy import deepcopy
from ... import engine as e


def finish_nested(state,player):
    """Wait for generated rewards before returning to the acquiring effect.

    Decisions are replayed inside the parent action, including potion inventory
    changes, so a save between rewards cannot complete the parent prematurely.
    """
    from ...core.decisions import select
    from ..potions import capacity, procure
    from ...relics.hooks import inventory_changed
    while player.get('pendingCardRewards') or player.get('pendingRelicRewards') or player.get('pendingPotions'):
        rows=[]
        for reward in player.get('pendingCardRewards',[]):
            for card in reward['cards']:
                view=e.card_view(card)
                rows.append({'id':reward['id']+':'+card['id'],'label':f"领取 {view['name']}：{view['description']}",
                             'operation':'card','reward':reward['id'],'card':card['id']})
            rows.append({'id':reward['id']+':skip','label':'跳过这份卡牌奖励','operation':'card','reward':reward['id'],'card':'skip'})
            if 'recipe' in reward:
                for choice,label in alternatives(player,reward):rows.append({'id':reward['id']+':'+choice,'label':label,'operation':'card','reward':reward['id'],'card':choice})
        for row in relic_options(player):rows.append({**row,'operation':'relic'})
        for potion in player.get('pendingPotions',[]):
            name=e.POTIONS[potion['key']][0]
            if len(player['potions'])<capacity(player) or 'Sozu' in player['relics']:
                rows.append({'id':'potion:'+potion['id'],'label':'领取 '+name,'operation':'potion','potion':potion['id']})
            rows.append({'id':'skipPotion:'+potion['id'],'label':'跳过 '+name,'operation':'skipPotion','potion':potion['id']})
        if player.get('pendingPotions'):
            for potion in player['potions']:
                rows.append({'id':'dropPotion:'+potion['id'],'label':'丢弃已持有的 '+e.POTIONS[potion['key']][0],
                             'operation':'dropPotion','potion':potion['id']})
        selected=select(state,player,'rewardSet','完成遗物产生的奖励',rows)[0]
        operation=selected['operation']
        if operation=='card':
            claim(state,player,{'reward':selected['reward'],'card':selected['card']})
        elif operation=='relic':claim_relic(state,player,selected['action'])
        else:
            queue=player['potions'] if operation=='dropPotion' else player['pendingPotions']
            potion=next(p for p in queue if p['id']==selected['potion'])
            if operation=='potion':e.require(procure(state,player,potion) or 'Sozu' in player['relics'],'药水栏已满。')
            queue.remove(potion)
            if operation=='dropPotion':inventory_changed(state,player)


def required_relics(state,player,keys):
    from ...core.decisions import select
    remaining=list(enumerate(keys))
    while remaining:
        rows=[]
        for index,key in remaining:
            name,description=e.RELICS.get(key,(key,'效果尚未实现，领取将拒绝'))
            rows.append({'id':'required:'+str(index),'label':f'领取 {name}：{description}','index':index,'relic':key})
        selected=select(state,player,'requiredRelics','领取全部遗物（不可跳过）',rows)[0]
        e.relic(state,player,selected['relic'])
        finish_nested(state,player)
        remaining=[item for item in remaining if item[0]!=selected['index']]


def resolve(rngs,ref):
    """Materialise a saved stream reference.

    A reward spec has to survive ``json.dumps``, so when a draw comes off a
    stream other than the default one the spec carries a *description* of that
    stream rather than the stream itself. Only events are referenced so far.
    """
    e.require(rngs is not None,'缺少随机流。')
    if ref['kind']=='event':return rngs.event(ref['name'],ref['seat'])
    raise e.InvalidAction('未知的随机流。')


def queue_relic(state,player,rarity=None,*,rng=None):
    from ...relics.pool import pull, rarity_from
    if rng is not None:
        # ``RelicReward`` with an rng override rolls the rarity and pulls from
        # the front off that stream.
        rarity=rarity_from(rng)
    key=pull(state,player,rarity);state['serial']+=1
    reward={'id':'relicReward:'+str(state['serial']),'key':key}
    player.setdefault('pendingRelicRewards',[]).append(reward)
    return reward


def relic_options(player):
    rows=[]
    for reward in player.get('pendingRelicRewards',[]):
        name,description=e.RELICS.get(reward['key'],(reward['key'],'效果尚未实现，领取将拒绝'))
        for choice,label in [('claim',f'领取 {name}：{description}'),('skip',f'跳过 {name}')]:
            rows.append({'id':reward['id']+':'+choice,'label':label,
                         'action':{'type':'customRelicReward','reward':reward['id'],'card':choice}})
    return rows


def claim_relic(state,player,action):
    queue=player.get('pendingRelicRewards',[])
    reward=next((r for r in queue if r['id']==action.get('reward')),None)
    e.require(reward is not None and action.get('card') in ('claim','skip'),'遗物奖励已变化。')
    if action['card']=='claim':
        e.relic(state,player,reward['key'])
        if reward.get('wax'):player.setdefault('waxRelics',[]).append(reward['key'])
    queue.remove(reward)


def offer_relic(state,player,*,key=None,skippable=True):
    """Populate once from the complete bag, then suspend for private acceptance."""
    from ...relics.pool import pull, DATA
    from ...core.decisions import select
    key=key if key is not None else pull(state,player)
    e.require(key in DATA,'未知遗物奖励。')
    name,description=e.RELICS.get(key,(key,'效果尚未实现，领取将拒绝；可保留或跳过奖励'))
    rows=[{'id':'claim','label':f'领取 {name}：{description}','relic':key}]
    if skippable:rows.append({'id':'skip','label':'跳过本次遗物奖励'})
    selected=select(state,player,'relicReward','遗物奖励',rows)[0]
    if selected['id']=='claim':e.relic(state,player,key)
    return key if selected['id']=='claim' else None


def recipe(player,*,source='other',count=3,pools=None,rarity=None,kind=None,uniform=False,pool_modifications=True,upgrade_all=False,no_upgrade_roll=False,stream=None):
    spec=dict(source=source,count=count,pools=[player['character']] if pools is None else list(pools),rarity=rarity,kind=kind,uniform=uniform,pool_modifications=pool_modifications,upgrade_all=upgrade_all,no_upgrade_roll=no_upgrade_roll)
    # Only present when the draws come off a stream other than the default, so
    # ordinary specs keep their existing shape.
    if stream is not None:spec['stream']=dict(stream)
    return spec


def populate(state,player,spec,*,rngs=None,rng=None):
    if rng is None and spec.get('stream'):rng=resolve(rngs,spec['stream'])
    choices=e.card_choices(state,player,[d for d in e.CARDS.values() if d['pool'] in spec['pools']],source=spec['source'],count=spec['count'],act_index=state.get('actIndex',0),is_reward=True,
                           uniform=spec.get('uniform',False),pool_modifications=spec.get('pool_modifications',True),rarity_filter=spec.get('rarity'),kind_filter=spec.get('kind'),no_upgrade_roll=spec.get('no_upgrade_roll',False),rng=rng)
    cards=[e.new_card(state,row['key'],row['upgraded']) for row in choices]
    if spec.get('upgrade_all'):
        for card in cards:
            if e.upgradable(card):e.upgrade(card)
    return cards


def offer_cards(state,player,*,rng=None,stream=None,**kwargs):
    spec=recipe(player,stream=stream,**kwargs)
    return offer_instances(state,player,populate(state,player,spec,rng=rng),spec=spec)


def offer_instances(state,player,cards,*,special=False,spec=None):
    from ...relics.hooks import card_reward_options
    if not special:card_reward_options(player,cards,state)
    state['serial']+=1
    reward={'id':'reward:'+str(state['serial']),'cards':cards}
    if not special:reward['recipe']=spec if spec is not None else recipe(player,count=len(cards),pools=[])
    player.setdefault('pendingCardRewards',[]).append(reward)
    return reward


def options(player):
    from ...text.choices import display_row
    rows=[]
    for index,reward in enumerate(player['pendingCardRewards']):
        for card in reward['cards']:
            rows.append({'id':reward['id']+':'+card['id'],
                         **display_row(None,player,[card],prefix=f"奖励 {index+1}：",choice={'source':'deck'}),
                         'action':{'type':'customReward','reward':reward['id'],'card':card['id']}})
        rows.append({'id':reward['id']+':skip','label':f'跳过卡牌奖励 {index+1}',
                     'action':{'type':'customReward','reward':reward['id'],'card':'skip'}})
        if 'recipe' in reward:
            for choice,label in alternatives(player,reward):rows.append({'id':reward['id']+':'+choice,'label':label,'action':{'type':'customReward','reward':reward['id'],'card':choice}})
    return rows


def claim(state,player,action):
    queue=player.get('pendingCardRewards',[])
    reward=next((r for r in queue if r['id']==action.get('reward')),None)
    e.require(reward is not None,'奖励已变化。')
    if action.get('card') in ('reroll','sacrifice'):
        alternate(state,player,reward,action['card'])
        if action['card']=='sacrifice':queue.remove(reward)
        return
    if action.get('card')!='skip':e.obtain_card(state,player,deepcopy(e.find_card(reward['cards'],action.get('card'))))
    queue.remove(reward)


def alternatives(player,reward):
    result=[]
    if 'Driftwood' in player['relics'] and not reward.get('rerolled'):result.append(('reroll','漂流木：重抽本份奖励（一次）'))
    if 'PaelsWing' in player['relics']:result.append(('sacrifice','献祭本份奖励（每两份获得一件遗物）'))
    return result


def alternate(state,player,reward,choice):
    e.require('recipe' in reward and choice in dict(alternatives(player,reward)),'该奖励不能执行这个操作。')
    if choice=='reroll':
        from ...relics.hooks import card_reward_options
        reward['rerolled']=True
        if reward['recipe'].get('stream'):
            from ...rng import streams
            with streams.open(state) as rngs:
                reward['cards']=populate(state,player,reward['recipe'],rngs=rngs)
        else:
            reward['cards']=populate(state,player,reward['recipe'])
        card_reward_options(player,reward['cards'],state)
    else:
        player['paelsWingSacrifices']=player.get('paelsWingSacrifices',0)+1
        if player['paelsWingSacrifices']%2==0:
            from ...relics.pool import pull
            e.relic(state,player,pull(state,player))
