"""Source-defined event actions and persisted per-player/shared progress.

This registry is effect coverage, not an encounter-selection pool. Journey must
select from its complete source pool and pass the chosen identity to start().
"""
from ... import engine as e
from .. import potions
from ...combat.effects import select_now
from . import ancients
from ...text.events import prompt

NAMES={'DoorsOfLightAndDark':'光与暗的门扉','Bugslayer':'害虫杀手','AromaOfChaos':'混沌芳香',
       'ByrdonisNest':'多尼斯异鸟巢','InfestedAutomaton':'被寄生的自动机械','SunkenTreasury':'淹水金库',
       'SpiritGrafter':'灵魂嫁接者','PotionCourier':'药水快递员','TheLegendsWereTrue':'传说是真的',
       'MorphicGrove':'变形灵林谷','HungryForMushrooms':'蘑菇饥渴',
       'SunkenStatue':'沉没雕像','LostWisp':'迷失鬼火','RoomFullOfCheese':'满屋芝士','Neow':'涅奥','TrashHeap':'垃圾堆',
       'BrainLeech':'脑蛭','JungleMazeAdventure':'丛林迷宫奇遇','Reflections':'镜中倒影  影倒中镜',
       'ThisOrThat':'这个还是那个？','GraveOfTheForgotten':'遗忘之墓','FieldOfManSizedHoles':'人形洞穴之地',
       'TheLanternKey':'灯火钥匙','WarHistorianRepy':'战史学家 付袭',
       'ColossalFlower':'巨大花卉','SlipperyBridge':'滑脚木桥','SpiralingWhirlpool':'螺旋漩涡',
       'TheFutureOfPotions':'药水的未来？','TeaMaster':'茶艺大师',
       'RoundTeaParty':'圆桌茶会','WaterloggedScriptorium':'水漫缮写室','ZenWeaver':'修禅织网者',
       'AbyssalBaths':'深渊浴场','RanwidTheElder':'长者兰伟德','RelicTrader':'遗物交换商','StoneOfAllTime':'永恒之石'}
NAMES['DenseVegetation']='茂密的植被'
NAMES['Amalgamator']='熔合者'
NAMES['DollRoom']='玩偶室'
NAMES['LuminousChoir']='冷光合唱团'
NAMES['TinkerTime']='打造时间'
NAMES['Symbiote']='共生体'
NAMES['ColorfulPhilosophers']='色彩哲学家'
NAMES['WoodCarvings']='木雕'
NAMES['DrowningBeacon']='淹水灯塔'
NAMES['SelfHelpBook']='自助指南'
NAMES['PunchOff']='重拳出击'
NAMES['EndlessConveyor']='无尽传送带'
NAMES['Trial']='审判'
NAMES['BattlewornDummy']='战痕累累的训练假人'
NAMES['WelcomeToWongos']='欢迎来到旺购百货'
NAMES['FakeMerchant']='商人？？？'
NAMES.update({'Darv':'达弗','Nonupeipe':'诺奴佩普','Orobas':'欧洛巴斯','Pael':'佩尔',
              'Tanx':'坦克斯','Tezcatara':'特兹卡塔拉','Vakuu':'瓦库'})
NAMES['TheArchitect']='建筑师'
NAMES['CrystalSphere']='水晶球'
FAKE_RELICS=['FakeAnchor','FakeBloodVial','FakeHappyFlower','FakeLeesWaffle','FakeMango','FakeOrichalcum','FakeSneckoEye','FakeStrikeDummy','FakeVenerableTeaSet']
DISHES={'CAVIAR':(6,'鱼子酱：最大生命 +4'),'SPICY_SNAPPY':(3,'辛辣小食：随机升级一张牌'),
        'JELLY_LIVER':(3,'凝冻肝：变换一张牌'),'FRIED_EEL':(3,'炸鳗鱼：获得随机无色牌'),
        'SUSPICIOUS_CONDIMENT':(3,'可疑调料：随机药水'),'CLAM_ROLL':(6,'蛤蜊卷：治疗 10'),
        'GOLDEN_FYSH':(1,'金鱼：免费获得 75 金币'),'SEAPUNK_SALAD':(0,'海朋克沙拉：获得进食狂潮')}


def roll_dish(state,player,progress):
    progress['dishNumber']=progress.get('dishNumber',0)+1
    if progress['dishNumber']%5==0:progress['dish']='SEAPUNK_SALAD';return
    pool=[key for key in DISHES if key!='SEAPUNK_SALAD' and key!=progress.get('dish')
          and (key!='SUSPICIOUS_CONDIMENT' or len(player['potions'])<potions.capacity(player))
          and (key!='CLAM_ROLL' or player['hp']!=player['maxHp'])
          and (key!='GOLDEN_FYSH' or progress['dishNumber']>1)]
    roll=event_fraction(state,'EndlessConveyor',player)*sum(DISHES[key][0] for key in pool)
    for key in pool:
        roll-=DISHES[key][0]
        if roll<0:progress['dish']=key;return
BOOK_OPTIONS={'Sharp':('attack','读封底：攻击牌附加锋利 2'),'Nimble':('skill','读一段：技能牌附加灵巧 2'),'Swift':('power','读全书：能力牌附加迅速 2')}


def book_cards(player,key):
    from ...combat.enchantments import can_enchant
    return [c for c in player['deck'] if e.definition(c)['kind']==BOOK_OPTIONS[key][0] and can_enchant(c,key,in_deck=True)]

SCIENCE_RIDERS={'attack':['sapping','violence','choking'],'skill':['energized','wisdom','chaos'],'power':['expertise','curious','improvement']}
SCIENCE_OPTIONS={'attack':'CHOOSE_CARD_TYPE.ATTACK','skill':'CHOOSE_CARD_TYPE.SKILL','power':'CHOOSE_CARD_TYPE.POWER',
                 **{key:'CHOOSE_RIDER.'+key.upper() for key in ('sapping','violence','choking','energized','wisdom','chaos','expertise','curious','improvement')}}
SCIENCE_VALUES={'SappingWeak':2,'SappingVulnerable':2,'ChokingDamage':6,'EnergizedEnergy':2,'WisdomCards':3,
                'ExpertiseStrength':2,'ExpertiseDexterity':2,'CuriousReduction':1}
DOLLS=['DaughterOfTheWind','MrStruggles','BingBong']
SHARED={'MorphicGrove','JungleMazeAdventure','TheLanternKey','WarHistorianRepy','DenseVegetation','PunchOff','BattlewornDummy','FakeMerchant'}
EVENT_PETS={'Byrdpip','PaelsLegion'}


# Identities whose handler is not implemented. A shelved event that still gets
# drawn fails to start, and on a node with a single outgoing path that wedges the
# run, so journey skips them both when the pool is built and when it is drawn.
DISABLED = frozenset()


def allowed(state,key):
    players=list(state['players'].values())
    if key=='FakeMerchant':return state.get('actIndex',0)>=1 and len(players)==1 and all(p['gold']>=100 or any(item['key']=='FoulPotion' for item in p['potions']) for p in players)
    if key=='WelcomeToWongos':return state.get('actIndex',0)==1 and all(p['gold']>=100 for p in players)
    if key=='EndlessConveyor':return all(p['gold']>=120 for p in players)
    if key=='PunchOff':return state.get('floor',0)>=6
    if key=='WoodCarvings':return all(any(e.definition(c)['rarity']=='basic' and e.removable(c) for c in p['deck']) for p in players)
    if key=='Symbiote':return state.get('actIndex',0)>0
    if key=='LuminousChoir':
        from ...relics.pool import has_available
        return all(p['gold']>=149 and has_available(state,p) for p in players)
    if key=='DollRoom':return state.get('actIndex',0)==1
    if key=='Amalgamator':return all(all(len(amalgamator_cards(p,tag))>=2 for tag in ('strike','defend')) for p in players)
    if key=='DenseVegetation':return len(players)==1 or all(p['hp']>8 for p in players)
    if key=='StoneOfAllTime':return state.get('actIndex',0)==1 and all(p['potions'] for p in players)
    if key in ('RelicTrader','RanwidTheElder'):
        from ...relics.trade import candidates
        return state.get('actIndex',0)>0 and all(len(candidates(p))>=5 if key=='RelicTrader' else bool(candidates(p)) and p['gold']>=100 and bool(p['potions']) for p in players)
    if key=='RoundTeaParty':return all(p['hp']>=12 for p in players)
    if key=='UnrestSite':return all(p['hp']*100<=p['maxHp']*70 for p in players)
    if key=='WhisperingHollow':return all(p['gold']>=44 for p in players)
    if key=='WaterloggedScriptorium':return all(p['gold']>=55 for p in players)
    if key=='ZenWeaver':return all(p['gold']>=125 for p in players)
    if key=='TheFutureOfPotions':return all(len(p['potions'])>=2 for p in players)
    if key=='TeaMaster':return state.get('actIndex',0)<2 and all(p['gold']>=150 for p in players)
    if key=='ColossalFlower':return all(p['hp']>=19 for p in players)
    if key=='SlipperyBridge':return state.get('floor',0)>6 and all(any(e.removable(c) for c in p['deck']) for p in players)
    if key=='SpiralingWhirlpool':
        from ...combat.enchantments import can_enchant
        return all(any(can_enchant(c,'Spiral',in_deck=True) for c in p['deck']) for p in players)
    if key=='WarHistorianRepy':return False
    if key=='TrashHeap':return all(p['hp']>5 for p in players)
    if key=='BrainLeech':return state.get('actIndex',0)<2
    if key=='JungleMazeAdventure':return len(players)==1 or all(p['hp']>18 for p in players)
    if key in ('GraveOfTheForgotten','FieldOfManSizedHoles'):
        from ...combat.enchantments import can_enchant
        enchantment='SoulsPower' if key=='GraveOfTheForgotten' else 'PerfectFit'
        return all(any(can_enchant(c,enchantment,in_deck=True) for c in p['deck']) for p in players)
    if key=='PotionCourier':return state.get('actIndex',0)>0
    if key=='RoomFullOfCheese':return state.get('actIndex',0)<2
    if key=='TheLegendsWereTrue':return state.get('actIndex',0)==0 and all(p['deck'] and p['hp']>=10 for p in players)
    if key=='ByrdonisNest':return all(not EVENT_PETS.intersection(p['relics']) and not any(c['key']=='ByrdonisEgg' for c in p['deck']) for p in players)
    if key=='MorphicGrove':return all(p['gold']>=100 and sum(e.removable(c) for c in p['deck'])>=2 for p in players)
    # ``IsAllowed``: everyone can afford the fee, and only from the second act.
    if key=='CrystalSphere':return state.get('actIndex',0)>0 and all(p['gold']>=100 for p in players)
    return True


