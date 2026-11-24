"""Named encounter formations and source-specific move transitions.

Coverage is explicit. Unknown encounter identities are errors, never replaced
by one of the implemented fights.
"""
from ..content.ascension import monster_hp, monster_value
from decimal import Decimal

MONSTERS={
    'Architect':('建筑师',9999,9999,[{'hidden':True}]),
    'FakeMerchantMonster':('商人？？？',165,165,[{'damage':13},{'damage':2,'hits':8},{'damage':9,'debuffs':{'frail':1}},{'strength':2}]),
    'BattleFriendV1':('战斗好伙伴V1.0',75,75,[{}]),
    'BattleFriendV2':('战斗好伙伴V2.0',150,150,[{}]),
    'BattleFriendV3':('战斗好伙伴V3.0',300,300,[{}]),
    'ThievingHopper':('偷窃草蜢',79,79,[{'damage':17,'stealCard':True},{'flutter':5},{'damage':21},{'damage':14},{'escapeEnemy':True}]),
    'TheLost':('失落之物',93,93,[{'debuffs':{'strength':-2},'strength':2},{'damage':4,'hits':2}]),
    'TheForgotten':('遗忘之物',106,106,[{'debuffs':{'dexterity':-2},'moveBlock':8,'dexterity':2},{'damage':13}]),
    'AxeRubyRaider':('劫掠者斧手',20,22,[{'damage':5,'moveBlock':5},{'damage':5,'moveBlock':5},{'damage':12}]),
    'AssassinRubyRaider':('劫掠者刺客',18,23,[{'damage':10}]),
    'BruteRubyRaider':('劫掠者暴徒',30,33,[{'damage':7},{'strength':3}]),
    'CrossbowRubyRaider':('劫掠者弩手',18,21,[{'moveBlock':3},{'damage':14}]),
    'TrackerRubyRaider':('劫掠者追踪手',21,25,[{'debuffs':{'frail':2}},{'damage':1,'hits':8}]),
    'HauntedShip':('幽灵船',63,63,[{'debuffs':{'weak':3},'status':'Dazed','count':5},{'damage':13},{'damage':4,'hits':3}]),
    'LouseProgenitor':('虱虫之祖',134,136,[{'damage':9,'debuffs':{'frail':2}},{'moveBlock':14,'strength':5},{'damage':14}]),
    'Ovicopter':('直飞产卵虫',124,130,[{'layEggs':3},{'damage':16},{'damage':7,'debuffs':{'vulnerable':2}},{'strength':3}]),
    'ToughEgg':('结实的卵',14,18,[{'hatchEgg':True},{'damage':4}]),
    'Fabricator':('组装师',150,150,[{'fabricate':2},{'damage':18,'fabricate':1},{'damage':11}]),
    'Zapbot':('电击机器人',18,23,[{'damage':14}]),
    'Stabbot':('戳刺机器人',18,23,[{'damage':11,'debuffs':{'frail':1}}]),
    'Guardbot':('守护机器人',16,20,[{'guardFabricator':15}]),
    'Noisebot':('噪音机器人',18,23,[{'status':'Dazed','count':1,
                                   'statusExtra':[{'status':'Dazed','count':1,'pile':'draw','randomPosition':True}]}]),
    'Myte':('异螨',61,67,[{'status':'Toxic','count':2,'statusPile':'hand'},{'damage':13},{'damage':4,'strength':2}]),
    'OwlMagistrate':('猫头鹰法官',231,231,[{'damage':16},{'damage':4,'hits':6},{'soar':True},{'damage':33,'debuffs':{'vulnerable':4},'land':True}]),
    'GremlinMerc':('地精佣兵',47,49,[{'damage':7,'hits':2,'stealGold':20},{'damage':6,'hits':2,'stealGold':20,'debuffs':{'weak':2}},{'damage':8,'stealGold':20,'strength':2}]),
    'SneakyGremlin':('卑鄙地精',10,14,[{'wakeGremlin':True},{'damage':9}]),
    'FatGremlin':('胖地精',13,17,[{'wakeGremlin':True},{'escapeEnemy':True}]),
    'TwoTailedRat':('双尾鼠',17,21,[{'damage':8},{'damage':6},{'debuffs':{'frail':1}},{'ratBackup':True}]),
    'LivingFog':('活雾',80,80,[{'damage':8,'debuffs':{'smoggy':1}},{'damage':5,'bloat':True},{'damage':8}]),
    'GasBomb':('气态炸弹',7,7,[{'damage':8,'deathBlow':True,'selfKill':True}]),
    'Fogmog':('雾菇',74,74,[{'summonEnemy':'EyeWithTeeth'},{'damage':8,'strength':1},{'damage':8,'strength':1},{'damage':14}]),
    'EyeWithTeeth':('利齿之眼',6,6,[{'status':'Dazed','count':3},{'reviveIllusion':True}]),
    'TheObscura':('胧光怪',123,123,[{'summonEnemy':'Parafright'},{'damage':10},{'teamStrength':3},{'damage':6,'block':6}]),
    'Parafright':('寄生惧魔',21,21,[{'damage':16},{'reviveIllusion':True}]),
    'SlitheringStrangler':('蛇行扼杀者',53,55,[{'debuffs':{'constrict':3}},{'damage':7,'block':5},{'damage':12}]),
    'SlumberingBeetle':('熟睡甲虫',86,86,[{'sleep':True},{'damage':16,'strength':2},{'stunned':True}]),
    'LivingShield':('活体盾',55,55,[{'damage':6},{'damage':16,'strength':3}]),
    'TurretOperator':('高塔炮手',41,41,[{'damage':3,'hits':5},{'damage':3,'hits':5},{'strength':1}]),
    'Seapunk':('海洋混混',44,46,[{'damage':11},{'damage':2,'hits':4},{'block':7,'strength':1}]),
    'CalcifiedCultist':('钙化邪教徒',38,41,[{'ritual':2},{'damage':9}]),
    'SewerClam':('下水道蚌',56,56,[{'damage':10},{'strength':4}]),
    'SlimedBerserker':('史莱姆狂战士',261,261,[{'status':'Slimed','count':10},{'damage':4,'hits':4},{'debuffs':{'weak':3},'strength':3},{'damage':30}]),
    'GlobeHead':('电球头',148,148,[{'damage':13,'debuffs':{'frail':2}},{'damage':6,'hits':3},{'damage':16,'strength':2}]),
    'FrogKnight':('青蛙骑士',191,191,[{'damage':13,'debuffs':{'frail':2}},{'damage':21},{'strength':5},{'damage':35}]),
    'HunterKiller':('猎人杀手',121,121,[{'debuffs':{'tender':1}},{'damage':17},{'damage':7,'hits':3}]),
    'Chomper':('啃咬机',60,64,[{'damage':8,'hits':2},{'status':'Dazed','count':3}]),
    'DevotedSculptor':('虔诚雕刻师',162,162,[{'ritual':9},{'damage':12}]),
    'BowlbugRock':('盛碗虫（石）',45,48,[{'damage':15},{'stunned':True}]),
    'BowlbugEgg':('盛碗虫（卵）',21,22,[{'damage':7,'block':7}]),
    'BowlbugNectar':('盛碗虫（蜜）',35,38,[{'damage':3},{'strength':15},{'damage':3}]),
    'BowlbugSilk':('盛碗虫（丝）',40,43,[{'damage':4,'hits':2},{'debuffs':{'weak':1}}]),
    'PhantasmalGardener':('花园幽灵鳗',26,31,[{'damage':5},{'damage':7},{'damage':1,'hits':3},{'strength':2}]),
    **{key:('残杀千足虫',40,46,[{'damage':5,'hits':2},{'damage':6,'strength':2},{'damage':8,'debuffs':{'weak':1}},{'stunned':True},{'reattach':True}]) for key in ('DecimillipedeSegmentFront','DecimillipedeSegmentMiddle','DecimillipedeSegmentBack')},
    'InfestedPrism':('感染棱柱',161,161,[{'damage':15},{'damage':11,'block':11},{'damage':5,'hits':3},{'damage':8,'block':20,'vitalSpark':2}]),
    'SkulkingColony':('鬼祟珊瑚群',75,75,[{'damage':14},{'damage':14},{'damage':9,'strength':2},{'damage':7,'hits':2}]),
    'TerrorEel':('骇鳗',140,140,[{'damage':16},{'damage':3,'hits':3,'vigor':6},{'stunned':True},{'debuffs':{'vulnerable':99}}]),
    'Entomancer':('蜂群术士',145,145,[{'damage':3,'hits':7},{'damage':18},{'hiveSpit':True}]),
    'SoulNexus':('灵魂枢纽',234,234,[{'damage':29},{'damage':6,'hits':4},{'damage':18,'debuffs':{'vulnerable':2,'weak':2}}]),
    'MechaKnight':('机甲骑士',300,300,[{'damage':25},{'damage':8,'status':'Burn','count':4,'statusPile':'hand'},{'block':15,'strength':5},{'damage':35}]),
    'Crusher':('碾碎爪',209,209,[{'damage':12},{'damage':4},{'damage':6,'hits':2,'debuffs':{'weak':2,'frail':2}},{'strength':2},{'damage':12,'block':18}]),
    'Rocket':('火箭',199,199,[{'damage':3},{'damage':18},{'strength':2},{'damage':31},{'sleep':True}]),
    'KinFollower':('同族信徒',58,59,[{'damage':5},{'damage':2,'hits':2},{'strength':2}]),
    'KinPriest':('同族神官',190,190,[{'damage':8,'debuffs':{'frail':1}},{'damage':8,'debuffs':{'weak':1}},{'damage':3,'hits':3},{'strength':2}]),
    'TheInsatiable':('无厌沙虫',321,321,[{'liquify':True},{'damage':8,'hits':2},{'damage':28},{'strength':2},{'damage':8,'hits':2}]),
    'Queen':('女王',400,400,[{'debuffs':{'chainsOfBinding':3}},{'debuffs':{'frail':99,'weak':99,'vulnerable':99}},{'block':20,'allyStrength':1},{'damage':3,'hits':5},{'damage':15},{'strength':2}]),
    'TorchHeadAmalgam':('火炬头聚合体',199,199,[{'damage':26},{'damage':18},{'damage':8,'hits':3},{'damage':14},{'damage':14}]),
    'TestSubject':('实验体 #C{Count}',100,100,[{'damage':20},{'damage':14,'debuffs':{'vulnerable':1}},{'damage':10,'hits':3},{'damage':10,'hits':3},{'damage':45},{'status':'Burn','count':3,'strength':2},{'revive':True}]),
    'WaterfallGiant':('瀑布巨兽',240,240,[{'steam':15},{'damage':15,'debuffs':{'weak':1}},{'damage':10},{'healPerPlayer':10},{'damage':20},{'damage':13},{'stunned':True},{'damage':0,'deathBlow':True}]),
    'Aeonglass':('永世沙漏',512,512,[{'damage':22,'block':33},{'damage':11,'hits':2},{'intensify':True}]),
    'SoulFysh':('灵魂异鱼',211,211,[{'beckon':True},{'damage':16},{'damage':7,'status':'Beckon','count':1},{'intangible':2},{'damage':13,'debuffs':{'vulnerable':3}}]),
    'LagavulinMatriarch':('乐加维林族母',222,222,[{'sleeping':True},{'damage':19},{'damage':9,'hits':2},{'damage':12,'block':12},{'debuffs':{'strength':-2,'dexterity':-2},'strength':2},{'stunned':True}]),
    'CeremonialBeast':('仪式兽',252,252,[{'plow':150},{'damage':18,'strength':2},{'stunned':True},{'debuffs':{'ringing':1}},{'damage':15},{'damage':17,'strength':3}]),
    'FossilStalker':('化石追踪者',51,53,[{'damage':9,'debuffs':{'frail':1}},{'damage':12},{'damage':3,'hits':2}]),
    'SpinyToad':('棘刺蟾蜍',116,119,[{'thornsAfter':5},{'damage':23,'thornsAfter':-5},{'damage':17}]),
    'Tunneler':('地道虫',87,87,[{'damage':13},{'block':32,'burrowed':1},{'damage':23},{'stunned':True}]),
    'Exoskeleton':('外骨骼虫',24,28,[{'damage':1,'hits':3},{'damage':8},{'strength':2}]),
    'Toadpole':('蟾蜍蝌蚪',21,25,[{'damage':3,'hits':3,'thornsBefore':-2},{'damage':7},{'thornsAfter':2}]),
    'SludgeSpinner':('淤泥旋螺',37,39,[{'damage':8,'debuffs':{'weak':1}},{'damage':11},{'damage':6,'strength':3}]),
    'Axebot':('巨斧机器人',70,78,[{'block':10},{'damage':10,'hits':2},{'damage':14,'debuffs':{'weak':2,'frail':2}}]),
    'PhrogParasite':('异蛙寄生虫',61,64,[{'status':'Infection','count':3},{'damage':4,'hits':4}]),
    'Wriggler':('扭动虫',17,21,[{'damage':6},{'status':'Infection','count':1,'strength':2}]),
    'FlailKnight':('连枷骑士',101,101,[{'strength':3},{'damage':9,'hits':2},{'damage':15}]),
    'SpectralKnight':('幽灵骑士',93,93,[{'debuffs':{'hex':2}},{'damage':15},{'damage':3,'hits':3}]),
    'MagiKnight':('魔法骑士',82,82,[{'damage':6,'block':5},{'debuffs':{'dampen':1}},{'damage':10},{'block':5},{'damage':35}]),
    'VineShambler':('藤蔓蹒跚者',61,61,[{'damage':8,'debuffs':{'tangled':1}},{'damage':6,'hits':2},{'damage':16}]),
    'MysteriousKnight':('神秘骑士',101,101,[{'strength':3},{'damage':9,'hits':2},{'damage':15}]),
    'Mawler':('蛮兽',72,72,[{'damage':14},{'debuffs':{'vulnerable':3}},{'damage':4,'hits':2}]),
    'SnappingJaxfruit':('闪光贾克斯果',31,33,[{'damage':3,'strength':2}]),
    'CorpseSlug':('噬尸蛞蝓',25,27,[{'damage':3,'hits':2},{'damage':8},{'debuffs':{'frail':2}}]),
    'CalcifiedCultist':('钙化邪教徒',38,41,[{'ritual':2},{'damage':9}]),
    'DampCultist':('潮湿邪教徒',51,53,[{'ritual':5},{'damage':1}]),
    'LeafSlimeM':('树叶史莱姆（中）',32,35,[{'damage':8},{'status':'Slimed','count':2}]),
    'TwigSlimeM':('树枝史莱姆（中）',26,28,[{'damage':11},{'status':'Slimed','count':1}]),
    'ShrinkerBeetle':('缩小甲虫',38,40,[{'debuffs':{'shrink':-1}},{'damage':7},{'damage':13}]),
    'CubexConstruct':('方柱构装体',65,65,[{'strength':2},{'damage':7,'strength':2},{'damage':7,'strength':2},{'damage':5,'hits':2}]),
    'Flyconid':('飞蝇菌子',47,49,[{'debuffs':{'vulnerable':2}},{'damage':8,'debuffs':{'frail':2}},{'damage':11}]),
    'PunchConstruct':('拳击构装体',55,55,[{'block':10},{'damage':5,'hits':2,'debuffs':{'frail':1}},{'damage':14}]),
    'ScrollOfBiting':('咬人卷轴',30,37,[{'damage':14},{'damage':5,'hits':2},{'strength':2}]),
}
FIXED={
    'TheArchitectEventEncounter':['Architect'],
    'ThievingHopperWeak':['ThievingHopper'],
    'TheLostAndForgottenNormal':['TheLost','TheForgotten'],
    'HauntedShipNormal':['HauntedShip'],
    'LouseProgenitorNormal':['LouseProgenitor'],
    'OvicopterNormal':['Ovicopter'],
    'FabricatorNormal':['Fabricator'],
    'MytesNormal':['Myte','Myte'],
    'OwlMagistrateNormal':['OwlMagistrate'],
    'GremlinMercNormal':['GremlinMerc'],
    'TwoTailedRatsNormal':['TwoTailedRat']*3,
    'LivingFogNormal':['LivingFog'],
    'FogmogNormal':['Fogmog'],
    'TheObscuraNormal':['TheObscura'],
    'SlumberingBeetleNormal':['BowlbugRock','BowlbugSilk','SlumberingBeetle'],
    'TurretOperatorWeak':['LivingShield','TurretOperator'],
    'SeapunkWeak':['Seapunk'],
    'SeapunkNormal':['CalcifiedCultist','Seapunk'],
    'SewerClamNormal':['SewerClam'],
    'SlimedBerserkerNormal':['SlimedBerserker'],
    'GlobeHeadNormal':['GlobeHead'],
    'FrogKnightNormal':['FrogKnight'],
    'HunterKillerNormal':['HunterKiller'],
    'ChompersNormal':['Chomper','Chomper'],
    'DevotedSculptorWeak':['DevotedSculptor'],
    'PhantasmalGardenersElite':['PhantasmalGardener']*4,
    'DecimillipedeElite':['DecimillipedeSegmentFront','DecimillipedeSegmentMiddle','DecimillipedeSegmentBack'],
    'InfestedPrismsElite':['InfestedPrism'],
    'SkulkingColonyElite':['SkulkingColony'],
    'TerrorEelElite':['TerrorEel'],
    'EntomancerElite':['Entomancer'],
    'SoulNexusElite':['SoulNexus'],
    'MechaKnightElite':['MechaKnight'],
    'ByrdonisElite':['Byrdonis'],
    'KaiserCrabBoss':['Crusher','Rocket'],
    'TheKinBoss':['KinFollower','KinFollower','KinPriest'],
    'TheInsatiableBoss':['TheInsatiable'],
    'QueenBoss':['TorchHeadAmalgam','Queen'],
    'TestSubjectBoss':['TestSubject'],
    'WaterfallGiantBoss':['WaterfallGiant'],
    'AeonglassBoss':['Aeonglass'],
    'SoulFyshBoss':['SoulFysh'],
    'LagavulinMatriarchBoss':['LagavulinMatriarch'],
    'CeremonialBeastBoss':['CeremonialBeast'],
    'VantomBoss':['Vantom'],
    'FossilStalkerNormal':['FossilStalker'],
    'SpinyToadNormal':['SpinyToad'],
    'TunnelerWeak':['Tunneler'],
    'PunchOffEventEncounter':['PunchConstruct']*2,
    'BattlewornDummyEventV1Encounter':['BattleFriendV1'],
    'BattlewornDummyEventV2Encounter':['BattleFriendV2'],
    'BattlewornDummyEventV3Encounter':['BattleFriendV3'],
    'FakeMerchantEventEncounter':['FakeMerchantMonster'],
    'ExoskeletonsWeak':['Exoskeleton']*3,'ExoskeletonsNormal':['Exoskeleton']*4,
    'ToadpolesWeak':['Toadpole']*2,'SludgeSpinnerWeak':['SludgeSpinner'],
    'AxebotsNormal':['Axebot'],
    'PhrogParasiteElite':['PhrogParasite'],
    'DenseVegetationEventEncounter':['Wriggler']*4,
    'KnightsElite':['FlailKnight','SpectralKnight','MagiKnight'],
    'VineShamblerNormal':['VineShambler'],
    'MysteriousKnightEventEncounter':['MysteriousKnight'],
    'MawlerNormal':['Mawler'],'SnappingJaxfruitNormal':['SnappingJaxfruit','Flyconid'],
    'CorpseSlugsWeak':['CorpseSlug']*2,'CorpseSlugsNormal':['CorpseSlug']*3,
    'CultistsNormal':['CalcifiedCultist','DampCultist'],
    'FuzzyWurmCrawlerWeak':['FuzzyWurmCrawler'], 'NibbitsWeak':['Nibbit'],
    'NibbitsNormal':['Nibbit','Nibbit'], 'InkletsNormal':['Inklet']*3,
    'BygoneEffigyElite':['BygoneEffigy'], 'KnowledgeDemonBoss':['KnowledgeDemon'],
    'ShrinkerBeetleWeak':['ShrinkerBeetle'], 'CubexConstructNormal':['CubexConstruct'],
    'OvergrowthCrawlers':['ShrinkerBeetle','FuzzyWurmCrawler'],
    'PunchConstructNormal':['PunchConstruct'],
    'ConstructMenagerieNormal':['PunchConstruct','CubexConstruct','CubexConstruct'],
    'ScrollsOfBitingWeak':['ScrollOfBiting']*3,
    'ScrollsOfBitingNormal':['ScrollOfBiting']*4,
}
KINDS={key:'elite' if key.endswith('Elite') else 'boss' if key.endswith('Boss') else 'battle'
       for key in [*FIXED,'SlimesWeak','SlimesNormal','FlyconidNormal','BowlbugsWeak','BowlbugsNormal','SlitheringStranglerNormal','RubyRaidersNormal']}


