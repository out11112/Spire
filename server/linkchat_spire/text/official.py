"""Render the Chinese game localization for the terminal projection.

The source templates are copied from extracted_localization/raw/zhs, v0.111.0.
The original game supplies values and formatting through its own UI; this
module supplies those from the Spire simulation's projected content.
"""
import re
from ..content.data import load as load_data


DESCRIPTIONS = load_data('official_descriptions.json', encoding='utf-8')
POWER_NAMES = load_data('official_power_names.json', encoding='utf-8')
POWER_DESCRIPTIONS = load_data('official_power_descriptions.json', encoding='utf-8')
# Statuses the simulation tracks under its own key. The game shows temporary
# stat changes under the source's title with the shared TEMPORARY_* wording,
# so each maps to (official title, official description key).
POWER_ALIASES = {
    'setupStrike': ('预备打击', 'TEMPORARY_STRENGTH_POWER'),
    'feedingFrenzy': ('疯狂进食', 'TEMPORARY_STRENGTH_POWER'),
    'coordinate': ('协同配合', 'TEMPORARY_STRENGTH_POWER'),
    'reptileTrinket': ('爬行动物饰品', 'TEMPORARY_STRENGTH_POWER'),
    'potionTemporaryStrength': ('肌肉药水', 'TEMPORARY_STRENGTH_POWER'),
    'temporaryDexterity': ('预判', 'TEMPORARY_DEXTERITY_POWER'),
    'fadeDexterity': ('消影', 'TEMPORARY_DEXTERITY_POWER'),
    'helicalDart': ('螺线飞镖', 'TEMPORARY_DEXTERITY_POWER'),
    'potionTemporaryDexterity': ('速度药水', 'TEMPORARY_DEXTERITY_POWER'),
    'temporaryFocus': ('集中打击', 'TEMPORARY_FOCUS_POWER'),
    'focusedStrikeFocus': ('集中打击', 'TEMPORARY_FOCUS_POWER'),
    'hotfixFocus': ('热修复', 'TEMPORARY_FOCUS_POWER'),
    'synchronizeFocus': ('同步', 'TEMPORARY_FOCUS_POWER'),
    'darkShackles': ('黑暗镣铐', 'TEMPORARY_STRENGTH_DOWN'),
    'mangle': ('凌虐', 'TEMPORARY_STRENGTH_DOWN'),
    'crushUnder': ('下砸', 'TEMPORARY_STRENGTH_DOWN'),
    'dyingStar': ('星灭', 'TEMPORARY_STRENGTH_DOWN'),
    'enfeeblingTouch': ('弱化之触', 'TEMPORARY_STRENGTH_DOWN'),
    'piercingWail': ('尖啸', 'TEMPORARY_STRENGTH_DOWN'),
    'monarchsGazeDown': ('王之凝视', 'TEMPORARY_STRENGTH_DOWN'),
    'shacklingPotion': ('镣铐药水', 'TEMPORARY_STRENGTH_DOWN'),
    'hyperbeamFocusDown': ('超能光束', 'TEMPORARY_FOCUS_DOWN'),
    'bomb': ('炸弹', 'THE_BOMB_POWER'),
    'drawNextTurn': ('下回合抽牌', 'DRAW_CARDS_NEXT_TURN_POWER'),
    'permanentThorns': ('荆棘', 'THORNS_POWER'),
}
INTERNAL_POWER_NAMES = {key: name for key, (name, _) in POWER_ALIASES.items()}
# A stunned enemy is shown with the official STUN intent wording.
POWER_ALIASES['stunned'] = ('击晕', None)
INTERNAL_POWER_NAMES['stunned'] = '击晕'
EXTRA_POWER_DESCRIPTIONS = {'stunned': {'description': '这个敌人在其下一回合无法行动。'}}


