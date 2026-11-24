"""Read-only previews: what a card would look like, and what a teammate holds.

Nothing in this module may commit anything. A preview that changed a card, the
log, a pending reward, the RNG or the save would be a bug, so the "after" is
always computed on a copy and the copy is what makes that impossible rather
than merely unlikely.

The client keeps no second upgrade table: the after-view comes from the same
value path a real upgrade takes, so a preview cannot disagree with the thing it
is previewing.
"""
from copy import deepcopy

from .. import engine as e

# ``GET /rooms/{id}/players/{playerId}/inspection`` pages its rows; a deck of
# forty is the size the plan fixes as the default.
INSPECTION_PAGE_SIZE = 40

# The piles an inspection walks, in the order a reader expects to see them.
INSPECTION_PILES = ('deck',)


def upgrade_preview(player, card_id, source, *, state=None):
    """``CardPreviewMode.Upgrade``: the card before and after, without the after.

    The copy is upgraded through the ordinary ``upgrade`` path, so anything that
    path changes -- the cost floor, the added keywords, the enchantment's own
    modifiers -- shows up here for free and stays in step with it.
    """
    e.require(source in ('deck','hand','draw','discard','exhaust','reward','shop'),'卡牌来源无效。')
    sources=[player.get(source,[])] if source!='shop' else []
    if source=='reward':sources.extend(reward.get('cards',[]) for reward in player.get('pendingCardRewards',[]))
    if source=='shop':sources.extend([item['card']] for item in player.get('shop',[]) if item.get('kind')=='card')
    card=next((card for cards in sources for card in cards if card.get('id')==card_id),None)
    e.require(card is not None,'卡牌不存在。')
    e.require(e.upgradable(card), '这张牌不能升级。')
    preview = deepcopy(card)
    e.upgrade(preview)
    def project(value):
        if state is not None and state.get('phase')=='combat' and source in ('hand','draw','discard','exhaust'):
            return e.combat_card_view(state,player,value)
        return e.card_view(value,owner=player)
    return {'card':card_id,'before':project(card),'after':project(preview)}


def upgrade_snapshot(player, state):
    """Current-instance previews sent with the private player projection."""
    sources={key:list(player.get(key,[])) for key in ('deck','hand','draw','discard','exhaust','reward')}
    sources['reward'].extend(card for reward in player.get('pendingCardRewards',[]) for card in reward.get('cards',[]))
    sources['shop']=[item['card'] for item in player.get('shop',[]) if item.get('kind')=='card']
    result={}
    for source,cards in sources.items():
        rows={}
        for card in cards:
            if card['id'] not in rows and e.upgradable(card):
                rows[card['id']]=upgrade_preview(player,card['id'],source,state=state)
        result[source]=rows
    return result


def card_rows(cards):
    rows = []
    for card in cards:
        view = e.card_view(card)
        rows.append({'id': card['id'], 'key': card['key'], 'upgraded': bool(card.get('upgraded')),
                     'name': view['name'], 'cost': view['cost'], 'description': view['description']})
    return rows


def inspection(target):
    """What one player may read about another, as one flat paged list.

    Read-only by construction: it builds rows from the target's own state and
    returns them. It takes no viewer, so it cannot leak anything the target
    would not show, and it never writes, so looking cannot change what is seen.
    """
    rows = []
    for pile in INSPECTION_PILES:
        for row in card_rows(target.get(pile, [])):
            rows.append({**row, 'pile': pile})
    for key in target.get('relics', []):
        name, description = e.RELICS.get(key, (key, '效果尚未实现'))
        rows.append({'id': 'relic:' + key, 'pile': 'relics', 'key': key,
                     'name': name, 'description': description})
    for item in target.get('potions', []):
        name, description = e.POTIONS.get(item['key'], (item['key'], ''))
        rows.append({'id': 'potion:' + item['id'], 'pile': 'potions', 'key': item['key'],
                     'name': name, 'description': description})
    for key, amount in sorted(target.get('powers', {}).items()):
        # Powers are projected as raw keys everywhere else, so the client labels
        # them from its own vocabulary rather than the server inventing a name.
        rows.append({'id': 'power:' + key, 'pile': 'status', 'key': key, 'amount': amount})
    return {
        'player': target['id'],
        'name': target['name'],
        'character': target['character'],
        'hp': target['hp'],
        'maxHp': target['maxHp'],
        'gold': target['gold'],
        'total': len(rows),
        'pageSize': INSPECTION_PAGE_SIZE,
        'rows': rows,
    }


def page(rows, page_number=0, size=INSPECTION_PAGE_SIZE):
    """One page of rows. Out-of-range pages come back empty rather than failing."""
    e.require(isinstance(page_number, int) and page_number >= 0, '页码无效。')
    e.require(isinstance(size, int) and 1 <= size <= 200, '每页数量无效。')
    start = page_number * size
    return rows[start:start + size]
