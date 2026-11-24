"""Implemented enchantment hooks; unknown identities are never substituted."""


IMPLEMENTED={'Glam','SoulsPower','PerfectFit','Spiral','Steady','Vigorous','Corrupted','Slither','Nimble','Sharp','Swift','Adroit','Momentum','RoyallyApproved'}
IMPLEMENTED.add('TezcatarasEmber')
IMPLEMENTED.update(('Goopy','Clone','Instinct','Imbued'))
IMPLEMENTED.update(('Inky','Sown'))
BLOCK_CARDS=set('''Armaments Backflip BloodWall Blur BoneShards BoostAway BootSequence Bulwark ChargeBattery CloakAndDagger CloakOfStars Colossus Compact Constellation CosmicIndifference Dash DeathsDoor DefendDefect DefendIronclad DefendNecrobinder DefendRegent DefendSilent Deflect Defy Delay DemonicShield DodgeAndRoll Entrench Equilibrium EscapePlan EvilEye ExpectAFight FightThrough Finesse Fisticuffs FlameBarrier GatherLight GeneticAlgorithm Glacier Glasswork Glitterstream GraveWarden HandTrick Hologram IAmInvincible Impervious Intercept IronWave Leap LegSweep Lift LightningRod ManifestAuthority Melancholy Mimic MinionSacrifice Mirage NegativePulse PanicButton ParticleWall Patter PullAggro Rally Reflect Relax Sacrifice SecondWind ShadowShield ShrugItOff Stack Survivor Taunt TheGambit ToricToughness TrueGrit UltimateDefend Undeath Untouchable'''.split())


def can_enchant(card,key,*,in_deck=False,player=None):
    from ..content import definition
    d=definition(card)
    return (key in IMPLEMENTED and d['kind'] in ('attack','skill','power') and not card.get('enchantment') and not card.get('inky') and not card.get('sown')
            and not (in_deck and d['values'].get('unplayable'))
            and (key!='SoulsPower' or d['values'].get('exhaust',False))
            and (key not in ('Vigorous','Corrupted','Sharp','Momentum') or d['kind']=='attack')
            and (key!='RoyallyApproved' or d['kind'] in ('attack','skill'))
            and (key!='Goopy' or d['values'].get('defend'))
            and (key!='Instinct' or d['kind']=='attack')
            and (key!='Imbued' or d['kind']=='skill')
            and (key!='Slither' or not d['values'].get('unplayable') and not d['values'].get('xCost'))
            and (key!='Nimble' or card['key'] in BLOCK_CARDS or card['key']=='MadScience' and d['kind']=='skill'
                 or card['key']=='SovereignBlade' and not in_deck and player is not None and player['powers'].get('parry',0)>0)
            and (key!='Spiral' or d['rarity']=='basic' and (d['values'].get('strike') or d['values'].get('defend'))))


def can_glam(card,*,in_deck=False):return can_enchant(card,'Glam',in_deck=in_deck)


def enchant(card,key,*,in_deck=False,amount=1,player=None):
    from ..engine import require
    require(can_enchant(card,key,in_deck=in_deck,player=player),'这张牌不能附加 '+key+'。')
    card['enchantment']={'key':key,'amount':amount}
    if key=='Inky':card['inky']=True
    if key=='Sown':card['sown']=True
    modify_card(card)


def modify_card(card):
    key=card.get('enchantment',{}).get('key')
    if key=='Goopy' and 'exhaust' not in card.setdefault('addedKeywords',[]):card['addedKeywords'].append('exhaust')
    if key=='TezcatarasEmber':
        from ..content import CARDS
        definition=CARDS[card['key']]
        card['baseCostAdjustment']=-definition['cost']-(definition['upgrade'].get('cost',0) if card.get('upgraded') else 0)
        if 'eternal' not in card.setdefault('addedKeywords',[]):card['addedKeywords'].append('eternal')
    if key=='RoyallyApproved':
        for keyword in ('innate','retain'):
            if keyword not in card.setdefault('addedKeywords',[]):card['addedKeywords'].append(keyword)
    if key=='Steady' and 'retain' not in card.setdefault('addedKeywords',[]):card['addedKeywords'].append('retain')
    if key=='SoulsPower':
        card.setdefault('removedKeywords',[]).append('exhaust')
        card['addedKeywords']=[k for k in card.get('addedKeywords',[]) if k!='exhaust']