def amalgamator_cards(player,tag):
    return [c for c in player['deck'] if e.definition(c)['rarity']=='basic' and e.definition(c)['values'].get(tag) and e.removable(c)]


def event_pick(state,key,player,items):
    from ...rng import streams
    with streams.open(state) as rngs:
        rng=rngs.event(key,streams.seat_of(player),shared=key in SHARED)
        return rng.next_item(list(items))


def event_roll(state,key,player,count):
    from ...rng import streams
    with streams.open(state) as rngs:
        rng=rngs.event(key,streams.seat_of(player),shared=key in SHARED)
        return rng.next_int(count)


def event_shuffle(state,key,player,items):
    from ...rng import streams
    with streams.open(state) as rngs:
        rng=rngs.event(key,streams.seat_of(player),shared=key in SHARED)
        values=list(items);rng.shuffle(values);return values


def shared_vote_pick(state,votes):
    """``EventSynchronizer``'s own stream, choosing among the votes.

    The host draws the option from a stream named ``event_synchronizer`` seeded
    from the run seed, one entry per player slot in join order and repeats kept,
    so a majority option is drawn proportionally more often.
    """
    from ...rng import streams
    with streams.open(state) as rngs:
        return rngs.named('event_synchronizer').next_item(list(votes))


def event_fraction(state,key,player):
    """``Rng.NextFloat`` on the event's own stream, for a weighted pick."""
    from ...rng import streams
    with streams.open(state) as rngs:
        return rngs.event(key,streams.seat_of(player),shared=key in SHARED).next_float()




def spend_gold(player,cost):
    e.require(player['gold']>=cost,'金币不足。')
    player['gold']-=cost
    if cost and 'MawBank' in player['relics']:player['mawBankSpent']=True


CRYSTAL_SPHERE = 'CrystalSphere'


def sphere_stream_ref(player):
    """A save-safe description of the sphere's stream, for a deferred reward.

    The card rewards it hands out can be rerolled by a relic in a later action,
    and that reroll has to draw from the sphere's stream again. A reference
    survives ``json.dumps``; the stream itself cannot.
    """
    from ...rng import streams
    return {'kind':'event','name':CRYSTAL_SPHERE,'seat':streams.seat_of(player)}


def sphere_progress(state,player):
    return state['eventState']['players'][str(player['id'])]


def sphere_board(state,player):
    progress=sphere_progress(state,player)
    board=progress.get('sphere')
    if board is None:raise e.InvalidAction('尚未开始占卜。')
    return board


def begin_sphere(state,player,option):
    """Lay the board out once, when the option is taken.

    The layout is stored rather than replayed from its stream, so a reconnect, a
    reload or a retry cannot deal a second board or charge a second fee.
    """
    from . import crystal_sphere
    from ...rng import streams
    progress=sphere_progress(state,player)
    e.require('sphere' not in progress,'占卜已经开始。')
    if option=='uncoverFuture':
        spend_gold(player,min(progress['cost'],player['gold']))
        divinations=3
    elif option=='paymentPlan':
        e.obtain_card(state,player,e.new_card(state,'Debt'))
        divinations=6
    else:raise e.InvalidAction('无效的事件选择。')
    with streams.open(state) as rngs:
        game=crystal_sphere.Minigame(rngs.event(CRYSTAL_SPHERE,streams.seat_of(player)),divinations)
    progress['sphere']={'board':game.to_dict(),'awarded':False}


def sphere_act(state,player,action):
    """One look at the board, or a change of tool."""
    from . import crystal_sphere
    board=sphere_board(state,player)
    e.require(not board['awarded'],'占卜已经结算。')
    game=crystal_sphere.Minigame.from_dict(board['board'])
    op=action.get('op')
    if op=='tool':
        tool=action.get('tool')
        e.require(tool in (crystal_sphere.TOOL_SMALL,crystal_sphere.TOOL_BIG),'未知的占卜工具。')
        game.set_tool(tool)
    elif op=='use':
        e.require(not game.finished,'占卜次数已经用完。')
        x,y=action.get('x'),action.get('y')
        e.require(isinstance(x,int) and isinstance(y,int),'无效的占卜位置。')
        try:found=game.cell_clicked(x,y)
        except ValueError:raise e.InvalidAction('无效的占卜位置。')
        for item in dict.fromkeys(found):
            # Revealing the curse puts Doubt straight into the deck; every other
            # item becomes a reward at the end instead.
            if item.kind=='Curse':e.obtain_card(state,player,e.new_card(state,'Doubt'))
        if found:e.log(state,f"{player['name']} 占卜出了 {len(dict.fromkeys(found))} 个结果。")
    else:raise e.InvalidAction('无效的占卜操作。')
    board['board']=game.to_dict()
    if game.finished and not board['awarded']:
        settle_sphere(state,player,game)
        board['awarded']=True
        # Both, because they gate different things: ``player['done']`` lets the
        # engine advance, and the progress record is what the event view reports.
        player['done']=True
        sphere_progress(state,player)['done']=True
    e.advance_if_ready(state)


def settle_sphere(state,player,game):
    """Hand out what the board showed, in reveal order.

    The reference maps every found item through ``ToReward`` against the
    sphere's own stream: potions are drawn there and then, the relic and the
    card rewards are drawn when they are opened. Gold and the curse carry no
    draw. A relic or card reward left pending keeps the player from advancing
    until it is claimed.
    """
    from ...rng import streams
    from ..rewards.custom import offer_cards, queue_relic
    from ..rewards.gold import queue as queue_gold
    gold=0
    with streams.open(state) as rngs:
        rng=rngs.event(CRYSTAL_SPHERE,streams.seat_of(player))
        for item in game.revealed:
            if item.kind=='Gold':gold+=30 if item.variant else 10
            elif item.kind=='Potion':
                pool=[key for key in potions.pool_for(player['character'])
                      if potions.DATA[key]['rarity']==item.variant]
                if pool:
                    player['pendingPotions'].append(potions.create(state,rng.next_item(pool)))
            elif item.kind=='Relic':queue_relic(state,player,rng=rng)
            elif item.kind=='CardReward':
                offer_cards(state,player,rng=rng,stream=sphere_stream_ref(player),
                            source='event',count=3,uniform=True,rarity=item.variant,
                            pool_modifications=False,no_upgrade_roll=False)
    if gold:queue_gold(state,player,gold,'CrystalSphere')
    e.log(state,f"{player['name']} 完成了占卜。")


