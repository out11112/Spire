"""The card table, the registration helper, and what a card instance resolves to."""
from copy import deepcopy
from .colorless import describe as describe_colorless
# cost, type, target, base values, upgrade increments, additional behavior
CARDS = {}
def card(key, name, cost, kind, target='self', upgrade=None, rarity=None, pool='ironclad', **values):
    CARDS[key] = dict(key=key, name=name, cost=cost, kind=kind, target=target, rarity=rarity or (kind if kind in ('curse','status') else 'common'),pool=kind if kind in ('curse','status') else pool,values=values,upgrade=upgrade or {})


def definition(instance,owner=None):
    d=deepcopy(CARDS[instance['key']]); v=d['values']
    from .special import modify_definition
    modify_definition(instance,d)
    if instance.get('upgraded'):
        for key,increment in d['upgrade'].items():
            if key=='cost': d['cost']+=increment
            else: v[key]=v.get(key,0)+increment
    from ...combat.costs import resolve
    if not v.get('xCost') and d['cost']>=0:d['cost']=max(0,d['cost']+instance.get('baseCostAdjustment',0))
    if not v.get('xCost'):d['cost']=resolve(instance,d['cost'])
    if instance.get('bonusDamage'):v['damage']=v.get('damage',0)+instance['bonusDamage']
    if instance.get('bonusBlock'):v['block']=v.get('block',0)+instance['bonusBlock']
    if instance['key']=='Wither':v['endDamage']=3+3*instance.get('witherLevel',0)
    for keyword in instance.get('removedKeywords',[]):v.pop(keyword,None)
    for keyword in instance.get('addedKeywords',[]):v[keyword]=True
    if instance.get('affliction',{}).get('key')=='Hexed' and (owner is None or owner['powers'].get('hex')):v['ethereal']=True
    if instance.get('slyThisTurn'):v['sly']=True
    return d

