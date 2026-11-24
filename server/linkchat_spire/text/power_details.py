"""Values that fill the official status wording in the projection.

The official templates (``official_power_descriptions.json``) name values the
stack count alone cannot supply: another card's damage, the applier's name, a
percentage. This module reads them from the run state without changing it.
Each status maps to one value set per instance; ``Amount`` is included when
the official amount differs from the projected stack (per-instance statuses).
"""


def _name(state, creature_id):
    player = state['players'].get(str(creature_id))
    if player:
        return player['name']
    return next((e['name'] for e in state['enemies'] if e['id'] == creature_id), '')


def _names(state, ids):
    return '、'.join(name for name in (_name(state, i) for i in ids) if name)


def _vulnerable_increase(state, creature, viewer):
    # Enemies are attacked by players; the viewer's own modifiers apply.
    if creature in state['enemies'] and viewer is not None:
        increase = 50 + viewer['powers'].get('cruelty', 0) + (25 if 'PaperPhrog' in viewer.get('relics', []) else 0)
    else:
        increase = 50
    return increase * 2 if creature['powers'].get('debilitate') else increase


def details(state, creature, uid=None):
    powers = creature.get('powers', {})
    viewer = state['players'].get(str(uid)) if uid is not None else None
    records = creature.get('colorless', {})
    out = {}

    def put(key, *rows):
        if powers.get(key) and rows:
            out[key] = [dict(row) for row in rows]

    put('bomb', *({'Amount': r['left'], 'Damage': r['damage']} for r in records.get('bomb', [])))
    put('automation', *({'Amount': r['energy'], 'BaseCards': 10} for r in records.get('automation', [])))
    put('panache', *({'Amount': r['damage'], 'CardsLeft': r['left']} for r in records.get('panache', [])))
    put('rollingBoulder', *({'Amount': r['damage'], 'Damage': 5} for r in records.get('rollingBoulder', [])))
    put('cacophony', *({'Amount': r['damage'], 'Cards': r['left']} for r in creature.get('cacophonyInstances', [])))
    put('orbit', *({'Amount': r['amount'], 'Energy': 4} for r in creature.get('orbitInstances', [])))
    put('toricToughness', *({'Amount': r['left'], 'Block': r['block']} for r in creature.get('toricInstances', [])))
    put('nightmare', *({'Amount': r['amount'], 'Card': _card_name(r['card'])} for r in creature.get('nightmareInstances', [])))
    put('imitationLearning', *({'Amount': count, 'TargetPlayer': _name(state, target)}
                               for target, count in creature.get('imitationTargets', {}).items() if count > 0))
    put('soulbound', *({'Amount': r['amount'], 'ApplierName': _name(state, r['owner'])}
                       for r in creature.get('soulboundInstances', [])))
    put('covered', {'Applier': _names(state, creature.get('coverSources', []))})
    put('intercept', {'Covering': _names(state, creature.get('covering', []))})
    if powers.get('guarded'):
        put('guarded', {'DamageDecrease': round((1 - 0.5 ** powers['guarded']) * 100),
                        'Applier.StringValue': _names(state, creature.get('guardians', []))})
    put('crabRage', {'StrengthPower': 6, 'Block': 99})
    put('crimsonMantle', {'SelfDamage': creature.get('crimsonMantleLoss', 1)})
    put('inferno', {'SelfDamage': creature.get('infernoLoss', 1)})
    put('danseMacabre', {'Energy': 2})
    put('radiance', {'Energy': 1})
    put('paleBlueDot', {'CardPlay': 5})
    put('plating', {'Decrement': 1})
    put('galvanic', {'AfflictionTitle': '流电'})
    for key in ('colossus', 'flutter', 'soar'):
        put(key, {'DamageDecrease': 50})
    put('tank', {'DamageIncrease': 50, 'DamageDecrease': 50})
    put('shrink', {'DamageDecrease': 30})
    put('vulnerable', {'DamageIncrease': _vulnerable_increase(state, creature, viewer)})
    if powers.get('slow'):
        put('slow', {'SlowAmount': creature.get('slowCards', 0) * 10, 'DisplayAmount': creature.get('slowCards', 0) * 10})
    return out


def _card_name(card):
    from ..engine import definition
    return definition(card)['name']