def scaling(state):
    index=state.get('actIndex',0)
    e.require(index in (0,1,2),'无效的幕索引。')
    return Decimal('1.1') if index==0 else Decimal('1.3') if index==2 and state['encounterKind']=='boss' else Decimal('1.2')


def hp(state,base):
    count=len(state['players'])
    return base if count==1 else int(Decimal(base)*count*scaling(state))


def initial_hp(state,low,high):
    # The reference compares against earlier creatures' current max HP, which
    # has already been multiplayer-scaled, before scaling this creature.
    occupied={enemy['maxHp'] for enemy in state['enemies']}
    eligible=[amount for amount in range(low,high+1) if amount not in occupied]
    base=e.niche_choose(state,eligible or list(range(low,high+1)))
    return hp(state,base)


def block(state,base):
    count=len(state['players'])
    return int(Decimal(base)*count*(1 if count<=2 else scaling(state)))


def formation(state,key):
    e.require(key in KINDS,'遭遇效果尚未实现：'+str(key))
    if key in FIXED:return list(FIXED[key])
    # The roster is built on the encounter's own stream, seeded with the act's
    # floor as well as the identity, so the same encounter on two floors deals
    # different rosters.
    def pick(items):
        return encounter_rng(state,key,lambda rng:rng.next_item(list(items)))

    def roll(count):
        return encounter_int(state,key,count)

    if key=='RubyRaidersNormal':
        pool=['AxeRubyRaider','AssassinRubyRaider','BruteRubyRaider','CrossbowRubyRaider','TrackerRubyRaider'];selected=[]
        for _ in range(3):
            raider=pick(pool);pool.remove(raider);selected.append(raider)
        return selected
    if key=='SlitheringStranglerNormal':
        branch=roll(3)
        allies=['SnappingJaxfruit'] if branch==0 else [pick(['LeafSlimeM','TwigSlimeM'])] if branch==1 else [pick(['LeafSlimeS','TwigSlimeS']) for _ in range(2)]
        return [*allies,'SlitheringStrangler']
    if key=='BowlbugsWeak':return ['BowlbugRock',pick(['BowlbugEgg','BowlbugNectar'])]
    if key=='BowlbugsNormal':
        workers=['BowlbugEgg','BowlbugSilk','BowlbugNectar'];chosen=[]
        for _ in range(2):
            worker=pick(workers);workers.remove(worker);chosen.append(worker)
        return ['BowlbugRock',*chosen]
    if key=='FlyconidNormal':return [pick(['LeafSlimeM','TwigSlimeM']),'Flyconid']
    small=encounter_rng(state,key,lambda rng:rng.shuffle(['LeafSlimeS','TwigSlimeS']))
    if key=='SlimesWeak':return [small[0],pick(['LeafSlimeM','TwigSlimeM']),small[1]]
    return ['TwigSlimeM','LeafSlimeM',*small]


