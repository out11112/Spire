"""Read-only projections of playable content, independent of any saved run."""
from ..content import cost_text
from collections import Counter
from functools import lru_cache
from copy import deepcopy
from ..content import CARDS, RELICS, POTIONS, CONTENT_VERSION, card_view
from ..content.characters import CHARACTERS
from ..content.ascension import LEVELS, monster_hp, monster_intent
from ..engine import ENEMIES
from ..combat.monsters import FIXED, KINDS
from .official import power_name
from ..content.potions import DATA as POTION_DATA
from ..relics.pool import DATA as RELIC_DATA

CATEGORIES = {'cards': '卡牌', 'monsters': '怪物', 'relics': '遗物', 'potions': '药水', 'characters': '角色'}
KINDS_ZH = {'attack':'攻击', 'skill':'技能', 'power':'能力', 'status':'状态', 'curse':'诅咒', 'battle':'普通', 'elite':'精英', 'boss':'首领'}
RARITIES = {'basic':'初始','common':'普通','uncommon':'罕见','rare':'稀有','special':'特殊','starter':'初始','event':'事件','shop':'商店','ancient':'先古'}
MOVE_LABELS = {'damage':'伤害','hits':'攻击次数','block':'格挡','moveBlock':'格挡','strength':'力量','dexterity':'敏捷','vigor':'活力',
 'allyStrength':'其他敌人力量','teamStrength':'全体敌人力量','healPerPlayer':'每名玩家对应治疗量','ritual':'仪式','intangible':'无实体',
 'thornsBefore':'行动前荆棘','thornsAfter':'行动后荆棘','debuffs':'施加状态','status':'加入卡牌','statusExtra':'额外卡牌','statusPile':'加入位置','count':'数量',
 'hidden':'隐藏行动','stunned':'眩晕','sleep':'休眠','sleeping':'沉睡','revive':'复活','reviveIllusion':'复活幻象','selfKill':'自我毁灭',
 'summonEnemy':'召唤敌人','bloat':'膨胀','burrowed':'钻地','escapeEnemy':'逃跑','fabricate':'制造','flutter':'振翅','guardFabricator':'保护制造者',
 'hatchEgg':'孵化','hiveSpit':'蜂巢喷吐','intensify':'强化','land':'落地','layEggs':'产卵','liquify':'液化','plow':'犁击','ratBackup':'呼叫援鼠',
 'reattach':'重新接合','soar':'飞升','stealCard':'偷取卡牌','stealGold':'窃取金币','steam':'蒸汽','vitalSpark':'生命火花','wakeGremlin':'唤醒地精',
 'beckon':'召唤呼唤','deathBlow':'致命一击','knowledge':'知识仪式'}
MONSTER_NOTES = {
 'TestSubject':['爪击次数随战斗中的额外利爪增长。'],
 'WaterfallGiant':['压力枪和喷发伤害随战斗状态变化；此处展示基础数值。'],
 'Axebot':['启动获得的力量随复活次数增长。'],
 'TwoTailedRat':['初始招式与同伴错开，召唤援军受冷却限制。'],
 'DecimillipedeSegment':['同伴段节错开行动；受损段节能够重新接合。'],
 'PhantasmalGardener':['初始行动取决于队伍中的席位。'],
 'Fabricator':['根据场上敌人数量选择制造或攻击。'],
 'Myte':['单独出现和有同类在场时使用不同的初始行动。'],
 'Exoskeleton':['初始行动受同类席位影响，后续行动限制连续重复。'],
 'CorpseSlug':['同类错开行动。'], 'ScrollOfBiting':['同类错开行动；四名同类在场时改变初始招式。'],
}


def name_of(key):
    return CARDS[key]['name'] if key in CARDS else ENEMIES[key][0] if key in ENEMIES else power_name(key) if power_name(key)!='状态' else key


def readable(value):
    if isinstance(value, dict):
        return '、'.join(f'{MOVE_LABELS.get(k, name_of(k))} {readable(v)}' for k,v in value.items())
    if isinstance(value, list): return '；'.join(readable(v) for v in value)
    if isinstance(value, bool): return '是' if value else '否'
    if isinstance(value, str): return {**RARITIES,'discard':'弃牌堆','draw':'抽牌堆','hand':'手牌','AnyTime':'随时','CombatOnly':'仅战斗','Automatic':'自动触发','AnyPlayer':'任意玩家','AnyEnemy':'任意敌人','AllEnemies':'所有敌人','Self':'自己','None':'无'}.get(value, name_of(value))
    return str(value)


def monster_groups(key):
    groups = {KINDS_ZH.get(KINDS.get(encounter), '特殊') for encounter, members in FIXED.items() if key in members}
    return sorted(groups) or ['特殊']


