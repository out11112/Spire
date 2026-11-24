"""Defect card rules, including cross-character generation dependencies."""


def register(card):
    def attack(key,name,cost,damage,upgrade,rarity='common',target='enemy',**values):
        card(key,name,cost,'attack',target,upgrade,rarity=rarity,pool='defect',damage=damage,**values)
    def skill(key,name,cost,upgrade=None,rarity='common',target='self',**values):
        card(key,name,cost,'skill',target,upgrade,rarity=rarity,pool='defect',**values)
    def ability(key,name,cost,upgrade=None,rarity='uncommon',target='self',**values):
        card(key,name,cost,'power',target,upgrade,rarity=rarity,pool='defect',**values)
    skill('BoostAway','高速脱离',0,{'block':3},block=6,generatedStatus='Dazed')
    skill('BootSequence','启动流程',0,{'block':3},'uncommon',block=10,innate=True,exhaust=True)
    ability('BulkUp','暴涨',2,{'strength':1,'dexterity':1},strength=2,dexterity=2,removeOrbSlots=1)
    ability('Capacitor','扩容',1,{'addOrbSlots':1},addOrbSlots=2)
    skill('Chaos','混沌',1,{'randomOrbs':1},'uncommon',randomOrbs=1)
    skill('ChargeBattery','充电',1,{'block':3},block=7,energyNextTurn=1)
    skill('Chill','冰寒',0,{'exhaust':-1},'uncommon',chill=True,exhaust=True)
    ability('Coolant','冷却剂',1,{'coolant':1},'rare',coolant=2)
    skill('Coolheaded','冷静头脑',1,{'drawAfterChannel':1},channel='frost',drawAfterChannel=1)
    skill('Darkness','漆黑',1,{'darknessTriggers':1},'uncommon',channel='dark',darknessTriggers=1)
    ability('Defragment','碎片整理',1,{'focus':1},'rare',focus=1)
    skill('DoubleEnergy','双倍能量',1,{'cost':-1},'uncommon',doubleEnergy=True,exhaust=True)
    skill('EnergySurge','能量涌动',1,{'allEnergy':1},'uncommon',target='allies',allEnergy=2,exhaust=True,multiplayerOnly=True)
    skill('Fusion','聚变',1,{'exhaust':-1},'uncommon',channel='plasma',exhaust=True)
    skill('Glacier','冰川',2,{'block':3},'uncommon',block=6,channel='frost',channelCount=2)
    skill('Glasswork','玻璃工艺',1,{'block':3},'uncommon',block=5,channel='glass')
    skill('Leap','飞跃',1,{'block':3},block=9)
    skill('Overclock','超频',0,{'draw':1},'uncommon',draw=2,generatedStatus='Burn')
    skill('Rainbow','彩虹',2,{'exhaust':-1},'rare',rainbow=True,exhaust=True)
    skill('Skim','快速检索',1,{'draw':1},'uncommon',draw=3)
    skill('Turbo','内核加速',0,{'energy':1},energy=2,generatedStatus='Void')
    skill('Tempest','暴风雨',0,{'tempestBonus':1},'uncommon',tempest=True,xCost=True)
    ability('BiasedCognition','偏差认知',1,{'focus':1},'ancient',focus=5,biasedCognition=1)
    ability('Buffer','缓冲',2,{'buffer':1},'rare',buffer=1)
    skill('Compact','压缩',1,{'block':1},'uncommon',block=6,compact=True)
    ability('ConsumingShadow','吞噬暗影',2,{'channelCount':1},'rare',channel='dark',channelCount=2,consumingShadow=1)
    ability('CreativeAi','创造性AI',3,{'cost':-1},'rare',creativeAi=1)
    ability('EchoForm','回响形态',3,{'ethereal':-1},'rare',echoForm=1,ethereal=True)
    ability('Feral','野性',2,{'cost':-1},feral=1)
    skill('FightThrough','强撑',1,{'block':4},'uncommon',block=13,generatedStatus='Wound',statusCount=2)
    skill('GeneticAlgorithm','遗传算法',1,{'geneticGrowth':1},'rare',block=1,geneticGrowth=3,exhaust=True)
    ability('Hailstorm','冰雹风暴',1,{'hailstorm':2},hailstorm=6)
    skill('Hibernate','休眠',2,{'hibernate':1},'uncommon',hibernate=2,multiplayerOnly=True)
    skill('Hologram','全息影像',1,{'block':2,'exhaust':-1},block=3,graveblast=True,exhaust=True)
    skill('Hotfix','热修复',0,{'exhaust':-1},temporaryFocus=2,exhaust=True)
    card('Ignition','引火',1,'skill','ally',{'exhaust':-1},rarity='uncommon',pool='defect',allyChannel='plasma',exhaust=True,multiplayerOnly=True)
    card('ImitationLearning','模仿学习',1,'skill','ally',{'imitationLearning':1},rarity='rare',pool='defect',imitationLearning=2,exhaust=True,multiplayerOnly=True)
    ability('Iteration','迭代',1,{'iteration':1},iteration=2)
    skill('LightningRod','引雷针',1,{'block':3},block=4,lightningRod=2)
    ability('Loop','循环',1,{'loop':1},loop=1)
    ability('MachineLearning','机器学习',1,{'innate':1},'rare',machineLearning=1)
    skill('Modded','模组改造',0,{'moddedDraw':1},'rare',addOrbSlots=1,moddedDraw=1)
    skill('MultiCast','多重释放',0,{'multiCastBonus':1},'rare',multiCast=True,xCost=True)
    ability('OneForAll','一心化万',1,{'oneForAll':1},'rare',target='allies',oneForAll=3,multiplayerOnly=True)
    skill('Quadcast','四重释放',1,{'cost':-1},'ancient',evokeFirst=4)
    skill('Reboot','重启',0,{'reboot':2},'rare',reboot=4,exhaust=True)
    skill('Scavenge','内存清理',1,{'scavenge':1},'uncommon',scavenge=2)
    skill('ShadowShield','暗影之盾',2,{'block':4},'uncommon',block=11,channel='dark')
    skill('SignalBoost','信号增强',1,{'cost':-1},'rare',signalBoost=1,exhaust=True)
    ability('Smokestack','烟囱',1,{'smokestack':2},smokestack=5)
    ability('Spinner','旋转工艺',1,{'spinnerChannel':1},'rare',spinner=1)
    ability('Storm','雷暴',1,{'storm':1},storm=1)
    ability('Subroutine','子程序',1,{'cost':-1},subroutine=1)
    skill('Supercritical','超临界态',0,{'energy':2},'rare',energy=4,exhaust=True)
    skill('Synchronize','同步',1,{'synchronize':1},'uncommon',synchronize=1)
    ability('Thunder','雷霆',1,{'thunder':3},thunder=8)
    ability('TrashToTreasure','化废为宝',1,{'cost':-1},'rare',trashToTreasure=1)
    skill('Voltaic','电流相生',3,{'exhaust':-1},'rare',voltaic=True,exhaust=True)
    skill('WhiteNoise','白噪声',1,{'cost':-1},'uncommon',whiteNoise=True,exhaust=True)
    card('Fuel','燃料',0,'skill','self',{'energy':1},rarity='token',pool='token',energy=1,exhaust=True)
    attack('AdaptiveStrike','适应打击',2,18,{'damage':5},'rare',strike=True,adaptiveStrike=True)
    attack('AllForOne','万物一心',2,10,{'damage':4},'rare',allForOne=True)
    attack('BallLightning','球状闪电',1,7,{'damage':3},channel='lightning')
    attack('Barrage','弹幕齐射',1,5,{'damage':2},barrage=True)
    attack('BeamCell','光束射线',0,3,{'damage':1,'vulnerable':1},vulnerable=1)
    attack('Claw','爪击',0,3,{'damage':1,'claw':1},claw=2)
    attack('ColdSnap','寒流',1,6,{'damage':3},channel='frost')
    attack('CompileDriver','编译冲击',1,7,{'damage':3},compileDriver=True)
    attack('FlakCannon','散射炮',2,8,{'damage':3},'rare',target='random',flakCannon=True)
    attack('FocusedStrike','集中打击',1,9,{'damage':2,'temporaryFocus':1},strike=True,temporaryFocus=1)
    attack('Ftl','超越光速',0,5,{'damage':1,'ftl':1},'uncommon',ftl=3)
    attack('GoForTheEyes','眼部攻击',0,3,{'damage':1,'attackIntentWeak':1},attackIntentWeak=1)
    attack('GunkUp','污秽攻击',1,4,{'damage':1},hits=3,generatedStatus='Slimed')
    attack('HelixDrill','螺旋钻击',0,3,{'damage':2},'rare',helixDrill=True)
    attack('Hyperbeam','超能光束',2,24,{'damage':6},'rare',target='all',temporaryFocus=-3)
    attack('IceLance','冰之长枪',3,19,{'damage':5},'rare',channel='frost',channelCount=3)
    attack('MeteorStrike','陨石打击',5,24,{'damage':6},'rare',strike=True,channel='plasma',channelCount=3)
    attack('MomentumStrike','趁势打击',1,11,{'damage':4},strike=True,zeroAfterPlay=True)
    attack('Null','空值',2,10,{'damage':3,'weak':1},'uncommon',weak=1,channel='dark')
    attack('Refract','折射',3,10,{'damage':3},'uncommon',hits=2,channel='glass',channelCount=2)
    attack('RocketPunch','火箭飞拳',2,13,{'damage':1,'draw':1},'uncommon',draw=1,rocketPunch=True)
    attack('Scrape','刮削',1,7,{'damage':3,'scrape':1},'uncommon',scrape=4)
    attack('Shatter','打碎',1,7,{'damage':4},'rare',target='all',exhaust=True,shatter=True)
    attack('Sunder','分离',3,26,{'damage':8},'uncommon',killEnergy=3)
    attack('SweepingBeam','扫荡射线',1,6,{'damage':3},target='all',draw=1)
    attack('Synthesis','人工合成',2,14,{'damage':6},'uncommon',freePower=1)
    attack('TeslaCoil','特斯拉线圈',0,3,{'damage':1,'teslaCoil':1},'uncommon',teslaCoil=1)
    attack('Uproar','骚动',2,6,{'damage':2},hits=2,uproar=True)


