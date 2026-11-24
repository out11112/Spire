"""Ancient acquisition choices with saved card identities and full source pools."""
from copy import deepcopy

DATA={
 'PaelsEye':('佩尔之眼','每场一次，整回合未手动出牌时消耗手牌并获得额外回合；耳环首回合除外'),
 'WhisperingEarring':('低语耳环','每回合额外 1 能量；首回合按手牌顺序自动支付并打出至多十三张可打出的牌'),
 'Driftwood':('浮木','每份普通卡牌奖励可以重抽一次，沿用该奖励的完整生成规则'),
 'PaelsWing':('佩尔之翼','可献祭卡牌奖励；每献祭两份获得一件完整遗物袋中的遗物'),
 'LastingCandy':('吃不完的糖','每第二次战斗奖励额外加入一张能力牌，优先不重复身份'),
 'GlassEye':('玻璃眼珠','获得两份普通、两份罕见和一份稀有卡牌奖励，各三张候选'),
 'SeaGlass':('海玻璃','指定职业普通、罕见、稀有各五张候选，任选数量加入牌组'),
 'DistinguishedCape':('卓越斗篷','获得两个不同的合格随机诅咒和三张灵体'),
 'ArchaicTooth':('古老牙齿','将牌组中首张合格初始牌转化为对应古老牌，保留升级与合格附魔'),
 'Claws':('利爪','选择至多六张牌变为撕咬，保留升级与合格附魔'),
 'DustyTome':('尘封魔典','随机获得一张已升级的本职业非超越古老牌'),
 'BloodSoakedRose':('血染玫瑰','获得迷魂；每回合额外 1 能量'),
 'BlessedAntler':('赐福鹿角','每回合额外 1 能量；首回合向抽牌堆随机加入三张晕眩'),
 'JeweledMask':('宝石面具','首回合从抽牌堆随机取一张能力牌，本回合免费，优先非固有牌'),
 'TanxsWhistle':('坦克斯的哨子','获得时向牌组加入吹哨'),
 'Storybook':('故事书','获得时向牌组加入至亮之焰'),
 'TouchOfOrobas':('欧洛巴斯之触','将第一件初始遗物替换为对应升级遗物'),
 'ChoicesParadox':('选择悖论','首回合从五张随机本职业牌中选一张加入手牌，获得保留'),
 'PaelsClaw':('佩尔之爪','牌组中所有合格防御牌附魔黏糊：消耗，每次打出永久增加 1 格挡'),
 'PaelsGrowth':('佩尔的增生组织','选择一张牌附魔克隆；营地可复制所有带克隆的牌'),
 'PaelsTooth':('佩尔之牙','暂时移除五张可升级牌，每次存活结束战斗随机升级并归还一张'),
 'ElectricShrymp':('放电异虾','选择一张技能牌附魔注能，首回合自动打出'),
 'TriBoomerang':('三刃回旋镖','选择三张攻击牌附魔本能，攻击伤害翻倍'),
}

TRANSCEND={'Bash':'Break','Neutralize':'Suppress','Unleash':'Protector','FallingStar':'MeteorShower','Dualcast':'Quadcast'}
STARTERS={'BurningBlood':'BlackBlood','RingOfTheSnake':'RingOfTheDrake','DivineRight':'DivineDestiny','BoundPhylactery':'PhylacteryUnbound','CrackedCore':'InfusedCore'}


def select_cards(state,player,cards,minimum,maximum,title):
    from ... import engine as e
    from ...core.decisions import select
    if not cards:return []
    rows=[{'id':c['id'],'label':e.card_view(c)['name']+'：'+e.card_view(c)['description']} for c in cards]
    selected=select(state,player,'ancientCards',title,rows,min(minimum,len(rows)),min(maximum,len(rows)))
    return [e.find_card(cards,row['id']) for row in selected]


