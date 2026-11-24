"""Shop relic effects shared by card and reward lifecycles."""
DATA={
 'BurningSticks':('燃烧木棍','每场首次消耗自己的技能牌后，将其复制加入手牌'),
 'DingyRug':('肮脏地毯','普通卡牌奖励池加入无色牌'),
 'GhostSeed':('幽灵种子','战斗中基础打击与防御获得虚无'),
 'GnarledHammer':('扭曲锤子','选择至多三张攻击牌附魔锋利 3'),
 'Kifuda':('木札','选择至多三张牌附魔伶俐 3'),
 'LavaLamp':('熔岩灯','本场未受到可格挡伤害时，升级战斗中的卡牌奖励'),
 'MiniatureTent':('微型帐篷','营地可使用每种可用选项一次，也可随时离开'),
 'MysticLighter':('神秘打火机','自己的附魔攻击牌额外造成 9 基础伤害'),
 'PunchDagger':('拳刃','选择一张攻击牌附魔动量 5'),
 'RingingTriangle':('三角铃鼓','首回合结束不丢弃手牌，虚无仍正常结算'),
 'RoyalStamp':('王室印章','选择一张攻击或技能牌获得固有和保留'),
 'Toolbox':('工具箱','首回合抽牌前，从三张不同无色牌中选择一张加入手牌'),
 'UndyingSigil':('不死符文','敌人灾厄不低于其生命时，对你的攻击伤害减半'),
 'VitruvianMinion':('维特鲁威仆从','自己的仆从牌伤害和格挡翻倍'),
 'WingCharm':('羽翼护符','每份卡牌奖励随机一张合格牌附魔迅速 1'),
}

def obtained(state,player,key):
    from .. import engine as e
    from ..core.decisions import select
    from ..combat.enchantments import can_enchant, enchant
    specs={'GnarledHammer':('Sharp',3,0,3),'Kifuda':('Adroit',3,0,3),'PunchDagger':('Momentum',5,1,1),'RoyalStamp':('RoyallyApproved',1,1,1)}
    if key not in specs:return
    enchantment,amount,minimum,maximum=specs[key]
    cards=[c for c in player['deck'] if can_enchant(c,enchantment,in_deck=True)]
    if key=='RoyalStamp':cards=e.niche_shuffled(state,cards)
    if not cards:return
    rows=[{'id':c['id'],'label':e.card_view(c)['name']+'：'+e.card_view(c)['description']} for c in cards]
    chosen=select(state,player,'enchantDeck',DATA[key][0]+'：选择附魔牌',rows,min(minimum,len(rows)),min(maximum,len(rows)))
    for row in chosen:enchant(e.find_card(cards,row['id']),enchantment,in_deck=True,amount=amount)

def entered_card(player,card):
    from .. import engine as e
    d=e.definition(card)
    if 'GhostSeed' in player['relics'] and d['rarity']=='basic' and (d['values'].get('strike') or d['values'].get('defend')):
        keywords=card.setdefault('addedKeywords',[])
        if 'ethereal' not in keywords:keywords.append('ethereal')

def before_draw(state,player):
    if player.get('turnNumber')==1:
        from .. import engine as e
        if 'BlessedAntler' in player['relics']:
            for _ in range(3):e.add_generated(state,player,e.new_card(state,'Dazed'),'draw',random_position=True)
        if 'JeweledMask' in player['relics']:
            from ..combat.costs import free
            cards=[c for c in e.top_first(player['draw']) if e.definition(c)['kind']=='power']
            cards=[c for c in cards if not e.definition(c)['values'].get('innate')] or cards
            if cards:
                card=e.combat_card_selection(state,cards);player['draw'].remove(card);free(card);e.add_to_hand(state,player,card)
    if 'FuneraryMask' in player['relics'] and player.get('turnNumber')==1:
        from .. import engine as e
        for _ in range(3):e.add_generated(state,player,e.new_card(state,'Soul'),'draw',random_position=True)
    if 'RadiantPearl' in player['relics'] and player.get('turnNumber')==1:
        from .. import engine as e
        e.add_generated(state,player,e.new_card(state,'Luminesce'))
    if 'Toolbox' not in player['relics'] or player.get('turnNumber')!=1:return
    from ..combat.effects import generated_cards, select_now
    cards=generated_cards(state,'colorless',3)
    if cards:select_now(state,player,{'op':'select','source':'generated','destination':'hand','cards':cards,'minimum':1,'maximum':1,'title':'工具箱：选择一张无色牌'})

def after_exhaust(state,player,card):
    from .. import engine as e
    used=player.setdefault('relicCombat',{})
    if 'BurningSticks' in player['relics'] and not used.get('burningSticks') and e.definition(card)['kind']=='skill':
        used['burningSticks']=True;e.add_generated(state,player,e.copy_card(state,card))

def reward_options(state,player,cards):
    from .. import engine as e
    from ..combat.enchantments import can_enchant, enchant
    if 'LavaLamp' in player['relics'] and state['phase'] in ('combat','reward') and not player.get('lavaLampDamaged'):
        for card in cards:
            if e.upgradable(card):e.upgrade(card)
    if 'WingCharm' in player['relics']:
        eligible=[c for c in cards if can_enchant(c,'Swift',in_deck=True)]
        if eligible:enchant(e.niche_choose(state,eligible),'Swift',in_deck=True,amount=1)
