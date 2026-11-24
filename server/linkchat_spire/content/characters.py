"""Fully unlocked character starting loadouts audited against v0.111.0."""
CHARACTERS={
    'ironclad':{'name':'铁甲战士','hp':80,'gold':99,'orbSlots':0,'deck':['StrikeIronclad']*5+['DefendIronclad']*4+['Bash'],'relics':['BurningBlood']},
    'silent':{'name':'静默猎手','hp':70,'gold':99,'orbSlots':0,'deck':['StrikeSilent']*5+['DefendSilent']*5+['Neutralize','Survivor'],'relics':['RingOfTheSnake']},
    'defect':{'name':'故障机器人','hp':75,'gold':99,'orbSlots':3,'deck':['StrikeDefect']*4+['DefendDefect']*4+['Zap','Dualcast'],'relics':['CrackedCore']},
    'regent':{'name':'储君','hp':75,'gold':99,'orbSlots':0,'deck':['StrikeRegent']*4+['DefendRegent']*4+['FallingStar','Venerate'],'relics':['DivineRight']},
    'necrobinder':{'name':'亡灵契约师','hp':66,'gold':99,'orbSlots':0,'deck':['StrikeNecrobinder']*4+['DefendNecrobinder']*4+['Bodyguard','Unleash'],'relics':['BoundPhylactery']},
}
STARTER_RELICS={key for character in CHARACTERS.values() for key in character['relics']}


def reward_pool(player):
    from . import CARDS
    return [d for d in CARDS.values() if d['pool']==player.get('character','ironclad') and d['rarity'] in ('common','uncommon','rare')]


def combat_start(state,player):
    from ..combat import orbs, osty
    if 'CrackedCore' in player['relics']:orbs.channel(state,player,'lightning')
    if 'DivineRight' in player['relics']:
        from ..combat.classes.regent import gain_stars
        gain_stars(state,player,3)
    if 'BoundPhylactery' in player['relics']:osty.summon(state,player,1)


def after_energy_reset(state,player):
    if player.get('turnNumber',state['turn'])>1 and 'BoundPhylactery' in player['relics']:
        from ..combat.osty import summon
        summon(state,player,1)