def initialize(state,enemy):
    key=enemy['key'];enemy['moveHistory']=[]
    if key.startswith('BattleFriendV'):enemy['powers']['battlewornDummyTimeLimit']=3
    if key=='ThievingHopper':enemy['powers']['escapeArtist']=5
    if key=='LouseProgenitor':enemy['powers']['curlUp']=hp(state,monster_value(state,key,'CurlBlock',14))
    if key=='TheLost':enemy['powers']['possessStrength']=1
    if key=='TheForgotten':enemy['powers']['possessSpeed']=1
    if key=='ToughEgg':enemy['powers']['hatch']=2 if state.get('side')=='enemy' else 1
    if key=='Fabricator':enemy['move']=random_branch(state,enemy,[(0,1.0,None),(1,1.0,None)]) if sum(m['hp']>0 for m in state['enemies'])<4 else 2
    if key=='Zapbot':enemy['powers']['highVoltage']=2
    if key=='Myte':enemy['move']=2 if any(m is not enemy and m['key']==key for m in state['enemies']) else 0
    if key=='GremlinMerc':enemy['powers'].update(surprise=1,thievery=20);enemy['stolenGold']={}
    if key=='TwoTailedRat':
        siblings=[m for m in state['enemies'] if m is not enemy and m['key']==key]
        enemy.update(ratWait=2,ratCalls=0,ratMoves=[])
        if state.get('turn',0)==0:
            if not siblings:state['ratStarter']=encounter_int(state,state.get('encounter') or 'TwoTailedRatsNormal',3)
            enemy['move']=(state['ratStarter']+len(siblings))%3
        else:enemy['move']=random_branch(state,enemy,[(0,1.0,(('repeat',1),)),(1,1.0,(('repeat',1),)),(2,1.0,(('cooldown',3),))])
    if key=='GasBomb':enemy['powers']['minion']=1
    if key in ('EyeWithTeeth','Parafright'):enemy['powers'].update(illusion=1,minion=1)
    if key=='SlumberingBeetle':
        enemy['powers'].update(slumber=3,plating=monster_value(state,key,'PlatingAmount',15)*(2*len(state['players'])-1))
    if key=='LivingShield':enemy['powers']['rampart']=hp(state,25)
    if key=='GlobeHead':enemy['powers']['galvanic']=monster_value(state,key,'GalvanicPowerAmount',6)
    if key=='SewerClam':enemy['powers']['plating']=monster_value(state,key,'PlatingAmount',8)*(2*len(state['players'])-1)
    if key=='FrogKnight':enemy['powers']['plating']=monster_value(state,key,'PlatingAmount',15)*(2*len(state['players'])-1)
    if key=='Chomper':
        enemy['powers']['artifact']=2
        enemy['move']=int(any(m is not enemy and m['key']==key for m in state['enemies']))
    if key=='BowlbugRock':enemy['powers']['imbalanced']=1
    if key=='BowlbugSilk':enemy['move']=1
    if key=='PhantasmalGardener':
        slot=sum(m is not enemy and m['key']==key for m in state['enemies'])
        enemy['move']=[2,0,1,3][slot%4]
        enemy['powers']['skittish']=int(monster_value(state,key,'SkittishAmount',6)*(len(state['players'])+1)/2)
    if key.startswith('DecimillipedeSegment'):
        siblings=[m for m in state['enemies'] if m is not enemy and m['key'].startswith('DecimillipedeSegment')]
        if not siblings:state['segmentStarter']=encounter_int(state,state.get('encounter') or 'DecimillipedeElite',3)
        enemy['move']=(state['segmentStarter']+len(siblings))%3
        health=enemy['maxHp']+(enemy['maxHp']%2)
        while any(m['maxHp']==health for m in state['enemies'] if m is not enemy):
            health+=2
            low,high=monster_hp(state,key,40,46)
            if health>hp(state,high):health=hp(state,low)
        enemy.update(hp=health,maxHp=health);enemy['powers']['reattach']=hp(state,25)
    if key=='Byrdonis':enemy['powers']['territorial']=1
    if key=='MechaKnight':enemy['powers']['artifact']=3
    if key=='Entomancer':enemy['powers']['personalHive']=1
    if key=='TerrorEel':enemy['powers']['shriek']=hp(state,monster_value(state,key,'ShriekAmount',70))
    if key=='SkulkingColony':enemy['powers']['hardenedShell']=hp(state,20)
    if key=='InfestedPrism':enemy['powers']['vitalSpark']=monster_value(state,key,'VitalSparkAmount',2)
    if key in ('Crusher','Rocket'):
        enemy['powers'].update(crabRage=1)
        enemy['powers']['backAttackLeft' if key=='Crusher' else 'backAttackRight']=1
    if key=='KinFollower':
        enemy['powers']['minion']=1
        enemy['move']=0 if any(m is not enemy and m['key']==key for m in state['enemies']) else 2
    if key=='TorchHeadAmalgam':enemy['powers']['minion']=1
    if key=='TestSubject':enemy['powers'].update(adaptable=1,enrage=monster_value(state,key,'EnrageAmount',2))
    if key=='Aeonglass':
        enemy['powers']['artifact']=3;enemy['witheringCounters']={str(p['id']):6 for p in state['players'].values()}
    if key=='LagavulinMatriarch':
        enemy['powers'].update(asleep=3,plating=12*(2*len(state['players'])-1))
    if key=='FossilStalker':enemy['move']=1;enemy['powers']['suck']=3
    if key=='Exoskeleton':
        slot=sum(m['key']==key and m is not enemy for m in state['enemies'])
        enemy['move']=slot if slot<3 else random_branch(state,enemy,[(0,1.0,(('repeat',1),)),(1,1.0,(('repeat',1),))])
        enemy['powers']['hardToKill']=9
    if key=='Toadpole':enemy['move']=1 if any(m['key']==key and m is not enemy for m in state['enemies']) else 2
    if key=='Axebot':enemy['powers']['stock']=2;enemy['move']=2
    if key=='PhrogParasite':enemy['powers']['infested']=4
    if key=='Wriggler':enemy['move']=sum(x['key']==key and x is not enemy for x in state['enemies'])%2
    if key in ('LeafSlimeM','TwigSlimeM','VineShambler'):enemy['move']=1
    elif key=='Flyconid':enemy['move']=random_branch(state,enemy,[(1,1.0,(('cooldown',2),)),(2,1.0,None)])
    elif key=='Mawler':enemy['move']=2
    elif key=='FlailKnight':enemy['move']=2
    elif key=='MysteriousKnight':
        enemy['move']=2;enemy['powers']['strength']=6
        enemy['powers']['plating']=6*(2*len(state['players'])-1)
    if key=='CorpseSlug':
        siblings=[x for x in state['enemies'] if x['key']==key and x is not enemy]
        enemy['move']=(siblings[0]['move']+len(siblings))%3 if siblings else encounter_int(state,str(state.get('encounter')),3)
        enemy['powers']['ravenous']=monster_value(state,key,'RavenousStr',4)
    if key=='CubexConstruct':enemy['powers']['artifact']=1;enemy['block']=block(state,13)
    if key=='PunchConstruct':
        enemy['powers']['artifact']=1
        if state.get('encounter')=='PunchOffEventEncounter':
            enemy['move']=0 if any(m['key']==key and m is not enemy for m in state['enemies']) else 1
            enemy['hp']=max(1,enemy['hp']-encounter_rng(state,'PunchOffEventEncounter',lambda rng:rng.next_int_range(2,10)))
    if key=='ScrollOfBiting':
        siblings=[x for x in state['enemies'] if x['key']==key and x is not enemy]
        enemy['move']=(siblings[0]['move']+len(siblings))%3 if siblings else encounter_int(state,str(state.get('encounter')),3)
        if len(siblings)==3:enemy['move']=2
        enemy['powers']['paperCuts']=2
    if enemy['powers'].get('artifact'):enemy['powers']['artifact']+=len(state['players'])-1
    enemy['moveHistory'].append(enemy['move'])


