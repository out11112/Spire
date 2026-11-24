"""Additional colorless definitions audited against the supplied v0.111.0."""
def register(card):
    def add(*args,**kwargs):card(*args,pool='colorless',**kwargs)
    add('Alchemize','炼制药水',1,'skill',upgrade={'cost':-1},rarity='rare',alchemize=True,exhaust=True,noCombatGenerate=True)
    add('Anointed','天选',1,'skill',upgrade={'retain':1},rarity='rare',anointed=True,exhaust=True)
    add('BeaconOfHope','希望灯塔',2,'power',upgrade={'innate':1},rarity='rare',beaconOfHope=1,multiplayerOnly=True)
    add('BelieveInYou','相信着你',0,'skill','ally',{'allyEnergy':1},rarity='uncommon',allyEnergy=2,multiplayerOnly=True)
    add('Bolas','流星锤',0,'attack','enemy',{'damage':1},rarity='rare',damage=3,returnNextTurn=True)
    add('Coordinate','协同配合',1,'skill','ally',{'coordinate':3},rarity='uncommon',coordinate=5,multiplayerOnly=True)
    add('EternalArmor','永恒铠甲',3,'power',upgrade={'plating':3},rarity='rare',plating=9)
    add('Entropy','熵',1,'power',upgrade={'innate':1},rarity='rare',entropy=1)
    add('Fasten','勒紧',1,'power',upgrade={'fasten':2},rarity='uncommon',fasten=4)
    add('Fisticuffs','拳斗',1,'attack','enemy',{'damage':2},rarity='uncommon',damage=7,fisticuffs=True)
    add('GangUp','群起攻之',1,'attack','enemy',{'gangUp':2},rarity='uncommon',damage=5,gangUp=5,multiplayerOnly=True)
    add('GoldAxe','金斧',1,'attack','enemy',{'retain':1},rarity='rare',goldAxe=True)
    add('HandOfGreed','贪婪之手',2,'attack','enemy',{'damage':5,'fatalGold':5},rarity='rare',damage=20,fatalGold=20,noCombatGenerate=True)
    add('HuddleUp','抱团',1,'skill','allies',{'allDraw':1},rarity='uncommon',allDraw=2,exhaust=True,multiplayerOnly=True)
    add('Knockdown','击倒',3,'attack','enemy',{'damage':4,'knockdown':1},rarity='rare',damage=10,knockdown=2,multiplayerOnly=True)
    add('Lift','托举',1,'skill','ally',{'allyBlock':5},rarity='uncommon',allyBlock=11,multiplayerOnly=True)
    add('Omnislice','万向斩',0,'attack','enemy',{'damage':3},rarity='uncommon',damage=8,omnislice=True)
    add('Prowess','非凡技艺',1,'power',upgrade={'strength':1,'dexterity':1},rarity='uncommon',strength=1,dexterity=1)
    add('Rend','撕碎',1,'attack','enemy',{'damage':2,'rend':3},rarity='rare',damage=10,rend=5)
    add('SeekerStrike','探寻打击',1,'attack','enemy',{'damage':3},rarity='uncommon',damage=9,seekerStrike=3,strike=True)
    add('UltimateDefend','究极防御',1,'skill',upgrade={'block':4},rarity='uncommon',block=11,defend=True)
    add('UltimateStrike','究极打击',1,'attack','enemy',{'damage':6},rarity='uncommon',damage=14,strike=True)
    add('Volley','连射',0,'attack','random',{'damage':4},rarity='uncommon',damage=10,xCost=True)
    add('Equilibrium','均衡',2,'skill',upgrade={'block':3},rarity='uncommon',block=13,retainHand=1)
    add('Intercept','拦截',1,'skill','ally',{'block':4},rarity='uncommon',block=9,intercept=True,multiplayerOnly=True)
    add('Mimic','拟态',1,'skill','ally',{'exhaust':-1},rarity='rare',mimic=True,exhaust=True,multiplayerOnly=True)
    add('Production','生产制造',0,'skill',upgrade={'energy':1},rarity='uncommon',energy=2,exhaust=True)
    add('Prolong','延伸',0,'skill',upgrade={'exhaust':-1},rarity='uncommon',prolong=True,exhaust=True)
    add('Rally','集结',2,'skill','allies',{'allBlock':5},rarity='rare',allBlock=12,multiplayerOnly=True)
    add('Restlessness','心神不宁',0,'skill',upgrade={'restlessness':1},rarity='uncommon',restlessness=2,retain=True)
    add('Salvo','箭雨',1,'attack','enemy',{'damage':4},rarity='uncommon',damage=12,retainHand=1)
    add('ThrummingHatchet','无休手斧',1,'attack','enemy',{'damage':3},rarity='uncommon',damage=11,returnNextTurn=True)
    add('RollingBoulder','滚石',3,'power',upgrade={'rollingBoulder':5},rarity='rare',rollingBoulder=5)
    add('TheBomb','炸弹',2,'skill',upgrade={'bomb':10},rarity='uncommon',bomb=40)
    add('TheGambit','孤注一掷',0,'skill',upgrade={'block':25},rarity='rare',block=50,theGambit=1)
    add('Panache','神气制胜',0,'power',upgrade={'panache':4},rarity='uncommon',panache=10)
    add('PrepTime','准备时间',1,'power',upgrade={'prepTime':2},rarity='uncommon',prepTime=4)
    add('Automation','自动化',1,'power',upgrade={'cost':-1},rarity='uncommon',automation=1)
    add('Jackpot','大奖',3,'attack','enemy',{'damage':5},rarity='rare',damage=25,jackpot=3)
    add('TheBall','魔球',1,'attack','enemy',{'theBall':5},rarity='uncommon',damage=10,theBall=10,multiplayerOnly=True)
    add('Nostalgia','怀旧',1,'power',upgrade={'cost':-1},rarity='rare',nostalgia=1)
    add('BeatDown','狠揍',3,'skill','random',{'beatDown':1},rarity='rare',beatDown=3)
    add('Catastrophe','横祸',2,'skill',upgrade={'catastrophe':1},rarity='uncommon',catastrophe=2)
    add('Calamity','劫难',3,'power',upgrade={'cost':-1},rarity='rare',calamity=1)
    add('HiddenGem','未掘宝石',1,'skill',upgrade={'hiddenGem':1},rarity='rare',hiddenGem=2,noCombatGenerate=True)
    add('TagTeam','双打组合',2,'attack','enemy',{'damage':4},rarity='uncommon',damage=11,tagTeam=1,multiplayerOnly=True)
    add('Splash','飞溅',1,'skill',rarity='rare',splash=True)
    add('Mayhem','乱战',2,'power',upgrade={'cost':-1},rarity='rare',mayhem=1)
    add('Stratagem','计策',1,'power',upgrade={'cost':-1},rarity='uncommon',stratagem=1)