def describe(values, *, upgraded=False):
    labels={'adaptiveStrike':'向弃牌堆加入本牌复制，复制本场费用为 0','allForOne':'取回弃牌堆费用为 0 的非 X 攻击、技能和能力',
            'barrage':'每个充能球攻击一次','compileDriver':'每种充能球抽一张牌','flakCannon':'消耗所有未被消耗的状态牌，每张随机攻击一次',
            'helixDrill':'攻击次数等于本回合已花费的能量','zeroAfterPlay':'打出后本场费用为 0',
            'rocketPunch':'自己每生成一张状态牌，本牌下次打出前费用降低 1','shatter':'依次激发每个充能球两次并移除',
            'uproar':'自动打出抽牌堆随机攻击牌'}
    labels.update(doubleEnergy='支付费用后，将剩余能量翻倍',chill='每个存活敌人生成一个冰霜球',rainbow='依次生成闪电、冰霜、黑暗球',
                  tempest='生成 '+('X+1' if upgraded else 'X')+' 个闪电球',compact='手牌状态牌变成燃料'+('+' if upgraded else ''),
                  multiCast='最前方充能球激发 '+('X+1' if upgraded else 'X')+' 次，最后一次移除',voltaic='按本场此前生成的闪电球数量，再生成等量闪电球',
                  whiteNoise='生成自己职业的随机能力牌，本回合免费')
    result=[label for key,label in labels.items() if values.get(key)]
    for key,label in {'claw':'本场所有已有爪击增加伤害','temporaryFocus':'本回合集中变化','ftl':'仅在本回合此前结算牌数小于此值时抽一张',
                      'attackIntentWeak':'目标意图为攻击时施加虚弱','scrape':'抽牌并主动弃掉其中非零费或 X 费牌，张数',
                      'killEnergy':'击杀时获得能量','freePower':'后续能力费用为 0 的次数','teslaCoil':'对目标触发每个闪电球被动的次数',
                      'focus':'集中','addOrbSlots':'增加充能球栏位','removeOrbSlots':'移除末尾充能球栏位且不激发','randomOrbs':'随机生成充能球',
                      'coolant':'回合开始每种充能球获得直接格挡','drawAfterChannel':'生成充能球后抽牌','darknessTriggers':'生成后触发所有黑暗球被动次数',
                      'allEnergy':'每位队员获得能量','biasedCognition':'以后每回合失去集中','buffer':'抵消失去生命的次数',
                      'consumingShadow':'回合结束激发并移除末尾充能球数','creativeAi':'每回合抽牌前生成自己职业的随机能力数',
                      'echoForm':'每回合前几个出牌序列额外打出一次','feral':'每回合前几张零能量值攻击返回手牌',
                      'geneticGrowth':'本牌本局永久增加格挡','hailstorm':'回合结束拥有冰霜球时对全体直接伤害',
                      'hibernate':'生成冰霜球，并使冰霜球本轮向队友提供格挡','imitationLearning':'自动复制所选队友后续能力的次数',
                      'iteration':'每回合首次抽到状态牌时额外抽牌','lightningRod':'每次能量重置生成一个闪电球的剩余回合',
                      'loop':'回合抽牌后触发最前方球被动的次数','machineLearning':'每回合额外正常抽牌','moddedDraw':'增加球栏后抽牌，本场费用再加 1',
                      'oneForAll':'全队非能量 X 且实际免费攻击额外伤害','evokeFirst':'最前方球激发次数，最后移除','reboot':'将手牌、弃牌堆与抽牌堆合并洗牌后抽牌',
                      'scavenge':'选一张手牌消耗，然后下回合获得能量','signalBoost':'后续能力额外打出一次的次数','smokestack':'每生成一张状态牌对全体直接伤害',
                      'spinner':'每次能量重置生成玻璃球','storm':'以后每次能力结算生成闪电球','subroutine':'以后每次能力结算获得能量',
                      'synchronize':'本回合每种充能球获得集中','thunder':'闪电激发后对同一存活目标追加直接伤害','trashToTreasure':'每生成一张状态牌随机生成充能球'}.items():
        if values.get(key):result.append(f'{label} {values[key]}')
    if values.get('channel'):result.append(f"生成充能球 {dict(lightning='闪电',frost='冰霜',dark='黑暗',plasma='等离子',glass='玻璃')[values['channel']]} ×{values.get('channelCount',1)}")
    if values.get('allyChannel'):result.append('向所选队友生成等离子球')
    if values.get('spinnerChannel'):result.append('立刻生成一个玻璃球')
    if values.get('generatedStatus'):result.append(f"向弃牌堆生成 {values.get('statusCount',1)} 张 "+{'Slimed':'黏液','Dazed':'晕眩','Burn':'灼伤','Void':'虚空','Wound':'伤口'}.get(values['generatedStatus'],values['generatedStatus']))
    return result