def spawn(state,key,*,move=0,hp_bonus=0,powers=None,stunned=False):
    name,low,high,_=MONSTERS[key]
    low,high=monster_hp(state,key,low,high)
    health=initial_hp(state,low+hp_bonus,high+hp_bonus)
    serial=max((int(m['id'][1:]) for m in state['enemies'] if m['id'].startswith('e')),default=-1)+1
    monster={'id':f'e{serial}','key':key,'name':name,'hp':health,'maxHp':health,
             'block':0,'powers':powers or {},'move':move,'slowCards':0,'moveHistory':[]}
    if stunned:monster['stunned']=True
    for player in state['players'].values():
        if 'PhilosophersStone' in player['relics']:e.power(monster,'strength',1)
    from ..relics.map import creature_added
    creature_added(state,monster)
    state['enemies'].append(monster);monster=state['enemies'][-1];e.intent(state,monster)
    return monster


def spawn_wrigglers(state):
    for slot in range(4):
        spawn(state,'Wriggler',move=slot%2,stunned=True)
    e.log(state,'寄生蛙体内钻出四只蠕虫。')


def encounter_rng(state,key,draw):
    """``EncounterModel.Rng`` — ``runSeed + TotalFloor + hash(entry)``.

    Its own lane, not one of the fifteen, and seeded with the floor as well as
    the identity: the same encounter on two floors is two different streams.
    """
    return e.derived_rng(state,key,(state.get('floor',0),),draw)


