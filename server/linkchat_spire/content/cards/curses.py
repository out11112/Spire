"""Generated statuses and curses."""


def register_generated(card):
    # Generated encounter/curse cards are outside the collectible thirty-card pool.
    card('Wound','伤口',99,'status',unplayable=True)
    card('Dazed','晕眩',99,'status',unplayable=True,ethereal=True)
    card('Guilty','愧疚',99,'curse',unplayable=True)


def register(card):
    # Curse and status pools are never mixed into normal card rewards.
    card('AscendersBane','进阶之灾',-1,'curse',unplayable=True,eternal=True,ethereal=True,noModifierGenerate=True)
    card('BadLuck','霉运',-1,'curse',unplayable=True,eternal=True,endHpLoss=13,noModifierGenerate=True)
    card('Clumsy','笨拙',-1,'curse',unplayable=True,ethereal=True)
    card('CurseOfTheBell','铃铛的诅咒',-1,'curse',unplayable=True,eternal=True,noModifierGenerate=True)
    card('Debt','债务',-1,'curse',unplayable=True,endGoldLoss=10)
    card('Decay','腐朽',-1,'curse',unplayable=True,endDamage=2)
    card('Doubt','疑虑',-1,'curse',unplayable=True,endWeak=True)
    card('Enthralled','执迷',2,'curse',eternal=True,enthralled=True,noModifierGenerate=True)
    card('Folly','愚行',-1,'curse',unplayable=True,eternal=True,innate=True,ethereal=True,noModifierGenerate=True)
    card('Greed','贪婪',-1,'curse',unplayable=True,eternal=True,noModifierGenerate=True)
    card('Guilty','愧疚',-1,'curse',unplayable=True)
    card('Injury','受伤',-1,'curse',unplayable=True)
    card('Normality','凡庸',-1,'curse',unplayable=True,normality=True)
    card('PoorSleep','睡眠不佳',-1,'curse',unplayable=True,retain=True,noModifierGenerate=True)
    card('Regret','悔恨',-1,'curse',unplayable=True,regret=True)
    card('Shame','羞耻',-1,'curse',unplayable=True,endFrail=True)
    card('SporeMind','孢子心灵',1,'curse',exhaust=True,noModifierGenerate=True)
    card('Writhe','苦恼',-1,'curse',unplayable=True,innate=True)
    card('Beckon','呼唤',1,'status',endHpLoss=6)
    card('Burn','灼伤',-1,'status',unplayable=True,endDamage=2)
    card('Dazed','晕眩',-1,'status',unplayable=True,ethereal=True)
    card('Debris','碎屑',1,'status',exhaust=True)
    card('FranticEscape','狂乱逃离',1,'status',franticEscape=True)
    card('Infection','感染',-1,'status',unplayable=True,endDamage=3)
    card('Slimed','黏液',1,'status',draw=1,exhaust=True)
    card('Soot','煤灰',-1,'status',unplayable=True)
    card('Toxic','毒素',1,'status',exhaust=True,endDamage=5)
    card('Void','虚空',-1,'status',unplayable=True,ethereal=True,drawEnergyLoss=1)
    card('Wither','凋萎',-1,'status',unplayable=True,endDamage=3)
    card('Wound','伤口',-1,'status',unplayable=True)
