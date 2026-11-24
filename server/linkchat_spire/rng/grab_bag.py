"""Port of ``MegaCrit.Sts2.Core.Helpers.GrabBag``.

A weighted bag that removes what it hands out and, when it empties, is refilled
from the full pool. Two details drive every encounter schedule in the game and
are easy to "improve" by accident:

* Selection is a linear scan over the *insertion order*, returning the first
  entry whose running total passes the roll — not a sorted-by-weight draw.
* A predicate does not filter the bag. It re-rolls until the drawn entry passes,
  so a restrictive predicate burns many draws.

The running total accumulates in binary64, and the weight added is the caller's
value; the original's ``double`` overload is what everything uses.
"""


class GrabBag:
    __slots__ = ('_entries', '_total')

    def __init__(self):
        self._entries = []
        self._total = 0.0

    def __len__(self):
        return len(self._entries)

    def __bool__(self):
        return bool(self._entries)

    def add(self, element, weight):
        self._entries.append((element, weight))
        self._total += weight

    def any(self):
        return bool(self._entries)

    def grab(self, rng, predicate=None):
        index = self._index(rng, predicate)
        return None if index < 0 else self._entries[index][0]

    def grab_and_remove(self, rng, predicate=None):
        index = self._index(rng, predicate)
        if index < 0:
            return None
        element = self._entries[index][0]
        self._remove(index)
        return element

    def _index(self, rng, predicate):
        if predicate is not None and not any(predicate(element) for element, _ in self._entries):
            return -1
        while True:
            index = self._weighted_index(rng)
            if index < 0 or predicate is None or predicate(self._entries[index][0]):
                return index

    def _weighted_index(self, rng):
        target = rng.next_double() * self._total
        running = 0.0
        for index, (_, weight) in enumerate(self._entries):
            running += weight
            if target < running:
                return index
        return -1

    def _remove(self, index):
        self._total -= self._entries[index][1]
        del self._entries[index]