def encounter_int(state,key,count):
    """``NextInt`` on the encounter's own stream."""
    return encounter_rng(state,key,lambda rng:rng.next_int(count))


def monster_ai_choose(state,items):
    """``MonsterAi.NextItem`` — a spawn or target pick on the monster lane."""
    items=list(items)
    return e.run_rng(state,'MonsterAi',lambda rng:rng.next_item(items))


def monster_ai_float(state,total):
    """``Rng.NextFloat(total)`` on the shared ``MonsterAi`` lane.

    Every monster rolls on this one stream, so a turn that draws shifts the
    next monster's move as well.
    """
    from ..rng.mega_random import f32
    span=f32(total)
    return e.run_rng(state,'MonsterAi',lambda rng:rng.next_float(0.0,span))


def _rule_applies(history,move,rule):
    kind=rule[0]
    if kind=='repeat':
        # ``CanRepeatXTimes(n)``: only blocked while the last n are all this.
        limit=rule[1]
        return len(history)>=limit and all(previous==move for previous in history[-limit:])
    if kind=='once':
        # ``UseOnlyOnce``: blocked for the rest of the combat, not just now.
        return move in history
    if kind=='cooldown':
        # Applied after the repeat check and strictly stronger: one appearance
        # inside the window blocks the branch, not n in a row.
        return move in history[-rule[1]:]
    raise ValueError('unknown branch rule: '+str(rule))


