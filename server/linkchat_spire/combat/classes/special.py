"""Lifecycle effects for ancient/event cards, separate from acquisition events."""
from ... import engine as e


def before_card(state,player,card,replay):
    if player['powers'].get('sloth'):player['slothPlays']=player.get('slothPlays',0)+1
    if replay:return
    d=e.definition(card);v=d['values']
    destination='discard'
    if d['kind']=='power' or v.get('exhaust') or card.get('forceExhaust'):destination='exhaust'
    elif v.get('returnToHand'):destination='hand'
    elif v.get('returnToTop'):destination='draw'
    for key,amount in list(player['powers'].items()):
        if not amount:continue
        if key=='corruption' and d['kind']=='skill':destination='exhaust'
        elif key=='nostalgia' and destination=='discard' and d['kind'] in ('attack','skill') and player.get('actionCards',0)<amount:
            card['nostalgiaReturn']=True;destination='draw'
        elif key=='rebound' and destination=='discard':
            card['reboundReturn']=True;destination='draw';e.power(player,'rebound',-1)


def apply_card(state,player,card,targets):
    from .defect import combat_cards
    from ..effects import generated_cards
    from ...run.potions import select
    v=e.definition(card)['values']
    if v.get('removeDeprecated'):player['deck']=[c for c in player['deck'] if c['id']!=card['id']]
    for key in ('helloWorld','rebound','curious','improvement'):
        if v.get(key):e.power(player,key,v[key])
    if v.get('feedingFrenzy'):e.power(player,'strength',v['feedingFrenzy']);e.power(player,'feedingFrenzy',v['feedingFrenzy'])
    if v.get('abundance'):
        cards=generated_cards(state,player.get('character','ironclad'),3,kind='power')
        for c in cards:e.upgrade(c)
        select(state,player,'generated','hand',cards=cards,free=True,title='富足：选择一张已升级能力牌，本回合免费')
    if v.get('apotheosis'):
        for c in combat_cards(state,player):
            if c['id']!=card['id'] and e.upgradable(c):e.upgrade(c)
    if v.get('brightestFlame'):
        player['energy']+=v['brightestFlame'];e.draw(state,player,v['brightestFlame'])
        maximum=player['maxHp']-2
        if player['hp']>maximum:e.hit(state,player,player,player['hp']-maximum,True,True,unblockable=True)
        player['maxHp']=max(1,maximum);player['hp']=min(player['hp'],player['maxHp'])
    if v.get('maul'):
        for c in combat_cards(state,player):
            if c['key']=='Maul':c['bonusDamage']=c.get('bonusDamage',0)+v['maul']
    if v.get('neowsFury'):
        maximum=min(v['neowsFury'],10-len(player['hand']))
        if maximum:select(state,player,'discard','hand',count=maximum,minimum=0,title='涅奥之怒：取回弃牌，可跳过')
    if v.get('wish'):select(state,player,'draw','hand',title='许愿：从抽牌堆取一张牌')
    if v.get('stun'):
        for target in targets:
            if target['hp']>0:target['stunned']=True
    if v.get('distraction') or v.get('scienceChaos'):
        for c in generated_cards(state,player.get('character','ironclad'),1,kind='skill' if v.get('distraction') else None):
            e.free_card(c);e.add_generated(state,player,c)
    if v.get('dualWield'):
        cards=[c for c in player['hand'] if e.definition(c)['kind'] in ('attack','power')]
        select(state,player,'hand','copy',cards=cards,copies=v['dualWield'],title='双持：复制一张攻击或能力手牌')
    if v.get('enlightenment'):
        for c in player['hand']:
            if e.definition(c)['values'].get('unplayable') or e.definition(c)['values'].get('xCost'):continue
            e.change_cost(c,1,expires=('combat',) if card['upgraded'] else ('turn','play'),reduce_only=True)
    if v.get('entrench'):e.gain_block(state,player,player['block'],True,card_source=True)
    if v.get('metamorphosis'):
        cards=[]
        for _ in range(v['metamorphosis']):cards+=generated_cards(state,player.get('character','ironclad'),1,kind='attack')
        for c in cards:
            e.free_card(c,combat=True);e.add_generated(state,player,c,'draw');player['draw'].remove(c)
            e.insert_at_random(state,player['draw'],c,draw_pile=True)
    if v.get('stack'):e.gain_block(state,player,len(player['discard'])+v.get('stackBase',0))


def before_draw(state,player):
    amount=player.get('helloWorldAtTurnStart',player['powers'].get('helloWorld',0))
    if player['powers'].get('helloWorld') and amount>0:
        from ..effects import generated_cards
        for card in generated_cards(state,player.get('character','ironclad'),amount,rarity='common'):e.add_generated(state,player,card)


def after_block_cleared(state,player):
    if not player.get('toricInstances'):return
    for record in list(player.get('toricInstances',[])):
        e.gain_block(state,player,record['block'],True);record['left']-=1
        if not record['left']:player['toricInstances'].remove(record)
    player['powers']['toricToughness']=sum(r['left'] for r in player.get('toricInstances',[]))


def turn_end(state,player):
    player['powers'].pop('rebound',None)
    for pile in ('hand','draw','discard','exhaust'):
        for card in player[pile]:e.expire_cost(card,'turn');card.pop('enlightenmentTurn',None)


def after_side_end_late(state,player):
    if player['hp']>0 and player['powers'].get('disintegration'):
        e.hit(state,player,player,player['powers']['disintegration'],True)


def after_combat(state,player):
    for _ in range(player['powers'].get('improvement',0)):
        cards=[c for c in player['deck'] if e.upgradable(c)]
        if not cards:break
        e.upgrade(e.combat_card_selection(state,cards))


def knowledge_choice(state,enemy):
    from ...run.potions import select
    index=enemy.get('knowledgeCount',0)
    e.require(index<3,'知识恶魔已完成三次抉择。')
    for player in state['players'].values():
        if player['hp']<=0:continue
        cards=[e.new_card(state,'Disintegration'),e.new_card(state,('MindRot','Sloth','WasteAway')[index])]
        cards[0]['knowledgeAmount']=6+index
        select(state,player,'generated','knowledge',cards=cards,title='知识恶魔：选择承受的代价')
    enemy['knowledgeCount']=index+1
