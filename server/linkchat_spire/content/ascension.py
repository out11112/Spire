"""Cumulative ascension rules for reference v0.111.0 (all levels available)."""
# Official titles and descriptions (ascension.json).
LEVELS = [
    ('无进阶','在没有任何进阶调整的影响下游玩。'), ('精英蜂拥','精英敌人出现更加频繁。'),
    ('旅途劳顿','先古之民只会回复你已损失生命值的80%。'),
    ('贫穷','敌人和宝箱掉落的金币减少25%。'), ('收紧腰带','游戏开始时药水栏位减少1。'),
    ('进阶之灾','游戏开始时被诅咒。'), ('通货膨胀','商人的卡牌移除服务价格提升。'),
    ('稀缺','稀有和已升级卡牌更少出现。'),
    ('强韧敌人','所有的敌人变得更难杀死。'),
    ('致命敌人','所有的敌人变得更加致命。'),
    ('双重Boss','在第3阶段最后与两个Boss战斗。'),
]

def level(state):return state.get('ascension',0)
def enabled(state,threshold):return level(state)>=threshold

def gold_range(state,kind):
    low,high={'boss':(100,100),'elite':(35,45)}.get(kind,(10,20))
    if enabled(state,3):low,high=int(low*.75),int(high*.75)
    return low,high+1

# Scalar parameters read from the reference model properties; bindings are explicit.
from .data import load as load_data
MONSTERS=load_data('ascension_monsters.json')

def monster_value(state,key,name,fallback):
    rule=MONSTERS.get(key,{}).get('values',{}).get(name)
    return rule[2] if rule and enabled(state,rule[0]) else fallback

def monster_hp(state,key,low,high):
    if not enabled(state,8):return low,high
    row=MONSTERS.get(key,{}).get('hp',{})
    index=2 if enabled(state,9) else 1
    return row.get('MinInitialHp',[low]*3)[index],row.get('MaxInitialHp',[high]*3)[index]

def monster_intent(state,monster,intent):
    for field,name in MONSTERS.get(monster['key'],{}).get('moves',{}).get(str(monster['move']),{}).items():
        intent[field]=monster_value(state,monster['key'],name,intent[field])