def _branch_excluded(history,move,rules):
    """Whether any of a branch's rules zeroes it out for the coming turn.

    A branch can carry more than one: the reference sets a cooldown *and* a
    repeat limit together, and the cooldown is the stricter of the two.
    """
    if not rules:return False
    return any(_rule_applies(history,move,rule) for rule in rules)


def random_branch(state,enemy,branches):
    """``RandomBranchState.GetNextState`` — one weighted roll on ``MonsterAi``.

    ``branches`` is ``(move, weight, rule)`` in the reference's ``AddBranch``
    order. The order is part of the result: the reference subtracts the weights
    cumulatively and takes the first branch the roll has not passed, so equal
    weights are not interchangeable.

    An excluded branch still contributes zero to the total and the roll is taken
    either way; when every branch is excluded the total is zero, ``NextFloat(0)``
    is still one draw, and the first branch is chosen. The reference does not
    fail there and it does not skip the draw — skipping it would shift the
    stream for every later monster.
    """
    from ..rng.mega_random import f32
    history=enemy.setdefault('moveHistory',[])
    weights=[0.0 if _branch_excluded(history,move,rule) else f32(weight)
             for move,weight,rule in branches]
    # ``moveHistory`` is never truncated: ``UseOnlyOnce`` and the longer
    # cooldowns need the whole combat, not the last few turns.
    roll=monster_ai_float(state,f32(sum(weights)))
    for (move,_weight,_rule),effective in zip(branches,weights):
        roll=f32(roll-f32(effective))
        if roll<=0:return move
    return branches[0][0]