def start(state,key):
    e.require(key in NAMES,'事件效果尚未实现：'+key)
    if key=='TheArchitect':
        from .ending import start as start_ending
        start_ending(state);return
    e.require(allowed(state,key) or key=='WarHistorianRepy' and state.get('actIndex')==2 and any(c['key']=='LanternKey' for p in state['players'].values() for c in p['deck']),'当前不满足事件条件。')
    state['event']=key
    state['eventState']={'key':key,'page':0,'votes':{},'players':{}}
    for player in state['players'].values():
        progress={'done':False,'page':0}
        if key in ancients.KEYS or key=='Neow':
            if key=='Neow':player['hp']=0
            missing=player['maxHp']-player['hp']
            e.heal(player,missing*4//5 if state.get('ascension',0)>=2 else missing)
        if key in ancients.KEYS:
            progress.update(ancients.roll(state,player,key))
        if key=='FakeMerchant':
            from ..shop import rolled_cost
            from decimal import Decimal
            progress['inventory']=[{'key':k,'cost':rolled_cost(state,player,50,low=0.85,high=1.15,ties_away=False)} for k in event_shuffle(state,key,player,FAKE_RELICS)[:6]]
        if key=='WelcomeToWongos':
            from ...relics.pool import pull
            progress['featured']=pull(state,player,'rare',shop_allowed=True)
        if key=='EndlessConveyor':roll_dish(state,player,progress)
        if key=='PunchOff':progress['gold']=91+event_roll(state,key,player,8)
        if key=='ColorfulPhilosophers':
            progress['pools']=[pool for pool in ('necrobinder','ironclad','regent','silent','defect') if pool!=player['character']]
            while len(progress['pools'])>3:progress['pools'].pop(event_roll(state,key,player,len(progress['pools'])))
        if key=='LuminousChoir':progress['tribute']=149-event_roll(state,key,player,50)
        if key=='DenseVegetation':progress['gold']=61+event_roll(state,key,player,39)
        if key=='StoneOfAllTime':progress['potion']=event_pick(state,key,player,player['potions'])['id']
        if key in ('RelicTrader','RanwidTheElder'):
            from ...relics.trade import candidates
            if key=='RelicTrader':
                import re
                from ...relics.pool import pull
                owned=sorted(candidates(player),key=lambda k:re.sub(r'(?<!^)(?=[A-Z])','_',k).upper())
                progress['ownedTrades']=event_shuffle(state,key,player,owned)[:3]
                progress['newTrades']=[pull(state,player) for _ in range(3)]
            else:
                progress['potion']=event_pick(state,key,player,player['potions'])['id']
                progress['relic']=event_pick(state,key,player,candidates(player))
        if key=='TheFutureOfPotions':
            progress['potionTypes']={item['id']:event_pick(state,key,player,
                ['attack','skill'] if potions.DATA[item['key']]['rarity'] in ('common','token') else ['attack','skill','power'])
                for item in player['potions']}
        if key=='SlipperyBridge':bridge_card(state,player,progress)
        if key=='Neow':
            from .neow import roll
            progress['options']=roll(state,player)
        if key=='SunkenTreasury':
            progress['smallGold']=52+event_roll(state,key,player,16)
            progress['largeGold']=303+event_roll(state,key,player,61)
        if key=='SunkenStatue':progress['gold']=101+event_roll(state,key,player,21)
        if key=='LostWisp':progress['gold']=45+event_roll(state,key,player,31)
        if key=='ThisOrThat':progress['gold']=41+event_roll(state,key,player,28)
        if key=='CrystalSphere':
            # ``CalculateVars``: 50 plus ``NextInt(1, 50)``, which is
            # ``(int)(NextDouble() * 49) + 1`` -- so 51 to 99, one draw per
            # player, taken before the board is laid out on the same stream.
            progress['cost']=51+event_roll(state,key,player,49)
        if key=='JungleMazeAdventure':
            progress['soloGold']=int(135+30*event_fraction(state,key,player))
            progress['groupGold']=int(35+30*event_fraction(state,key,player))
        state['eventState']['players'][str(player['id'])]=progress


def choices(state,player):
    key=state['event'];progress=state['eventState']['players'][str(player['id'])]
    if key=='TheArchitect':
        from .ending import choices as ending_choices
        return ending_choices(state,player)
    if key in ancients.KEYS:return ancients.choices(progress,player)
    if key=='FakeMerchant':
        return [('buy:'+r['key'],f"购买 {e.RELICS[r['key']][0]}：{r['cost']} 金币；{e.RELICS[r['key']][1]}") for r in progress['inventory'] if player['gold']>=r['cost']]+[('leave','离开')]
    from ...text.events import label as L
    card=lambda k:e.CARDS[k]['name'];relic=lambda k:e.RELICS[k][0];potion=lambda k:e.POTIONS[k][0]
    if key=='WelcomeToWongos':
        rows=[('bargain',100,L('WELCOME_TO_WONGOS','INITIAL.BARGAIN_BIN',BargainBinCost=100)),
              ('featured',200,L('WELCOME_TO_WONGOS','INITIAL.FEATURED_ITEM',FeaturedItemCost=200,RandomRelic=relic(progress['featured']))),
              ('mystery',300,L('WELCOME_TO_WONGOS','INITIAL.MYSTERY_BOX',MysteryBoxCost=300,MysteryBoxCombatCount=5,MysteryBoxRelicCount=3))]
        return [(k,label) for k,cost,label in rows if player['gold']>=cost]+[('leave',L('WELCOME_TO_WONGOS','INITIAL.LEAVE'))]
    if key=='BattlewornDummy':
        from ...combat.monsters import hp
        return [(str(i),L('BATTLEWORN_DUMMY',f'INITIAL.SETTING_{i}',**{f'Setting{i}Hp':hp({**state,"encounterKind":"battle"},health)}))
                for i,health in [(1,75),(2,150),(3,300)]]
    if key=='Trial':
        if progress['page']==0:return [('accept',L('TRIAL','INITIAL.ACCEPT')),('reject',L('TRIAL','INITIAL.REJECT'))]
        if progress.get('trialRejected'):return [('accept',L('TRIAL','REJECT.ACCEPT')),('doubleDown',L('TRIAL','REJECT.DOUBLE_DOWN'))]
        page=progress['trialCase'].upper()
        return [('guilty',L('TRIAL',page+'.GUILTY')),('innocent',L('TRIAL',page+'.INNOCENT'))]
    if key=='EndlessConveyor':
        grab=L('ENDLESS_CONVEYOR','ALL.'+progress['dish'],Gold=40,CaviarMaxHp=4,ClamRollHeal=10,GoldenFyshGold=75)
        return (([('grab',grab)] if player['gold']>=40 else [])
                +([('observe',L('ENDLESS_CONVEYOR','INITIAL.OBSERVE_CHEF'))] if not progress['page'] else [('leave',L('ENDLESS_CONVEYOR','GRAB_SOMETHING_OFF_THE_BELT.LEAVE'))]))
    if key=='PunchOff':
        if state['eventState']['page']:return [('fight',L('PUNCH_OFF','I_CAN_TAKE_THEM.FIGHT'))]
        return [('nab',L('PUNCH_OFF','INITIAL.NAB')),('take',L('PUNCH_OFF','INITIAL.I_CAN_TAKE_THEM'))]
    if key=='SelfHelpBook':
        rows={'Sharp':L('SELF_HELP_BOOK','INITIAL.READ_THE_BACK',Enchantment1='锋利',Enchantment1Amount=2),
              'Nimble':L('SELF_HELP_BOOK','INITIAL.READ_PASSAGE',Enchantment2='灵巧',Enchantment2Amount=2),
              'Swift':L('SELF_HELP_BOOK','INITIAL.READ_ENTIRE_BOOK',Enchantment3='迅速',Enchantment3Amount=2)}
        return [(key,rows[key]) for key in BOOK_OPTIONS if book_cards(player,key)] or [('skip',L('SELF_HELP_BOOK','INITIAL.NO_OPTIONS'))]
    if key=='DrowningBeacon':
        return [('bottle',L('DROWNING_BEACON','INITIAL.BOTTLE',Potion=potion('GlowwaterPotion'))),
                ('climb',L('DROWNING_BEACON','INITIAL.CLIMB',Relic=relic('FresnelLens'),HpLoss=13))]
    if key=='WoodCarvings':
        from ...combat.enchantments import can_enchant
        snake=any(can_enchant(c,'Slither',in_deck=True) for c in player['deck'])
        return ([('bird',L('WOOD_CARVINGS','INITIAL.BIRD',BirdCard=card('Peck')))]
                +([('snake',L('WOOD_CARVINGS','INITIAL.SNAKE',SnakeEnchantment='蛇行'))] if snake else [])
                +[('torus',L('WOOD_CARVINGS','INITIAL.TORUS',ToricCard=card('ToricToughness')))])
    if key=='ColorfulPhilosophers':return [(pool,L('COLORFUL_PHILOSOPHERS','INITIAL.'+pool.upper(),Cards=3)) for pool in progress['pools']]
    if key=='Symbiote':
        from ...combat.enchantments import can_enchant
        approach=any(can_enchant(c,'Corrupted',in_deck=True) for c in player['deck'])
        return ([('approach',L('SYMBIOTE','INITIAL.APPROACH',Enchantment='腐化'))] if approach else [])+[('fire',L('SYMBIOTE','INITIAL.KILL_WITH_FIRE'))]
    if key=='TinkerTime':
        if progress['page']==0:return [('begin',L('TINKER_TIME','INITIAL.CHOOSE_CARD_TYPE'))]
        return [(key,L('TINKER_TIME',SCIENCE_OPTIONS[key],**SCIENCE_VALUES)) for key in progress['scienceOptions']]
    if key=='LuminousChoir':
        tribute=[('tribute',L('LUMINOUS_CHOIR','INITIAL.OFFER_TRIBUTE',Gold=progress['tribute']))] if player['gold']>=progress['tribute'] else []
        return [('flesh',L('LUMINOUS_CHOIR','INITIAL.REACH_INTO_THE_FLESH'))]+tribute
    if key=='DollRoom':
        if progress['page']:return [(key,L('DOLL_ROOM','TAKE.TAKE',RelicName=relic(key))) for key in progress['dolls']]
        return [('random',L('DOLL_ROOM','INITIAL.RANDOM')),('time',L('DOLL_ROOM','INITIAL.TAKE_SOME_TIME',TakeTimeHpLoss=5)),
                ('examine',L('DOLL_ROOM','INITIAL.EXAMINE',ExamineHpLoss=15))]
    if key=='Amalgamator':
        return [('strike',L('AMALGAMATOR','INITIAL.COMBINE_STRIKES',Card1=card('UltimateStrike'))),
                ('defend',L('AMALGAMATOR','INITIAL.COMBINE_DEFENDS',Card2=card('UltimateDefend')))]
    if key=='DenseVegetation':
        if state['eventState']['page']:return [('fight',L('DENSE_VEGETATION','REST.FIGHT'))]
        heal=player['maxHp']*3//10+(15 if 'RegalPillow' in player['relics'] else 0)
        return [('trudge',L('DENSE_VEGETATION','INITIAL.TRUDGE_ON',Gold=progress['gold'],HpLoss=8)),
                ('rest',L('DENSE_VEGETATION','INITIAL.REST',Heal=heal))]
    if key=='StoneOfAllTime':
        from ...combat.enchantments import can_enchant
        item=next(item for item in player['potions'] if item['id']==progress['potion'])
        push=any(can_enchant(c,'Vigorous',in_deck=True) for c in player['deck'])
        return ([('lift',L('STONE_OF_ALL_TIME','INITIAL.LIFT',DrinkRandomPotion=potion(item['key']),DrinkMaxHpGain=10))]
                +([('push',L('STONE_OF_ALL_TIME','INITIAL.PUSH',PushHpLoss=6,PushVigorousAmount=8))] if push else []))
    if key=='AbyssalBaths':
        if progress['page']==0:
            return [('immerse',L('ABYSSAL_BATHS','INITIAL.IMMERSE',MaxHp=2,Damage=3)),('abstain',L('ABYSSAL_BATHS','INITIAL.ABSTAIN',Heal=10))]
        damage=3+progress['page']
        # The official DEATH_WARNING page line, shown once another soak would kill.
        warning='（再泡下去，你就死定了。）' if player['hp']<=damage-2 else ''
        return [('linger',L('ABYSSAL_BATHS','ALL.LINGER',MaxHp=2,Damage=damage)+warning),('exit',L('ABYSSAL_BATHS','ALL.EXIT_BATHS'))]
    if key=='RelicTrader':
        name=lambda k:e.RELICS.get(k,(k,''))[0]
        return [(str(i),L('RELIC_TRADER','INITIAL.'+slot,**{slot.title()+'RelicOwned':name(old),slot.title()+'RelicNew':name(new)}))
                for i,(slot,old,new) in enumerate(zip(('TOP','MIDDLE','BOTTOM'),progress['ownedTrades'],progress['newTrades']))]
    if key=='RanwidTheElder':
        item=next(item for item in player['potions'] if item['id']==progress['potion'])
        return [('potion',L('RANWID_THE_ELDER','INITIAL.POTION',Potion=potion(item['key']))),('gold',L('RANWID_THE_ELDER','INITIAL.GOLD',Gold=100)),
                ('relic',L('RANWID_THE_ELDER','INITIAL.RELIC',Relic=e.RELICS.get(progress['relic'],(progress['relic'],''))[0]))]
    if key=='RoundTeaParty':
        if progress['page']:return [('continueFight',L('ROUND_TEA_PARTY','PICK_FIGHT.CONTINUE_FIGHT'))]
        return [('enjoy',L('ROUND_TEA_PARTY','INITIAL.ENJOY_TEA',Relic=relic('RoyalPoison'))),('fight',L('ROUND_TEA_PARTY','INITIAL.PICK_FIGHT',Damage=11))]
    if key=='WaterloggedScriptorium':
        rows=[('quill',L('WATERLOGGED_SCRIPTORIUM','INITIAL.TENTACLE_QUILL',Gold=55),55),
              ('sponge',L('WATERLOGGED_SCRIPTORIUM','INITIAL.PRICKLY_SPONGE',PricklySpongeGold=99,Cards=2),99)]
        return [('ink',L('WATERLOGGED_SCRIPTORIUM','INITIAL.BLOODY_INK'))]+[(key,label) for key,label,cost in rows if player['gold']>=cost]
    if key=='ZenWeaver':
        rows=[('breathing',L('ZEN_WEAVER','INITIAL.BREATHING_TECHNIQUES',BreathingTechniquesCost=50),50),
              ('awareness',L('ZEN_WEAVER','INITIAL.EMOTIONAL_AWARENESS',EmotionalAwarenessCost=125),125),
              ('acupuncture',L('ZEN_WEAVER','INITIAL.ARACHNID_ACUPUNCTURE',ArachnidAcupunctureCost=250),250)]
        return [(key,label) for key,label,cost in rows if player['gold']>=cost]
    if key=='TheFutureOfPotions':
        labels={'attack':'攻击','skill':'技能','power':'能力'};rarities={'common':'普通','uncommon':'罕见','rare':'稀有'}
        return [(item['id'],L('THE_FUTURE_OF_POTIONS','INITIAL.POTION',Potion=potion(item['key']),Rarity=rarities[potion_card_rarity(item)],
                              Type=labels[progress['potionTypes'][item['id']]]))
                for item in player['potions'][:3]]
    if key=='TeaMaster':
        rows=[('BoneTea',L('TEA_MASTER','INITIAL.BONE_TEA',BoneTeaCost=50,BoneTeaDescription=e.RELICS['BoneTea'][1]),50),
              ('EmberTea',L('TEA_MASTER','INITIAL.EMBER_TEA',EmberTeaCost=150,EmberTeaDescription=e.RELICS['EmberTea'][1]),150),
              ('TeaOfDiscourtesy',L('TEA_MASTER','INITIAL.TEA_OF_DISCOURTESY',TeaOfDiscourtesyDescription=e.RELICS['TeaOfDiscourtesy'][1]),0)]
        return [(key,label) for key,label,cost in rows if player['gold']>=cost]
    if key=='ColossalFlower':
        depth=progress['page']
        page=('INITIAL','REACH_DEEPER_1','REACH_DEEPER_2')[depth]
        extract=('EXTRACT_CURRENT_PRIZE_1','EXTRACT_CURRENT_PRIZE_2','EXTRACT_INSTEAD')[depth]
        return [('extract',L('COLOSSAL_FLOWER',page+'.'+extract,**{f'Prize{depth+1}':(35,75,135)[depth]})),
                ('deeper',L('COLOSSAL_FLOWER',page+'.REACH_DEEPER_'+str(depth+1))) if depth<2 else ('core',L('COLOSSAL_FLOWER',page+'.POLLINOUS_CORE'))]
    if key=='SlipperyBridge':
        bridge=e.find_card(player['deck'],progress['bridgeCard'])
        return [('overcome',L('SLIPPERY_BRIDGE','INITIAL.OVERCOME',RandomCard=e.card_view(bridge)['name'])),
                ('hold',L('SLIPPERY_BRIDGE','INITIAL.HOLD_ON_0',HpLoss=3+progress['page']))]
    if key=='SpiralingWhirlpool':
        return [('observe',L('SPIRALING_WHIRLPOOL','INITIAL.OBSERVE')),('drink',L('SPIRALING_WHIRLPOOL','INITIAL.DRINK',Heal=player['maxHp']*33//100))]
    if key=='Neow':
        from .neow import choices as neow_choices
        return neow_choices(progress)
    if key=='DoorsOfLightAndDark':return [('light',L('DOORS_OF_LIGHT_AND_DARK','INITIAL.LIGHT',Cards=2)),('dark',L('DOORS_OF_LIGHT_AND_DARK','INITIAL.DARK'))]
    if key=='Bugslayer':
        return [('exterminate',L('BUGSLAYER','INITIAL.EXTERMINATION',Card1=card('Exterminate'))),('squash',L('BUGSLAYER','INITIAL.SQUASH',Card2=card('Squash')))]
    if key=='AromaOfChaos':return [('letGo',L('AROMA_OF_CHAOS','INITIAL.LET_GO')),('control',L('AROMA_OF_CHAOS','INITIAL.MAINTAIN_CONTROL'))]
    if key=='ByrdonisNest':return [('eat',L('BYRDONIS_NEST','INITIAL.EAT',MaxHp=7)),('take',L('BYRDONIS_NEST','INITIAL.TAKE',Card=card('ByrdonisEgg')))]
    if key=='InfestedAutomaton':return [('study',L('INFESTED_AUTOMATON','INITIAL.STUDY')),('core',L('INFESTED_AUTOMATON','INITIAL.TOUCH_CORE'))]
    if key=='SunkenTreasury':
        return [('small',L('SUNKEN_TREASURY','INITIAL.FIRST_CHEST',SmallChestGold=progress['smallGold'])),
                ('large',L('SUNKEN_TREASURY','INITIAL.SECOND_CHEST',LargeChestGold=progress['largeGold']))]
    if key=='SpiritGrafter':
        return [('accept',L('SPIRIT_GRAFTER','INITIAL.LET_IT_IN',LetItInHealAmount=25)),('reject',L('SPIRIT_GRAFTER','INITIAL.REJECTION',RejectionHpLoss=10))]
    if key=='PotionCourier':return [('grab',L('POTION_COURIER','INITIAL.GRAB_POTIONS',FoulPotions=3)),('ransack',L('POTION_COURIER','INITIAL.RANSACK'))]
    if key=='TheLegendsWereTrue':
        return [('map',L('THE_LEGENDS_WERE_TRUE','INITIAL.NAB_THE_MAP')),('exit',L('THE_LEGENDS_WERE_TRUE','INITIAL.SLOWLY_FIND_AN_EXIT',Damage=8))]
    if key=='MorphicGrove':
        return [('group',L('MORPHIC_GROVE','INITIAL.GROUP',IsMultiplayer=len(state['players'])>1)),('loner',L('MORPHIC_GROVE','INITIAL.LONER',MaxHp=5))]
    if key=='HungryForMushrooms':
        # The official options carry only a title; the game shows the relic beside it.
        return [(option,L('HUNGRY_FOR_MUSHROOMS','INITIAL.'+official)+'：'+e.RELICS[relic_key][1])
                for option,official,relic_key in [('big','BIG_MUSHROOM','BigMushroom'),('fragrant','FRAGRANT_MUSHROOM','FragrantMushroom')]]
    if key=='SunkenStatue':
        return [('sword',L('SUNKEN_STATUE','INITIAL.GRAB_SWORD',Relic=relic('SwordOfStone'))),
                ('dive',L('SUNKEN_STATUE','INITIAL.DIVE_INTO_WATER',Gold=progress['gold'],HpLoss=7))]
    if key=='LostWisp':
        return [('claim',L('LOST_WISP','INITIAL.CLAIM',Curse=card('Decay'),Relic=relic('LostWisp'))),('search',L('LOST_WISP','INITIAL.SEARCH',Gold=progress['gold']))]
    if key=='RoomFullOfCheese':return [('gorge',L('ROOM_FULL_OF_CHEESE','INITIAL.GORGE')),('search',L('ROOM_FULL_OF_CHEESE','INITIAL.SEARCH',Damage=14))]
    if key=='TrashHeap':return [('dive',L('TRASH_HEAP','INITIAL.DIVE_IN',HpLoss=8)),('grab',L('TRASH_HEAP','INITIAL.GRAB',Gold=100))]
    if key=='BrainLeech':
        return [('share',L('BRAIN_LEECH','INITIAL.SHARE_KNOWLEDGE',FromCardChoiceCount=5,CardChoiceCount=1)),('rip',L('BRAIN_LEECH','INITIAL.RIP',RipHpLoss=5))]
    if key=='JungleMazeAdventure':
        return [('solo',L('JUNGLE_MAZE_ADVENTURE','INITIAL.SOLO_QUEST',SoloGold=progress['soloGold'],SoloHp=18)),
                ('group',L('JUNGLE_MAZE_ADVENTURE','INITIAL.JOIN_FORCES',JoinForcesGold=progress['groupGold']))]
    if key=='Reflections':return [('touch',L('REFLECTIONS','INITIAL.TOUCH_A_MIRROR')),('shatter',L('REFLECTIONS','INITIAL.SHATTER'))]
    if key=='ThisOrThat':
        return [('plain',L('THIS_OR_THAT','INITIAL.PLAIN',HpLoss=6,Gold=progress['gold'])),('ornate',L('THIS_OR_THAT','INITIAL.ORNATE',Curse=card('Clumsy')))]
    if key=='CrystalSphere':
        # Both are always offered: ``IsAllowed`` already guarantees 100 gold and
        # the fee never exceeds 99, so the paid option is always affordable.
        if 'sphere' in progress:return []  # the board is played, not chosen from
        return [('uncoverFuture',L('CRYSTAL_SPHERE','INITIAL.UNCOVER_FUTURE',UncoverFutureCost=progress['cost'],UncoverFutureProphesizeCount=3)),
                ('paymentPlan',L('CRYSTAL_SPHERE','INITIAL.PAYMENT_PLAN',CurseTitle=card('Debt'),PaymentPlanCount=6))]
    if key=='GraveOfTheForgotten':
        return [('confront',L('GRAVE_OF_THE_FORGOTTEN','INITIAL.CONFRONT',Curse=card('Decay'),Enchantment='灵魂之力')),
                ('accept',L('GRAVE_OF_THE_FORGOTTEN','INITIAL.ACCEPT',Relic=relic('ForgottenSoul')))]
    if key=='FieldOfManSizedHoles':
        return [('resist',L('FIELD_OF_MAN_SIZED_HOLES','INITIAL.RESIST',Cards=2,ResistCurse=card('Normality'))),
                ('enter',L('FIELD_OF_MAN_SIZED_HOLES','INITIAL.ENTER_YOUR_HOLE',Enchantment='完美契合'))]
    if key=='TheLanternKey':
        if state['eventState']['page']:return [('fight',L('THE_LANTERN_KEY','KEEP_THE_KEY.FIGHT'))]
        return [('return',L('THE_LANTERN_KEY','INITIAL.RETURN_THE_KEY',Gold=100)),('keep',L('THE_LANTERN_KEY','INITIAL.KEEP_THE_KEY'))]
    if key=='WarHistorianRepy':
        rows=[('cage',L('WAR_HISTORIAN_REPY','INITIAL.UNLOCK_CAGE')),('chest',L('WAR_HISTORIAN_REPY','INITIAL.UNLOCK_CHEST'))]
        return [row for row in rows if not progress.get('firstUnlock') or row[0]!=progress['firstUnlock']]
    raise e.InvalidAction('事件选项尚未实现：'+key)


def options(state,player):
    record=state['eventState']
    if record['players'][str(player['id'])]['done']:return []
    return [{'id':state['event']+':'+key,'label':label,
             'action':{'type':'event','option':key,'event':state['event'],'page':record['page'] if state['event'] in SHARED else record['players'][str(player['id'])]['page']}}
            for key,label in choices(state,player)]


def select_deck(state,player,destination,*,count=1,title,upgrade=False):
    cards=[card for card in player['deck'] if (e.upgradable(card) if upgrade else e.removable(card))]
    select_now(state,player,{'op':'select','source':'deck','destination':destination,'cards':cards,
                            'minimum':count,'maximum':count,'title':title})


def fixed_potion(state,player,key):
    item=potions.create(state,key)
    if not potions.procure(state,player,item) and 'Sozu' not in player['relics']:player['pendingPotions'].append(item)


def random_potion(state,player,*,rarity=None):
    pool=[key for key in potions.candidates(player) if rarity is None or potions.DATA[key]['rarity']==rarity]
    fixed_potion(state,player,e.rewards_rng(state,player,lambda rng:rng.next_item(list(pool))))


def bridge_card(state,player,progress):
    previous=next((c for c in player['deck'] if c['id']==progress.get('bridgeCard')),None)
    skipped=progress.setdefault('skippedRemovals',[])
    if previous:skipped.append(previous['id'])
    eligible=[c for c in player['deck'] if e.removable(c) and c['id'] not in skipped and
              (c['key']!=previous['key'] if previous else e.CARDS[c['key']]['rarity']!='basic')]
    if not eligible:eligible=[c for c in player['deck'] if e.removable(c)]
    progress['bridgeCard']=event_pick(state,'SlipperyBridge',player,eligible)['id']


def apply_effect(state,player,option):
    key=state['event'];progress=state['eventState']['players'][str(player['id'])]
    if key=='FakeMerchant':
        if option.startswith('buy:'):
            item=next(r for r in progress['inventory'] if r['key']==option[4:])
            spend_gold(player,item['cost']);e.relic(state,player,item['key']);progress['inventory'].remove(item)
            progress['page']+=1;return
    elif key=='WelcomeToWongos':
        if option=='leave':
            upgraded=[c for c in player['deck'] if c.get('upgraded')]
            if upgraded:e.downgrade(event_pick(state,key,player,upgraded))
        else:
            from ...relics.pool import pull
            from ..rewards.custom import finish_nested
            cost,points={'bargain':(100,32),'featured':(200,16),'mystery':(300,8)}[option]
            spend_gold(player,cost)
            relic=pull(state,player,'common',shop_allowed=True) if option=='bargain' else progress['featured'] if option=='featured' else 'WongosMysteryTicket'
            e.relic(state,player,relic);finish_nested(state,player)
            previous=state.get('accountProgress',{}).get(str(player['id']),{}).get('wongoPoints',0)
            player['wongoPointsEarned']=points;progress['points']=previous+points
            if previous%2000+points>=2000:e.relic(state,player,'WongoCustomerAppreciationBadge')
            e.log(state,f"{player['name']} 获得 {points} 翁戈积分，累计 {previous+points}；本局结束后保存。")
    elif key=='Trial':
        from ..rewards.custom import offer_cards, finish_nested
        if option=='accept':
            progress['trialCase']=event_pick(state,key,player,['merchant','noble','nondescript'])
            progress['trialRejected']=False;progress['page']+=1;return
        if option=='reject':progress['trialRejected']=True;progress['page']+=1;return
        if option=='doubleDown':
            from ...core.decisions import select
            choice=select(state,player,'trialAbandon','确认放弃本局？',[{'id':'cancel','label':'返回审判'}, {'id':'abandon','label':'确认放弃整个队伍的本局攀登'}])[0]
            if choice['id']=='abandon':e.phase(state,'abandoned');state['paused']=False
            return
        case=progress['trialCase']
        curse={'merchant':'Regret' if option=='guilty' else 'Shame','noble':None if option=='guilty' else 'Regret','nondescript':'Doubt'}[case]
        if curse:e.obtain_card(state,player,e.new_card(state,curse))
        if case=='merchant' and option=='guilty':
            from ...relics.pool import pull
            for _ in range(2):e.relic(state,player,pull(state,player));finish_nested(state,player)
        elif case=='merchant':select_deck(state,player,'upgrade',count=2,title=prompt('upgrade',2),upgrade=True)
        elif case=='noble':
            if option=='guilty':e.heal(player,10)
            else:e.gain_gold(state,player,300)
        elif option=='guilty':
            for _ in range(2):offer_cards(state,player)
            finish_nested(state,player)
        else:select_deck(state,player,'randomTransform',count=2,title=prompt('transform',2))
    elif key=='EndlessConveyor':
        dish=progress['dish']
        if option=='grab':
            if dish!='GOLDEN_FYSH':spend_gold(player,40)
            if dish=='CAVIAR':player['maxHp']+=4;e.heal(player,4)
            elif dish=='CLAM_ROLL':e.heal(player,10)
            elif dish=='GOLDEN_FYSH':e.gain_gold(state,player,75)
            elif dish=='JELLY_LIVER':select_deck(state,player,'randomTransform',title=prompt('transform'))
            elif dish=='SEAPUNK_SALAD':e.obtain_card(state,player,e.new_card(state,'FeedingFrenzy'))
            elif dish=='FRIED_EEL':
                row=e.card_choices(state,player,[d for d in e.CARDS.values() if d['pool']=='colorless'],source='event',count=1)[0]
                e.obtain_card(state,player,e.new_card(state,row['key'],row['upgraded']))
            elif dish=='SUSPICIOUS_CONDIMENT':
                from ..rewards.custom import finish_nested
                player['pendingPotions'].append(potions.create(state,e.rewards_rng(state,player,lambda rng:rng.next_item(potions.candidates(player)))))
                finish_nested(state,player)
        if option=='observe' or option=='grab' and dish=='SPICY_SNAPPY':
            cards=[c for c in player['deck'] if e.upgradable(c)]
            if cards:e.upgrade(event_pick(state,key,player,cards))
        if option=='grab':roll_dish(state,player,progress);progress['page']+=1;return
    elif key=='SelfHelpBook':
        if option!='skip':select_now(state,player,{'op':'select','source':'deck','destination':'enchant','enchantment':option,'enchantmentAmount':2,
            'cards':book_cards(player,option),'minimum':1,'maximum':1,'title':prompt('enchant')})
    elif key=='PunchOff':
        from ..rewards.custom import offer_relic, finish_nested
        e.obtain_card(state,player,e.new_card(state,'Injury'));offer_relic(state,player);finish_nested(state,player)
    elif key=='DrowningBeacon':
        if option=='bottle':
            from ..rewards.custom import finish_nested
            player['pendingPotions'].append(potions.create(state,'GlowwaterPotion'));finish_nested(state,player)
        else:e.lose_max_hp(state,player,13);e.relic(state,player,'FresnelLens')
    elif key=='WoodCarvings':
        if option=='snake':
            from ...combat.enchantments import can_enchant
            select_now(state,player,{'op':'select','source':'deck','destination':'enchant','enchantment':'Slither',
                'cards':[c for c in player['deck'] if can_enchant(c,'Slither',in_deck=True)],'minimum':1,'maximum':1,'title':prompt('enchant')})
        else:
            select_now(state,player,{'op':'select','source':'deck','destination':'transform','transformKey':'Peck' if option=='bird' else 'ToricToughness',
                'cards':[c for c in player['deck'] if e.definition(c)['rarity']=='basic' and e.removable(c)],'minimum':1,'maximum':1,'title':prompt('transform')})
    elif key=='ColorfulPhilosophers':
        from ..rewards.custom import offer_cards, finish_nested
        for rarity in ('common','uncommon','rare'):
            offer_cards(state,player,pools=[option],rarity=rarity,uniform=True,pool_modifications=False)
        finish_nested(state,player)
    elif key=='Symbiote':
        if option=='fire':select_deck(state,player,'randomTransform',title=prompt('transform'))
        else:
            from ...combat.enchantments import can_enchant
            select_now(state,player,{'op':'select','source':'deck','destination':'enchant','enchantment':'Corrupted',
                'cards':[c for c in player['deck'] if can_enchant(c,'Corrupted',in_deck=True)],'minimum':1,'maximum':1,'title':prompt('enchant')})
    elif key=='TinkerTime':
        if progress['page']==0:
            progress['scienceOptions']=event_shuffle(state,key,player,list(SCIENCE_RIDERS))[:2]
            progress['page']=1;return
        if progress['page']==1:
            progress['scienceType']=option
            progress['scienceOptions']=event_shuffle(state,key,player,SCIENCE_RIDERS[option])[:2]
            progress['page']=2;return
        card=e.new_card(state,'MadScience');card.update(scienceType=progress['scienceType'],scienceRider=option)
        e.obtain_card(state,player,card)
    elif key=='LuminousChoir':
        if option=='flesh':
            select_deck(state,player,'removeDeck',count=2,title=prompt('remove',2))
            e.obtain_card(state,player,e.new_card(state,'SporeMind'))
        else:
            from ...relics.pool import pull
            from ..rewards.custom import finish_nested
            spend_gold(player,progress['tribute']);e.relic(state,player,pull(state,player));finish_nested(state,player)
    elif key=='DollRoom':
        if option in ('time','examine'):
            e.hit(state,player,player,5 if option=='time' else 15,True,unblockable=True)
            progress['dolls']=event_shuffle(state,key,player,sorted(DOLLS))[:2 if option=='time' else 3]
            progress['page']+=1;return
        e.relic(state,player,event_pick(state,key,player,DOLLS) if option=='random' else option)
    elif key=='Amalgamator':
        select_now(state,player,{'op':'select','source':'deck','destination':'removeDeck','cards':amalgamator_cards(player,option),
            'minimum':2,'maximum':2,'title':prompt('remove',2)})
        e.obtain_card(state,player,e.new_card(state,'UltimateStrike' if option=='strike' else 'UltimateDefend'))
    elif key=='DenseVegetation':
        if option=='trudge':
            e.hit(state,player,player,8,True,unblockable=True);e.gain_gold(state,player,progress['gold'])
        else:
            from ...relics.hooks import rest_heal
            from ..rewards.custom import finish_nested
            e.heal(player,player['maxHp']*3//10+(15 if 'RegalPillow' in player['relics'] else 0))
            rest_heal(state,player);finish_nested(state,player)
            return
    elif key=='StoneOfAllTime':
        if option=='lift':
            from ...relics.hooks import inventory_changed
            item=next(item for item in player['potions'] if item['id']==progress['potion'])
            player['potions'].remove(item);inventory_changed(state,player)
            player['maxHp']+=10;e.heal(player,10)
        else:
            from ...combat.enchantments import can_enchant
            e.hit(state,player,player,6,True,unblockable=True)
            select_now(state,player,{'op':'select','source':'deck','destination':'enchant','enchantment':'Vigorous','enchantmentAmount':8,
                'cards':[c for c in player['deck'] if can_enchant(c,'Vigorous',in_deck=True)],'minimum':1,'maximum':1,'title':prompt('enchant')})
        event_roll(state,key,player,100)
    elif key=='AbyssalBaths':
        if option=='abstain':e.heal(player,10)
        elif option!='exit':
            player['maxHp']+=2;e.heal(player,2)
            e.hit(state,player,player,3+progress['page'],True,unblockable=True)
            progress['page']+=1;return
    elif key in ('RelicTrader','RanwidTheElder'):
        from ...relics.trade import remove
        from ...relics.pool import pull
        from ..rewards.custom import finish_nested
        if key=='RelicTrader':
            index=int(option);remove(state,player,progress['ownedTrades'][index])
            e.relic(state,player,progress['newTrades'][index]);finish_nested(state,player)
        else:
            if option=='gold':spend_gold(player,100)
            elif option=='potion':
                from ...relics.hooks import inventory_changed
                item=next(item for item in player['potions'] if item['id']==progress['potion'])
                player['potions'].remove(item);inventory_changed(state,player)
            else:remove(state,player,progress['relic'])
            for _ in range(2 if option=='relic' else 1):
                e.relic(state,player,pull(state,player));finish_nested(state,player)
    elif key=='RoundTeaParty':
        if option=='fight':progress['page']+=1;return
        if option=='enjoy':e.relic(state,player,'RoyalPoison');e.heal(player,player['maxHp'])
        else:
            from ...relics.pool import pull
            from ..rewards.custom import finish_nested
            e.hit(state,player,player,11,True,unblockable=True)
            e.relic(state,player,pull(state,player));finish_nested(state,player)
    elif key=='WaterloggedScriptorium':
        if option=='ink':player['maxHp']+=6;e.heal(player,6)
        else:
            from ...combat.enchantments import can_enchant
            spend_gold(player,55 if option=='quill' else 99)
            count=1 if option=='quill' else 2
            select_now(state,player,{'op':'select','source':'deck','destination':'enchant','enchantment':'Steady',
                'cards':[c for c in player['deck'] if can_enchant(c,'Steady',in_deck=True)],
                'minimum':count,'maximum':count,'title':prompt('enchant',count)})
    elif key=='ZenWeaver':
        if option=='breathing':
            spend_gold(player,50)
            for _ in range(2):e.obtain_card(state,player,e.new_card(state,'Enlightenment'))
        else:
            count=1 if option=='awareness' else 2
            select_deck(state,player,'removeDeck',count=count,title=prompt('remove',count))
            spend_gold(player,125 if count==1 else 250)
    elif key=='TheFutureOfPotions':
        from ..rewards.custom import offer_instances, finish_nested, recipe
        from ...relics.hooks import inventory_changed
        item=next(item for item in player['potions'] if item['id']==option)
        rarity=potion_card_rarity(item);kind=progress['potionTypes'][option]
        player['potions'].remove(item);inventory_changed(state,player)
        pool=[d for d in e.CARDS.values() if d['pool']==player['character'] and d['rarity']==rarity and d['kind']==kind]
        rows=e.card_choices(state,player,pool,source='event',count=3,uniform=True)
        cards=[e.new_card(state,row['key'],row['upgraded']) for row in rows]
        offer_instances(state,player,cards,spec=recipe(player,rarity=rarity,kind=kind,uniform=True,pool_modifications=False,upgrade_all=True))
        for card in cards:
            if e.upgradable(card):e.upgrade(card)
        finish_nested(state,player)
    elif key=='TeaMaster':
        cost={'BoneTea':50,'EmberTea':150,'TeaOfDiscourtesy':0}[option]
        spend_gold(player,cost)
        e.relic(state,player,option)
    elif key=='ColossalFlower':
        depth=progress['page']
        if option=='extract':e.gain_gold(state,player,(35,75,135)[depth])
        else:
            e.hit(state,player,player,5+depth,True,unblockable=True)
            if option=='deeper':progress['page']+=1;return
            e.relic(state,player,'PollinousCore')
    elif key=='SlipperyBridge':
        if option=='overcome':player['deck'].remove(e.find_card(player['deck'],progress['bridgeCard']))
        else:
            e.hit(state,player,player,3+progress['page'],True,unblockable=True)
            progress['page']+=1;bridge_card(state,player,progress);return
    elif key=='SpiralingWhirlpool':
        if option=='drink':e.heal(player,player['maxHp']*33//100)
        else:
            from ...combat.enchantments import can_enchant
            select_now(state,player,{'op':'select','source':'deck','destination':'enchant','enchantment':'Spiral',
                'cards':[c for c in player['deck'] if can_enchant(c,'Spiral',in_deck=True)],
                'minimum':1,'maximum':1,'title':prompt('enchant')})
    elif key=='Neow':e.relic(state,player,option)
    elif key in ancients.KEYS:ancients.obtain(state,player,progress,option)
    elif key=='WarHistorianRepy':
        from ..rewards.custom import queue_relic, finish_nested
        keys=[c for c in player['deck'] if c['key']=='LanternKey']
        second=progress.get('firstUnlock') is not None
        for card in keys if len(state['players'])>1 or second else keys[:1]:player['deck'].remove(card)
        if option=='cage':state['freedRepy']=True;e.relic(state,player,'HistoryCourse')
        else:
            potions.reward(state,player,2)
            for _ in range(2):queue_relic(state,player)
            finish_nested(state,player)
        if len(state['players'])==1 and not second and any(c['key']=='LanternKey' for c in player['deck']):
            progress['firstUnlock']=option;return
    elif key=='BrainLeech':
        from ..rewards.custom import offer_instances
        pool=e.reward_pool(player) if option=='share' else [d for d in e.CARDS.values() if d['pool']=='colorless']
        if option=='rip':e.hit(state,player,player,5,True,unblockable=True)
        choices=e.card_choices(state,player,pool,source='event',count=5 if option=='share' else 3)
        cards=[e.new_card(state,c['key'],c['upgraded']) for c in choices]
        if option=='rip':
            from ..rewards.custom import recipe
            offer_instances(state,player,cards,spec=recipe(player,pools=['colorless'],pool_modifications=False))
        else:select_now(state,player,{'op':'select','source':'generated','destination':'deck','cards':cards,'minimum':1,'maximum':1,'title':'分享知识：选择一张牌'})
    elif key=='JungleMazeAdventure':
        if option=='solo':e.hit(state,player,player,18,True,unblockable=True)
        e.gain_gold(state,player,progress['soloGold' if option=='solo' else 'groupGold'])
    elif key=='Reflections':
        if option=='touch':
            cards=[c for c in player['deck'] if c.get('upgraded')]
            for _ in range(min(2,len(cards))):
                card=event_pick(state,key,player,cards);cards.remove(card);e.downgrade(card)
            cards=[c for c in player['deck'] if e.upgradable(c)]
            for _ in range(min(4,len(cards))):
                card=event_pick(state,key,player,cards);cards.remove(card);e.upgrade(card)
        else:
            for card in list(player['deck']):e.obtain_card(state,player,e.copy_card(state,card))
            e.obtain_card(state,player,e.new_card(state,'BadLuck'))
    elif key=='ThisOrThat':
        if option=='plain':
            e.hit(state,player,player,6,True,unblockable=True);e.gain_gold(state,player,progress['gold'])
        else:
            from ...relics.pool import pull
            from ..rewards.custom import finish_nested
            e.relic(state,player,pull(state,player));finish_nested(state,player)
            e.obtain_card(state,player,e.new_card(state,'Clumsy'))
    elif key in ('GraveOfTheForgotten','FieldOfManSizedHoles'):
        if key=='GraveOfTheForgotten' and option=='accept':e.relic(state,player,'ForgottenSoul')
        elif key=='FieldOfManSizedHoles' and option=='resist':
            select_deck(state,player,'removeDeck',count=2,title=prompt('remove',2))
            e.obtain_card(state,player,e.new_card(state,'Normality'))
        else:
            from ...combat.enchantments import can_enchant
            enchantment='SoulsPower' if key=='GraveOfTheForgotten' else 'PerfectFit'
            if key=='GraveOfTheForgotten':e.obtain_card(state,player,e.new_card(state,'Decay'))
            cards=[c for c in player['deck'] if can_enchant(c,enchantment,in_deck=True)]
            select_now(state,player,{'op':'select','source':'deck','destination':'enchant','enchantment':enchantment,
                                     'cards':cards,'minimum':1,'maximum':1,'title':prompt('enchant')})
    elif key=='TrashHeap':
        if option=='dive':
            e.hit(state,player,player,8,True,unblockable=True)
            e.relic(state,player,event_pick(state,key,player,['DarkstonePeriapt','DreamCatcher','HandDrill','MawBank','TheBoot']))
        else:
            e.gain_gold(state,player,100)
            e.obtain_card(state,player,e.new_card(state,event_pick(state,key,player,['Caltrops','Clash','Distraction','DualWield','Entrench','HelloWorld','Outmaneuver','Rebound','RipAndTear','Stack'])))
    elif key=='DoorsOfLightAndDark':
        if option=='light':
            for card in event_shuffle(state,key,player,e.reference_sorted(c for c in player['deck'] if e.upgradable(c)))[:2]:e.upgrade(card)
        else:select_deck(state,player,'removeDeck',title=prompt('remove'))
    elif key=='Bugslayer':e.obtain_card(state,player,e.new_card(state,'Exterminate' if option=='exterminate' else 'Squash'))
    elif key=='AromaOfChaos':select_deck(state,player,'randomTransform' if option=='letGo' else 'upgrade',title=prompt('upgrade' if option=='control' else 'transform'),upgrade=option=='control')
    elif key=='ByrdonisNest':
        if option=='eat':player['maxHp']+=7;e.heal(player,7)
        else:e.obtain_card(state,player,e.new_card(state,'ByrdonisEgg'))
    elif key=='InfestedAutomaton':
        pool=[d for d in e.reward_pool(player) if (d['kind']=='power' if option=='study' else d['cost']==0 and not d['values'].get('xCost'))]
        result=e.card_choices(state,player,pool,count=1,source='event')
        for card in result:e.obtain_card(state,player,e.new_card(state,card['key'],card['upgraded']))
    elif key=='SunkenTreasury':
        e.gain_gold(state,player,progress['smallGold' if option=='small' else 'largeGold'])
        if option=='large':e.obtain_card(state,player,e.new_card(state,'Greed'))
    elif key=='SpiritGrafter':
        if option=='accept':e.heal(player,25);e.obtain_card(state,player,e.new_card(state,'Metamorphosis'))
        else:
            select_deck(state,player,'upgrade',title=prompt('upgrade'),upgrade=True)
            e.lose_hp(state,player,10)
    elif key=='PotionCourier':
        if option=='grab':
            for _ in range(3):fixed_potion(state,player,'FoulPotion')
        else:random_potion(state,player,rarity='uncommon')
    elif key=='TheLegendsWereTrue':
        if option=='map':e.obtain_card(state,player,e.new_card(state,'SpoilsMap'))
        else:e.lose_hp(state,player,8);random_potion(state,player)
    elif key=='HungryForMushrooms':e.relic(state,player,'BigMushroom' if option=='big' else 'FragrantMushroom')
    elif key=='SunkenStatue':
        if option=='sword':e.relic(state,player,'SwordOfStone')
        else:e.gain_gold(state,player,progress['gold']);e.lose_hp(state,player,7)
    elif key=='LostWisp':
        if option=='claim':e.obtain_card(state,player,e.new_card(state,'Decay'));e.relic(state,player,'LostWisp')
        else:e.gain_gold(state,player,progress['gold'])
    elif key=='RoomFullOfCheese':
        if option=='search':e.lose_hp(state,player,14);e.relic(state,player,'ChosenCheese')
        else:
            pool=[d for d in e.reward_pool(player) if d['rarity']=='common']
            cards=e.card_choices(state,player,pool,source='event',count=8,uniform=True)
            cards=[e.new_card(state,c['key'],c['upgraded']) for c in cards]
            select_now(state,player,{'op':'select','source':'generated','destination':'deck','cards':cards,
                                    'minimum':2,'maximum':2,'title':'大快朵颐：选择两张牌加入牌组'})
    elif key=='MorphicGrove':
        if option=='loner':player['maxHp']+=5;e.heal(player,5)
        else:
            player['gold']=0
            select_deck(state,player,'randomTransform',count=2,title=prompt('transform',2))
    else:raise e.InvalidAction('事件效果尚未实现：'+key)
    progress['done']=True;player['done']=True


def fight_fake_merchant(state,player):
    progress=state['eventState']['players'][str(player['id'])]
    state['eventCombat']={'key':'FakeMerchant','encounter':'FakeMerchantEventEncounter',
                         'relics':['FakeMerchantsRug',*[r['key'] for r in progress['inventory']]]}
    progress['done']=True
    e.start_battle(state,'battle','FakeMerchantEventEncounter')


def finish_event_combat(state):
    battle=state['eventCombat']
    for player in state['players'].values():
        player['reward']=[];player['extraRewardChoices']=[];player['done']=True
        extra_cards=player.pop('extraCardRewards',0)
        state['eventState']['players'][str(player['id'])]['done']=True
        state['eventState']['players'][str(player['id'])]['trainingResult']='timeout' if battle.get('ranOutOfTime') else 'victory'
        if battle['key']=='BattlewornDummy' and not battle.get('ranOutOfTime'):
            if battle['setting']==1:
                key=e.rewards_rng(state,player,lambda rng:rng.next_item(potions.candidates(player)))
                player['pendingPotions'].append(potions.create(state,key))
            elif battle['setting']==2:
                for card in event_shuffle(state,'BattlewornDummy',player,e.reference_sorted(c for c in player['deck'] if e.upgradable(c)))[:2]:e.upgrade(card)
            else:
                from ..rewards.custom import queue_relic
                queue_relic(state,player)
            from ..rewards.custom import offer_cards
            for _ in range(extra_cards):offer_cards(state,player,source=state['encounterKind'])
    e.log(state,'训练超时，未获得档位奖励。' if battle.get('ranOutOfTime') else '训练完成，领取档位奖励。')
    e.advance_if_ready(state)


def potion_card_rarity(item):
    rarity=potions.DATA[item['key']]['rarity']
    return {'event':'rare','token':'common'}.get(rarity,rarity)


def potions_locked(state,player):
    return (state.get('phase')=='event' and state.get('event') in ('TheFutureOfPotions','RanwidTheElder','StoneOfAllTime')
            and not state['eventState']['players'][str(player['id'])]['done'])


def act(state,player,action):
    record=state['eventState'];key=state['event'];option=action.get('option')
    page=record['page'] if key in SHARED else record['players'][str(player['id'])]['page']
    e.require(action.get('event')==key and action.get('page')==page,'事件页面已变化。')
    e.require(not record['players'][str(player['id'])]['done'],'事件已完成。')
    e.require(option in [item[0] for item in choices(state,player)],'无效的事件选择。')
    if key in SHARED:
        record['votes'][str(player['id'])]=option;player['vote']=option
        if len(record['votes'])<len(state['players']):return
        selected=shared_vote_pick(state,[record['votes'][uid] for uid in state['players']])
        record['votes']={};record['page']+=1
        if key=='BattlewornDummy':
            for member in state['players'].values():member['vote']=None
            encounter='BattlewornDummyEventV'+selected+'Encounter'
            state['eventCombat']={'key':key,'encounter':encounter,'setting':int(selected),'noOrdinaryRewards':True}
            e.start_battle(state,'battle',encounter);return
        if key=='PunchOff' and selected in ('take','fight'):
            for member in state['players'].values():member['vote']=None
            if selected=='take':e.phase(state,'event');return
            for member in state['players'].values():record['players'][str(member['id'])]['done']=True
            state['eventCombat']={'key':key,'encounter':'PunchOffEventEncounter'}
            e.start_battle(state,'battle','PunchOffEventEncounter');return
        if key=='DenseVegetation' and selected=='fight':
            for member in state['players'].values():
                member['vote']=None;record['players'][str(member['id'])]['done']=True
            state['eventCombat']={'key':key,'encounter':'DenseVegetationEventEncounter'}
            e.start_battle(state,'battle','DenseVegetationEventEncounter');return
        if key=='TheLanternKey':
            for member in state['players'].values():member['vote']=None
            if selected=='keep':e.phase(state,'event');return
            if selected=='fight':
                state['eventCombat']={'key':key,'encounter':'MysteriousKnightEventEncounter'}
                e.start_battle(state,'battle','MysteriousKnightEventEncounter')
                return
            for member in state['players'].values():
                e.gain_gold(state,member,100);member['done']=True;record['players'][str(member['id'])]['done']=True
            e.advance_if_ready(state);return
        e.phase(state,'event')
        from ...core.continuation import current
        runtime=current()
        for member in state['players'].values():
            member['vote']=None
            if runtime and runtime.independent and runtime.scheduler:
                runtime.scheduler.add('event-'+str(state['phaseId'])+':'+str(member['id']),
                                      lambda member=member:apply_effect(state,member,selected))
            else:apply_effect(state,member,selected)
    elif key==CRYSTAL_SPHERE:begin_sphere(state,player,option)
    else:apply_effect(state,player,option)
    e.advance_if_ready(state)


def view(state,player):
    record=state['eventState']
    progress=record['players'][str(player['id'])];description=''
    if state['event']=='TheArchitect':
        from .ending import description as ending_description
        description=ending_description(state,player)
    if state['event'] in ancients.KEYS:
        description='从本人的三份馈赠中选择一份；领取和选牌完成后等待同伴。'
        if 'locked' in progress['options']:description+=' 第三份馈赠不可用：没有可替换的初始遗物或可超越的初始牌。'
    if state['event']=='Trial' and progress.get('trialCase'):
        description='当前审判对象：'+{'merchant':'商人','noble':'贵族','nondescript':'身份不明者'}[progress['trialCase']]
    elif state['event']=='FakeMerchant':description='购买后可继续挑选。可在药水页投掷恶臭药水，引发战斗。'
    elif state['event']=='WelcomeToWongos':
        points=state.get('accountProgress',{}).get(str(player['id']),{}).get('wongoPoints',0)
        description=f'历史翁戈积分 {points}，每跨过 2000 积分获得纪念徽章。'
    result={'key':state['event'],'description':description,'shared':state['event'] in SHARED,'page':record['page'] if state['event'] in SHARED else record['players'][str(player['id'])]['page'],
            'votes':dict(record['votes']),
            'players':{uid:{'done':progress['done'],'page':progress['page']} for uid,progress in record['players'].items()}}
    if state['event']==CRYSTAL_SPHERE and 'sphere' in progress:
        result['sphere']=sphere_view(progress['sphere'])
    return result


def sphere_view(board):
    """What a player may be shown: the cells they have uncovered, nothing else.

    The layout is generated and kept server-side, so the items still hidden and
    the total number of them never leave this process.
    """
    from . import crystal_sphere
    game=crystal_sphere.Minigame.from_dict(board['board'])
    return {'divinations':game.divinations,'tool':game.tool,'finished':game.finished,
            'width':crystal_sphere.GRID_WIDTH,'height':crystal_sphere.GRID_HEIGHT,
            'cells':game.visible_board()}