def transform(state,player,card,key):
    from ... import engine as e
    from ...combat.enchantments import can_enchant, enchant
    from .transforms import replace_in_pile
    new=e.new_card(state,key,card.get('upgraded',False))
    old=card.get('enchantment')
    if old and can_enchant(new,old['key'],in_deck=True):enchant(new,old['key'],in_deck=True,amount=old['amount'])
    replace_in_pile(state,player,player['deck'],card,new)


def obtained(state,player,key):
    from ... import engine as e
    from ...combat.enchantments import can_enchant, enchant
    if key=='GlassEye':
        from ..rewards.custom import offer_cards
        # The reference builds these with NoUpgradeRoll, so they are never
        # offered pre-upgraded.
        for rarity in ('common','common','uncommon','uncommon','rare'):offer_cards(state,player,rarity=rarity,uniform=True,no_upgrade_roll=True)
    elif key=='SeaGlass':
        from ...combat.effects import select_now
        pool=player.setdefault('seaGlassCharacter','ironclad');e.require(pool in e.CHARACTERS,'海玻璃职业无效。')
        cards=[]
        for rarity in ('common','uncommon','rare'):
            rows=e.card_choices(state,player,[d for d in e.CARDS.values() if d['pool']==pool and d['rarity']==rarity],source='other',count=5,uniform=True,pool_modifications=False,act_index=state.get('actIndex',0))
            batch=[e.new_card(state,row['key'],row['upgraded']) for row in rows]
            from ...relics.hooks import card_reward_options
            card_reward_options(player,batch,state,is_card_reward=False);cards.extend(batch)
        select_now(state,player,{'op':'select','source':'generated','destination':'deck','cards':cards,'minimum':0,'maximum':len(cards),'title':'海玻璃：任选卡牌加入牌组'})
    elif key=='DistinguishedCape':
        from .transforms import POOLS
        # The reference draws from the curse pool minus the curses that opt out
        # of modifier generation, so those can never be handed out here.
        curses=[row['key'] for row in POOLS['curse']
                if row['constraint']!=('SingleplayerOnly' if len(state['players'])>1 else 'MultiplayerOnly')
                and not e.definition(e.new_card(state,row['key']))['values'].get('noModifierGenerate')]
        for _ in range(min(2,len(curses))):
            chosen=e.niche_choose(state,curses);curses.remove(chosen);e.obtain_card(state,player,e.new_card(state,chosen))
        for _ in range(3):e.obtain_card(state,player,e.new_card(state,'Apparition'))
    if key in ('TanxsWhistle','Storybook','BloodSoakedRose'):
        e.obtain_card(state,player,e.new_card(state,{'TanxsWhistle':'Whistle','Storybook':'BrightestFlame','BloodSoakedRose':'Enthralled'}[key]))
    elif key=='ArchaicTooth':
        card=next((c for c in player['deck'] if c['key'] in TRANSCEND),None)
        e.require(card is not None,'牌组没有可超越的初始牌。')
        transform(state,player,card,TRANSCEND[card['key']])
    elif key=='Claws':
        for card in select_cards(state,player,[c for c in player['deck'] if e.removable(c)],0,6,'利爪：选择至多六张牌变为撕咬'):transform(state,player,card,'Maul')
    elif key=='TouchOfOrobas':
        from ...relics.hooks import DATA as relic_data
        original=next((r for r in player['relics'] if relic_data[r]['rarity']=='starter'),None)
        e.require(original is not None,'没有可替换的初始遗物。')
        replacement=STARTERS.get(original,'Circlet');index=player['relics'].index(original)
        player['relics'].remove(original);e.relic(state,player,replacement)
        player['relics'].remove(replacement);player['relics'].insert(index,replacement)
    elif key=='DustyTome':
        pool=[k for k,d in e.CARDS.items() if d['pool']==player['character'] and d['rarity']=='ancient' and k not in TRANSCEND.values()
              and not (len(state['players'])==1 and d['values'].get('multiplayerOnly')) and not (len(state['players'])>1 and d['values'].get('singleplayerOnly'))]
        chosen=player.get('dustyTomeCard') or e.rewards_rng(state,player,lambda rng:rng.next_item(list(pool)))
        e.require(chosen in pool,'古老牌身份不属于本职业合格候选池。')
        player['dustyTomeCard']=chosen;card=e.new_card(state,chosen)
        if e.upgradable(card):e.upgrade(card)
        e.obtain_card(state,player,card)
    elif key in ('PaelsClaw','PaelsGrowth','ElectricShrymp','TriBoomerang'):
        enchantment={'PaelsClaw':'Goopy','PaelsGrowth':'Clone','ElectricShrymp':'Imbued','TriBoomerang':'Instinct'}[key]
        cards=[c for c in player['deck'] if can_enchant(c,enchantment,in_deck=True)]
        if key!='PaelsClaw':cards=select_cards(state,player,cards,3 if key=='TriBoomerang' else 1,3 if key=='TriBoomerang' else 1,e.RELICS[key][0]+'：选择附魔牌')
        for card in cards:enchant(card,enchantment,in_deck=True,amount=4 if key=='PaelsGrowth' else 1)
    elif key=='PaelsTooth':
        cards=select_cards(state,player,[c for c in player['deck'] if e.removable(c) and e.upgradable(c)],5,5,'佩尔之牙：暂时移除五张可升级牌')
        player['paelsToothCards']=deepcopy(sorted(cards,key=lambda c:c['key']))
        for card in cards:player['deck'].remove(card)


