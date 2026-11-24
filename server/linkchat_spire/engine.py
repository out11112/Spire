"""Deterministic, I/O-free rules. Every action runs on a copy and either commits whole or fails.

The rules that used to live in this module now live in ``core/`` (run state,
actions, the view), ``combat/`` (piles, damage, battle flow, playing a card)
and ``rng/draws.py``. This module stays as the one name the rest of the
package, the service and the tests import as ``engine`` / ``e``.

It holds no rules of its own. Reading ``engine.draw`` returns the current
``combat.piles.draw``; setting it -- which is what ``unittest.mock.patch``
does -- sets it on ``combat.piles``, so a patch through this module reaches
every caller, including the bare calls inside the owning module.
"""
import sys
import types

from .rng import draws as _draws
from .core import errors as _errors, state as _state, actions as _actions, view as _view
from .combat import piles as _piles, damage as _damage, battle as _battle, play as _play
# Imported by the old module although no rule here uses them any more.
from .content import REWARDS  # noqa: F401
from .content.characters import STARTER_RELICS  # noqa: F401

# Search order for a name. A rule function is defined in exactly one of these;
# a name engine used to import (CARDS, deepcopy, ...) resolves to the first
# module that imports it, which is the same object.
_HOMES = (_errors, _state, _draws, _piles, _damage, _battle, _play, _actions, _view)

_OWNER = {}
for _module in _HOMES:
    for _name, _value in vars(_module).items():
        # The split modules refer to each other by module (piles.draw); those
        # bindings are not engine names.
        if not _name.startswith('__') and _value not in _HOMES:
            _OWNER.setdefault(_name, _module)
del _module, _name, _value
# ``from engine import *`` exports what it did before the split: every public
# name, including the ones the old module imported.
__all__ = sorted({name for name in _OWNER if not name.startswith('_')} | {'REWARDS', 'STARTER_RELICS'})


class _Facade(types.ModuleType):

    def __getattr__(self, name):
        owner = _OWNER.get(name)
        if owner is None or name not in vars(owner):
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
        return vars(owner)[name]

    def __setattr__(self, name, value):
        owner = _OWNER.get(name)
        if owner is None:
            super().__setattr__(name, value)
        else:
            setattr(owner, name, value)

    def __delattr__(self, name):
        owner = _OWNER.get(name)
        if owner is None:
            super().__delattr__(name)
        else:
            delattr(owner, name)

    def __dir__(self):
        return sorted(set(super().__dir__()) | set(_OWNER))


sys.modules[__name__].__class__ = _Facade
