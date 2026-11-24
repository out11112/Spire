"""Regent attacks and forge token needed by cross-character generation."""


def register(card):
    def attack(key,name,cost,damage,upgrade,rarity='common',target='enemy',**values):
        card(key,name,cost,'attack',target,upgrade,rarity=rarity,pool='regent',damage=damage,**values)
    attack('AstralPulse','星界脉冲',0,6,{'damage':2},target='all',hits=2,starCost=3)
    attack('BeatIntoShape','锻打成型',1,5,{'damage':2,'forgePerHit':2},'rare',forgePerHit=5)
    attack('Bombardment','轰击',3,18,{'damage':6},'rare',exhaust=True,bombardment=True)
    attack('CelestialMight','天穹之力',2,6,{'hits':1},hits=3)
    attack('CollisionCourse','碰撞轨迹',0,10,{'damage':4},debris=1)
    attack('Comet','彗星',0,33,{'damage':11},'rare',starCost=5,weak=3,vulnerable=3)
    attack('CrashLanding','迫降',1,21,{'damage':5},'rare',target='all',fillDebris=True)
    attack('CrescentSpear','新月长矛',1,8,{'starCardDamage':1},starCost=1,starCardDamage=2)
    attack('CrushUnder','下砸',1,8,{'damage':1,'temporaryEnemyStrength':1},target='all',temporaryEnemyStrength=1)
    attack('Devastate','葬送',1,35,{'damage':10},'uncommon',starCost=4)
    attack('DyingStar','星灭',1,9,{'damage':2,'temporaryEnemyStrength':2},'rare',target='all',starCost=3,ethereal=True,temporaryEnemyStrength=9)
    attack('GammaBlast','伽马爆破',0,13,{'damage':5},'uncommon',starCost=3,weak=2,vulnerable=2)
    attack('GuidingStar','引导之星',1,12,{'damage':1,'drawNextTurn':1},starCost=1,drawNextTurn=2)
    attack('HeavenlyDrill','天际钻头',0,8,{'damage':2},'rare',xCost=True,doubleXAt=4)
    attack('Hegemony','霸权',2,15,{'damage':3,'energyNextTurn':1},'uncommon',energyNextTurn=2)
    attack('HeirloomHammer','传承之锤',2,20,{'damage':5},'rare',copyColorless=1)
    attack('KinglyKick','王者之踢',4,27,{'damage':8},'uncommon',drawCostReduction=1)
    attack('KinglyPunch','王者之拳',1,8,{'damage':2,'drawDamageGrowth':2},'uncommon',drawDamageGrowth=4)
    attack('KnockoutBlow','决胜一击',3,30,{'damage':8},'uncommon',killStars=5)
    attack('LunarBlast','月面射击',0,4,{'damage':1},'uncommon',lunarBlast=True)
    attack('MakeItSo','如此甚好',0,6,{'damage':3},'rare',returnAfterSkills=3)
    attack('PhotonCut','光子切割',1,10,{'damage':3,'photonCut':1},photonCut=1)
    attack('Radiate','辐射',0,3,{'damage':1},'uncommon',target='all',radiate=True)
    attack('SevenStars','七星',2,7,{'cost':-1},'rare',target='all',starCost=7,hits=7)
    attack('ShiningStrike','明耀打击',1,8,{'damage':3},'uncommon',strike=True,stars=2,returnToTop=True)
    attack('SolarStrike','太阳打击',1,9,{'damage':1,'stars':1},strike=True,stars=1)
    attack('Stardust','星尘',0,5,{'damage':2},'uncommon',target='random',starX=True)
    attack('Supermassive','超质量体',1,5,{'generatedDamage':1},'uncommon',generatedDamage=3)
    attack('WroughtInWar','战火铸就',1,7,{'damage':2,'forge':2},forge=7)
    card('SovereignBlade','君王之剑',2,'attack','enemy',{'cost':-1},rarity='token',pool='token',damage=10,retain=True,sovereignBlade=True)
    def skill(key,name,cost,upgrade=None,rarity='common',target='self',**values):
        card(key,name,cost,'skill',target,upgrade,rarity=rarity,pool='regent',**values)
    def power(key,name,cost,upgrade=None,rarity='uncommon',**values):
        card(key,name,cost,'power','self',upgrade,rarity=rarity,pool='regent',**values)
    skill('Glow','辉光',1,{'stars':1},stars=1,glowDraw=1)
    skill('GatherLight','收集光辉',1,{'block':3},block=8,stars=1)
    skill('ParticleWall','粒子墙',0,{'block':3},'uncommon',block=9,starCost=2,returnToHand=True)
    skill('Bulwark','铸墙',2,{'block':3,'forge':3},'uncommon',block=12,forge=10)
    skill('RefineBlade','淬炼刀刃',1,{'forge':4},forge=8,energyNextTurn=1)
    skill('Glimmer','微光',1,{'photonCut':1},'uncommon',photonCut=3)
    skill('Patter','星星点点',1,{'block':2,'vigor':1},block=8,vigor=2)
    skill('Prophesize','预言',2,{'draw':3},'uncommon',draw=6)
    skill('HiddenCache','隐秘藏品',1,{'starNextTurn':1},stars=1,starNextTurn=3)
    skill('ManifestAuthority','君权自授',1,{'block':1},'uncommon',block=7,manifestAuthority=True)
    power('Parry','招架',1,{'parry':4},parry=10)
    power('HammerTime','锤子时间',2,{'cost':-1},'rare',hammerTime=1,multiplayerOnly=True)
    power('NeutronAegis','中子护盾',1,{'plating':3},'rare',plating=8,starCost=5)
    skill('Alignment','星位序列',0,{'energy':1},'uncommon',energy=2,starCost=2)
    skill('TheSmith','铸剑者',1,{'forge':10},'rare',forge=30,starCost=4)
    card('Conqueror','征服者',1,'skill','enemy',{'forge':2},rarity='uncommon',pool='regent',forge=3,conqueror=1)
    power('Arsenal','武器库',1,{'innate':1},'rare',arsenal=1)
    power('Furnace','熔炉',1,{'furnace':2},furnace=5)
    power('Genesis','创世纪',2,{'genesis':1},'rare',genesis=2)
    power('SwordSage','剑圣',2,{'cost':-1},'rare',swordSage=1)
    power('SeekingEdge','追踪之刃',1,{'forge':4},'rare',forge=7,seekingEdge=True)
    skill('CloakOfStars','群星斗篷',0,{'block':3},block=7,starCost=1)
    card('Constellation','群星荟萃',0,'skill','ally',{'constellationBlock':3},rarity='uncommon',pool='regent',starCost=2,constellationBlock=9,multiplayerOnly=True)
    power('ChildOfTheStars','群星之子',1,{'childOfTheStars':1},childOfTheStars=2)
    power('BlackHole','黑洞',1,{'blackHole':1},blackHole=3)
    power('Orbit','环绕轨道',2,{'cost':-1},orbit=1)
    power('PillarOfCreation','创世之柱',1,{'pillarOfCreation':1},pillarOfCreation=2)
    power('TheSealedThrone','封印王座',1,{'cost':-1},'ancient',starCost=3,theSealedThrone=1)
    skill('Convergence','汇流',1,{'starNextTurn':1},'uncommon',retainHand=1,energyNextTurn=1,starNextTurn=1)
    skill('CosmicIndifference','宇宙冷漠',1,{'block':3},block=6,headbutt=True)
    attack('MeteorShower','流星雨',0,14,{'damage':7},'ancient',target='all',starCost=2,weak=2,vulnerable=2)
    card('Resonance','共鸣',1,'skill','all',{'strength':1},rarity='uncommon',pool='regent',starCost=2,strength=1,resonance=True)
    skill('Monologue','独白',0,{'retain':1},'uncommon',monologue=1)
    power('PaleBlueDot','暗淡蓝点',1,{'paleBlueDot':1},paleBlueDot=1)
    skill('RoyalGamble','胜券在王',0,{'retain':1},'uncommon',starCost=5,stars=9,exhaust=True)
    skill('SpoilsOfBattle','战利品',1,{'forge':3},forge=6,drawAfterForge=2)
    skill('BigBang','大爆炸',0,{'innate':1},'rare',draw=1,bigBang=True,exhaust=True)
    skill('BundleOfJoy','新生之喜',1,{'colorlessGeneration':1},'rare',colorlessGeneration=3,exhaust=True)
    skill('ForegoneConclusion','既定事项',1,{'foregoneConclusion':1},'rare',foregoneConclusion=2)
    card('KnowThyPlace','何人僭越',0,'skill','enemy',{'exhaust':-1},pool='regent',weak=1,vulnerable=1,exhaust=True)
    card('Largesse','慷慨捐助',0,'skill','ally',rarity='uncommon',pool='regent',largesse=True,multiplayerOnly=True)
    skill('Begone','下去！',1,minionTransform='MinionStrike',transformCount=1)
    skill('Charge','冲锋！！',1,rarity='uncommon',minionTransform='MinionDiveBomb',transformCount=2,transformSource='draw')
    skill('Guards','护驾！！！',2,rarity='rare',minionTransform='MinionSacrifice',transformCount=10,transformOptional=True,exhaust=True)
    skill('DecisionsDecisions','抉择，抉择',0,{'draw':2},'rare',starCost=6,draw=3,decisionsDecisions=3,exhaust=True)
    skill('Glitterstream','流光溢彩',2,{'block':2,'delayedBlock':2},block=11,delayedBlock=5)
    skill('IAmInvincible','所向无敌',1,{'block':3},'rare',block=10,invincibleTop=True)
    power('MonarchsGaze','王之凝视',2,{'cost':-1},'rare',monarchsGaze=1)
    skill('Plot','筹划',1,{'plot':1},'uncommon',target='allies',plot=2,multiplayerOnly=True)
    skill('Quasar','类星体',0,rarity='uncommon',starCost=2,quasar=True)
    skill('Reflect','倒映',1,{'block':5},'uncommon',block=15,starCost=3,reflect=1)
    power('Royalties','王国资产',1,{'royalties':10},'rare',royalties=30,noCombatGenerate=True)
    power('SpectrumShift','光谱偏移',2,{'cost':-1},spectrumShift=1)
    skill('SummonForth','征召上前',1,{'forge':3},'uncommon',forge=8,summonForth=True)
    skill('Terraforming','地形改造',1,{'vigor':3},'uncommon',vigor=7)
    card('Tutor','指导',1,'skill','ally',{'cost':-1},rarity='rare',pool='regent',tutor=True,multiplayerOnly=True)
    power('Tyranny','暴政',1,{'innate':1},'rare',tyranny=1)
    power('VoidForm','虚空形态',3,{'ethereal':-1},'rare',voidForm=2,ethereal=True)
    card('MinionStrike','仆从打击',0,'attack','enemy',{'damage':3},rarity='token',pool='token',damage=6,draw=1,exhaust=True,strike=True,minion=True)
    card('MinionSacrifice','仆从捐躯',0,'skill','self',{'block':3},rarity='token',pool='token',block=7,exhaust=True,minion=True)
    card('MinionDiveBomb','仆从俯冲',0,'attack','enemy',{'damage':3},rarity='token',pool='token',damage=13,exhaust=True,minion=True)