VALUES={'hiddenGem':'为抽牌堆中随机尚无额外出牌次数的可用牌增加本场额外出牌次数，数量','catastrophe':'依次自动打出抽牌堆随机牌，优先可打出的牌，数量','beatDown':'自动打出弃牌堆中随机攻击牌，数量','allyEnergy':'队友获得能量','allyBlock':'队友获得格挡','allDraw':'全队抽牌','allBlock':'全队获得格挡',
        'coordinate':'队友本回合力量','fasten':'防御牌额外基础格挡','gangUp':'目标本回合每被其他队友攻击一次的额外伤害',
        'fatalGold':'致命击杀获得金币','knockdown':'本回合其他角色攻击目标的伤害倍率','rend':'目标每种非临时负面状态额外伤害',
        'seekerStrike':'从抽牌堆随机候选中选择一张加入手牌，候选数','rollingBoulder':'每回合开始全体直接伤害，之后增加 5',
        'bomb':'第三次己方回合结束时全体直接伤害','panache':'打出后每回合每 5 张牌造成全体直接伤害',
        'prepTime':'每回合开始获得下一次攻击的额外伤害','automation':'每抽 10 张牌获得能量',
        'jackpot':'生成随机费用为 0 的职业牌张数','theBall':'每次打出后本牌伤害增加，传入随机队友抽牌堆',
        'nostalgia':'每回合首张攻击或技能回到抽牌堆顶的次数','restlessness':'仅当打出后没有其他手牌时，抽牌并获得能量'}
FLAGS={'anointed':'将抽牌堆随机稀有牌加入手牌，直到没有候选或手牌已满',
       'beaconOfHope':'己方回合获得格挡时，将一半格挡分享给其他队友',
       'returnNextTurn':'若本回合打出，下一回合抽牌前返回手牌',
       'fisticuffs':'获得等同实际攻击伤害（含格挡和溢出）的基础格挡',
       'goldAxe':'基础伤害等于本场全队已完成的出牌次数',
       'omnislice':'对其他敌人造成等同本次攻击实际伤害的直接伤害',
       'retainHand':'本回合保留全部手牌，虚无仍然生效',
       'intercept':'本回合目标免疫攻击伤害，自身按掩护人数承受更多攻击伤害',
       'mimic':'获得等同队友当前格挡的基础格挡',
       'prolong':'记录当前格挡，下次清空格挡时重新获得',
       'theGambit':'受到攻击并损失生命时立即死亡，直到战斗结束',
       'calamity':'每次攻击后生成随机职业攻击牌加入手牌',

       'tagTeam':'其他队友下一张命中此目标的指定或全体攻击额外打出一次'}


def describe(values, *, upgraded=False):
    return ([f"每当你在一回合内打出五张牌时，对所有敌人造成 {values['panache']} 点伤害"] if values.get('panache') else []) + [f'{label} {values[key]}' for key,label in VALUES.items() if values.get(key) and key!='panache']+[label for key,label in FLAGS.items() if values.get(key)]+(['生成的牌均已升级'] if values.get('jackpot') and upgraded else [])
