"""Silent cards, including cross-pool generation dependencies."""


def register(card):
    def attack(key,name,cost,damage,upgrade,rarity='common',target='enemy',**values):
        card(key,name,cost,'attack',target,upgrade,rarity=rarity,pool='silent',damage=damage,**values)
    attack('Assassinate','刺杀',0,10,{'damage':3,'vulnerable':1},'rare',vulnerable=1,innate=True,exhaust=True)
    attack('Backstab','背刺',0,11,{'damage':4},'uncommon',innate=True,exhaust=True)
    attack('DaggerSpray','匕首雨',1,4,{'damage':2},target='all',hits=2)
    attack('DaggerThrow','投掷匕首',1,9,{'damage':3},drawDiscard=1)
    attack('Dash','冲刺',2,10,{'damage':3,'block':3},'uncommon',block=10)
    attack('EchoingSlash','回响斩击',1,10,{'damage':3},'uncommon',target='all',echoingSlash=True)
    attack('Finisher','终结技',1,6,{'damage':2},'uncommon',finisher=True)
    attack('Flechettes','飞镖',1,5,{'damage':2},'uncommon',flechettes=True)
    attack('FlickFlack','翻越撑击',1,7,{'damage':2},target='all',sly=True)
    attack('GrandFinale','华丽收场',0,60,{'damage':15},'rare',target='all',emptyDrawOnly=True)
    attack('LeadingStrike','先制打击',1,3,{'damage':3},shivs=2,strike=True)
    attack('MementoMori','铭记死亡',1,9,{'damage':2,'discardDamage':1},'uncommon',discardDamage=4)
    attack('Murder','谋杀',3,1,{'cost':-1},'rare',drawnDamage=1)
    attack('Pinpoint','精密瞄准',3,15,{'damage':4},'uncommon',pinpoint=True)
    attack('PoisonedStab','带毒刺击',1,6,{'damage':2,'poison':1},poison=3)
    attack('Pounce','猛扑',2,14,{'damage':6},'uncommon',freeSkill=1)
    attack('PreciseCut','精确切击',0,13,{'damage':3},'uncommon',handPenalty=2)
    attack('Predator','猎杀者',2,15,{'damage':5},drawNextTurn=2)
    attack('Ricochet','连续反弹',2,3,{'hits':1},target='random',hits=4,sly=True)
    attack('Skewer','串刺',0,8,{'damage':3},'uncommon',xCost=True)
    attack('Slice','切割',0,6,{'damage':3})
    attack('Strangle','紧勒',1,8,{'damage':2,'strangle':1},'uncommon',strangle=2)
    attack('SuckerPunch','突然一拳',1,8,{'damage':2,'weak':1},weak=1)
    card('Shiv','小刀',0,'attack','enemy',{'damage':2},rarity='token',pool='token',damage=4,exhaust=True,shiv=True)
    # Skills/powers reachable when Entropy transforms a Silent attack. These do
    # not enter Ironclad rewards or Splash's attack-only candidate pool.
    def skill(key,name,cost,upgrade=None,rarity='common',target='self',**values):
        card(key,name,cost,'skill',target,upgrade,rarity=rarity,pool='silent',**values)
    skill('Backflip','后空翻',1,{'block':3},block=5,draw=2)
    skill('Deflect','偏折',0,{'block':3},block=4)
    skill('DodgeAndRoll','闪躲翻滚',1,{'block':2},block=4,repeatBlockNextTurn=True)
    card('Footwork','灵动步法',1,'power','self',{'dexterity':1},rarity='uncommon',pool='silent',dexterity=2)
    skill('DeadlyPoison','致命毒药',1,{'poison':2},target='enemy',poison=5)
    skill('LegSweep','扫腿',2,{'block':3,'weak':1},'uncommon','enemy',block=11,weak=2)
    skill('Adrenaline','肾上腺素',0,{'energy':1},'rare',energy=1,draw=2,exhaust=True)
    skill('Acrobatics','杂技',1,{'drawDiscard':1},'uncommon',drawDiscard=3,discardCount=1)
    skill('Prepared','早有准备',0,{'drawDiscard':1},drawDiscard=1)
    skill('EscapePlan','逃脱计划',0,{'escapePlan':2},'uncommon',escapePlan=3)
    skill('Expertise','独门技术',1,{'drawRetain':1},'uncommon',drawRetain=2)
    def ability(key,name,cost,upgrade=None,rarity='uncommon',**values):
        card(key,name,cost,'power','self',upgrade,rarity=rarity,pool='silent',**values)
    ability('Abrasive','磨蚀',3,{'permanentThorns':2},'rare',permanentThorns=4,dexterity=1,sly=True)
    ability('Accelerant','触媒',1,{'accelerant':1},accelerant=1)
    ability('Accuracy','精准',1,{'accuracy':2},accuracy=4)
    ability('Afterimage','余像',1,{'innate':1},'rare',afterimage=1)
    skill('Anticipate','预判',0,{'temporaryDexterity':2},temporaryDexterity=2)
    skill('BladeDance','刀刃之舞',1,{'shivs':1},shivs=3,exhaust=True)
    skill('BladeOfInk','墨之刃',1,{'inkyShivs':1},'rare',inkyShivs=2)
    skill('BladeSymphony','刀刃交响曲',2,{'cost':-1},'uncommon',target='allies',allShivs=2,multiplayerOnly=True)
    skill('Blur','残影',1,{'block':3},'uncommon',block=5,blur=1)
    skill('BouncingFlask','弹跳药瓶',2,{'poisonBounces':1},'uncommon',target='random',poisonBounces=3,bouncePoison=3)
    skill('BubbleBubble','咕嘟冒泡',1,{'poisonIfPoisoned':3},'uncommon','enemy',poisonIfPoisoned=9)
    skill('BulletTime','子弹时间',3,{'cost':-1},'rare',bulletTime=True)
    skill('Burst','爆发',1,{'burst':1},'rare',burst=1)
    skill('CalculatedGamble','计算下注',0,{'retain':1},'uncommon',calculatedGamble=True,exhaust=True)
    skill('CloakAndDagger','斗篷与匕首',1,{'shivs':1},block=6,shivs=1)
    skill('Reflex','本能反应',3,{'draw':1},'uncommon',draw=2,sly=True)
    skill('Tactician','战术大师',3,{'energy':1},'uncommon',energy=1,sly=True)
    skill('HiddenDaggers','隐秘匕首',0,rarity='uncommon',hiddenDaggers=2)
    skill('StormOfSteel','钢铁风暴',1,rarity='rare',stormOfSteel=True)
    ability('InfiniteBlades','无尽刀刃',1,{'innate':1},infiniteBlades=1)
    ability('NoxiousFumes','毒雾',1,{'noxiousFumes':1},noxiousFumes=2)
    ability('Envenom','涂毒',2,{'envenom':1},'rare',envenom=1)
    skill('Concoct','调制',0,{'concoct':1},'uncommon','ally',concoct=3,multiplayerOnly=True)
    skill('CorrosiveWave','腐蚀波',1,{'corrosiveWave':1},'rare',corrosiveWave=2)
    skill('Expose','暴露',0,{'expose':1},'uncommon','enemy',expose=2,exhaust=True)
    skill('Fade','消影',0,{'allyTemporaryDexterity':3},'uncommon','ally',allyTemporaryDexterity=6,retain=True,multiplayerOnly=True)
    ability('FanOfKnives','刀扇',2,{'fanOfKnives':1},'rare',fanOfKnives=4)
    skill('Flanking','夹击',2,{'cost':-1},'rare','enemy',flanking=2,multiplayerOnly=True)
    skill('HandTrick','手上技法',1,{'block':3},'uncommon',block=7,handTrick=True)
    skill('Haze','迷雾',2,{'hazePoison':2,'hazeWeak':1},'uncommon','all',hazePoison=4,hazeWeak=1)
    skill('KnifeTrap','刀刃陷阱',2,rarity='rare',target='enemy',knifeTrap=True)
    skill('Malaise','萎靡',0,{'malaiseBonus':1},'rare','enemy',malaise=True,xCost=True,exhaust=True)
    ability('MasterPlanner','谋划专家',2,{'cost':-1},'rare',masterPlanner=True)
    skill('Mirage','蜃景',1,{'exhaust':-1},'uncommon',mirage=True,exhaust=True)
    skill('Nightmare','夜魇',3,{'cost':-1},'rare',nightmare=True,exhaust=True,noCombatGenerate=True)
    skill('Outbreak','毒性爆发',3,{'poison':3},'rare','all',poison=9,outbreak=True)
    ability('PhantomBlades','幻影之刃',1,{'phantomBlades':3},phantomBlades=9)
    skill('PiercingWail','尖啸',1,{'piercingWail':2},target='all',piercingWail=6,exhaust=True)
    ability('SerpentForm','群蛇形态',3,{'serpentForm':2},'rare',serpentForm=4)
    skill('ShadowStep','暗影步',1,{'cost':-1},'rare',shadowStep=True)
    skill('Shadowmeld','融入暗影',1,{'cost':-1},'rare',shadowmeld=1)
    skill('Sidestep','侧步',0,{'energyNextTurn':1},'uncommon',energyNextTurn=1)
    skill('Snakebite','蛇咬',2,{'poison':3},target='enemy',poison=7,retain=True)
    ability('Sneaky','鬼祟',2,{'sneaky':1},'rare',sneaky=1,sly=True,multiplayerOnly=True)
    ability('Speedster','速行者',2,{'innate':1},speedster=2)
    attack('Suppress','压制',0,11,{'damage':6,'weak':2},'ancient',weak=3,innate=True)
    attack('TheHunt','狩猎',1,10,{'damage':5},'rare',theHunt=True,exhaust=True,noCombatGenerate=True)
    ability('ToolsOfTheTrade','必备工具',1,{'cost':-1},'rare',toolsOfTheTrade=1)
    ability('Tracking','跟踪',2,{'cost':-1},'rare',tracking=50)
    skill('Untouchable','触不可及',2,{'block':3},block=6,sly=True)
    skill('UpMySleeve','袖里乾坤',2,{'shivs':1},'uncommon',shivs=3,cheaperAfterPlay=1)
    ability('WellLaidPlans','计划妥当',2,{'cost':-1},'rare',wellLaidPlans=True)
    ability('WraithForm','幽魂形态',3,{'intangible':1},'ancient',intangible=2,wraithForm=1)


