"""Necrobinder attacks required by Splash, with no automatic pet grant."""


def register(card):
    def attack(key,name,cost,damage,upgrade,rarity='common',target='enemy',**values):
        card(key,name,cost,'attack',target,upgrade,rarity=rarity,pool='necrobinder',damage=damage,**values)
    attack('BansheesCry','女妖之嚎',9,33,{'cost':-2},'rare',target='all',etherealCostReduction=2)
    attack('BlightStrike','荒疫打击',1,8,{'damage':2},strike=True,damageToDoom=True)
    attack('BoneShards','碎骨',1,9,{'damage':3,'ostySacrificeBlock':3},'uncommon',target='all',osty=True,ostySacrificeBlock=9)
    attack('Bury','埋葬',4,52,{'damage':11},'uncommon')
    attack('DeathMarch','死亡行军',1,8,{'damage':1,'extraDrawDamage':2},'uncommon',extraDrawDamage=4)
    attack('Debilitate','摧残',1,10,{'damage':2,'debilitate':1},'uncommon',debilitate=2)
    attack('Defile','玷污',1,13,{'damage':4},ethereal=True)
    attack('DrainPower','能量汲取',1,10,{'damage':2,'upgradeDiscard':1},upgradeDiscard=2)
    attack('Eradicate','根除',0,11,{'damage':3},'rare',xCost=True,retain=True)
    attack('Fear','恐惧',1,7,{'damage':1,'vulnerable':1},ethereal=True,vulnerable=1)
    attack('Fetch','取回',0,3,{'damage':3},'uncommon',osty=True,fetch=1)
    attack('Flatten','重压',2,12,{'damage':4},osty=True,flatten=True)
    attack('Graveblast','坟冢爆射',1,4,{'damage':2,'exhaust':-1},exhaust=1,graveblast=True)
    attack('Hang','吊杀',1,10,{'damage':3},'rare',hang=True)
    attack('HighFive','击掌',2,11,{'damage':2,'vulnerable':1},'uncommon',target='all',osty=True,requiresOsty=True,vulnerable=2)
    attack('Misery','苦难',0,7,{'damage':2,'retain':1},'rare',misery=True)
    attack('Poke','戳击',0,6,{'damage':3},osty=True)
    attack('PullFromBelow','亡魂牵引',1,5,{'damage':2},'uncommon',etherealHits=True)
    attack('Rattle','猛晃',1,7,{'damage':2},'uncommon',osty=True,rattle=True)
    attack('Reap','收割',3,27,{'damage':6},retain=True)
    attack('Reave','剥夺',1,10,{'damage':3},reave=True)
    attack('RightHandHand','得力助手',0,4,{'damage':2},'uncommon',osty=True,returnAfterEnergy=2)
    attack('SculptingStrike','雕琢打击',1,9,{'damage':3},strike=True,grantKeyword='ethereal')
    attack('Severance','切断',2,13,{'damage':5},'uncommon',severance=True)
    attack('SicEm','紧追不放',1,5,{'damage':1,'sicEm':1},'uncommon',osty=True,sicEm=3)
    attack('Snap','响指',1,7,{'damage':3},osty=True,grantKeyword='retain')
    attack('SoulStorm','灵魂风暴',1,9,{'soulDamage':2},'rare',soulDamage=4)
    attack('Sow','播种',1,8,{'damage':3},target='all',retain=True)
    attack('Squeeze','榨取',3,25,{'damage':5,'ostyCardDamage':1},'rare',osty=True,ostyCardDamage=5)
    attack('TheScythe','巨镰',2,13,{'scythe':2},'rare',exhaust=True,scythe=5)
    attack('TimesUp','大限已至',2,0,{'retain':1},'rare',doomDamage=True)
    attack('Veilpiercer','刺破帷幕',1,10,{'damage':3},'uncommon',veilpiercer=1)
    card('Soul','灵魂',0,'skill',upgrade={'draw':1},rarity='token',pool='token',draw=2,exhaust=True)
    def skill(key,name,cost,upgrade=None,rarity='common',target='self',**values):
        card(key,name,cost,'skill',target,upgrade,rarity=rarity,pool='necrobinder',**values)
    def power(key,name,cost,upgrade=None,rarity='uncommon',**values):
        card(key,name,cost,'power','self',upgrade,rarity=rarity,pool='necrobinder',**values)
    skill('BorrowedTime','预借时间',1,{'energy':2},'uncommon',energy=4,borrowedTime=1)
    skill('CaptureSpirit','捕捉灵魂',1,{'captureSpirit':1,'soulDrawGeneration':1},'uncommon','enemy',captureSpirit=3,soulDrawGeneration=3)
    skill('Cleanse','洁净',1,{'summon':2},'uncommon',summon=3,cleanse=True)
    skill('DeathsDoor','死亡之门',1,{'deathDoorBlock':1},'uncommon',deathDoorBlock=6)
    skill('Defy','违逆',1,{'block':3},target='enemy',block=6,weak=1,ethereal=True)
    skill('Delay','拖延',2,{'block':2,'energyNextTurn':1},'uncommon',block=11,energyNextTurn=1)
    skill('GraveWarden','守墓人',1,{'block':3},block=8,soulDrawGeneration=1)
    skill('NegativePulse','负能量脉冲',1,{'block':1,'doom':4},target='all',block=5,doom=7)
    skill('NoEscape','无处可逃',1,{'noEscape':5},'uncommon','enemy',noEscape=10)
    skill('Putrefy','腐败',1,{'weak':1,'vulnerable':1},'uncommon','enemy',weak=2,vulnerable=2,exhaust=True)
    skill('Afterlife','来生',1,{'summon':3},summon=6,exhaust=True)
    skill('Dirge','挽歌',0,{'dirgeSummon':1},'uncommon',dirgeSummon=3,xCost=True,exhaust=True)
    skill('Dredge','清淤',1,{'retain':1},'uncommon',dredge=3,exhaust=True)
    skill('Eidolon','幻景',2,{'cost':-1},'rare',eidolon=True,exhaust=True,noCombatGenerate=True)
    skill('EnfeeblingTouch','弱化之触',1,{'temporaryEnemyStrength':3},'uncommon','enemy',temporaryEnemyStrength=8,ethereal=True)
    power('Calcify','钙化',1,{'calcify':2},calcify=4)
    power('Countdown','倒数计时',1,{'countdown':3},countdown=6)
    power('DanseMacabre','死亡之舞',1,{'danseMacabre':2},danseMacabre=4)
    power('DevourLife','吞噬生命',1,{'devourLife':1},'rare',devourLife=1)
    power('Cacophony','不谐合曲',2,{'cacophony':33},'rare',cacophony=66,multiplayerOnly=True)
    power('Friendship','友谊',1,{'friendshipStrengthLoss':-1},friendship=1,friendshipStrengthLoss=2)
    skill('GlimpseBeyond','彼岸一瞥',1,{'allySouls':1},'rare',target='allies',allySouls=3,exhaust=True,multiplayerOnly=True)
    power('Haunt','纠缠',1,{'haunt':2},haunt=7)
    skill('Invoke','唤起',1,{'summonNextTurn':1,'energyNextTurn':1},summonNextTurn=2,energyNextTurn=2)
    skill('LegionOfBone','骸骨军团',2,{'allSummon':2},'uncommon',target='allies',allSummon=6,multiplayerOnly=True)
    power('Lethality','致死性',1,{'lethality':25},lethality=50,ethereal=True)
    skill('Melancholy','忧郁',3,{'block':4},'uncommon',block=13,deathCostReduction=1)
    power('Neurosurge','精神过载',0,{'energy':1},'rare',energy=3,draw=2,neurosurge=3)
    skill('Oblivion','湮灭',0,{'oblivion':1},'rare','enemy',oblivion=3)
    skill('Parse','领会',1,{'draw':1},'uncommon',draw=3,ethereal=True)
    attack('Protector','守护者',1,10,{'cost':-1,'damage':5},'ancient',osty=True,ostyMaxHpDamage=True)
    skill('PullAggro','吸引仇恨',2,{'summon':1,'blockAfterSummon':2},summon=4,blockAfterSummon=7)
    skill('Reanimate','死者苏生',3,{'summon':5},'rare',summon=20,exhaust=True)
    skill('Sacrifice','牺牲',1,{'cost':-1},'rare',sacrificeOsty=3,retain=True)
    skill('Scourge','鞭打',1,{'doom':3,'drawAfterDoom':1},target='enemy',doom=13,drawAfterDoom=1)
    skill('Seance','降灵',1,{'cost':-1},'rare',seance=True,ethereal=True)
    power('SentryMode','哨卫模式',2,{'cost':-1},'rare',sentryMode=1)
    skill('SharedFate','命运同担',0,{'enemyStrengthLoss':1},'rare','enemy',selfStrengthLoss=2,enemyStrengthLoss=2,exhaust=True)
    power('Shroud','厄运之衣',1,{'shroud':1},shroud=3)
    power('SleightOfFlesh','血肉戏法',2,{'sleightOfFlesh':4},sleightOfFlesh=9)
    power('CallOfTheVoid','虚空之唤',1,{'innate':1},'rare',callOfTheVoid=1)
    skill('Deathbringer','死亡使者',2,{'doom':5},'uncommon','all',doom=21,weakAfterDoom=1)
    power('Demesne','领域',3,{'cost':-1},'rare',demesne=1,ethereal=True)
    skill('EndOfDays','末日降临',3,{'doom':8},'rare','all',doom=29,endOfDays=True)
    power('ForbiddenGrimoire','禁忌魔典',2,{'cost':-1},'ancient',forbiddenGrimoire=1,eternal=True)
    power('NecroMastery','亡灵精通',2,{'summon':3},'rare',summon=5,necroMastery=1)
    power('Pagestorm','书页风暴',1,{'cost':-1},pagestorm=1)
    power('ReaperForm','死神形态',3,{'retain':1},'rare',reaperForm=1)
    card('Soulbound','灵魂绑定',1,'power','ally',{'innate':1},rarity='uncommon',pool='necrobinder',soulbound=1,multiplayerOnly=True)
    power('SpiritOfAsh','灰烬之灵',1,{'spiritOfAsh':1},'rare',spiritOfAsh=4)
    skill('Spur','增生',1,{'summon':2,'healOsty':2},'uncommon',summon=3,healOsty=5,retain=True)
    skill('Transfigure','重构',1,{'exhaust':-1},'rare',transfigure=True,exhaust=True,noCombatGenerate=True)
    skill('Undeath','不死',0,{'block':2},'rare',block=7,copy=True)
    skill('Underworld','幽冥之界',2,{'exhaust':-1},'uncommon',underworld=1,exhaust=True,multiplayerOnly=True)
    skill('Wisp','鬼火',0,{'retain':1},energy=1,exhaust=True)
    card('SweepingGaze','扫荡凝视',0,'attack','random',{'damage':5},rarity='token',pool='token',damage=10,osty=True,ethereal=True,exhaust=True)


