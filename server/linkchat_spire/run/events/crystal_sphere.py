"""The crystal sphere divination grid, ported from the reference assembly.

An 11x11 grid of cells, all hidden at first except a border region around the
four corners. The items are laid out over the hidden cells, and the player
spends divinations to uncover cells until they find what they want.

Four details are load-bearing and easy to "tidy away":

* Placement scans candidate positions column-major (x outer, y inner) and draws
  an *index* into that list, so the scan order is part of the result.
* ``SetItem`` records the item but does **not** uncover the cell. An item stays
  invisible until something clears a cell it occupies.
* ``PopulateItems`` appends to the item list on every attempt. A failed attempt
  leaves its items behind, and a retry adds another full set; the reference does
  not clear between attempts, so neither does this.
* The cleared border is the four corners dilated twice by one cell
  horizontally or vertically — not diagonally, and not a square ring. That is
  24 cells, not the 75 a "two rings around each corner" reading would give.

The layout is generated once per player and kept server-side. Only the cells a
player has actually looked at may leave the server.
"""

GRID_WIDTH = 11
GRID_HEIGHT = 11

TOOL_NONE = 'None'
TOOL_SMALL = 'Small'
TOOL_BIG = 'Big'

# ``CrystalSphereItem`` subclasses, in the order ``PopulateItems`` builds them.
# ``(name, variant, size, is_good)``; the potion's size depends on its rarity
# and the gold's on whether it is the big one.
ITEMS = (
    ('Relic', None, (4, 4), True),
    ('Potion', 'common', (1, 3), True),
    ('Potion', 'common', (1, 3), True),
    ('Potion', 'rare', (2, 2), True),
    ('CardReward', 'common', (2, 2), True),
    ('CardReward', 'uncommon', (2, 2), True),
    ('CardReward', 'rare', (2, 2), True),
    ('Curse', None, (2, 2), False),
    ('Gold', False, (1, 1), True),
    ('Gold', False, (1, 1), True),
    ('Gold', False, (1, 1), True),
    ('Gold', False, (1, 1), True),
    ('Gold', False, (1, 1), True),
    ('Gold', True, (2, 1), True),
    ('Gold', True, (2, 1), True),
)

PLACEMENT_ATTEMPTS = 10


class Cell:
    """``CrystalSphereCell`` — one square, hidden until looked at."""

    __slots__ = ('x', 'y', 'hidden', 'item')

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.hidden = True
        self.item = None

    def set_item(self, item):
        """``SetItem`` records the occupant. It does not uncover the cell."""
        if self.item is not None:
            raise ValueError(f'[{self.x},{self.y}] already occupied')
        self.item = item


class Item:
    """A placed reward: its shape, where it landed, and whether it is good."""

    __slots__ = ('kind', 'variant', 'size', 'good', 'position', 'listeners')

    def __init__(self, kind, variant, size, good):
        self.kind = kind
        self.variant = variant
        self.size = size
        self.good = good
        self.position = None
        # ``PopulateItems`` subscribes ``OnItemRevealed`` to every item in the
        # list on every attempt, so a retry leaves the earlier items with two
        # subscriptions and their reveal lands in ``revealed`` twice.
        self.listeners = 0

    @property
    def cells(self):
        if self.position is None:
            return []
        x, y = self.position
        return [(x + dx, y + dy) for dx in range(self.size[0]) for dy in range(self.size[1])]

    def to_dict(self):
        return {'kind': self.kind, 'variant': self.variant,
                'size': list(self.size), 'good': self.good,
                'listeners': self.listeners,
                'position': list(self.position) if self.position else None}

    @classmethod
    def from_dict(cls, data):
        item = cls(data['kind'], data['variant'], tuple(data['size']), data['good'])
        item.position = tuple(data['position']) if data['position'] else None
        item.listeners = data['listeners']
        return item


def horizontal_cells(x, y):
    return [(x + step, y) for step in (-1, 1) if 0 <= x + step < GRID_WIDTH]


def vertical_cells(x, y):
    return [(x, y + step) for step in (-1, 1) if 0 <= y + step < GRID_HEIGHT]


def diagonal_cells(x, y):
    return [(x + dx, y + dy) for dx in (-1, 1) for dy in (-1, 1)
            if 0 <= x + dx < GRID_WIDTH and 0 <= y + dy < GRID_HEIGHT]


def adjacent_cells(x, y):
    """``GetAdjacentCells`` — the big tool's footprint, in the reference's order."""
    return (horizontal_cells(x, y) + vertical_cells(x, y)
            + diagonal_cells(x, y) + [(x, y)])


def starting_clear_region():
    """The corners, dilated twice along the axes. Diagnostics and tests read it."""
    cleared = set()
    current = [(0, 0), (GRID_WIDTH - 1, 0), (GRID_WIDTH - 1, GRID_HEIGHT - 1), (0, GRID_HEIGHT - 1)]
    for _ in range(2):
        expanded = list(current)
        for x, y in current:
            expanded += horizontal_cells(x, y)
            expanded += vertical_cells(x, y)
        current = expanded
    cleared.update(current)
    return cleared


def build_grid():
    grid = [[Cell(x, y) for y in range(GRID_HEIGHT)] for x in range(GRID_WIDTH)]
    for x, y in starting_clear_region():
        grid[x][y].hidden = False
    return grid


