"""Starting cards of the four additional characters, reference v0.111.0."""


def register(card):
    for character in ('Silent','Defect','Regent','Necrobinder'):
        card('Strike'+character,'打击',1,'attack','enemy',{'damage':3},rarity='basic',pool=character.lower(),damage=6,strike=True)
        card('Defend'+character,'防御',1,'skill','self',{'block':3},rarity='basic',pool=character.lower(),block=5,defend=True)
    card('Neutralize','中和',0,'attack','enemy',{'damage':1,'weak':1},rarity='basic',pool='silent',damage=3,weak=1)
    card('Survivor','生存者',1,'skill','self',{'block':3},rarity='basic',pool='silent',block=8,discardOnly=1)
    card('Zap','电击',1,'skill','self',{'cost':-1},rarity='basic',pool='defect',channel='lightning')
    card('Dualcast','双重释放',1,'skill','self',{'cost':-1},rarity='basic',pool='defect',dualcast=True)
    card('FallingStar','陨星',0,'attack','enemy',{'damage':4},rarity='basic',pool='regent',damage=8,weak=1,vulnerable=1,starCost=2)
    card('Venerate','崇拜',1,'skill','self',{'stars':1},rarity='basic',pool='regent',stars=2)
    card('Bodyguard','护卫',1,'skill','self',{'summon':2},rarity='basic',pool='necrobinder',summon=5)
    card('Unleash','出击',1,'attack','enemy',{'damage':3},rarity='basic',pool='necrobinder',damage=6,osty=True,ostyHpDamage=True)