def card_view(instance,owner=None):
    d=definition(instance,owner); v=d['values']; parts=[]
    active=lambda power:owner is None or bool(owner['powers'].get(power))
    from ...combat.afflictions import description as affliction_description
    if instance.get('affliction'):
        text=affliction_description(instance['affliction'],active)
        if text:parts.append(text)
    if instance.get('retainThisTurn'):parts.append('保留')
    if instance.get('inky') and not instance.get('enchantment'):
        from ...combat.enchantments import OFFICIAL as enchantment_text
        parts.append(enchantment_text['Inky'].format(amount=1))
    extra_description=list(parts)
    if v.get('discardOnly'):parts.append(f"主动弃 {v['discardOnly']} 张手牌")
    if v.get('dualcast'):parts.append('最前方充能球激发两次，再移除该球')
    if v.get('summon'):parts.append(f"召唤奥斯提 {v['summon']}；存活时增加当前和最大生命")
    if v.get('ostyHpDamage'):parts.append('基础伤害额外增加奥斯提当前生命')
    for key,label in [('hpLoss','失去生命'),('damage','伤害'),('block','格挡'),('draw','抽牌'),('energy','能量'),('strength','力量'),('dexterity','敏捷'),('vigor','活力'),('weak','虚弱'),('vulnerable','易伤'),('rage','本回合每张攻击获得格挡'),('thorns','本回合受攻击荆棘'),('demonForm','每回合力量'),('darkEmbrace','消耗时抽牌'),('feelNoPain','消耗时格挡'),('rupture','自己的回合每次失去生命时获得力量'),('blockPerExhaust','消耗所有非攻击牌，每张格挡')]:
        if v.get(key):
            scope='对所有敌人' if d['target']=='all' else '对随机敌人' if d['target']=='random' else ''
            parts.append(f"{scope if key in ('damage','weak','vulnerable') else ''}{label} {v[key]}")
    if v.get('hits'):parts.append(f"{v['hits']} 次")
    for key,label in [('exhaust','消耗'),('copy','复制到弃牌堆'),('bodySlam','伤害等于格挡'),('upgradeHand','升级全部手牌' if instance.get('upgraded') else '升级一张手牌'),('exhaustChoice','选择消耗一张手牌'),('trueGrit','选择消耗一张手牌' if instance.get('upgraded') else '随机消耗一张手牌'),('noDraw','本回合无法再抽牌'),('xCost','消耗全部能量，攻击 X 次' if d['kind']=='attack' else '消耗全部能量，X 为消耗的能量'),('unplayable','不能被打出'),('ethereal','虚无')]:
        if v.get(key):parts.append(label)
    if instance.get('sown') and not instance.get('enchantment'):
        from ...combat.enchantments import OFFICIAL as enchantment_text
        parts.append(enchantment_text['Sown'].format(amount=1)+('（本场已生效）' if instance.get('sownUsed') else ''))
    for key,label in [('endDamage','回合结束仍在手牌时受到伤害'),('endHpLoss','回合结束仍在手牌时失去生命'),('endGoldLoss','回合结束仍在手牌时失去金币')]:
        if v.get(key):parts.append(f'{label} {v[key]}')
    for key,label in [('innate','固有'),('eternal','永恒'),('retain','保留'),('regret','回合结束失去等同手牌数的生命'),('endWeak','回合结束获得 1 虚弱'),('endFrail','回合结束获得 1 脆弱'),('normality','在手牌中时，每回合最多打出 3 张牌'),('enthralled','在手牌中时，必须优先打出此牌'),('drawEnergyLoss','抽到时失去 1 能量'),('franticEscape','提高对自己的沙坑进度；本场费用增加 1')]:
        if v.get(key):parts.append(label)
    if instance['key']=='Guilty':parts.append(f"再经历 {max(0,5-instance.get('combats',0))} 场战斗后移除")
    if v.get('searchDraw'):parts.append('从抽牌堆选择一张'+('攻击牌' if v['searchDraw']=='attack' else '技能牌')+'加入手牌')
    if v.get('purity'):parts.append(f"选择至多 {v['purity']} 张手牌消耗")
    if v.get('thinkingAhead'):parts.append(f"抽 {v['thinkingAhead']} 张牌，再将一张手牌放回抽牌堆顶")
    if v.get('discovery'):parts.append('从随机三张职业牌中选择一张加入手牌，本回合费用为 0；可以跳过')
    if v.get('splash'):parts.append('从其他职业随机三张不同攻击牌中选择一张，本回合免费；可跳过'+('，候选均升级' if instance.get('upgraded') else ''))
    if v.get('mayhem'):parts.append(f"回合抽牌后自动打出抽牌堆顶 {v['mayhem']} 张牌")
    if v.get('hellraiser'):parts.append('每次抽到带有打击标签的牌时立即自动打出')
    if v.get('stratagem'):parts.append(f"每次洗牌后从抽牌堆选择 {v['stratagem']} 张加入手牌，再继续原来的抽牌")
    if v.get('entropy'):parts.append(f"每回合抽牌后选择 {v['entropy']} 张手牌随机变形；按原牌所属池逐牌等概率，不保留升级")
    if v.get('alchemize'):parts.append('按职业与通用药水池随机生成一瓶战斗药水；药水栏满时无法获得')
    quests={'ByrdonisEgg':'在营地选择孵化，所有蛋变成异鸟扑击','Dowsing':f"再进入 {max(0,5-instance.get('questRooms',0))} 个问号房间后变为富足",'LanternKey':'第三幕将问号节点改为战争史学家事件','SpoilsMap':'第二幕路线汇聚到宝藏；到达宝藏获得 600 金币并移除此牌'}
    if instance['key'] in quests:parts.append(quests[instance['key']])
    if v.get('noBlock'):parts.append(f"{v['noBlock']} 回合内无法从卡牌获得格挡")
    if v.get('darkShackles'):parts.append(f"敌人力量降低 {v['darkShackles']}，其回合结束后恢复")
    if v.get('drawToFull'):parts.append('抽牌至手牌上限 10 张')
    if v.get('impatience'):parts.append('仅在手牌中没有攻击牌时抽牌')
    if v.get('mindBlast'):parts.append('基础伤害等于抽牌堆张数')
    if v.get('jackOfAllTrades'):parts.append(f"随机生成 {v['jackOfAllTrades']} 张不同的无色牌加入手牌")
    for key,label in [('ashenStrike','每张消耗堆卡牌额外伤害'),('bully','目标每层易伤额外伤害'),('perfectedStrike','本场每张打击牌额外伤害'),('rampage','打出后本牌伤害增加'),('setupStrike','本回合力量'),('enemyStrength','目标力量增加')]:
        if v.get(key):parts.append(f'{label} {v[key]}')
    for key,label in [('randomExhaust','随机消耗一张手牌'),('dismantle','目标有易伤时攻击两次'),('dominate','获得等同目标易伤层数的力量'),('evilEye','本回合消耗过牌时获得两次格挡'),('headbutt','选择一张弃牌放回抽牌堆顶'),('brand','消耗一张手牌，再获得力量'),('infernalBlade','生成一张随机职业攻击牌，本回合费用为 0'),('juggling','每回合第三张攻击打出前，复制到手牌'),('thrash','随机消耗一张攻击手牌，将其伤害加入本牌')]:
        if v.get(key):parts.append(label)
    for key,label in {"allyStrength":"队友力量","exhaustEnergy":"本牌被消耗时获得能量","strengthBlock":"每点正力量额外格挡","feed":"致命击杀增加最大生命","heal":"恢复生命","pyre":"每回合额外能量","plating":"覆甲：回合结束获得格挡，之后每回合衰减 1","vicious":"施加易伤时抽牌","juggernaut":"每次获得格挡时对随机敌人造成直接伤害","crimsonMantle":"回合开始失去 1 生命并获得格挡","inferno":"回合开始失去 1 生命；自己的回合每次失去生命时对所有敌人造成伤害","cruelty":"易伤倍率增加百分点","aggression":"回合开始取回弃牌堆随机攻击并升级","freeAttack":"后续攻击费用为 0 的次数"}.items():
        if v.get(key):parts.append(f'{label} {v[key]}')
    for key,label in {"barricade":"格挡不会在回合开始清空","corruption":"技能费用为 0，打出后消耗","colossus":"本回合受到有易伤敌人的攻击伤害减半","demonicShield":"队友获得等同自身当前格挡的基础格挡","fiendFire":"消耗当前全部手牌，每张攻击一次","midnight":"本场任意玩家每消耗一张牌，费用降低 1","doubleVulnerable":"目标剩余易伤翻倍","outrage":"给所有存活玩家（包括自己）的弃牌堆加入本牌复制","minimumExhaust":"消耗堆至少 3 张时才造成伤害","pillage":"连续抽牌，直到抽到非攻击牌或手牌已满","primalForce":"将手牌中可变换的攻击变成巨石"+("+" if instance.get("upgraded") else ""),"spite":f"本回合失去过生命时攻击 {v.get('spite',0)} 次","stoke":"消耗当前手牌，生成等量"+("已升级的" if instance.get("upgraded") else "")+"随机职业牌","stomp":"本回合每打出一次攻击，费用降低 1","tank":"自身受到攻击伤害增加 50%，存活期间队友受到攻击伤害减半","tearAsunder":"本场每次失去生命增加一次攻击","unmovable":"每回合首张提供格挡的卡牌，格挡翻倍"}.items():
        if v.get(key):parts.append(label)
    parts.extend(describe_colorless(v, upgraded=bool(instance.get('upgraded'))))
    from .special import describe as describe_special
    parts.extend(describe_special(v, upgraded=bool(instance.get('upgraded'))))
    from .silent import describe
    parts.extend(describe(v, upgraded=bool(instance.get('upgraded'))))
    from .defect import describe as describe_defect
    parts.extend(describe_defect(v, upgraded=bool(instance.get('upgraded'))))
    from .regent import describe as describe_regent
    parts.extend(describe_regent(v, upgraded=bool(instance.get('upgraded'))))
    from .necrobinder import describe as describe_necrobinder
    parts.extend(describe_necrobinder(v, upgraded=bool(instance.get('upgraded'))))
    if d['target']=='all':
        scoped={f'施加灾厄 {v.get("doom")}':f'对所有敌人施加灾厄 {v.get("doom")}',
                f'中毒 {v.get("poison")}':f'对所有敌人施加中毒 {v.get("poison")}',
                f'目标本回合失去力量 {v.get("temporaryEnemyStrength")}':f'所有敌人本回合失去力量 {v.get("temporaryEnemyStrength")}'}
        parts=[scoped.get(part,part) for part in parts]
    for key,label in [('cascade','自动打出抽牌堆顶 '+('X+1' if instance.get('upgraded') else 'X')+' 张牌'),('havoc','自动打出抽牌堆顶一张牌，并消耗'),('howlFromBeyond','回合结束时若在消耗堆中，自动打出'),('oneTwoPunch','本回合接下来的攻击额外打出一次，次数'),('stampede','回合结束自动打出随机攻击手牌，张数')]:
        if v.get(key):parts.append(f'{label}'+(f" {v[key]}" if key in ('oneTwoPunch','stampede') else ''))
    from ...combat.enchantments import description as enchantment_description, can_enchant
    if enchantment_description(instance):parts.append(enchantment_description(instance))
    suffix=f"+{instance['witherLevel']}" if instance.get('witherLevel') else '+' if instance.get('upgraded') else ''
    old_description='；'.join(parts)
    from ...text.official import render as official_description
    official=official_description('card',instance['key'],values={**v,'kind':d['kind'],'target':d['target']},
                                  upgraded=bool(instance.get('upgraded')),old=old_description)
    keyword_names={'exhaust':'消耗','innate':'固有','retain':'保留','ethereal':'虚无',
                   'sly':'奇巧','unplayable':'不能被打出','eternal':'永恒'}
    keywords=[label for key,label in keyword_names.items() if v.get(key) and label not in (official or '')]
    description=' · '.join([official,*keywords,*extra_description,*([enchantment_description(instance)] if enchantment_description(instance) else [])]) if official else old_description
    return {**instance,**({'starCost':'X' if v.get('starX') else v.get('starCost',0)} if 'starCost' in v or v.get('starX') else {}),'name':d['name']+suffix,'cost':'X' if v.get('xCost') else '—' if d['cost']<0 else d['cost'],'kind':d['kind'],'target':d['target'],'removable':not v.get('eternal'),'canSown':bool(can_enchant(instance,'Sown',in_deck=True)),'description':description,'choice': 'upgrade' if v.get('upgradeHand') and not instance.get('upgraded') else 'exhaust' if v.get('exhaustChoice') or v.get('trueGrit') and instance.get('upgraded') else None}


def cost_text(card):
    return str(card['cost'])+(','+str(card['starCost']) if 'starCost' in card else '')