def describe(values, *, upgraded=False):
    result=[]
    for key,label in {'starCost':'辉星消耗','stars':'获得辉星','forge':'铸造','forgePerHit':'基础铸造及目标本回合此前每次受到自己攻击的额外铸造',
                      'debris':'向手牌生成碎屑','starCardDamage':'本场每张辉星牌额外伤害','temporaryEnemyStrength':'目标本回合失去力量',
                      'doubleXAt':'X 达到此值时攻击次数翻倍','copyColorless':'选择一张无色手牌复制',
                      'drawCostReduction':'每次被抽到降低本场费用','drawDamageGrowth':'每次被抽到增加本场伤害','killStars':'击杀获得辉星',
                      'returnAfterSkills':'每结算此数量技能将本牌取回手牌','photonCut':'抽牌后将一张手牌放回抽牌堆顶，抽牌数',
                      'generatedDamage':'本场自己每生成一张牌额外伤害','glowDraw':'获得辉星后抽牌，并在下回合额外抽牌',
                      'starNextTurn':'下回合获得辉星','parry':'君王之剑攻击后获得格挡','arsenal':'自己生成战斗牌时获得力量',
                      'furnace':'回合开始铸造','genesis':'每次能量重置后获得辉星','swordSage':'君王之剑额外打出次数',
                      'conqueror':'目标受到君王之剑伤害翻倍，持续敌方回合数','constellationBlock':'队友抽一张牌、获得一能量及格挡',
                      'childOfTheStars':'每花费一颗辉星获得格挡','blackHole':'每次获得辉星或花辉星打牌结算后对所有敌人造成伤害',
                      'orbit':'生效后每花费四能量返还能量','pillarOfCreation':'自己生成战斗牌时获得格挡','theSealedThrone':'每次打牌前获得辉星',
                      'monologue':'本回合此后每次打牌后获得临时力量','paleBlueDot':'本回合结算至少五次牌后，下回合额外抽牌',
                      'drawAfterForge':'铸造后抽牌','colorlessGeneration':'生成不同的随机无色手牌','foregoneConclusion':'下次正常抽牌前从抽牌堆选择加入手牌',
                      'decisionsDecisions':'选一张技能自动打出次数','delayedBlock':'下回合格挡，按打出时修正计算','monarchsGaze':'每次攻击使命中敌人本回合失去力量',
                      'plot':'所有存活玩家（包括自己）下回合额外抽牌','reflect':'反弹攻击中被格挡的伤害，持续回合数','royalties':'胜利后额外金币',
                      'spectrumShift':'每次正常抽牌前生成不同的随机无色手牌','tyranny':'正常抽牌额外张数，之后选择消耗同样数量',
                      'voidForm':'结束回合，此后每回合前几张手动打出的牌不花能量和辉星'}.items():
        if values.get(key):result.append(f'{label} {values[key]}')
    for key,label in {'bombardment':'回合开始时若在消耗堆，自动打出','fillDebris':'用碎屑填满手牌','lunarBlast':'每张本回合已结算技能攻击一次',
                      'radiate':'本回合每获得一颗辉星攻击一次','returnToTop':'结算后放回抽牌堆顶','starX':'消耗全部辉星，按辉星数量攻击',
                      'returnToHand':'结算后回到手牌','manifestAuthority':"生成一张随机"+("已升级的" if upgraded else "")+"无色牌到手牌",
                      'hammerTime':'自己铸造时，存活队友也铸造相同数值，不递归触发','seekingEdge':'君王之剑攻击所有敌人',
                      'resonance':'所有敌人失去 1 力量，可被人工制品抵挡','bigBang':'抽牌后获得 1 辉星、1 能量，再铸造 5',
                      'largesse':"为指定队友生成一张随机"+("已升级的" if upgraded else "")+"无色牌",'invincibleTop':'结束回合时若位于抽牌堆顶则自动打出',
                      'quasar':"从三张随机"+("已升级的" if upgraded else "")+"无色牌中选一张加入手牌，可跳过",
                      'summonForth':'先取回所有君王之剑，再铸造','tutor':'由目标队友从其抽牌堆选择一张加入手牌'}.items():
        if values.get(key):result.append(label)
    if values.get('minionTransform'):
        token={'MinionStrike':'仆从打击','MinionDiveBomb':'仆从俯冲','MinionSacrifice':'仆从捐躯'}[values['minionTransform']]
        result.append(f"从{'抽牌堆' if values.get('transformSource')=='draw' else '手牌'}选择{'任意数量' if values.get('transformOptional') else values['transformCount']}牌变为{token}{'+' if upgraded else ''}")
    return result