def describe(values, *, upgraded=False):
    labels={'shivs':'生成小刀','discardDamage':'本回合每次主动弃牌额外伤害',
            'drawnDamage':'本场每次实际抽牌额外伤害','poison':'中毒','freeSkill':'后续技能费用为 0 的次数',
            'handPenalty':'每张其他手牌减少伤害','drawNextTurn':'下回合额外抽牌','strangle':'本回合随后每次自己出牌令目标失去生命',
            'escapePlan':'抽一张牌，若为技能则获得格挡','drawRetain':'抽牌并仅在本回合保留',
            'permanentThorns':'本场持续荆棘','accuracy':'小刀额外伤害','afterimage':'后续每次出牌获得直接格挡',
            'accelerant':'敌方中毒每次额外触发次数（每次递减）','temporaryDexterity':'本回合敏捷',
            'inkyShivs':'生成带 1 虚弱附魔的小刀','allShivs':'给每位存活队员生成小刀','blur':'保留格挡的回合数',
            'poisonIfPoisoned':'目标已有中毒时追加中毒','burst':'本回合随后双重打出的技能数',
            'infiniteBlades':'每回合抽牌前生成小刀','noxiousFumes':'每回合开始对所有敌人施加中毒',
            'envenom':'每次攻击造成未格挡伤害时施加中毒','concoct':'队友本轮攻击造成未格挡伤害时施加中毒',
            'corrosiveWave':'本回合每次实际抽牌对所有敌人施加中毒','expose':'移除目标全部格挡和人工制品，再施加易伤',
            'allyTemporaryDexterity':'队友本回合敏捷','fanOfKnives':'生成小刀，并使本场所有小刀攻击全体',
            'flanking':'本轮其他攻击者对目标的伤害倍率','phantomBlades':'小刀获得保留，本回合首张小刀额外伤害',
            'piercingWail':'全体敌人本轮力量降低','serpentForm':'随后每次出牌对随机敌人造成直接伤害',
            'shadowmeld':'本回合所有格挡翻倍的层数','energyNextTurn':'下回合额外能量','sneaky':'其他队员打出攻击时获得直接格挡',
            'speedster':'己方回合额外抽牌时对全体造成直接伤害','toolsOfTheTrade':'每回合额外正常抽牌并随后弃牌',
            'tracking':'对虚弱目标的攻击增伤百分比','cheaperAfterPlay':'本牌打出后本场费用降低',
            'intangible':'无实体回合数','wraithForm':'以后每回合开始失去敏捷'}
    result=[f'{label} {values[key]}' for key,label in labels.items() if values.get(key)]
    if values.get('drawDiscard'):result.append(f"抽 {values['drawDiscard']} 张牌，再主动弃 {values.get('discardCount',values['drawDiscard'])} 张")
    if values.get('poisonBounces'):result.append(f"随机施加 {values['bouncePoison']} 中毒，重复 {values['poisonBounces']} 次")
    if values.get('hiddenDaggers'):result.append("先主动弃 2 张牌，再生成 2 张小刀"+("+" if upgraded else ""))
    for key,label in {'echoingSlash':'每击杀一个敌人，额外对全体攻击一次','finisher':'攻击次数等于本回合已结算的攻击牌数',
                      'flechettes':'每张技能手牌攻击一次','emptyDrawOnly':'仅在抽牌堆为空时可打出',
                      'sly':'奇巧：被主动弃掉时自动打出，回合结束清空手牌不触发',
                      'pinpoint':'本回合每结算一张技能，费用降低 1',
                      'repeatBlockNextTurn':'下回合获得本次实际取得的格挡数值，不再计算敏捷',
                      'bulletTime':'当前非能量 X 费手牌本回合免费，本回合不能抽牌',
                      'calculatedGamble':'弃掉全部手牌并抽取同样数量，再依次自动打出弃掉的奇巧牌',
                      'stormOfSteel':'弃掉全部手牌，然后生成等量小刀'+('+' if upgraded else ''),
                      'handTrick':'选择一张尚无奇巧的技能，本回合赋予奇巧',
                      'knifeTrap':('先升级消耗堆所有小刀，再' if upgraded else '')+'对选定敌人依次打出消耗堆所有小刀',
                      'malaise':'使目标失去 '+('X+1' if upgraded else 'X')+' 力量并获得 '+('X+1' if upgraded else 'X')+' 虚弱',
                      'masterPlanner':'本场技能结算后获得奇巧','mirage':'获得等于所有存活敌人中毒总层数的格挡',
                      'nightmare':'选择一张手牌，下回合抽牌前生成 3 张副本','outbreak':'施毒后立即触发中毒',
                      'shadowStep':'弃掉全部手牌，下回合攻击伤害翻倍','theHunt':'致命击杀后额外获得一次选牌奖励',
                      'wellLaidPlans':'回合结束保留全部普通手牌；虚无和回合结束效果仍触发'}.items():
        if values.get(key):result.append(label)
    if values.get('hazePoison'):result.append(f"对全体先施加 {values['hazePoison']} 中毒，再施加 {values['hazeWeak']} 虚弱")
    return result
