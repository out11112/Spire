"""Ordered local energy-cost modifiers with explicit expiration.

Legacy fields remain readable for old fixtures; new effects append modifiers.
Global power/affliction costs are applied by the engine afterward.
"""
LEGACY=('combatCost','fixedCombatCost','untilPlayedCost','enlightenmentCombat','enlightenmentTurn','freeThisTurn','potionTurnCost','freeThisCombat')


def legacy(card):
    rows=[]
    for field in LEGACY:
        if field not in card:continue
        value=card[field]
        if (field.startswith('free') or field.startswith('enlightenment')) and not value:continue
        mode='add' if field in ('combatCost','untilPlayedCost') else 'set'
        expires=['play'] if field=='untilPlayedCost' else ['turn','play'] if field in ('enlightenmentTurn','freeThisTurn','potionTurnCost') else ['combat']
        amount=1 if field.startswith('enlightenment') else 0 if field.startswith('free') else value
        rows.append({'mode':mode,'amount':amount,'expires':expires,'reduceOnly':field.startswith('enlightenment')})
    return rows


def add(card,amount,*,mode='set',expires=('combat',),reduce_only=False):
    if 'costModifiers' not in card:card['costModifiers']=legacy(card)
    card['costModifiers'].append({'mode':mode,'amount':amount,'expires':list(expires),'reduceOnly':reduce_only})


def resolve(card,base):
    if base<0:return base
    for row in card.get('costModifiers',legacy(card)):
        changed=base+row['amount'] if row['mode']=='add' else row['amount']
        base=min(base,changed) if row['reduceOnly'] else changed
    return base


def expire(card,event):
    if 'costModifiers' in card:card['costModifiers']=[row for row in card['costModifiers'] if event not in row['expires']]


def free(card,*,combat=False):
    add(card,0,expires=('combat',) if combat else ('turn','play'))
    # These markers also drive the separate star-cost rules.
    card['freeThisCombat' if combat else 'freeThisTurn']=True