def combat_end(state,player):
    from ... import engine as e
    if player['hp']>0 and 'PaelsTooth' in player['relics'] and player.get('paelsToothCards'):
        card=e.rewards_rng(state,player,lambda rng:rng.next_item(list(player['paelsToothCards'])))
        player['paelsToothCards'].remove(card)
        if e.upgradable(card):e.upgrade(card)
        e.obtain_card(state,player,card)


def whisper(state,player):
    from ... import engine as e
    from ...combat.afflictions import smog_blocks, ringing_blocks, bound_blocks
    from ...core.continuation import current
    from ...combat.effects import autoplay
    if 'WhisperingEarring' not in player['relics'] or player.get('turnNumber')!=1:return
    runtime=current();e.require(runtime is not None,'耳环自动决策必须通过游戏动作执行。')
    def playable(card):
        d=e.combat_definition(player,card);v=d['values']
        if v.get('unplayable') or e.energy_cost(state,player,card)>player['energy'] or e.star_cost(player,card)>player.get('stars',0):return False
        if any(f(player,card) for f in (smog_blocks,ringing_blocks,bound_blocks)):return False
        if 'VelvetChoker' in player['relics'] and player.get('velvetChokerPlayed',0)>=6:return False
        if player['powers'].get('sloth') and player.get('slothPlays',0)>=player['powers']['sloth']:return False
        if any(c['key']=='Enthralled' for c in player['hand']) and card['key']!='Enthralled':return False
        if any(c['key']=='Normality' for c in player['hand']) and player.get('cardsPlayed',0)>=3:return False
        if v.get('attackOnlyHand') and any(e.definition(c)['kind']!='attack' for c in player['hand']):return False
        if v.get('emptyDrawOnly') and player['draw']:return False
        if v.get('requiresOsty') and player.get('osty',{}).get('hp',0)<=0:return False
        if d['target']=='ally' and not any(p['id']!=player['id'] and p['hp']>0 for p in state['players'].values()):return False
        return True
    previous=runtime.vakuu;runtime.vakuu=True
    try:
        for _ in range(13):
            if player['hp']<=0 or player.get('done') or player.get('endRequested') or player['turnNumber']!=1 or not any(m['hp']>0 for m in state['enemies']):break
            card=next((c for c in player['hand'] if playable(c)),None)
            if card is None:break
            target=None;kind=e.combat_definition(player,card)['target']
            if kind=='enemy':target=next(m['id'] for m in state['enemies'] if m['hp']>0)
            elif kind=='ally':target=e.random_target(state,[p for p in state['players'].values() if p['id']!=player['id'] and p['hp']>0])['id']
            autoplay(state,player,card,target=target,spend_resources=True)
    finally:runtime.vakuu=previous