def power_templates():
    """Official description templates keyed by the simulation's status keys."""
    def camel(key):
        words = key.removesuffix('_POWER').lower().split('_')
        return words[0] + ''.join(word.title() for word in words[1:])
    templates = {camel(key): value for key, value in POWER_DESCRIPTIONS.items()}
    templates.update({key: POWER_DESCRIPTIONS[template] for key, (_, template) in POWER_ALIASES.items() if template})
    templates.update(EXTRA_POWER_DESCRIPTIONS)
    return templates
TOKEN = re.compile(r'\{([^{}]*)\}')
MARKUP = re.compile(r'\[/?(?:gold|blue|green|red|purple|yellow|white|orange|gray|grey)\]')
NUMBER = re.compile(r'(?<![A-Za-z])\d+(?:\.\d+)?|[一二两三四五六七八九十]+')
CHINESE_DIGITS = {'一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5,
                  '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
CARD_VALUES = {
    'BigBang': {'Energy': 1, 'Stars': 1, 'Forge': 5},
    'Cacophony': {'Cards': 33},
    'Constellation': {'Cards': 1, 'Energy': 1},
    'DeathsDoor': {'Repeat': 3},
    'Demesne': {'Energy': 1, 'Cards': 1},
    'Glimmer': {'PutBack': 1},
    'NoEscape': {'DoomThreshold': 10, 'CalculationExtra': 5},
    'PaleBlueDot': {'CardPlay': 5},
    'Tank': {'DamageIncrease': 1.5, 'DamageDecrease': 0.5},
    'TheBomb': {'Turns': 3},
    'Transfigure': {'Energy': 1},
    'Stack': {'CalculationBase': 3},
    'DanseMacabre': {'Energy': 2},
    'Orbit': {'Energy': 1},
    'PactsEnd': {'Cards': 3},
}
CARD_FIELDS = {
    'BladeOfInk': {'Cards': 'inkyShivs'},
    'BrightestFlame': {'Energy': 'brightestFlame', 'Cards': 'brightestFlame', 'MaxHp': 'brightestFlame'},
    'Automation': {'Energy': 'automation'},
    'BansheesCry': {'Energy': 'etherealCostReduction'},
    'BorrowedTime': {'ExtraCost': 'borrowedTime'},
    'BulkUp': {'OrbSlots': 'removeOrbSlots'},
    'ChildOfTheStars': {'BlockForStars': 'childOfTheStars'},
    'Claw': {'Increase': 'claw'},
    'CloakAndDagger': {'Cards': 'shivs'},
    'Cacophony': {'Damage': 'cacophony'},
    'Constellation': {'Block': 'constellationBlock'},
    'CrescentSpear': {'ExtraDamage': 'starCardDamage'},
    'CrushUnder': {'StrengthLoss': 'temporaryEnemyStrength'},
    'Deathbringer': {'WeakPower': 'weakAfterDoom'},
    'DeathsDoor': {'Block': 'deathDoorBlock'},
    'DecisionsDecisions': {'Repeat': 'decisionsDecisions'},
    'DrainPower': {'Cards': 'upgradeDiscard'},
    'DyingStar': {'StrengthLoss': 'temporaryEnemyStrength'},
    'EscapePlan': {'Block': 'escapePlan'},
    'FlameBarrier': {'DamageBack': 'thorns'},
    'Ftl': {'PlayMax': 'ftl'},
    'GangUp': {'ExtraDamage': 'gangUp'},
    'GeneticAlgorithm': {'Increase': 'geneticGrowth'},
    'Glitterstream': {'BlockNextTurn': 'delayedBlock'},
    'Glimmer': {'Cards': 'photonCut'},
    'GoForTheEyes': {'WeakPower': 'attackIntentWeak'},
    'HeavenlyDrill': {'Energy': 'doubleXAt'},
    'Jackpot': {'Cards': 'jackpot'},
    'KinglyPunch': {'Increase': 'drawDamageGrowth'},
    'MakeItSo': {'Cards': 'returnAfterSkills'},
    'Mangle': {'StrengthLoss': 'darkShackles'},
    'Maul': {'Increase': 'maul'},
    'Melancholy': {'Energy': 'deathCostReduction'},
    'Modded': {'Repeat': 'addOrbSlots', 'Cards': 'moddedDraw'},
    'NeowsFury': {'Cards': 'neowsFury'},
    'NoEscape': {'CalculationBase': 'noEscape'},
    'OneTwoPunch': {'Attacks': 'oneTwoPunch'},
    'PaleBlueDot': {'Cards': 'paleBlueDot'},
    'Panache': {'PanacheDamage': 'panache'},
    'PanicButton': {'Turns': 'noBlock'},
    'PhotonCut': {'Cards': 'photonCut'},
    'PullAggro': {'Block': 'blockAfterSummon'},
    'Rampage': {'Increase': 'rampage'},
    'Restlessness': {'Cards': 'restlessness', 'Energy': 'restlessness'},
    'Scourge': {'Cards': 'drawAfterDoom'},
    'Scavenge': {'Energy': 'scavenge'},
    'Scrape': {'Cards': 'scrape'},
    'SeekerStrike': {'Cards': 'seekerStrike'},
    'SetupStrike': {'StrengthPower': 'setupStrike'},
    'Spite': {'Repeat': 'spite'},
    'SpoilsOfBattle': {'Cards': 'drawAfterForge'},
    'Spur': {'Heal': 'healOsty'},
    'Stack': {'CalculationBase': 'stackBase'},
    'Sunder': {'Energy': 'killEnergy'},
    'Supermassive': {'ExtraDamage': 'generatedDamage'},
    'TheScythe': {'Increase': 'scythe'},
    'TheBall': {'Increase': 'theBall'},
    'TheBomb': {'BombDamage': 'bomb'},
    'Uppercut': {'Power': 'weak'},
    'Synchronize': {'CalculationExtra': 'synchronize'},
}
RELIC_VALUES = {
    'PaelsGrowth': {'EnchantmentName': '克隆'},
    'RoyalStamp': {'Enchantment': '王室认证'},
    'MembershipCard': {'Discount': 50},
    'RedSkull': {'HpThreshold': 50, 'StrengthPower': 3},
    'MeatOnTheBone': {'HpThreshold': 50, 'Heal': 12},
    'GnarledHammer': {'Cards': 3, 'SharpAmount': 3},
    'AlchemicalCoffer': {'PotionSlots': 4},
    'NeowsBones': {'Relics': 2, 'Curses': 1},
    'SeaGlass': {'Cards': 15},
    'Bread': {'LoseEnergy': 2, 'GainEnergy': 1},
    'LizardTail': {'Heal': 50},
    'PaelsFlesh': {'Energy': 1},
    'PumpkinCandle': {'Energy': 1, 'CombatCount': 5},
    'SparklingRouge': {'StrengthPower': 1, 'DexterityPower': 1},
}
# Named values must not be inferred from prose: “一名敌人” is a target count,
# and the official template may order duration and magnitude differently.
POTION_VALUES = {
    'FlexPotion': {'StrengthPower': 5},
    'SpeedPotion': {'DexterityPower': 5},
    'FirePotion': {'Damage': 20},
    'PotionShapedRock': {'Damage': 15},
    'PoisonPotion': {'PoisonPower': 6},
    'PotionOfDoom': {'DoomPower': 33},
    'WeakPotion': {'WeakPower': 3},
    'VulnerablePotion': {'VulnerablePower': 3},
    'BeetleJuice': {'Repeat': 4, 'DamageDecrease': 30},
}


def _clean(value):
    return re.sub(r'\s*\n\s*', ' ', MARKUP.sub('', value).replace('\\|', '|')).strip()


def _number(raw):
    if raw in CHINESE_DIGITS:
        return CHINESE_DIGITS[raw]
    if '十' in raw:
        left, right = raw.split('十', 1)
        return CHINESE_DIGITS.get(left, 1) * 10 + CHINESE_DIGITS.get(right, 0)
    return float(raw) if '.' in raw else int(raw)


def power_name(key, player=False):
    # A player's thorns only ever come from Flame Barrier, shown as that status.
    if player and key == 'thorns':
        return POWER_NAMES['FLAME_BARRIER_POWER']
    upper = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', key).upper()
    if key in INTERNAL_POWER_NAMES:
        return INTERNAL_POWER_NAMES[key]
    return POWER_NAMES.get(upper + '_POWER', POWER_NAMES.get(upper, '状态'))


def _value(name, values, old_numbers, position):
    if name in values:
        return values[name], position
    bare = name.removesuffix('Power')
    key = bare[0].lower() + bare[1:] if bare else bare
    aliases = {
        'Cards': ('draw', 'allDraw', 'drawNextTurn'),
        'Energy': ('energy', 'allyEnergy', 'allEnergy', 'energyNextTurn', 'exhaustEnergy'),
        'Stars': ('stars', 'killStars', 'starNextTurn'),
        'Repeat': ('hits', 'repeat', 'replay', 'channelCount', 'shivs'),
        'HpLoss': ('hpLoss', 'endHpLoss'),
        'Damage': ('damage', 'endDamage', 'doomDamage'),
        'Block': ('block', 'allBlock', 'allyBlock', 'delayedBlock'),
        'Summon': ('summon', 'allSummon', 'dirgeSummon'),
        'Gold': ('gold', 'endGoldLoss', 'fatalGold'),
        'MaxHp': ('maxHp', 'feed'),
        'Forge': ('forge', 'forgePerHit'),
        'Shivs': ('shivs', 'allShivs', 'inkyShivs'),
        'Thorns': ('thorns', 'permanentThorns'),
        'Strength': ('strength', 'allyStrength'),
        'Weak': ('weak', 'hazeWeak', 'endWeak'),
        'Vulnerable': ('vulnerable', 'doubleVulnerable'),
        'Poison': ('poison', 'hazePoison'),
        'Focus': ('focus', 'temporaryFocus'),
    }
    for candidate in (key, *aliases.get(bare, ())):
        if candidate in values and isinstance(values[candidate], (int, float)) and not isinstance(values[candidate], bool):
            return values[candidate], position
    if position < len(old_numbers):
        raw = old_numbers[position]
        return _number(raw), position + 1
    return None, position


def _mad_science(values):
    kind = values.get('kind', 'attack')
    rider = values.get('scienceRider', 'none')
    if kind == 'attack':
        base = f"造成{values.get('damage', 12)}点伤害" + (f"{values.get('hits', 3)}次" if rider == 'violence' else '') + '。'
    elif kind == 'skill':
        base = f"获得{values.get('block', 8)}点格挡。"
    else:
        base = '？？？'
    extras = {
        'sapping': lambda: f"给予{values.get('weak', 2)}层虚弱。\n给予{values.get('vulnerable', 2)}层易伤。",
        'choking': lambda: f"本回合，你每打出一张牌，该敌人失去{values.get('strangle', 6)}点生命。",
        'energized': lambda: f"获得{values.get('energy', 2)}能量。",
        'wisdom': lambda: f"抽{values.get('draw', 3)}张牌。",
        'chaos': lambda: '将一张随机牌放入你的手牌，这张牌在本回合可以免费打出。',
        'expertise': lambda: f"获得{values.get('strength', 2)}点力量。\n获得{values.get('dexterity', 2)}点敏捷。",
        'curious': lambda: '能力牌的耗能减少1能量。',
        'improvement': lambda: '在战斗结束时，升级你牌组中的一张随机牌。',
    }
    return base + ('\n' + extras[rider]() if rider in extras else '')


def render(category, key, *, values=None, upgraded=False, in_combat=False, old=''):
    """Return official wording with terminal-friendly values and plain text."""
    template = DESCRIPTIONS.get(category, {}).get(key)
    if not template:
        return None
    if category == 'card' and key == 'Transfigure':
        template = template.replace('1{Energy:energyIcons()}', '1能量')
    values = values or {}
    if category == 'card':
        values = {**{name: values[field] for name, field in CARD_FIELDS.get(key, {}).items() if field in values}, **values}
    values = {**{'card': CARD_VALUES, 'relic': RELIC_VALUES, 'potion': POTION_VALUES}.get(category, {}).get(key, {}), **values}
    if category == 'card' and key == 'MadScience':
        return _clean(_mad_science(values))
    old_numbers = NUMBER.findall(old)
    position = 0

    # These fields are populated only while viewing a live combat target.
    # Normal card views use the official non-combat branch.
    if not in_combat:
        template = re.sub(r'\{(?:InCombat|IsTargeting):.*?\|\}', '', template, flags=re.S)
    # Entity-specific hover text has no selected entity in the TUI projection.
    if category == 'relic':
        template = re.sub(r'\{CardTitles\.StringValue:cond:.*?\|\}', '', template, flags=re.S)
        for field in ('StarterCard', 'AncientCard', 'StarterRelic', 'Character'):
            template = re.sub(r'\{' + field + r'\.StringValue:cond:.*?\|(.*?)\}', r'\1', template, flags=re.S)

    def replace(match):
        nonlocal position
        token = match.group(1)
        if token.startswith('IfUpgraded:show:'):
            branches = token[len('IfUpgraded:show:'):].split('|', 1)
            return branches[0] if upgraded else branches[1] if len(branches) > 1 else ''
        if token.startswith('InCombat:'):
            branches = token[len('InCombat:'):].split('|', 1)
            return branches[0] if in_combat else branches[1] if len(branches) > 1 else ''
        if token.startswith('TargetType:choose(AllEnemies):'):
            branches = token.split(':', 2)[2].split('|', 1)
            return branches[0] if values.get('target') == 'all' else branches[1] if len(branches) > 1 else ''
        if token.startswith('CardType:choose('):
            choices = token.split(':', 2)[-1].split('|')
            index = {'attack': 0, 'skill': 1, 'power': 2}.get(values.get('kind'), 3)
            return choices[min(index, len(choices) - 1)]
        if token.startswith('energyPrefix:energyIcons('):
            return '能量'
        if token == 'singleStarIcon':
            return '辉星'
        if token == '':
            return ''
        name, _, operation = token.partition(':')
        if operation.startswith('plural:'):
            branches = operation[7:].split('|', 1)
            value, position = _value(name, values, old_numbers, position)
            return branches[0] if value == 1 else branches[1] if len(branches) > 1 else branches[0]
        if operation.startswith('choose('):
            branches = operation.split(':', 1)[-1].split('|', 1)
            if name == 'Skills':
                return branches[0] if values.get('burst', 1) == 1 else branches[1] if len(branches) > 1 else branches[0]
            return branches[0]
        if operation.startswith('cond:'):
            branches = operation[5:].split('|', 1)
            return branches[0] if values.get(name.split('.')[0]) else branches[1] if len(branches) > 1 else ''
        if operation and not operation.endswith(('()', ')')):
            branches = operation.split('|', 1)
            return branches[0] if values.get(name) else branches[1] if len(branches) > 1 else ''
        value, position = _value(name, values, old_numbers, position)
        if value is None:
            raise ValueError(f'No official localization value for {category}/{key}: {token}')
        if 'percentMore' in operation or 'percentLess' in operation:
            value = round((value - 1) * 100) if 'percentMore' in operation and value <= 2 else round((1 - value) * 100) if 'percentLess' in operation and value <= 1 else value
        if 'energyIcons' in operation:
            return f'{value}能量'
        if 'starIcons' in operation:
            return f'{value}辉星'
        return str(value)

    for _ in range(12):
        updated = TOKEN.sub(replace, template)
        if updated == template:
            break
        template = updated
    if '{' in template or '}' in template:
        raise ValueError(f'Unresolved official localization for {category}/{key}: {template}')
    return _clean(template)
