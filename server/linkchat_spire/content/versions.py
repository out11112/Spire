"""What a saved run and a client must agree on, and the phases a run can be in."""
RULES_VERSION = 'spire-tui-4'
CONTENT_VERSION = '0.1.0-alpha.2.dev17'
SCHEMA_VERSION = 3
PROTOCOL_VERSION = 8
# The phases a run can be in. The TUI keeps the same list as its screen
# vocabulary, so a phase has to be added on both sides: the projection is the
# only channel between the rules and the client, and a client that does not
# know a phase cannot render the state it arrives in.
PHASES = ('lobby', 'map', 'combat', 'reward', 'rest', 'shop', 'event', 'treasure', 'actComplete', 'ending', 'victory', 'defeat', 'abandoned')