def branch(state,enemy,limits):
    """``CanRepeatXTimes`` branches at equal weight, in the given order."""
    return random_branch(state,enemy,[(move,1.0,(('repeat',limit),)) for move,limit in limits])


def cooldown_branch(state,enemy,cooldowns):
    """Branches blocked for the last ``n`` moves, at equal weight."""
    return random_branch(state,enemy,[(move,1.0,(('cooldown',n),)) for move,n in cooldowns])


def advance(state,enemy):
    key=enemy['key'];move=enemy['move']
    if key not in MONSTERS:return False
    if key=='FakeMerchantMonster':
        branches=[(0,1.0,(('repeat',1),)),(1,1.0,(('repeat',1),)),(2,1.0,(('repeat',1),))]
        if move!=2:branches.append((3,1.0,(('cooldown',3),('repeat',1))))
        following=random_branch(state,enemy,branches)
    elif key=='Architect' or key.startswith('BattleFriendV'):following=0
    elif key=='ThievingHopper':following=min(4,move+1)
    elif key in ('TheLost','TheForgotten','BruteRubyRaider','CrossbowRubyRaider'):following=1-move
    elif key=='AxeRubyRaider':following=(move+1)%3
    elif key=='AssassinRubyRaider':following=0
    elif key=='TrackerRubyRaider':following=1
    elif key=='HauntedShip':following=2 if move==1 else 1
    elif key=='LouseProgenitor':following=(move+1)%3
    elif key=='Ovicopter':following=(0 if sum(m['hp']>0 for m in state['enemies'])<=3 else 3) if move==2 else 2 if move==1 else 1
    elif key=='ToughEgg':following=1
    elif key=='Fabricator':following=random_branch(state,enemy,[(0,1.0,None),(1,1.0,None)]) if sum(m['hp']>0 for m in state['enemies'])<4 else 2
    elif key in ('Zapbot','Stabbot','Guardbot','Noisebot'):following=0
    elif key=='OwlMagistrate':following=(move+1)%4
    elif key in ('GremlinMerc','Myte'):following=(move+1)%3
    elif key in ('SneakyGremlin','FatGremlin'):following=1
    elif key=='TwoTailedRat':
        enemy['ratMoves']=(enemy.get('ratMoves',[])+[move])[-3:]
        if move!=3:enemy['ratWait']-=1
        can_summon=(enemy['ratWait']<=0 and enemy['ratCalls']<3
                    and sum(m['hp']>0 for m in state['enemies'])<5
                    and not any(m is not enemy and m['hp']>0 and m['intent'].get('ratBackup') for m in state['enemies']))
        # Not one draw from an eligible list: four weighted branches on one
        # roll, where the summon branch carries most of the weight.
        weight=1.0/12.0 if can_summon else 1.0
        branches=[(0,weight,(('repeat',1),)),(1,weight,(('repeat',1),)),
                  (2,weight,(('cooldown',3),))]
        if can_summon and not enemy.get('ratCalled'):branches.append((3,0.75,(('once',),)))
        following=random_branch(state,enemy,branches)
    elif key in ('EyeWithTeeth','Parafright','GasBomb'):following=0
    elif key=='LivingFog':following=1 if move in (0,2) else 2
    elif key=='Fogmog':following=random_branch(state,enemy,[(2,0.4,(('repeat',1),)),(3,0.6,(('repeat',1),))]) if move==1 else {0:1,2:3,3:1}[move]
    elif key=='TheObscura':following=random_branch(state,enemy,[(1,1.0,(('repeat',1),)),(2,1.0,(('repeat',1),)),(3,1.0,(('repeat',1),))])
    elif key=='SlitheringStrangler':following=random_branch(state,enemy,[(1,1.0,None),(2,1.0,None)]) if move==0 else 0
    elif key in ('GlobeHead','Seapunk','TurretOperator'):following=(move+1)%3
    elif key=='LivingShield':following=0 if move==0 and any(m is not enemy and m['hp']>0 for m in state['enemies']) else 1
    elif key=='SlumberingBeetle':following=0 if move==0 and enemy['powers'].get('slumber') else 1
    elif key=='SewerClam':following=1-move
    elif key=='SlimedBerserker':following=(move+1)%4
    elif key=='FrogKnight':
        if move==3:enemy['beetleCharged']=True
        following=(3 if not enemy.get('beetleCharged') and enemy['hp']<enemy['maxHp']//2 else 0) if move==2 else {0:1,1:2,3:0}[move]
    elif key=='HunterKiller':
        # BITE then PUNCTURE, the latter blocked for two moves after itself.
        following=random_branch(state,enemy,[(1,1.0,(('repeat',1),)),(2,1.0,(('cooldown',2),))])
    elif key in ('Chomper','BowlbugSilk'):following=1-move
    elif key in ('DevotedSculptor','CalcifiedCultist'):following=1
    elif key=='BowlbugEgg':following=0
    elif key=='BowlbugNectar':following=min(2,move+1)
    elif key=='BowlbugRock':following=1 if move==0 and enemy.pop('offBalance',False) else 0
    elif key.startswith('DecimillipedeSegment'):following=random_branch(state,enemy,[(0,1.0,(('repeat',1),)),(1,1.0,(('repeat',1),)),(2,1.0,(('repeat',1),))]) if move==4 else {0:2,1:0,2:1,3:4}[move]
    elif key in ('SkulkingColony','InfestedPrism','PhantasmalGardener'):following=(move+1)%4
    elif key=='TerrorEel':following={0:1,1:0,2:3,3:0}[move]
    elif key=='Entomancer':following=(move+1)%3
    elif key=='SoulNexus':following=random_branch(state,enemy,[(0,1.0,(('repeat',1),)),(1,1.0,(('repeat',1),)),(2,1.0,(('repeat',1),))])
    elif key=='MechaKnight':following=1 if move==3 else move+1
    elif key in ('KinFollower','KinPriest','Crusher','Rocket'):following=(move+1)%len(MONSTERS[key][3])
    elif key=='TheInsatiable':following=1 if move==4 else move+1
    elif key=='Queen':following=1 if move==0 else (3 if enemy.get('amalgamDied') else 2) if move in (1,2) else 3 if move==5 else move+1
    elif key=='TorchHeadAmalgam':following=2 if move==4 else move+1
    elif key=='TestSubject':following=(2 if enemy.get('respawns',0)==1 else 3) if move==6 else {0:1,1:0,2:2,3:4,4:5,5:3}[move]
    elif key=='WaterfallGiant':following=1 if move==5 else min(7,move+1)
    elif key=='Aeonglass':following=(move+1)%3
    elif key=='SoulFysh':following=(move+1)%5
    elif key=='LagavulinMatriarch':following=(0 if enemy['powers'].get('asleep',0)>1 else 1) if move==0 else 1 if move in (4,5) else move+1
    elif key=='CeremonialBeast':following={0:1,1:1,2:3,3:4,4:5,5:3}[move]
    elif key=='FossilStalker':following=random_branch(state,enemy,[(1,1.0,(('cooldown',2),('repeat',2))),(0,1.0,(('cooldown',2),('repeat',2))),(2,1.0,(('cooldown',2),('repeat',2)))])
    elif key=='Tunneler':following={0:1,1:2,2:2,3:0}[move]
    elif key=='Exoskeleton':following=2 if move==1 else branch(state,enemy,[(0,1),(1,1)])
    elif key in ('Toadpole','SpinyToad'):following=(move+1)%3
    elif key=='SludgeSpinner':following=branch(state,enemy,[(0,1),(1,1),(2,1)])
    elif key=='Axebot':following=1 if move==2 else 2
    elif key in ('Wriggler','PhrogParasite'):following=1-move
    elif key=='VineShambler':following={1:0,0:2,2:1}[move]
    elif key in ('MysteriousKnight','FlailKnight'):following=random_branch(state,enemy,[(0,1.0,(('repeat',1),)),(1,1.0,(('cooldown',2),('repeat',2))),(2,1.0,(('cooldown',2),('repeat',2)))])
    elif key=='SpectralKnight':following=1 if move==0 else random_branch(state,enemy,[(1,1.0,(('cooldown',2),('repeat',2))),(2,1.0,(('repeat',1),))])
    elif key=='MagiKnight':following=2 if move==4 else move+1
    elif key=='Mawler':
        following=random_branch(state,enemy,[(0,1.0,(('repeat',1),)),(1,1.0,(('once',),)),(2,1.0,(('repeat',1),))])
    elif key=='Flyconid':following=random_branch(state,enemy,[(0,1.0,(('cooldown',3),)),(1,1.0,(('cooldown',2),)),(2,1.0,(('repeat',1),))])
    elif key=='SnappingJaxfruit':following=0
    elif key=='CorpseSlug':following=(move+1)%3
    elif key in ('CalcifiedCultist','DampCultist'):following=1
    elif key=='LeafSlimeM':following=1-move
    elif key=='TwigSlimeM':following=branch(state,enemy,[(0,2),(1,1)])
    elif key=='ShrinkerBeetle':following=2 if move==1 else 1
    elif key=='CubexConstruct':following=1 if move==3 else move+1
    elif key=='PunchConstruct':following=(move+1)%3
    elif key=='ScrollOfBiting':following=2 if move==0 else 1 if move==2 else branch(state,enemy,[(0,1),(1,2)])
    else:following=random_branch(state,enemy,[(0,1.0,(('cooldown',3),)),(1,1.0,(('cooldown',2),)),(2,1.0,(('cooldown',1),))])
    enemy['move']=following;enemy['moveHistory'].append(following)
    return True


# Define the catalog before importing the engine, which consumes MONSTERS.
from .. import engine as e