def describe(values, *, upgraded=False):
    result=[]
    for key,label in {'etherealCostReduction':'本场每结算一张虚无牌降低费用','ostySacrificeBlock':'奥斯提攻击后获得格挡并牺牲它',
                      'extraDrawDamage':'本回合每张非回合抽牌额外伤害','debilitate':'使目标虚弱和易伤加倍的回合数','upgradeDiscard':'随机升级弃牌',
                      'fetch':'本牌每回合首次由奥斯提攻击后抽牌','returnAfterEnergy':'结算费用值达到此值的牌后从弃牌堆取回本牌',
                      'sicEm':'本回合奥斯提攻击此目标时召唤量','soulDamage':'消耗堆每张灵魂额外伤害','ostyCardDamage':'其他奥斯提攻击牌每张额外伤害',
                      'scythe':'打出后本牌永久增加伤害','veilpiercer':'后续虚无牌免费次数','borrowedTime':'本回合后续牌能量费用增加',
                      'captureSpirit':'穿透格挡的直接伤害','soulDrawGeneration':'生成灵魂到抽牌堆随机位置','deathDoorBlock':'获得格挡，本回合施加过灾厄则获得三次',
                      'doom':'施加灾厄','weakAfterDoom':'施加灾厄后对所有敌人施加虚弱','noEscape':'施加灾厄，每十层现有灾厄再增加五层','dirgeSummon':'每点 X 向抽牌堆生成一张灵魂'+('+' if upgraded else '')+'，并召唤',
                      'dredge':'从弃牌堆选回手牌，受空余手牌位置限制','calcify':'奥斯提攻击额外伤害','countdown':'回合开始向随机敌人施加灾厄',
                      'danseMacabre':'打出费用值至少为二的牌前获得格挡','devourLife':'每次打出灵魂后召唤','cacophony':'全队每抽三十三张牌对随机敌人造成伤害',
                      'friendship':'每回合额外能量','friendshipStrengthLoss':'失去力量','allySouls':'向所有存活玩家（包括自己）的抽牌堆各生成灵魂',
                      'haunt':'每次打出灵魂后，随机敌人失去生命','summonNextTurn':'下回合召唤','allSummon':'为所有存活玩家召唤',
                      'lethality':'每回合首个攻击牌的第一次结算伤害增加百分比','deathCostReduction':'每次生物死亡降低本牌战斗费用',
                      'neurosurge':'之后每回合开始对自己施加灾厄','oblivion':'本回合后续每次打牌对目标施加灾厄',
                      'blockAfterSummon':'召唤后获得格挡','sacrificeOsty':'牺牲奥斯提，获得其最大生命乘以此数的格挡','drawAfterDoom':'施加灾厄后抽牌',
                      'sentryMode':'回合抽牌前生成扫荡凝视','selfStrengthLoss':'失去力量','enemyStrengthLoss':'目标失去力量','shroud':'自己成功施加灾厄后获得格挡',
                      'sleightOfFlesh':'自己施加非临时负面效果后对目标造成伤害','callOfTheVoid':'回合抽牌前生成本职业随机牌并赋予虚无',
                      'demesne':'每回合额外能量和抽牌','forbiddenGrimoire':'胜利后额外删牌次数','necroMastery':'奥斯提每失去一点生命，使所有敌人失去生命的倍数',
                      'pagestorm':'抽到虚无牌时额外抽牌','reaperForm':'攻击伤害转为额外灾厄的倍数','soulbound':'施法者生成灵魂时为目标生成灵魂',
                      'spiritOfAsh':'每次打出虚无牌前获得格挡','healOsty':'召唤后恢复奥斯提生命','underworld':'本回合其他队友的攻击伤害转为额外灾厄的倍数'}.items():
        if values.get(key):result.append(f'{label} {values[key]}')
    for key,label in {'damageToDoom':'对目标施加等同本次伤害的灾厄','osty':'由奥斯提攻击；缺席时不攻击','flatten':'奥斯提本回合攻击过后费用为 0',
                      'graveblast':'选择一张弃牌取回手牌','hang':'目标之后受到本牌伤害的倍率翻倍','requiresOsty':'必须有存活奥斯提才能手动打出',
                      'misery':'将目标攻击前的负面效果复制到其他敌人','etherealHits':'本场每结算一张虚无牌攻击一次','rattle':'奥斯提本回合此前每次攻击增加一次攻击',
                      'reave':'向抽牌堆随机位置生成一张灵魂'+('+' if upgraded else ''),'severance':'抽牌、弃牌、手牌各生成一张灵魂','doomDamage':'基础伤害等于目标灾厄',
                      'cleanse':'召唤后从抽牌堆选择一张消耗','eidolon':'依次自动打出消耗堆中可打出的虚无牌',
                      'ostyMaxHpDamage':'加上存活奥斯提的最大生命作为基础伤害','seance':'将抽牌堆的一张牌变为未升级的灵魂',
                      'endOfDays':'施加灾厄后立即击杀灾厄不低于生命的敌人','transfigure':'选一张手牌，本场费用增加一且额外打出一次，X 费不增加费用'}.items():
        if values.get(key):result.append(label)
    if values.get('grantKeyword'):result.append('选择一张手牌赋予'+{'ethereal':'虚无','retain':'保留'}[values['grantKeyword']])
    return result