def glam(card):
    enchant(card,'Glam')


def extra_plays(card):
    enchantment=card.get('enchantment',{})
    return int(enchantment.get('key')=='Spiral' or enchantment.get('key')=='Glam' and not enchantment.get('usedThisCombat'))


def played(card):
    enchantment=card.get('enchantment',{})
    if enchantment.get('key') in ('Glam','Vigorous'):enchantment['usedThisCombat']=True


def reset_combat(card):
    card.pop('sownUsed',None)
    if card.get('enchantment',{}).get('key')=='Momentum':card['enchantment'].pop('extraDamage',None)
    if card.get('enchantment',{}).get('key') in ('Glam','Vigorous','Swift'):card['enchantment'].pop('usedThisCombat',None)


# Official enchantment titles and descriptions (enchantments.json); the
# bracketed notes after them record this combat's use.
OFFICIAL = {'Inky': '墨影：这张牌造成{amount}层虚弱。', 'Sown': '播种：你在每场战斗中第一次打出这张牌时，获得{amount}能量。',
            'Goopy': '黏糊：这张牌获得消耗。当被打出时，这张牌的格挡值永久增加1点。', 'Clone': '克隆：这张牌能在休息处被复制。',
            'Instinct': '本能：这张牌的攻击伤害翻倍。', 'Imbued': '注能：这张牌在每场战斗开始时自动打出。',
            'TezcatarasEmber': '特兹卡塔拉的余烬：费用为0，造成3 点额外伤害，且获得永恒。', 'Adroit': '伶俐：获得{amount}点格挡。',
            'Momentum': '动量：在本场战斗中，每次打出就增加这张牌的攻击伤害{amount}点。', 'RoyallyApproved': '王室认证：这张牌拥有固有和保留。',
            'Sharp': '锋利：这张牌上的伤害值增加{amount}点。', 'Swift': '迅速：你第一次打出这张牌时，抽{amount}张牌。',
            'Nimble': '灵巧：这张牌获得的格挡值增加{amount}点。', 'Slither': '蛇行：当你抽到这张牌时，使其费用在0到3之间随机变化。',
            'Corrupted': '腐化：造成的伤害增加50%，但会失去2生命。', 'Vigorous': '活力：第一次打出这张牌时，造成{amount}点额外伤害。',
            'Glam': '华彩：这张牌每场战斗能够重放一次。', 'SoulsPower': '灵魂之力：这张牌失去消耗。',
            'PerfectFit': '完美契合：每当这张牌要被洗入抽牌堆时，将其放在抽牌堆顶。', 'Spiral': '涡旋：这张牌获得重放1。',
            'Steady': '稳定：这张牌获得保留。'}


def description(card):
    enchantment=card.get('enchantment',{})
    key=enchantment.get('key')
    if key not in OFFICIAL:return ''
    text=OFFICIAL[key].format(amount=enchantment.get('amount',1))
    if key=='Sown' and card.get('sownUsed'):text+='（本场已生效）'
    if key=='Momentum':text+=f"（已增加 {enchantment.get('extraDamage',0)}）"
    if key in ('Swift','Vigorous','Glam') and enchantment.get('usedThisCombat'):text+='（本场已使用）'
    return text


def drawn(state,player,card):
    if card.get('enchantment',{}).get('key')=='Slither' and card in player['hand']:
        from .. import engine as e
        e.change_cost(card,e.roll_energy_cost(state))


def shuffled(player,listeners=None):
    # Engine draws from the end. Each hook moves its own card to the top.
    cards=listeners if listeners is not None else list(reversed(player['draw']))
    for card in cards:
        if card in player['draw'] and card.get('enchantment',{}).get('key')=='PerfectFit':
            player['draw'].remove(card);player['draw'].append(card)
