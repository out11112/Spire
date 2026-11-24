"""Cards obtained from events, ancients and their generated dependencies."""
def register(card):
    # Event cards can retain a character appearance despite sharing this registry.
    colored_events={'Caltrops','Clash','Distraction','DualWield','Entrench','HelloWorld','Outmaneuver','Rebound','RipAndTear','Stack'}
    def add(*args,**kwargs):
        card(*args,pool='special',visualColorless=args[0] not in colored_events and args[3]!='quest',**kwargs)
    add('Abundance','富足',1,'skill',upgrade={'cost':-1},rarity='ancient',exhaust=True,abundance=True,noCombatGenerate=True)
    add('Apotheosis','神化',2,'skill',upgrade={'cost':-1},rarity='ancient',exhaust=True,innate=True,apotheosis=True)
    add('Apparition','灵体',1,'skill',upgrade={'ethereal':-1},rarity='ancient',ethereal=True,exhaust=True,intangible=1)
    add('BrightestFlame','至亮之焰',0,'skill',upgrade={'brightestFlame':1},rarity='ancient',brightestFlame=2)
    add('Maul','撕咬',1,'attack','enemy',{'damage':1,'maul':1},rarity='ancient',damage=5,hits=2,maul=2)
    add('NeowsFury','涅奥之怒',1,'attack','enemy',{'damage':4,'neowsFury':1},rarity='ancient',damage=10,neowsFury=2,exhaust=True,noCombatGenerate=True)
    add('Relax','放松',3,'skill',upgrade={'block':2,'drawNextTurn':1,'energyNextTurn':1},rarity='ancient',block=16,drawNextTurn=2,energyNextTurn=2,exhaust=True)
    add('Whistle','吹哨',2,'attack','enemy',{'damage':11},rarity='ancient',damage=33,stun=True,exhaust=True)
    add('Wish','许愿',0,'skill',upgrade={'retain':1},rarity='ancient',wish=True,exhaust=True)
    add('Luminesce','冷光',0,'skill',upgrade={'energy':1},rarity='token',energy=2,retain=True,exhaust=True)
    add('Caltrops','铁蒺藜',1,'power',upgrade={'permanentThorns':2},rarity='event',permanentThorns=3)
    add('Clash','交锋',0,'attack','enemy',{'damage':4},rarity='event',damage=14,attackOnlyHand=True)
    add('Distraction','声东击西',1,'skill',upgrade={'cost':-1},rarity='event',distraction=True,exhaust=True)
    add('DualWield','双持',1,'skill',upgrade={'dualWield':1},rarity='event',dualWield=1)
    add('Enlightenment','开悟',0,'skill',rarity='event',enlightenment=True,exhaust=True)
    add('Entrench','巩固',2,'skill',upgrade={'cost':-1},rarity='event',entrench=True)
    add('Exterminate','杀灭',1,'attack','all',{'damage':1},rarity='event',damage=3,hits=4)
    add('FeedingFrenzy','疯狂进食',0,'skill',upgrade={'feedingFrenzy':2},rarity='event',feedingFrenzy=5)
    add('HelloWorld','你好世界',1,'power',upgrade={'innate':1},rarity='event',helloWorld=1)
    add('MadScience','疯狂科学',1,'attack','enemy',{'innate':1},rarity='event',madScience=True)
    add('Metamorphosis','羽化',2,'skill',upgrade={'metamorphosis':2},rarity='event',metamorphosis=3,exhaust=True)
    add('Outmaneuver','抢占先机',1,'skill',upgrade={'energyNextTurn':1},rarity='event',energyNextTurn=2)
    add('Peck','啄击',1,'attack','enemy',{'hits':1},rarity='event',damage=2,hits=3)
    add('Rebound','弹回',1,'attack','enemy',{'damage':3},rarity='event',damage=9,rebound=1)
    add('RipAndTear','狂乱撕扯',1,'attack','random',{'damage':2},rarity='event',damage=7,hits=2)
    add('Squash','压扁',1,'attack','enemy',{'damage':2,'vulnerable':1},rarity='event',damage=10,vulnerable=2)
    add('Stack','堆栈',1,'skill',upgrade={'stackBase':3},rarity='event',stack=True)
    add('ToricToughness','坚韧之环',2,'skill',upgrade={'block':2},rarity='event',block=5,toricToughness=2)
    add('ByrdSwoop','异鸟扑击',0,'attack','enemy',{'damage':4},rarity='event',damage=14)
    add('DeprecatedCard','弃用卡牌',0,'status',rarity='status',draw=1,exhaust=True,removeDeprecated=True)
    for key,name in [('ByrdonisEgg','多尼斯异鸟蛋'),('Dowsing','探寻'),('LanternKey','灯火钥匙'),('SpoilsMap','藏宝图')]:
        add(key,name,-1,'quest',rarity='quest',unplayable=True)
    for key,name,power,amount in [('Disintegration','瓦解','disintegration',6),('MindRot','心灵腐化','mindRot',1),('Sloth','懒惰','sloth',3),('WasteAway','衰朽','wasteAway',1)]:
        add(key,name,-1,'status',rarity='status',unplayable=True,noCombatGenerate=True,knowledgePower=power,knowledgeAmount=amount)


