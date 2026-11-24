"""Read-only current-state attack previews, never a speculative play/draw/RNG run.

Damage is the first hit before block, not a promise of HP loss or a simulated
whole combo. Subsequent hits, replays, random targets and triggered powers can
change it. The actual attack and preview share base damage and multiplier code.
"""
from copy import deepcopy


def hit_count(state, player, card, target, x_value, stars):
    from .. import engine as e
    from ..combat.classes.defect import combat_cards
    v = e.definition(card)['values']
    hits = x_value if v.get('xCost') else v.get('hits', 1)
    for key, counter in (('finisher', 'attacksFinished'), ('lunarBlast', 'skillsFinished'),
                         ('radiate', 'starsGainedThisTurn'), ('etherealHits', 'etherealPlays')):
        if v.get(key): hits = player.get(counter, 0)
    if v.get('rattle'): hits = 1 + player.get('ostyAttacks', 0)
    if v.get('starX'): hits = stars + (2 if 'ChemicalX' in player['relics'] else 0)
    if v.get('doubleXAt') and x_value >= v['doubleXAt']: hits *= 2
    if v.get('flechettes'): hits = sum(e.definition(c)['kind'] == 'skill' for c in player['hand'] if c['id'] != card['id'])
    if v.get('barrage'): hits = len(player.get('orbs', []))
    # At the attack boundary energySpentThisTurn already includes this play.
    if v.get('helixDrill'): hits = max(0, player.get('energySpentThisTurn', 0) - e.energy_cost(state, player, card))
    if v.get('flakCannon'):
        exhausted = {c['id'] for c in player['exhaust']}
        hits = len({c['id'] for c in combat_cards(state, player) if e.CARDS[c['key']]['kind'] == 'status' and c['id'] not in exhausted})
    if v.get('dismantle') and target['powers'].get('vulnerable'): hits = 2
    if v.get('spite'): hits = v['spite'] if player.get('hpLostThisTurn') else 1
    if v.get('tearAsunder'): hits = 1 + player.get('hpLossCount', 0)
    if v.get('minimumExhaust') and len(player['exhaust']) < v['minimumExhaust']: hits = 0
    if v.get('fiendFire'): hits = sum(c['id'] != card['id'] for c in player['hand'])
    if v.get('osty') and not player.get('osty', {}).get('hp', 0): hits = 0
    return max(0, hits)


def damage_by_target(state, player, card):
    from .. import engine as e
    d = e.combat_definition(player, card)
    if d['kind'] != 'attack': return None
    v = d['values']
    # Only copy public actor information. Never play a card or inspect the next
    # random result to construct a preview; projection must not consume RNG.
    p = deepcopy(player)
    c = deepcopy(card)
    cost = e.energy_cost(state, player, card)
    c['paidEnergy'] = cost
    p['energySpentThisTurn'] = p.get('energySpentThisTurn', 0) + cost
    if 'PenNib' in p['relics'] and (p.get('penNibAttacks', 0) + 1) % 10 == 0:
        p['penNibCard'] = c['id']
    if p['powers'].get('gigantification') and not p.get('gigantificationCard'):
        p['gigantificationCard'] = c['key']
    x_value = player['energy'] + (2 if v.get('xCost') and 'ChemicalX' in p['relics'] else 0)
    stars = e.star_cost(player, card)
    actor = p.get('osty') if v.get('osty') else p
    lethality = p['powers'].get('lethality', 0) if not p.get('attacksPlayed') else 0
    result = {}
    for target in state['enemies']:
        if target['hp'] <= 0: continue
        hits = hit_count(state, p, c, target, x_value, stars)
        amount = e.damage_amount(actor, target, e.attack_base(p, c, target, state),
                                 card_key=c['key'], controller=p, lethality=lethality,
                                 card_instance=c) if actor and actor['hp'] > 0 and hits else 0
        result[str(target['id'])] = {'damage': amount, 'hits': hits}
    return result