def records(category):
    if category == 'cards':
        return [{'id':key, 'name':row['name'], 'group':CHARACTERS.get(row['pool'], {}).get('name', {'colorless':'无色','status':'状态','curse':'诅咒'}.get(row['pool'], '特殊')),
                 'kind':KINDS_ZH.get(row['kind'], row['kind']), 'rarity':RARITIES.get(row['rarity'], row['rarity'])} for key,row in CARDS.items()]
    if category == 'monsters':
        return [{'id':key,'name':row[0],'group':' / '.join(monster_groups(key))} for key,row in ENEMIES.items()]
    if category in ('relics', 'potions'):
        source = RELICS if category == 'relics' else POTIONS
        data=RELIC_DATA if category=='relics' else POTION_DATA
        return [{'id':key,'name':row[0], 'group':CHARACTERS.get(data.get(key,{}).get('pool'),{}).get('name', {'shared':'通用','special':'特殊'}.get(data.get(key,{}).get('pool'),'特殊')), 'rarity':RARITIES.get(data.get(key,{}).get('rarity'),'特殊')} for key,row in source.items()]
    if category == 'characters': return [{'id':key,'name':row['name'],'group':'角色'} for key,row in CHARACTERS.items()]
    raise KeyError(category)


def metadata():
    return {'version':CONTENT_VERSION, 'features':{'lobby':True,'catalog':True,'characterSetup':True,'replaceSolo':True},
            'categories':[{'id':key,'name':name,'count':len(records(key))} for key,name in CATEGORIES.items()],
            'characters':[{'id':key,**detail('characters',key)} for key in CHARACTERS],
            'ascensions':[{'level':level,'name':row[0],'description':row[1]} for level,row in enumerate(LEVELS)]}


def listing(category, query='', group='', offset=0, limit=50):
    rows = sorted(records(category), key=lambda row:row['id'])
    groups = sorted({row['group'] for row in rows})
    rows = [row for row in rows if (not group or row['group']==group) and all(part in f"{row['id']} {row['name']} {row.get('kind','')} {row.get('rarity','')}".casefold() for part in query.casefold().split())]
    return {'items':rows[offset:offset+limit], 'total':len(rows), 'offset':offset, 'limit':limit, 'groups':groups, 'version':CONTENT_VERSION}


def detail(category, key, ascension=0, upgraded=False):
    row = next((row for row in records(category) if row['id']==key), None)
    if row is None: raise KeyError(key)
    result = {**row, 'lines':[], 'links':[]}
    if category == 'cards':
        card = card_view({'id':key, 'key':key, 'upgraded':upgraded})
        result.update(card=card,name=card['name'])
        result['lines'] = [f"{row['group']} · {row['kind']} · {row['rarity']}", f"费用：[{cost_text(card)}]", card['description']]
    elif category == 'characters':
        character = CHARACTERS[key]
        result['lines'] = [f"初始生命：{character['hp']} · 金币：{character['gold']}", '初始牌组：']
        for card,count in Counter(character['deck']).items():
            result['lines'].append(f'{CARDS[card]["name"]} ×{count}')
            result['links'].append({'category':'cards','id':card,'name':CARDS[card]['name']})
        result['lines'].append('初始遗物：'+'、'.join(RELICS[relic][0] for relic in character['relics']))
        result['links'] += [{'category':'relics','id':relic,'name':RELICS[relic][0]} for relic in character['relics']]
    elif category in ('relics','potions'):
        source = RELICS if category=='relics' else POTIONS
        result['lines'] = [f"{row['group']} · {row['rarity']}", source[key][1]]
        if category=='potions':
            info=POTION_DATA.get(key,{})
            result['lines'] += [f'{label}：{readable(info[field])}' for field,label in [('rarity','稀有度'),('target','目标'),('usage','使用条件')] if field in info]
    else:
        _,low,high,moves = ENEMIES[key]
        low,high=monster_hp({'ascension':ascension},key,low,high)
        result['lines']=[f"{row['group']} · A{ascension} · 单人基础数值", f'生命：{low}–{high}', '全部招式（实际顺序由战斗阶段决定）：']
        for i,source in enumerate(moves):
            move=deepcopy(source);monster_intent({'ascension':ascension},{'key':key,'move':i},move)
            result['lines'].append(f'{i+1}. '+('；'.join(f'{MOVE_LABELS.get(field, name_of(field))}：{readable(value)}' for field,value in move.items()) or '无主动效果'))
        result['lines'] += list(monster_passives(key,ascension))
        result['lines'] += MONSTER_NOTES.get(key, [])
    return result


@lru_cache(maxsize=1188)
def monster_passives(key, ascension):
    # A disposable one-player sandbox: never reads or advances a saved run's RNG.
    from ..engine import new_run
    from ..combat.monsters import initialize
    from ..content.ascension import monster_value
    s=new_run('catalog-passives',1,'资料库','coop',ascension)
    _,low,high,_=ENEMIES[key]
    low,high=monster_hp(s,key,low,high)
    enemy={'id':'e0','key':key,'hp':low,'maxHp':low,'block':0,'powers':{},'move':0}
    s['enemies']=[enemy]
    if key=='BygoneEffigy':enemy['powers']['slow']=1
    if key in ('Vantom','Inklet'):enemy['powers']['slippery']=monster_value(s,key,'SlipperyAmt',8) if key=='Vantom' else 1
    initialize(s,enemy)
    return tuple(['初始状态（单独出现）：']+[f'{name_of(name)}：{value}' for name,value in enemy['powers'].items()]+([f"初始格挡：{enemy['block']}"] if enemy['block'] else [])) if enemy['powers'] or enemy['block'] else ()