def can_place_here(grid, size, x, y):
    """``CanPlaceHere`` — in bounds, still hidden, and empty."""
    for dx in range(size[0]):
        for dy in range(size[1]):
            gx, gy = x + dx, y + dy
            if not (0 <= gx < GRID_WIDTH and 0 <= gy < GRID_HEIGHT):
                return False
            cell = grid[gx][gy]
            if not cell.hidden or cell.item is not None:
                return False
    return True


def candidate_positions(grid, size):
    """Positions the item fits, in the reference's scan order: x outer, y inner."""
    return [(x, y) for x in range(GRID_WIDTH) for y in range(GRID_HEIGHT)
            if can_place_here(grid, size, x, y)]


def place_item(game, item):
    """``CrystalSphereItem.PlaceItem`` — one draw, or nothing if it will not fit."""
    candidates = candidate_positions(game.grid, item.size)
    if not candidates:
        return False
    item.position = game.rng.next_item(candidates)
    for x, y in item.cells:
        game.grid[x][y].set_item(item)
    return True


def populate_items(game):
    """``PopulateItems`` — every item in turn, all-or-nothing.

    Items are appended as they are built, before the result is known, so a
    failed attempt leaves its items in the list. A retry adds another full set.
    That is the reference's behaviour and is reproduced rather than corrected.
    """
    placed = True
    for kind, variant, size, good in ITEMS:
        item = Item(kind, variant, size, good)
        placed = place_item(game, item) and placed
        game.items.append(item)
    for item in game.items:
        item.listeners += 1
    return placed


class Minigame:
    """One player's divination board and how many looks they have left."""

    def __init__(self, rng, divinations):
        self.rng = rng
        self.grid = build_grid()
        self.items = []
        self.revealed = []
        self.divinations = divinations
        self.tool = TOOL_BIG
        self.placed_all_items = False
        attempts = 0
        while True:
            self.placed_all_items = populate_items(self)
            attempts += 1
            if self.placed_all_items or attempts >= PLACEMENT_ATTEMPTS:
                break

    @property
    def finished(self):
        return self.divinations == 0

    def set_tool(self, tool):
        self.tool = tool

    def all_occupied_cells_clear(self, item):
        """``AreAllOccupiedCellsClear`` — an item is found once every cell shows."""
        return all(not self.grid[x][y].hidden for x, y in item.cells)

    def clear_cell(self, x, y):
        """``ClearCell`` — uncover one cell, finding its item if that completes it.

        Returns the items this call revealed, in order.
        """
        if not (0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT):
            raise ValueError(f'[{x},{y}] is not a valid cell on this grid')
        cell = self.grid[x][y]
        if not cell.hidden:
            return []
        cell.hidden = False
        found = []
        if cell.item is not None and self.all_occupied_cells_clear(cell.item):
            found = self._reveal(cell.item)
        return found

    def _reveal(self, item):
        """``RevealItem`` — one entry per subscription, so retries can double up."""
        landed = [item] * item.listeners
        self.revealed.extend(landed)
        return landed

    def cell_clicked(self, x, y):
        """``CellClicked`` — spend one divination, then uncover per the tool.

        The divination is spent even when it uncovers nothing the player has not
        already seen; ``ClearCell`` is what is idempotent, not the click.
        """
        self.divinations -= 1
        targets = [(x, y)] if self.tool != TOOL_BIG else adjacent_cells(x, y)
        found = []
        for cx, cy in targets:
            found.extend(self.clear_cell(cx, cy))
        return found

    def hidden_cells(self):
        return sum(1 for column in self.grid for cell in column if cell.hidden)

    def visible_board(self):
        """What one player may be shown: uncovered cells and the items on them."""
        return [{'x': cell.x, 'y': cell.y,
                 'item': (cell.item.kind if cell.item else None),
                 'variant': (cell.item.variant if cell.item else None),
                 'good': (cell.item.good if cell.item else None)}
                for column in self.grid for cell in column if not cell.hidden]

    def to_dict(self):
        """The saved board. Kept server-side; only ``visible_board`` may ship."""
        return {
            'divinations': self.divinations,
            'tool': self.tool,
            'placedAllItems': self.placed_all_items,
            'items': [item.to_dict() for item in self.items],
            # Indices into ``items``, because the same item can be revealed
            # twice after a retry and a key would collapse those into one.
            'revealed': [self.items.index(item) for item in self.revealed],
            'cells': [[cell.hidden for cell in column] for column in self.grid],
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild a saved board without drawing anything.

        The board is stored rather than replayed from its stream so that a
        reload, a reconnect or a retry can never lay the items out again.
        """
        game = cls.__new__(cls)
        game.rng = None
        game.grid = build_grid()
        for x, column in enumerate(data['cells']):
            for y, hidden in enumerate(column):
                game.grid[x][y].hidden = hidden
        game.items = [Item.from_dict(row) for row in data['items']]
        game.revealed = [game.items[index] for index in data['revealed']]
        for item in game.items:
            for x, y in item.cells:
                game.grid[x][y].item = item
        game.divinations = data['divinations']
        game.tool = data['tool']
        game.placed_all_items = data['placedAllItems']
        return game
