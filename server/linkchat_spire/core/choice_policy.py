"""Phase actions admitted while another player owns a suspended task.

These sets are an admission policy, not rule validation: engine._apply still
checks ownership, prices, targets, inventory and the current phase.
"""
import os

REWARDS = frozenset(('goldReward', 'customReward', 'customRelicReward',
                     'claimPotion', 'skipPotion', 'potion', 'dropPotion'))
PHASE_ACTIONS = {
    'combat': REWARDS | {'play', 'end', 'undoEnd'},
    'event': REWARDS | {'event', 'sphere'},
    'rest': REWARDS | {'rest', 'continue'},
    'shop': REWARDS | {'buy', 'removeCard', 'continue'},
    'treasure': REWARDS | {'treasurePick', 'continue'},
    'reward': REWARDS | {'reward', 'rewardRemove', 'skipRemoval'},
}


def enabled():
    return os.environ.get('SPIRE_INDEPENDENT_CHOICES', '1').lower() not in ('0', 'false', 'off')


def actions(state):
    if state.get('phase') == 'combat':
        from ..engine import turn_is_resolving
        if turn_is_resolving(state):
            return frozenset()
    return PHASE_ACTIONS.get(state.get('phase'), frozenset())