def modify_definition(instance,definition):
    if instance['key']=='Disintegration':definition['values']['knowledgeAmount']=instance.get('knowledgeAmount',6)
    if instance['key']!='MadScience':return
    kind=instance.get('scienceType','attack');rider=instance.get('scienceRider','none')
    if kind not in ('attack','skill','power'):raise ValueError('无效的疯狂科学类型。')
    definition['kind']=kind;definition['target']='enemy' if kind=='attack' else 'self'
    values=definition['values'];values['scienceRider']=rider
    if kind=='attack':
        values['damage']=12
        if rider=='violence':values['hits']=3
    elif kind=='skill':values['block']=8
    elif rider=='expertise':values.update(strength=2,dexterity=2)
    elif rider=='curious':values['curious']=1
    elif rider=='improvement':values['improvement']=1
    if rider=='sapping':values.update(weak=2,vulnerable=2)
    elif rider=='choking':values['strangle']=6
    elif rider=='energized':values['energy']=2
    elif rider=='wisdom':values['draw']=3
    elif rider=='chaos':values['scienceChaos']=True


def describe(values, *, upgraded=False):
    result=[]
    descriptions={'abundance':'从三张已升级职业能力牌中选择一张，本回合免费',
        'apotheosis':'升级本场所有其他可升级卡牌','wish':'从抽牌堆取一张牌','distraction':'生成一张职业技能牌，本回合免费',
        'enlightenment':"降低当前手牌的能量费至最多 1，"+("持续整场战斗" if upgraded else "本回合有效"),
        'entrench':'额外获得当前格挡等量的格挡，不受敏捷影响','attackOnlyHand':'手牌中只能有攻击牌时才可手动打出',
        'stun':'眩晕目标，跳过其下一次行动','stack':'获得等于弃牌堆数量的格挡',
        'scienceChaos':'生成一张随机职业牌，本回合免费'}
    for key,label in descriptions.items():
        if values.get(key):result.append(label)
    for key,label in {'maul':'所有本场撕咬的伤害增加','neowsFury':'取回至多这些弃牌','dualWield':'复制一张手牌中的攻击或能力牌的次数',
                      'feedingFrenzy':'本回合力量','helloWorld':'回合抽牌前生成职业普通牌','metamorphosis':'生成这些职业攻击到抽牌堆，本场免费',
                      'rebound':'本回合下一张原本进入弃牌堆的牌置于抽牌堆顶','curious':'能力牌费用降低','improvement':'战斗结束随机升级牌组卡牌'}.items():
        if values.get(key):result.append(f'{label} {values[key]}')
    if values.get('brightestFlame'):result.append(f"获得 {values['brightestFlame']} 能量并抽同等牌，然后失去 2 最大生命")
    if values.get('toricToughness'):result.append('接下来两次格挡被回合清空后，重新获得本次实际格挡量')
    if values.get('stackBase'):result.append(f"额外基础格挡 {values['stackBase']}")
    if values.get('knowledgePower'):
        descriptions={'disintegration':'每回合结束受到可格挡伤害','mindRot':'每回合少抽牌','sloth':'每回合最多打出牌数','wasteAway':'每回合能量上限减少'}
        result.append(f"知识恶魔选项：{descriptions[values['knowledgePower']]} {values['knowledgeAmount']}；不加入牌组")
    if values.get('removeDeprecated'):result.append('打出后从永久牌组删除，用于废弃内容的旧存档')
    return result
