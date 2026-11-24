"""Explicit content rules checked against reference v0.111.0.
Text is written for the TUI. This is a simulation, not an original-game save format.
"""
from .versions import RULES_VERSION, CONTENT_VERSION, SCHEMA_VERSION, PROTOCOL_VERSION, PHASES
from .cards.base import CARDS, card, definition, card_view, cost_text
from .cards.colorless import register as register_colorless
from .cards import curses, ironclad

# Registration order is observable (reward pools, catalog order), so the
# pieces run in the order the single module used to execute them.
ironclad.register_starter(card)
curses.register_generated(card)
REWARDS = [k for k,v in CARDS.items() if v['kind'] not in ('status','curse') and k not in ('StrikeIronclad','DefendIronclad','Bash')]
from .relics import RELICS
from .potions import POTIONS
curses.register(card)
ironclad.register(card, CARDS)
register_colorless(card)
from .cards.silent import register as register_foreign
register_foreign(card)
from .cards.defect import register as register_defect
register_defect(card)
from .cards.regent import register as register_regent
register_regent(card)
from .cards.necrobinder import register as register_necrobinder
register_necrobinder(card)
from .cards.starting import register as register_starting
register_starting(card)
from .cards.special import register as register_special
register_special(card)
CARDS['DefendIronclad']['values']['defend']=True
REWARDS[:]=[k for k,d in CARDS.items() if d['pool']=='ironclad' and d['rarity'] in ('common','uncommon','rare')]
from ..text.official import render as _official_description
RELICS.update({key:(name,_official_description('relic',key,old=summary) or summary)
               for key,(name,summary) in RELICS.items()})
POTIONS.update({key:(name,_official_description('potion',key,old=summary) or summary)
                for key,(name,summary) in POTIONS.items()})

__all__ = ['RULES_VERSION', 'CONTENT_VERSION', 'SCHEMA_VERSION', 'PROTOCOL_VERSION', 'PHASES',
           'CARDS', 'REWARDS', 'RELICS', 'POTIONS', 'card', 'definition', 'card_view', 'cost_text']
